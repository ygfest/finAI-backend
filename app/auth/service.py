from datetime import timedelta, datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4
from fastapi import Depends
from passlib.context import CryptContext
import jwt
from jwt import PyJWTError
from sqlalchemy.orm import Session
from sqlalchemy import exc as sqlalchemy_exc
from app.entities.user import User
from . import models
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from ..exceptions import (
    AuthenticationError, 
    InvalidCredentialsError, 
    UserAccountLockedError, 
    UserAccountDisabledError, 
    TokenGenerationError,
    DatabaseError
)
import logging
from dotenv import load_dotenv
import os

load_dotenv()

# 
secret_key = os.getenv('SECRET_KEY')
algorithm = os.getenv('ALGORITHM', 'HS256')
access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))


oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return bcrypt_context.hash(password)


def authenticate_user(email: str, password: str, db: Session) -> User | bool:
    """
    Authenticate user with email and password.
    
    Args:
        email: User's email address
        password: User's plain text password
        db: Database session
        
    Returns:
        User object if authentication successful, False otherwise
    """
    try:
        # Query user by email (case-insensitive)
        user = db.query(User).filter(User.email.ilike(email)).first()
        
        if not user:
            logging.warning(f"Authentication failed: User not found for email: {email}")
            return False
            
        # Verify password
        if not verify_password(password, user.password_hash):
            logging.warning(f"Authentication failed: Invalid password for email: {email}")
            return False
            
        return user
        
    except sqlalchemy_exc.SQLAlchemyError as e:
        logging.error(f"Database error during authentication for {email}: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error during authentication for {email}: {str(e)}")
        return False


def create_access_token(email: str, user_id: UUID, expires_delta: timedelta) -> str:
    encode = {
        'sub': email,
        'id': str(user_id),
        'exp': datetime.now(timezone.utc) + expires_delta
    }
    return jwt.encode(encode, secret_key, algorithm=algorithm)


def verify_token(token: str) -> models.TokenData:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        user_id: str = payload.get('id')
        return models.TokenData(user_id=user_id)
    except PyJWTError as e:
        logging.warning(f"Token verification failed: {str(e)}")
        raise AuthenticationError()


def register_user(db: Session, register_user_request: models.RegisterUserRequest) -> None:
    try:
        create_user_model = User(
            id=uuid4(),
            email=register_user_request.email,
            first_name=register_user_request.first_name,
            last_name=register_user_request.last_name,
            password_hash=get_password_hash(register_user_request.password)
        )    
        db.add(create_user_model)
        db.commit()
        return models.AuthResponse(message="User registered successfully", status_code=201)
    except Exception as e:
        logging.error(f"Failed to register user: {register_user_request.email}. Error: {str(e)}")

        # Handle duplicate email constraint violation
        if "duplicate key value violates unique constraint" in str(e) and "email" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

        raise AuthenticationError()
    
    
def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]) -> models.TokenData:
    return verify_token(token)

CurrentUser = Annotated[models.TokenData, Depends(get_current_user)]


def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: Session) -> models.Token:
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise AuthenticationError()
    token = create_access_token(user.email, user.id, timedelta(minutes=access_token_expire_minutes))
    return models.Token(access_token=token, token_type='bearer')


def login_user(login_user_request: models.LoginUserRequest, db: Session) -> models.Token:
    """
    Login user with email and password and return access token.
    
    Args:
        login_user_request: Login credentials (email and password)
        db: Database session
        
    Returns:
        Token object with access token and user information
        
    Raises:
        InvalidCredentialsError: When email or password is incorrect
        UserAccountLockedError: When account is locked (future feature)
        UserAccountDisabledError: When account is disabled (future feature)
        TokenGenerationError: When token creation fails
        HTTPException: For database or other unexpected errors
    """
    try:
        # Input validation and sanitization
        if not login_user_request.email or not login_user_request.password:
            logging.warning("Login attempt with empty credentials")
            raise InvalidCredentialsError("Email and password are required")
        
        # Normalize email to lowercase for consistent comparison
        email = login_user_request.email.lower().strip()
        password = login_user_request.password
        
        # Log login attempt (without sensitive data)
        logging.info(f"Login attempt for email: {email}")
        
        # Authenticate user
        user = authenticate_user(email, password, db)
        if not user:
            # Log failed authentication attempt for security monitoring
            logging.warning(f"Failed login attempt for email: {email}")
            raise InvalidCredentialsError()
        
        # Future: Check if account is locked or disabled
        # if hasattr(user, 'is_locked') and user.is_locked:
        #     logging.warning(f"Login attempt on locked account: {email}")
        #     raise UserAccountLockedError()
        # 
        # if hasattr(user, 'is_disabled') and user.is_disabled:
        #     logging.warning(f"Login attempt on disabled account: {email}")
        #     raise UserAccountDisabledError()
        
        # Generate access token
        try:
            token = create_access_token(
                user.email, 
                user.id, 
                timedelta(minutes=access_token_expire_minutes)
            )
        except Exception as e:
            logging.error(f"Token generation failed for user {email}: {str(e)}")
            raise TokenGenerationError()
        
        # Prepare user data for response (exclude sensitive information)
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
        
        # Log successful login
        logging.info(f"Successful login for user: {email}")
        
        return models.Token(
            access_token=token, 
            token_type='bearer', 
            user=user_data
        )
        
    except (InvalidCredentialsError, UserAccountLockedError, UserAccountDisabledError, TokenGenerationError):
        # Re-raise authentication-related exceptions as-is
        raise
        
    except sqlalchemy_exc.SQLAlchemyError as e:
        # Handle database-specific errors
        logging.error(f"Database error during login for {login_user_request.email}: {str(e)}")
        raise DatabaseError("Database error occurred during login. Please try again later.")
        
    except Exception as e:
        # Handle any other unexpected errors
        logging.error(f"Unexpected error during login for {login_user_request.email}: {str(e)}")
        raise DatabaseError("An unexpected error occurred during login. Please try again later.")
