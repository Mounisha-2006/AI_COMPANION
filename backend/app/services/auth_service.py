import logging
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token

logger = logging.getLogger("app.services.auth")

class AuthService:
    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> Tuple[User, str]:
        clean_email = user_in.email.lower().strip()
        logger.info(f"Registration attempt for email='{clean_email}'")
        
        # Check if email is already registered
        existing_user = db.query(User).filter(User.email == clean_email).first()
        if existing_user:
            logger.warning(f"Registration rejected: email='{clean_email}' already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )
        
        # Hash password and create user
        hashed_pw = hash_password(user_in.password)
        db_user = User(
            name=user_in.name.strip(),
            email=clean_email,
            password_hash=hashed_pw,
            role=user_in.role or "user"
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        logger.info(f"Registration successful for user_id={db_user.id}, email='{clean_email}', role='{db_user.role}'")

        # Generate JWT token
        token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email, "role": db_user.role})
        return db_user, token

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[Tuple[User, str]]:
        clean_email = email.lower().strip()
        logger.info(f"Authentication attempt for email='{clean_email}'")

        user = db.query(User).filter(User.email == clean_email).first()
        if not user:
            logger.warning(f"Authentication failed: user not found for email='{clean_email}'")
            return None
        
        if not verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password for user_id={user.id}, email='{clean_email}'")
            return None
        
        logger.info(f"Authentication successful for user_id={user.id}, email='{clean_email}', role='{user.role}'")
        token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
        return user, token


    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
