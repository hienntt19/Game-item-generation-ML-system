import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL env variable is not set")

engine = create_engine(DATABASE_URL)

SQLAlchemyInstrumentor().instrument(
    engine=engine,
    enable_commenter=True,
    commenter_options={},
)

print("SQLAlchemy engine is instrumented for tracing.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

