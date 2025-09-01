"""
OpenAI API Controller

FastAPI routes for OpenAI functionality with proper error handling and validation.
"""

from typing import Dict, List, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from .service import get_openai_service, OpenAIError, OpenAIRateLimitError, OpenAIAuthenticationError
from .models import (
    ChatCompletionRequest, ChatCompletionResponse,
    EmbeddingRequest, EmbeddingResponse,
    ImageGenerationRequest, ImageResponse,
    ModerationRequest, ModerationResponse,
    ModelInfo, HealthResponse, APIErrorResponse
)
from ..rate_limiter import limiter
from ..logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/openai",
    tags=["openai"],
    responses={
        429: {"model": APIErrorResponse, "description": "Rate limit exceeded"},
        401: {"model": APIErrorResponse, "description": "Authentication failed"},
        500: {"model": APIErrorResponse, "description": "Internal server error"}
    }
)


def handle_openai_exceptions(func):
    """Decorator to handle OpenAI exceptions uniformly."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except OpenAIRateLimitError as e:
            logger.warning("Rate limit exceeded: %s", str(e))
            raise HTTPException(
                status_code=429,
                detail=str(e),
                headers={"Retry-After": "60"}
            )
        except OpenAIAuthenticationError as e:
            logger.error("Authentication error: %s", str(e))
            raise HTTPException(status_code=401, detail=str(e))
        except OpenAIError as e:
            logger.error("OpenAI error: %s", str(e))
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper


@router.get("/health", response_model=HealthResponse)
@handle_openai_exceptions
async def health_check():
    """Check OpenAI service health."""
    service = get_openai_service()

    try:
        # Quick health check by listing models
        models = await service.list_models()
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            version=len(models)  # Simple indicator that API is working
        )
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat()
        )


@router.get("/models", response_model=List[ModelInfo])
@limiter.limit("10/minute")
@handle_openai_exceptions
async def list_models(request: Any = None):  # request parameter for rate limiting
    """List available OpenAI models."""
    service = get_openai_service()
    models = await service.list_models()

    # Convert to our response model
    return [
        ModelInfo(
            id=model["id"],
            object=model["object"],
            created=model["created"],
            owned_by=model["owned_by"]
        )
        for model in models
    ]


@router.get("/models/{model_id}", response_model=ModelInfo)
@limiter.limit("30/minute")
@handle_openai_exceptions
async def get_model(model_id: str, request: Any = None):
    """Get details for a specific model."""
    service = get_openai_service()
    model = await service.get_model(model_id)

    return ModelInfo(
        id=model["id"],
        object=model["object"],
        created=model["created"],
        owned_by=model["owned_by"]
    )


@router.post("/chat/completions", response_model=ChatCompletionResponse)
@limiter.limit("20/minute")
@handle_openai_exceptions
async def create_chat_completion(
    request: ChatCompletionRequest,
    background_tasks: BackgroundTasks
):
    """Create a chat completion."""
    service = get_openai_service()

    # Convert Pydantic models to dictionaries for OpenAI API
    messages = [msg.dict() for msg in request.messages]

    # Add logging in background
    background_tasks.add_task(
        logger.info,
        "Processing chat completion request for model: %s",
        request.model
    )

    response = await service.create_chat_completion(
        messages=messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
        frequency_penalty=request.frequency_penalty,
        presence_penalty=request.presence_penalty,
        stop=request.stop
    )

    # Convert response to our model
    return ChatCompletionResponse(**response)


@router.post("/chat/completions/stream")
@limiter.limit("10/minute")
@handle_openai_exceptions
async def create_chat_completion_stream(request: ChatCompletionRequest):
    """Create a streaming chat completion."""
    if not request.stream:
        raise HTTPException(
            status_code=400,
            detail="Streaming must be enabled for this endpoint"
        )

    service = get_openai_service()
    messages = [msg.dict() for msg in request.messages]

    async def generate():
        try:
            async with service.session() as client:
                stream = await client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=True
                )

                async for chunk in stream:
                    if chunk.choices:
                        yield f"data: {chunk.model_dump_json()}\n\n"

                yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Streaming error: %s", str(e))
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/embeddings", response_model=EmbeddingResponse)
@limiter.limit("30/minute")
@handle_openai_exceptions
async def create_embeddings(request: EmbeddingRequest):
    """Create embeddings for input texts."""
    service = get_openai_service()

    response = await service.create_embeddings(
        input_texts=request.input,
        model=request.model,
        encoding_format=request.encoding_format,
        dimensions=request.dimensions,
        user=request.user
    )

    return EmbeddingResponse(**response)


@router.post("/images/generations", response_model=ImageResponse)
@limiter.limit("5/minute")
@handle_openai_exceptions
async def create_image(request: ImageGenerationRequest):
    """Generate an image using DALL-E."""
    service = get_openai_service()

    response = await service.create_image(
        prompt=request.prompt,
        model=request.model,
        size=request.size,
        quality=request.quality,
        n=request.n,
        style=request.style
    )

    return ImageResponse(**response)


@router.post("/moderations", response_model=ModerationResponse)
@limiter.limit("20/minute")
@handle_openai_exceptions
async def moderate_content(request: ModerationRequest):
    """Moderate content using OpenAI's moderation API."""
    service = get_openai_service()

    response = await service.moderate_content(request.input)

    return ModerationResponse(**response)


# Bulk operations for efficiency
@router.post("/embeddings/batch", response_model=EmbeddingResponse)
@limiter.limit("10/minute")
@handle_openai_exceptions
async def create_embeddings_batch(request: EmbeddingRequest):
    """Create embeddings for multiple texts in batch."""
    if isinstance(request.input, str):
        raise HTTPException(
            status_code=400,
            detail="Batch endpoint requires a list of texts"
        )

    if len(request.input) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 texts allowed in batch"
        )

    service = get_openai_service()
    response = await service.create_embeddings(
        input_texts=request.input,
        model=request.model,
        encoding_format=request.encoding_format,
        dimensions=request.dimensions,
        user=request.user
    )

    return EmbeddingResponse(**response)
