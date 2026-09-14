import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app as fastapi_app
from app.database.base import Base
from app.database.session import get_db
import app.models # noqa: F401

TEST_DB_FILE = "./test_study_companion.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

import app.database.session as app_db_session
import app.services.material_service as mat_service

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    app_db_session.SessionLocal = TestingSessionLocal
    mat_service.SessionLocal = TestingSessionLocal
    for f in [TEST_DB_FILE, f"{TEST_DB_FILE}-wal", f"{TEST_DB_FILE}-shm"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass
    Base.metadata.create_all(bind=test_engine)
    yield
    try:
        Base.metadata.drop_all(bind=test_engine)
    except Exception:
        pass
    for f in [TEST_DB_FILE, f"{TEST_DB_FILE}-wal", f"{TEST_DB_FILE}-shm"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass


@pytest.fixture(autouse=True)
def clean_tables_between_tests():
    yield
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()

@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def user_a_headers(client):
    # Register and get auth token for User A
    res = client.post("/auth/register", json={
        "name": "Alice Developer",
        "email": "alice@example.com",
        "password": "password123"
    })
    assert res.status_code == 201
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def user_b_headers(client):
    # Register and get auth token for User B
    res = client.post("/auth/register", json={
        "name": "Bob Student",
        "email": "bob@example.com",
        "password": "password123"
    })
    assert res.status_code == 201
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
