"""
OpenAI Service Module

This module provides a comprehensive interface to OpenAI APIs with best practices:
- Async/await support for concurrent requests
- Robust error handling and logging
- Rate limiting and retry logic
- Structured response handling
- Environment-based configuration
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass

from openai import AsyncOpenAI, OpenAI
from openai._exceptions import APIError, RateLimitError, AuthenticationError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI client."""
    api_key: str
    base_url: Optional[str] = None
    organization: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> 'OpenAIConfig':
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv('OPENAI_API_KEY', ''),
            base_url=os.getenv('OPENAI_BASE_URL'),
            organization=os.getenv('OPENAI_ORGANIZATION'),
            timeout=float(os.getenv('OPENAI_TIMEOUT', '60.0')),
            max_retries=int(os.getenv('OPENAI_MAX_RETRIES', '3'))
        )


class OpenAIError(Exception):
    """Base exception for OpenAI-related errors."""
    pass


class OpenAIRateLimitError(OpenAIError):
    """Raised when OpenAI API rate limit is exceeded."""
    pass


class OpenAIAuthenticationError(OpenAIError):
    """Raised when OpenAI API authentication fails."""
    pass


class OpenAIConnectionError(OpenAIError):
    """Raised when connection to OpenAI API fails."""
    pass


class OpenAIService:
    """
    OpenAI Service with comprehensive error handling and best practices.

    Features:
    - Async and sync client support
    - Automatic retry logic with exponential backoff
    - Rate limit handling
    - Structured logging
    - Connection pooling and timeouts
    """

    def __init__(self, config: Optional[OpenAIConfig] = None):
        self.config = config or OpenAIConfig.from_env()
        self._async_client: Optional[AsyncOpenAI] = None
        self._sync_client: Optional[OpenAI] = None

        # Validate configuration
        if not self.config.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        logger.info("OpenAI service initialized with config: timeout=%s, max_retries=%s",
                   self.config.timeout, self.config.max_retries)

    @property
    def async_client(self) -> AsyncOpenAI:
        """Get or create async OpenAI client."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                organization=self.config.organization,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        return self._async_client

    @property
    def sync_client(self) -> OpenAI:
        """Get or create sync OpenAI client."""
        if self._sync_client is None:
            self._sync_client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                organization=self.config.organization,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        return self._sync_client

    @asynccontextmanager
    async def session(self):
        """Context manager for OpenAI client session."""
        try:
            yield self.async_client
        except Exception as e:
            logger.error("OpenAI session error: %s", str(e))
            raise

    def _handle_openai_error(self, error: Exception) -> OpenAIError:
        """Convert OpenAI exceptions to custom exceptions."""
        if isinstance(error, RateLimitError):
            logger.warning("OpenAI rate limit exceeded")
            return OpenAIRateLimitError("Rate limit exceeded. Please try again later.")
        elif isinstance(error, AuthenticationError):
            logger.error("OpenAI authentication failed")
            return OpenAIAuthenticationError("Authentication failed. Check your API key.")
        elif isinstance(error, APIConnectionError):
            logger.error("OpenAI connection error: %s", str(error))
            return OpenAIConnectionError("Connection to OpenAI API failed.")
        elif isinstance(error, APIError):
            logger.error("OpenAI API error: %s", str(error))
            return OpenAIError(f"OpenAI API error: {error.message}")
        else:
            logger.error("Unexpected OpenAI error: %s", str(error))
            return OpenAIError(f"Unexpected error: {str(error)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError))
    )
    async def create_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion with retry logic and error handling.

        Args:
            messages: List of message dictionaries
            model: Model to use for completion
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Chat completion response

        Raises:
            OpenAIError: For API-related errors
        """
        try:
            logger.info("Creating chat completion with model: %s", model)

            async with self.session() as client:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )

                result = response.model_dump()
                logger.info("Chat completion successful")
                return result

        except Exception as e:
            raise self._handle_openai_error(e)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError))
    )
    async def create_embeddings(
        self,
        input_texts: Union[str, List[str]],
        model: str = "text-embedding-3-small",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create embeddings for input texts.

        Args:
            input_texts: Text or list of texts to embed
            model: Embedding model to use
            **kwargs: Additional parameters

        Returns:
            Embeddings response

        Raises:
            OpenAIError: For API-related errors
        """
        try:
            logger.info("Creating embeddings for %d texts with model: %s",
                       len(input_texts) if isinstance(input_texts, list) else 1, model)

            async with self.session() as client:
                response = await client.embeddings.create(
                    input=input_texts,
                    model=model,
                    **kwargs
                )

                result = response.model_dump()
                logger.info("Embeddings creation successful")
                return result

        except Exception as e:
            raise self._handle_openai_error(e)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError))
    )
    async def create_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate an image using DALL-E.

        Args:
            prompt: Text description of the image
            model: Image generation model
            size: Image size (e.g., "1024x1024")
            quality: Image quality ("standard" or "hd")
            **kwargs: Additional parameters

        Returns:
            Image generation response

        Raises:
            OpenAIError: For API-related errors
        """
        try:
            logger.info("Generating image with model: %s", model)

            async with self.session() as client:
                response = await client.images.generate(
                    prompt=prompt,
                    model=model,
                    size=size,
                    quality=quality,
                    **kwargs
                )

                result = response.model_dump()
                logger.info("Image generation successful")
                return result

        except Exception as e:
            raise self._handle_openai_error(e)

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available OpenAI models.

        Returns:
            List of available models

        Raises:
            OpenAIError: For API-related errors
        """
        try:
            logger.info("Listing available models")

            async with self.session() as client:
                response = await client.models.list()
                models = [model.model_dump() for model in response.data]

                logger.info("Retrieved %d models", len(models))
                return models

        except Exception as e:
            raise self._handle_openai_error(e)

    async def get_model(self, model_id: str) -> Dict[str, Any]:
        """
        Get details for a specific model.

        Args:
            model_id: ID of the model to retrieve

        Returns:
            Model details

        Raises:
            OpenAIError: For API-related errors
        """
        try:
            logger.info("Retrieving model: %s", model_id)

            async with self.session() as client:
                response = await client.models.retrieve(model_id)
                result = response.model_dump()

                logger.info("Model retrieval successful")
                return result

        except Exception as e:
            raise self._handle_openai_error(e)

    async def moderate_content(self, content: str) -> Dict[str, Any]:
        """
        Moderate content using OpenAI's moderation API.

        Args:
            content: Content to moderate

        Returns:
            Moderation results

        Raises:
            OpenAIError: For API-related errors
        """
        try:
            logger.info("Moderating content")

            async with self.session() as client:
                response = await client.moderations.create(input=content)
                result = response.model_dump()

                logger.info("Content moderation successful")
                return result

        except Exception as e:
            raise self._handle_openai_error(e)


# Global service instance
_openai_service: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    """Get or create global OpenAI service instance."""
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService()
    return _openai_service


async def health_check() -> bool:
    """
    Health check for OpenAI service.

    Returns:
        True if service is healthy, False otherwise
    """
    try:
        service = get_openai_service()
        await service.list_models()
        return True
    except Exception as e:
        logger.error("OpenAI health check failed: %s", str(e))
        return False

