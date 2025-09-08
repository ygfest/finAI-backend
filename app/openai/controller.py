"""
OpenAI API Controller

FastAPI routes for OpenAI functionality with proper error handling and validation.
"""

from typing import Dict, List, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from .service import get_openai_service, OpenAIError, OpenAIRateLimitError, OpenAIAuthenticationError
from functools import wraps
from .finance_advisor import get_finance_advisor_service
from .models import (
    ChatCompletionRequest, ChatCompletionResponse,
    EmbeddingRequest, EmbeddingResponse,
    ImageGenerationRequest, ImageResponse,
    ModerationRequest, ModerationResponse,
    ModelInfo, HealthResponse, APIErrorResponse,
    FinanceAdviceRequest, RiskAssessmentRequest, ConceptExplanationRequest,
    FinanceAdviceResponse, RiskProfileResponse, ConceptExplanationResponse
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

# Finance Advisor Router
finance_router = APIRouter(
    prefix="/finance-advisor",
    tags=["finance-advisor"],
    responses={
        429: {"model": APIErrorResponse, "description": "Rate limit exceeded"},
        401: {"model": APIErrorResponse, "description": "Authentication failed"},
        500: {"model": APIErrorResponse, "description": "Internal server error"}
    }
)


def handle_openai_exceptions(func):
    """Decorator to handle OpenAI exceptions uniformly, preserving endpoint signature."""
    @wraps(func)
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


@router.get("/models", response_model=List[ModelInfo])
@handle_openai_exceptions
@limiter.limit("10/minute")
async def list_models(request: Request):
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


@router.post("/chat/completions", response_model=ChatCompletionResponse)
@handle_openai_exceptions
@limiter.limit("20/minute")
async def create_chat_completion(
    chat_request: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    request: Request
):
    """Create a chat completion."""
    service = get_openai_service()

    # Convert Pydantic models to dictionaries for OpenAI API
    messages = [msg.dict() for msg in chat_request.messages]

    # Add logging in background
    background_tasks.add_task(
        logger.info,
        "Processing chat completion request for model: %s",
        chat_request.model
    )

    response = await service.create_chat_completion(
        messages=messages,
        model=chat_request.model,
        temperature=chat_request.temperature,
        max_tokens=chat_request.max_tokens,
        top_p=chat_request.top_p,
        frequency_penalty=chat_request.frequency_penalty,
        presence_penalty=chat_request.presence_penalty,
        stop=chat_request.stop
    )

    # Convert response to our model
    return ChatCompletionResponse(**response)


@router.post("/chat/completions/stream")
@handle_openai_exceptions
@limiter.limit("10/minute")
async def create_chat_completion_stream(chat_request: ChatCompletionRequest, request: Request):
    """Create a streaming chat completion."""
    if not chat_request.stream:
        raise HTTPException(
            status_code=400,
            detail="Streaming must be enabled for this endpoint"
        )

    service = get_openai_service()
    messages = [msg.dict() for msg in chat_request.messages]

    async def generate():
        try:
            async with service.session() as client:
                stream = await client.chat.completions.create(
                    model=chat_request.model,
                    messages=messages,
                    temperature=chat_request.temperature,
                    max_tokens=chat_request.max_tokens,
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
@handle_openai_exceptions
@limiter.limit("30/minute")
async def create_embeddings(request: EmbeddingRequest, req: Request):
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
@handle_openai_exceptions
@limiter.limit("5/minute")
async def create_image(request: ImageGenerationRequest, req: Request):
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


# Finance Advisor Endpoints

@finance_router.post("/advice", response_model=Dict[str, Any])
@handle_openai_exceptions
@limiter.limit("15/minute")
async def get_financial_advice(request: FinanceAdviceRequest, req: Request):
    """Get financial advice from AI advisor using o3-mini model."""
    logger.info(f"Received finance advice request: query='{request.query}', temp={request.temperature}")

    finance_service = get_finance_advisor_service()

    # Convert conversation history to dict format
    conversation_history = None
    if request.conversation_history:
        logger.info(f"Conversation history length: {len(request.conversation_history)}")
        conversation_history = [msg.dict() for msg in request.conversation_history]
        logger.info(f"Converted conversation history: {conversation_history}")

    response = await finance_service.get_financial_advice(
        user_query=request.query,
        conversation_history=conversation_history,
        temperature=request.temperature
    )

    logger.info(f"Finance advice response generated successfully")
    return response


@finance_router.post("/risk-assessment", response_model=Dict[str, Any])
@handle_openai_exceptions
@limiter.limit("10/minute")
async def assess_risk_profile(request: RiskAssessmentRequest, req: Request):
    """Assess user's financial risk profile."""
    finance_service = get_finance_advisor_service()

    response = await finance_service.assess_financial_risk_profile(
        answers=request.answers
    )

    return response


@finance_router.post("/explain-concept", response_model=Dict[str, Any])
@handle_openai_exceptions
@limiter.limit("20/minute")
async def explain_financial_concept(request: ConceptExplanationRequest, req: Request):
    """Explain a financial concept at the appropriate knowledge level."""
    finance_service = get_finance_advisor_service()

    response = await finance_service.explain_financial_concept(
        concept=request.concept,
        user_knowledge_level=request.knowledge_level
    )

    return response


@finance_router.get("/health", response_model=HealthResponse)
@handle_openai_exceptions
async def finance_advisor_health():
    """Check finance advisor service health."""
    try:
        finance_service = get_finance_advisor_service()
        openai_service = get_openai_service()

        # Test both services
        await openai_service.list_models()

        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            version="o3-mini"
        )
    except Exception as e:
        logger.error("Finance advisor health check failed: %s", str(e))
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat()
        )


@finance_router.get("/capabilities", response_model=Dict[str, Any])
async def get_capabilities():
    """Get finance advisor capabilities and features."""
    return {
        "model": "o3-mini",
        "capabilities": [
            "Financial planning advice",
            "Investment education",
            "Risk assessment",
            "Debt management guidance",
            "Budgeting assistance",
            "Retirement planning",
            "Concept explanations",
            "Market education"
        ],
        "specializations": [
            "Personal finance",
            "Investment basics",
            "Risk management",
            "Financial literacy",
            "Long-term planning"
        ],
        "limitations": [
            "Not a licensed financial advisor",
            "Cannot give personalized investment recommendations",
            "Cannot guarantee returns",
            "Users should consult professionals",
            "Educational and informational purposes only"
        ],
        "supported_languages": ["English"],
        "response_time": "Typically 2-5 seconds",
        "rate_limits": {
            "advice": "15 requests/minute",
            "risk_assessment": "10 requests/minute",
            "concept_explanation": "20 requests/minute"
        }
    }
