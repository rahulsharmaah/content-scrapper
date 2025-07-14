import httpx
import json
from typing import Optional, Dict
import structlog
from app.core.config import settings

logger = structlog.get_logger()

class LLMRewriter:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.gemini_api_key = settings.GEMINI_API_KEY
    
    async def rewrite_with_openai(self, content: str, style: str = "professional") -> Optional[str]:
        """Rewrite content using OpenAI API"""
        if not self.openai_api_key:
            logger.error("OpenAI API key not configured")
            return None
        
        try:
            prompt = f"""
            Please rewrite the following content in a {style} style while maintaining the core message and key information:
            
            {content}
            
            Make it engaging, well-structured, and original while preserving the main points.
            """
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4",
                        "messages": [
                            {"role": "system", "content": "You are a professional content rewriter."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.7
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error("OpenAI rewriting failed", error=str(e))
            return None
    
    async def rewrite_with_gemini(self, content: str, style: str = "professional") -> Optional[str]:
        """Rewrite content using Google Gemini API"""
        if not self.gemini_api_key:
            logger.error("Gemini API key not configured")
            return None
        
        try:
            prompt = f"""
            Please rewrite the following content in a {style} style while maintaining the core message and key information:
            
            {content}
            
            Make it engaging, well-structured, and original while preserving the main points.
            """
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.gemini_api_key}",
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {"text": prompt}
                                ]
                            }
                        ]
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result["candidates"][0]["content"]["parts"][0]["text"]
                
        except Exception as e:
            logger.error("Gemini rewriting failed", error=str(e))
            return None
    
    async def rewrite_content(self, content: str, provider: str = "openai", style: str = "professional") -> Optional[str]:
        """Main rewriting method that chooses between OpenAI and Gemini"""
        logger.info("Starting content rewriting", provider=provider, style=style)
        
        if provider.lower() == "openai":
            result = await self.rewrite_with_openai(content, style)
        elif provider.lower() == "gemini":
            result = await self.rewrite_with_gemini(content, style)
        else:
            logger.error("Unsupported LLM provider", provider=provider)
            return None
        
        if result:
            logger.info("Content rewriting completed successfully")
        else:
            logger.error("Content rewriting failed")
        
        return result 