from typing import Annotated
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

""" Prefer DATABASE_CONNECTION_STRING; fallback to DATABASE_URL; default to local SQLite for dev """
DATABASE_URL = (
    os.getenv("DATABASE_URL")

)

is_postgres = DATABASE_URL.startswith("postgresql")

engine_kwargs = {"pool_pre_ping": True}


if is_postgres and "sslmode=" not in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"sslmode": "require"},
        **engine_kwargs,
    )
else:
    engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
        print("Database connected")
    finally:
        db.close()
        
DbSession = Annotated[Session, Depends(get_db)]

