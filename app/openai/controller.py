"""
OpenAI API Controller

FastAPI routes for OpenAI functionality with proper error handling and validation.
"""

from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse

from .service import get_openai_service, OpenAIError, OpenAIRateLimitError, OpenAIAuthenticationError
from functools import wraps
from .finance_advisor import get_finance_advisor_service
from .models import (
    HealthResponse, APIErrorResponse,
    FinanceAdviceRequest, RiskAssessmentRequest, ConceptExplanationRequest,
)
from ..rate_limiter import limiter
from ..logging import get_logger

logger = get_logger(__name__)

# Finance Advisor Router (primary and only public OpenAI surface)
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


# Removed generic OpenAI endpoints to keep surface area minimal and focused on
# finance advisor features only.


# Finance Advisor Endpoints

@finance_router.post("/advice", response_model=Dict[str, Any])
@handle_openai_exceptions
@limiter.limit("15/minute")
async def get_financial_advice(request: Request, body: FinanceAdviceRequest):
    """Get financial advice from AI advisor using o3-mini model."""
    logger.info(f"Received finance advice request: query='{body.query}', temp={body.temperature}")

    finance_service = get_finance_advisor_service()

    # Convert conversation history to dict format
    conversation_history = None
    if body.conversation_history:
        logger.info(f"Conversation history length: {len(body.conversation_history)}")
        conversation_history = [msg.dict() for msg in body.conversation_history]
        logger.info(f"Converted conversation history: {conversation_history}")

    response = await finance_service.get_financial_advice(
        user_query=body.query,
        conversation_history=conversation_history,
        temperature=body.temperature
    )

    logger.info(f"Finance advice response generated successfully")
    return response


@finance_router.post("/risk-assessment", response_model=Dict[str, Any])
@handle_openai_exceptions
@limiter.limit("10/minute")
async def assess_risk_profile(request: Request, body: RiskAssessmentRequest):
    """Assess user's financial risk profile."""
    finance_service = get_finance_advisor_service()

    response = await finance_service.assess_financial_risk_profile(
        answers=body.answers
    )

    return response


@finance_router.post("/explain-concept", response_model=Dict[str, Any])
@handle_openai_exceptions
@limiter.limit("20/minute")
async def explain_financial_concept(request: Request, body: ConceptExplanationRequest):
    """Explain a financial concept at the appropriate knowledge level."""
    finance_service = get_finance_advisor_service()

    response = await finance_service.explain_financial_concept(
        concept=body.concept,
        user_knowledge_level=body.knowledge_level
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
