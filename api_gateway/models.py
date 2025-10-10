import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID
from .database import Base

class GenerationRequest(Base):
    __tablename__ = "generation_requests"
    request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text)
    num_inference_steps = Column(Integer)
    guidance_scale = Column(Float)
    seed = Column(BigInteger)
    status = Column(String(20), nullable=False, default="Pending")
    image_url = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    