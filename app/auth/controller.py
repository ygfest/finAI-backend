from typing import Annotated
from fastapi import APIRouter, Depends, Request, HTTPException
from starlette import status
from . import  models
from . import service
from fastapi.security import OAuth2PasswordRequestForm
from ..database.core import DbSession
from ..rate_limiter import limiter
from ..exceptions import (
    InvalidCredentialsError, 
    UserAccountLockedError, 
    UserAccountDisabledError, 
    TokenGenerationError,
    DatabaseError,
    UserNotFoundError
)

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)


@router.post("/token", response_model=models.Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: DbSession):
    try:
        return service.login_for_access_token(form_data, db)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
    except UserAccountLockedError as e:
        raise HTTPException(
            status_code=423,
            detail=str(e)
        )
    except UserAccountDisabledError as e:
        raise HTTPException(
            status_code=403,
            detail=str(e)
        )

    except UserNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except TokenGenerationError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are already properly formatted)
        raise
    except Exception as e:
        # Handle any other unexpected errors
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during login. Please try again later."
        )

@router.post("/register", response_model=models.AuthResponse)
async def register_user(request: Request, db: DbSession, register_user_request: models.RegisterUserRequest):
    try:
        return service.register_user(db, register_user_request)
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are already properly formatted)
        raise
    except Exception as e:
        # Handle any other unexpected errors
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during registration. Please try again later."
        )

@router.post("/login", response_model=models.Token)
async def login_user(db: DbSession, login_user_request: models.LoginUserRequest):
    try:
        return service.login_user(login_user_request, db)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
    except UserAccountLockedError as e:
        raise HTTPException(
            status_code=423,
            detail=str(e)
        )
    except UserAccountDisabledError as e:
        raise HTTPException(
            status_code=403,
            detail=str(e)
        )
    except TokenGenerationError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are already properly formatted)
        raise
    except Exception as e:
        # Handle any other unexpected errors
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during login. Please try again later."
        )
