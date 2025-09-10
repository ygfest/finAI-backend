from typing import Annotated
from fastapi import APIRouter, Depends, Request
from starlette import status
from . import  models
from . import service
from fastapi.security import OAuth2PasswordRequestForm
from ..database.core import DbSession
from ..rate_limiter import limiter

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)




@router.post("/token", response_model=models.Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: DbSession):
    return service.login_for_access_token(form_data, db)

@router.post("/register", response_model=models.AuthResponse)
async def register_user(request: Request, db: DbSession, register_user_request: models.RegisterUserRequest):
    return service.register_user(db, register_user_request)

@router.post("/login", response_model=models.Token)
async def login_user(db: DbSession, login_user_request: models.LoginUserRequest):
    return service.login_user(login_user_request, db)







