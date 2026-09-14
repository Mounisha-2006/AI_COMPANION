import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService
from app.models.user import User
from app.routers.deps import get_current_user

logger = logging.getLogger("app.routers.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account with secure password hashing,
    returning an access token and user info.
    """
    try:
        user, token = AuthService.register_user(db=db, user_in=user_in)
        logger.info(f"Successfully registered and generated token for user_id={user.id}")
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error during registration for email='{user_in.email.lower().strip()}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during account registration."
        )

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email and password, returning JWT access token.
    """
    clean_email = login_data.email.lower().strip()
    logger.info(f"POST /auth/login request received for email='{clean_email}'")
    try:
        auth_result = AuthService.authenticate_user(
            db=db,
            email=clean_email,
            password=login_data.password
        )
        if not auth_result:
            logger.info(f"Login failed (401) for email='{clean_email}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user, token = auth_result
        logger.info(f"Login successful (200) for user_id={user.id}, email='{user.email}'")
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error during login for email='{clean_email}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your login request."
        )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get profile information of the currently authenticated user.
    """
    return current_user
