from fastapi import FastAPI
from app.todos.controller import router as todos_router
from app.auth.controller import router as auth_router
from app.users.controller import router as users_router
from app.health import router as health_router
from app.openai.controller import router as openai_router

def register_routes(app: FastAPI):
    app.include_router(todos_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(health_router)
    app.include_router(openai_router)