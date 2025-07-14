from celery import Celery
from app.core.config import settings
from app.services.scraper import WebScraper
from app.services.llm_rewriter import LLMRewriter
from app.models.content import ContentStatus
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
import structlog

logger = structlog.get_logger()

# Initialize Celery
celery_app = Celery(
    "content_scraper",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task
def scrape_content_task(post_id: int, url: str, use_playwright: bool = False):
    """Celery task to scrape content from a URL"""
    logger.info("Starting scraping task", post_id=post_id, url=url)
    
    try:
        # Create async event loop for the task
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def scrape_and_save():
            # Scrape content
            scraper = WebScraper()
            result = await scraper.scrape_url(url, use_playwright)
            
            if result:
                # Update database
                async with AsyncSessionLocal() as session:
                    from app.models.content import Post
                    
                    post = await session.get(Post, post_id)
                    if post:
                        post.raw_title = result["title"]
                        post.raw_body = result["body"]
                        post.status = ContentStatus.SCRAPED
                        await session.commit()
                        
                        logger.info("Content scraped and saved", post_id=post_id)
                        
                        # Trigger rewriting task
                        rewrite_content_task.delay(post_id, "openai", "professional")
                    else:
                        logger.error("Post not found", post_id=post_id)
            else:
                # Update status to failed
                async with AsyncSessionLocal() as session:
                    from app.models.content import Post
                    
                    post = await session.get(Post, post_id)
                    if post:
                        post.status = ContentStatus.FAILED
                        await session.commit()
                        
                        logger.error("Scraping failed, status updated", post_id=post_id)
        
        loop.run_until_complete(scrape_and_save())
        loop.close()
        
    except Exception as e:
        logger.error("Scraping task failed", post_id=post_id, error=str(e))
        raise

@celery_app.task
def rewrite_content_task(post_id: int, provider: str = "openai", style: str = "professional"):
    """Celery task to rewrite content using LLM"""
    logger.info("Starting rewriting task", post_id=post_id, provider=provider)
    
    try:
        # Create async event loop for the task
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def rewrite_and_save():
            async with AsyncSessionLocal() as session:
                from app.models.content import Post
                
                post = await session.get(Post, post_id)
                if not post or not post.raw_body:
                    logger.error("Post not found or no content to rewrite", post_id=post_id)
                    return
                
                # Rewrite content
                rewriter = LLMRewriter()
                rewritten_content = await rewriter.rewrite_content(
                    post.raw_body, provider, style
                )
                
                if rewritten_content:
                    # Update database
                    post.rewritten_body = rewritten_content
                    post.status = ContentStatus.REWRITTEN
                    await session.commit()
                    
                    logger.info("Content rewritten and saved", post_id=post_id)
                else:
                    # Update status to failed
                    post.status = ContentStatus.FAILED
                    await session.commit()
                    
                    logger.error("Rewriting failed, status updated", post_id=post_id)
        
        loop.run_until_complete(rewrite_and_save())
        loop.close()
        
    except Exception as e:
        logger.error("Rewriting task failed", post_id=post_id, error=str(e))
        raise

@celery_app.task
def scheduled_scraping_task(job_id: int):
    """Celery task for scheduled scraping jobs"""
    logger.info("Starting scheduled scraping task", job_id=job_id)
    
    try:
        # Create async event loop for the task
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def process_scheduled_job():
            async with AsyncSessionLocal() as session:
                from app.models.job import ScrapingJob
                from app.models.content import Post
                
                job = await session.get(ScrapingJob, job_id)
                if not job:
                    logger.error("Scheduled job not found", job_id=job_id)
                    return
                
                # Create new post for this scraping
                post = Post(source_url=job.target_url)
                session.add(post)
                await session.flush()  # Get the ID
                
                # Update job status
                job.last_run_at = func.now()
                await session.commit()
                
                # Trigger scraping task
                scrape_content_task.delay(post.id, job.target_url)
        
        loop.run_until_complete(process_scheduled_job())
        loop.close()
        
    except Exception as e:
        logger.error("Scheduled scraping task failed", job_id=job_id, error=str(e))
        raise 