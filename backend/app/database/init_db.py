import sys
from sqlalchemy import inspect, text
from app.database.base import Base
from app.database.session import engine
# Import all models to ensure they are registered with Base.metadata
import app.models # noqa: F401

def init_db():
    print(f"Initializing database at: {engine.url}")
    Base.metadata.create_all(bind=engine)

    # Safe SQLite column migration helper for local dev
    try:
        inspector = inspect(engine)
        if "concept_masteries" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("concept_masteries")]
            if "previous_score" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE concept_masteries ADD COLUMN previous_score FLOAT DEFAULT 0.0;"))
                print("Migrated: Added missing previous_score to concept_masteries.")

        if "document_chunks" in inspector.get_table_names():
            chunk_cols = [col["name"] for col in inspector.get_columns("document_chunks")]
            if "chunk_type" not in chunk_cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE document_chunks ADD COLUMN chunk_type VARCHAR(50) DEFAULT 'text';"))
                print("Migrated: Added missing chunk_type to document_chunks.")
            if "metadata_json" not in chunk_cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE document_chunks ADD COLUMN metadata_json JSON;"))
                print("Migrated: Added missing metadata_json to document_chunks.")
    except Exception as e:
        print(f"Migration notice: {e}")

    # Ensure default admin account exists
    try:
        from app.database.session import SessionLocal
        from app.models.user import User
        from app.core.security import hash_password

        db = SessionLocal()
        admin_user = db.query(User).filter(User.role.in_(["ADMIN", "admin"])).first()
        if not admin_user:
            admin_account = User(
                name="System Administrator",
                email="admin@ai-study.edu",
                password_hash=hash_password("AdminPassword123!"),
                role="ADMIN"
            )
            db.add(admin_account)
            db.commit()
            print("Seeded default admin user: admin@ai-study.edu / AdminPassword123!")
        db.close()
    except Exception as e:
        print(f"Admin seeding notice: {e}")

    print("Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
