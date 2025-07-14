from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import structlog

from app.core.database import get_db
from app.schemas.content import Post, PostCreate, PostUpdate
from app.models.content import Post as PostModel
from app.workers.tasks import scrape_content_task, rewrite_content_task

logger = structlog.get_logger()
router = APIRouter()

@router.post("/", response_model=Post)
async def create_post(
    post: PostCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new post and trigger scraping"""
    try:
        db_post = PostModel(**post.dict())
        db.add(db_post)
        await db.flush()  # Get the ID
        
        # Trigger scraping task
        scrape_content_task.delay(db_post.id, str(post.source_url))
        
        await db.commit()
        await db.refresh(db_post)
        
        logger.info("Post created and scraping triggered", post_id=db_post.id)
        return db_post
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create post", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post"
        )

@router.get("/", response_model=List[Post])
async def get_posts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all posts with pagination"""
    try:
        result = await db.execute(
            select(PostModel).offset(skip).limit(limit).order_by(PostModel.created_at.desc())
        )
        posts = result.scalars().all()
        return posts
        
    except Exception as e:
        logger.error("Failed to fetch posts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch posts"
        )

@router.get("/{post_id}", response_model=Post)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific post by ID"""
    try:
        result = await db.execute(select(PostModel).where(PostModel.id == post_id))
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        return post
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch post", post_id=post_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post"
        )

@router.put("/{post_id}", response_model=Post)
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a post"""
    try:
        result = await db.execute(select(PostModel).where(PostModel.id == post_id))
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        # Update fields
        update_data = post_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(post, field, value)
        
        await db.commit()
        await db.refresh(post)
        
        logger.info("Post updated", post_id=post_id)
        return post
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to update post", post_id=post_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post"
        )

@router.post("/{post_id}/rewrite")
async def trigger_rewrite(
    post_id: int,
    provider: str = "openai",
    style: str = "professional",
    db: AsyncSession = Depends(get_db)
):
    """Trigger content rewriting for a post"""
    try:
        result = await db.execute(select(PostModel).where(PostModel.id == post_id))
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        if not post.raw_body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content to rewrite"
            )
        
        # Trigger rewriting task
        rewrite_content_task.delay(post_id, provider, style)
        
        logger.info("Rewriting triggered", post_id=post_id, provider=provider)
        return {"message": "Rewriting task started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to trigger rewrite", post_id=post_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger rewrite"
        )

@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a post"""
    try:
        result = await db.execute(select(PostModel).where(PostModel.id == post_id))
        post = result.scalar_one_or_none()
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        await db.delete(post)
        await db.commit()
        
        logger.info("Post deleted", post_id=post_id)
        return {"message": "Post deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to delete post", post_id=post_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete post"
        ) 