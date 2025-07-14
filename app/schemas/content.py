from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from app.models.content import ContentStatus

class PostBase(BaseModel):
    source_url: HttpUrl
    raw_title: Optional[str] = None
    raw_body: Optional[str] = None
    rewritten_title: Optional[str] = None
    rewritten_body: Optional[str] = None
    status: ContentStatus = ContentStatus.PENDING

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    raw_title: Optional[str] = None
    raw_body: Optional[str] = None
    rewritten_title: Optional[str] = None
    rewritten_body: Optional[str] = None
    status: Optional[ContentStatus] = None

class Post(PostBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 