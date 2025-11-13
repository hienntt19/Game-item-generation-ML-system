import os
import uuid
from datetime import datetime

from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

DATABASE_URL = settings.DATABASE_URL
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


class GenerationRequest(Base):
    __tablename__ = "generation_requests"
    request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    celery_task_id = Column(String(255), nullable=True, index=True)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text)
    num_inference_steps = Column(Integer)
    guidance_scale = Column(Float)
    seed = Column(BigInteger)
    status = Column(String(20), nullable=False, default="Pending")
    image_url = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
