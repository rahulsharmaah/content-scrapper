from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class ContentStatus(str, enum.Enum):
    PENDING = "pending"
    SCRAPED = "scraped"
    REWRITTEN = "rewritten"
    FAILED = "failed"

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String, nullable=False, index=True)
    raw_title = Column(Text)
    raw_body = Column(Text)
    rewritten_title = Column(Text)
    rewritten_body = Column(Text)
    status = Column(Enum(ContentStatus), default=ContentStatus.PENDING)
    metadata = Column(Text)  # JSON string for additional data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="posts")
