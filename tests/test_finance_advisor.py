"""
Tests for Finance Advisor functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.openai.finance_advisor import FinanceAdvisorService, get_finance_advisor_service
from app.openai.models import FinanceAdviceRequest, RiskAssessmentRequest, ConceptExplanationRequest


class TestFinanceAdvisorService:
    """Test cases for FinanceAdvisorService."""

    @pytest.fixture
    def mock_openai_service(self):
        """Mock OpenAI service for testing."""
        mock_service = AsyncMock()
        mock_service.create_chat_completion.return_value = {
            "id": "test-id",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "o3-mini",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response with safety disclaimers."
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        return mock_service

    @pytest.fixture
    def finance_service(self, mock_openai_service):
        """Create FinanceAdvisorService with mocked OpenAI service."""
        service = FinanceAdvisorService(mock_openai_service)
        return service

    @pytest.mark.asyncio
    async def test_get_financial_advice_basic(self, finance_service, mock_openai_service):
        """Test basic financial advice request."""
        request = FinanceAdviceRequest(
            query="How should I start saving money?",
            temperature=0.7
        )

        response = await finance_service.get_financial_advice(
            user_query=request.query,
            temperature=request.temperature
        )

        # Verify OpenAI service was called
        mock_openai_service.create_chat_completion.assert_called_once()

        # Verify response structure
        assert response["id"] == "test-id"
        assert response["model"] == "o3-mini"
        assert len(response["choices"]) == 1

        # Verify safety disclaimer was added
        content = response["choices"][0]["message"]["content"]
        assert "safety disclaimers" in content.lower()

    @pytest.mark.asyncio
    async def test_get_financial_advice_with_history(self, finance_service, mock_openai_service):
        """Test financial advice with conversation history."""
        conversation_history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]

        response = await finance_service.get_financial_advice(
            user_query="Follow-up question",
            conversation_history=conversation_history
        )

        # Verify conversation history was included
        call_args = mock_openai_service.create_chat_completion.call_args
        messages = call_args[1]["messages"]

        # Should have system message + history + current query
        assert len(messages) >= 3  # system + 2 history + current
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Follow-up question"

    @pytest.mark.asyncio
    async def test_assess_risk_profile(self, finance_service, mock_openai_service):
        """Test risk profile assessment."""
        answers = {
            "age": 30,
            "investment_experience": "intermediate",
            "risk_tolerance": "moderate"
        }

        response = await finance_service.assess_financial_risk_profile(answers)

        mock_openai_service.create_chat_completion.assert_called_once()

        # Verify answers were included in the prompt
        call_args = mock_openai_service.create_chat_completion.call_args
        messages = call_args[1]["messages"]
        system_content = messages[0]["content"]
        user_content = messages[1]["content"]

        assert "age" in user_content
        assert "30" in user_content

    @pytest.mark.asyncio
    async def test_explain_concept(self, finance_service, mock_openai_service):
        """Test concept explanation."""
        response = await finance_service.explain_financial_concept(
            concept="compound interest",
            user_knowledge_level="beginner"
        )

        mock_openai_service.create_chat_completion.assert_called_once()

        # Verify concept and knowledge level were included
        call_args = mock_openai_service.create_chat_completion.call_args
        messages = call_args[1]["messages"]
        user_content = messages[1]["content"]

        assert "compound interest" in user_content
        assert "beginner" in user_content

    @pytest.mark.asyncio
    async def test_contextual_instructions_investment(self, finance_service, mock_openai_service):
        """Test that contextual instructions are added for investment queries."""
        response = await finance_service.get_financial_advice(
            user_query="How should I invest in stocks?"
        )

        call_args = mock_openai_service.create_chat_completion.call_args
        messages = call_args[1]["messages"]
        system_content = messages[0]["content"]

        # Should include investment-specific instructions
        assert "past performance doesn't guarantee future results" in system_content

    @pytest.mark.asyncio
    async def test_contextual_instructions_debt(self, finance_service, mock_openai_service):
        """Test that contextual instructions are added for debt queries."""
        response = await finance_service.get_financial_advice(
            user_query="How should I pay off my credit card debt?"
        )

        call_args = mock_openai_service.create_chat_completion.call_args
        messages = call_args[1]["messages"]
        system_content = messages[0]["content"]

        # Should include debt-specific instructions
        assert "high-interest debt" in system_content

    @pytest.mark.asyncio
    async def test_safety_disclaimers_added(self, finance_service, mock_openai_service):
        """Test that safety disclaimers are always added to responses."""
        mock_openai_service.create_chat_completion.return_value = {
            "id": "test-id",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "o3-mini",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Here's some investment advice."
                },
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 150}
        }

        response = await finance_service.get_financial_advice(
            user_query="How should I invest?"
        )

        content = response["choices"][0]["message"]["content"]

        # Verify safety disclaimers are present
        assert "disclaimers" in content.lower()
        assert "not a licensed financial advisor" in content.lower()
        assert "consult" in content.lower()

    def test_system_instructions_comprehensive(self, finance_service):
        """Test that system instructions cover all required areas."""
        instructions = finance_service.system_instructions

        # Core principles
        assert "risk awareness" in instructions.lower()
        assert "educational focus" in instructions.lower()
        assert "regulatory compliance" in instructions.lower()

        # Safety protocols
        assert "disclaimer" in instructions.lower()
        assert "professional" in instructions.lower()

        # Response guidelines
        assert "communication style" in instructions.lower()
        assert "educational approach" in instructions.lower()


class TestFinanceAdvisorServiceIntegration:
    """Integration tests for FinanceAdvisorService."""

    def test_service_initialization(self):
        """Test that service initializes correctly."""
        service = get_finance_advisor_service()
        assert service is not None
        assert service.model == "o3-mini"
        assert service.system_instructions is not None

    def test_global_service_singleton(self):
        """Test that global service follows singleton pattern."""
        service1 = get_finance_advisor_service()
        service2 = get_finance_advisor_service()
        assert service1 is service2


# Example test data for different scenarios
TEST_SCENARIOS = [
    {
        "name": "investment_advice",
        "query": "Should I invest in individual stocks or index funds?",
        "expected_context": "diversification"
    },
    {
        "name": "debt_management",
        "query": "How should I prioritize paying off my debts?",
        "expected_context": "high-interest"
    },
    {
        "name": "budgeting",
        "query": "What's the 50/30/20 rule?",
        "expected_context": "budget"
    },
    {
        "name": "retirement",
        "query": "How much should I save for retirement?",
        "expected_context": "compound interest"
    }
]


@pytest.mark.parametrize("scenario", TEST_SCENARIOS)
def test_contextual_instructions_coverage(scenario):
    """Test that all query types get appropriate contextual instructions."""
    service = FinanceAdvisorService()

    # Get the contextual instructions for this query
    instructions = service._get_contextual_instructions(scenario["query"])

    # Verify expected context is included
    assert scenario["expected_context"].lower() in instructions.lower()

