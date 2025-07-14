import httpx
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from typing import Dict, Optional, Tuple
import structlog
from app.core.config import settings

logger = structlog.get_logger()

class WebScraper:
    def __init__(self):
        self.user_agent = settings.DEFAULT_USER_AGENT
        self.timeout = settings.REQUEST_TIMEOUT
    
    async def scrape_with_playwright(self, url: str) -> Optional[Dict]:
        """Scrape JavaScript-heavy websites using Playwright"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set user agent
                await page.set_extra_http_headers({
                    "User-Agent": self.user_agent
                })
                
                # Navigate to page
                await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
                
                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                # Extract content
                title = await page.title()
                body = await page.content()
                
                await browser.close()
                
                return {
                    "title": title,
                    "body": body,
                    "url": url
                }
                
        except Exception as e:
            logger.error("Playwright scraping failed", url=url, error=str(e))
            return None
    
    async def scrape_with_httpx(self, url: str) -> Optional[Dict]:
        """Scrape static websites using httpx"""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent}
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract title
                title_tag = soup.find('title')
                title = title_tag.get_text().strip() if title_tag else ""
                
                # Extract main content (basic implementation)
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                body = soup.get_text()
                
                return {
                    "title": title,
                    "body": body,
                    "url": url
                }
                
        except Exception as e:
            logger.error("HTTPX scraping failed", url=url, error=str(e))
            return None
    
    async def scrape_url(self, url: str, use_playwright: bool = False) -> Optional[Dict]:
        """Main scraping method that chooses between httpx and playwright"""
        logger.info("Starting scraping", url=url, use_playwright=use_playwright)
        
        if use_playwright:
            result = await self.scrape_with_playwright(url)
        else:
            result = await self.scrape_with_httpx(url)
        
        if result:
            logger.info("Scraping completed successfully", url=url)
        else:
            logger.error("Scraping failed", url=url)
        
        return result 