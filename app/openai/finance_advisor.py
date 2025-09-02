"""
Finance Advisor AI Service

Specialized service for financial advice using o3-mini model with comprehensive
system instructions and safety checks.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .service import OpenAIService, OpenAIConfig
from .models import ChatMessage, ChatCompletionRequest
from ..logging import get_logger

logger = get_logger(__name__)


class FinanceAdvisorService:
    """
    Specialized service for financial advice using o3-mini model.

    Features:
    - Comprehensive system instructions for financial advice
    - Risk assessment and safety checks
    - Regulatory compliance reminders
    - Investment education focus
    - Conservative approach to recommendations
    """

    def __init__(self, openai_service: Optional[OpenAIService] = None):
        self.openai_service = openai_service or OpenAIService()
        self.model = "o3-mini"  # Use o3-mini as specified

        # System instructions for financial advice
        self.system_instructions = self._get_system_instructions()

    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for financial advice."""
        return """# Financial Advisor AI - Expert Guidance System

You are an expert financial advisor AI powered by advanced reasoning capabilities. Your role is to provide professional, ethical, and educational financial guidance while maintaining the highest standards of responsibility and compliance.

## Core Principles

### 1. Risk Awareness & Conservative Approach
- Always emphasize that all investments carry risk
- Never guarantee returns or promise specific outcomes
- Focus on risk management and diversification
- Recommend consulting licensed professionals for personalized advice

### 2. Educational Focus
- Explain financial concepts clearly and accessibly
- Help users understand the "why" behind recommendations
- Encourage financial literacy and long-term thinking
- Provide context for market conditions and economic factors

### 3. Regulatory Compliance
- Clearly state that you are not a licensed financial advisor
- Remind users to consult qualified professionals
- Avoid giving specific investment recommendations
- Focus on general principles and education

## Response Guidelines

### Communication Style
- Professional yet approachable tone
- Clear, concise explanations
- Use analogies when helpful
- Avoid financial jargon or explain it when necessary

### Risk Management
- Always include risk warnings
- Discuss time horizons and liquidity needs
- Emphasize emergency fund importance
- Highlight the difference between saving and investing

### Educational Approach
- Break down complex topics into digestible parts
- Provide actionable next steps
- Suggest learning resources
- Encourage ongoing education

## Specialized Knowledge Areas

### Investment Basics
- Asset allocation principles
- Diversification strategies
- Risk tolerance assessment
- Long-term vs short-term goals

### Debt Management
- Good debt vs bad debt
- Debt payoff strategies
- Credit score importance
- Interest rate impact

### Budgeting & Saving
- 50/30/20 rule explanation
- Emergency fund guidelines
- Expense tracking methods
- Savings rate optimization

### Retirement Planning
- Compound interest power
- Retirement account types
- Contribution matching
- Required minimum distributions

## Safety Protocols

### Red Flags to Watch For
- Urgent investment opportunities
- Guaranteed high returns
- Unsolicited financial advice requests
- Complex derivative products
- Leverage recommendations

### Ethical Boundaries
- Never recommend specific stocks or cryptocurrencies
- Avoid day trading encouragement
- Discourage emotional decision-making
- Promote diversified, long-term strategies

## Response Structure

For each interaction:
1. **Acknowledge** the user's question or concern
2. **Educate** on relevant financial principles
3. **Provide guidance** with risk considerations
4. **Suggest next steps** and professional consultation
5. **Offer resources** for further learning

Remember: Your goal is to empower users with knowledge while keeping them safe from financial harm. Always err on the side of caution and education over speculation."""

    def _get_contextual_instructions(self, user_query: str) -> str:
        """Get contextual instructions based on the user's query."""
        query_lower = user_query.lower()

        # Investment-related queries
        if any(keyword in query_lower for keyword in ['invest', 'stock', 'bond', 'etf', 'mutual fund', 'portfolio']):
            return """
            For investment-related questions:
            - Emphasize that past performance doesn't guarantee future results
            - Discuss asset allocation based on risk tolerance and time horizon
            - Recommend diversified, low-cost index funds for most investors
            - Stress the importance of understanding fees and expenses
            - Suggest dollar-cost averaging for long-term investing"""

        # Debt-related queries
        elif any(keyword in query_lower for keyword in ['debt', 'loan', 'credit', 'mortgage', 'student loan']):
            return """
            For debt-related questions:
            - Prioritize high-interest debt payoff
            - Explain debt consolidation options
            - Discuss credit score impact
            - Recommend debt management plans when appropriate
            - Emphasize the psychological aspects of debt reduction"""

        # Budgeting queries
        elif any(keyword in query_lower for keyword in ['budget', 'saving', 'expense', 'income', 'salary']):
            return """
            For budgeting questions:
            - Introduce the 50/30/20 rule as a starting framework
            - Stress emergency fund importance (3-6 months of expenses)
            - Discuss tracking methods and tools
            - Explain lifestyle inflation risks
            - Recommend regular budget reviews"""

        # Retirement queries
        elif any(keyword in query_lower for keyword in ['retirement', '401k', 'ira', 'pension', 'social security']):
            return """
            For retirement questions:
            - Explain compound interest and time value of money
            - Discuss employer matching contributions
            - Cover different retirement account types
            - Address required minimum distributions
            - Emphasize starting early and consistent contributions"""

        # General financial queries
        else:
            return """
            For general financial questions:
            - Start with fundamental concepts
            - Build understanding progressively
            - Connect topics to broader financial literacy
            - Encourage building good financial habits
            - Suggest creating a comprehensive financial plan"""

    def _add_safety_disclaimers(self) -> str:
        """Add required safety disclaimers to responses."""
        return """

---

**Important Disclaimers:**
- I am an AI assistant and not a licensed financial advisor
- This is not personalized financial advice
- All investments carry risk of loss
- Past performance does not guarantee future results
- Consult with qualified financial professionals for your specific situation
- Consider your risk tolerance, time horizon, and financial goals
- Tax laws and regulations change frequently

For personalized advice, please consult a certified financial planner (CFP), certified public accountant (CPA), or licensed investment advisor."""

    async def get_financial_advice(
        self,
        user_query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Get financial advice using o3-mini model with specialized instructions.

        Args:
            user_query: User's financial question
            conversation_history: Previous conversation messages
            temperature: Sampling temperature (0.0 to 2.0)

        Returns:
            AI response with financial advice
        """
        try:
            logger.info("Processing financial advice request with o3-mini model")

            # Build conversation with system instructions
            messages = [
                ChatMessage(
                    role="system",
                    content=self.system_instructions + self._get_contextual_instructions(user_query)
                )
            ]

            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-10:]:  # Limit to last 10 messages
                    messages.append(ChatMessage(**msg))

            # Add current user query
            messages.append(ChatMessage(
                role="user",
                content=user_query
            ))

            # Create request
            request = ChatCompletionRequest(
                messages=messages,
                model=self.model,
                temperature=temperature,
                max_tokens=2000,  # Allow detailed responses
            )

            # Convert to dict for OpenAI API
            messages_dict = [msg.dict() for msg in messages]

            # Get response from OpenAI
            response = await self.openai_service.create_chat_completion(
                messages=messages_dict,
                model=self.model,
                temperature=temperature,
                max_tokens=2000,
            )

            # Add safety disclaimers to response
            if response.get('choices') and len(response['choices']) > 0:
                original_content = response['choices'][0]['message']['content']
                response['choices'][0]['message']['content'] = original_content + self._add_safety_disclaimers()

            logger.info("Financial advice generated successfully")
            return response

        except Exception as e:
            logger.error("Error generating financial advice: %s", str(e))
            raise

    async def assess_financial_risk_profile(
        self,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess user's risk tolerance and financial profile.

        Args:
            answers: User's answers to risk assessment questions

        Returns:
            Risk profile analysis
        """
        try:
            logger.info("Assessing financial risk profile")

            risk_assessment_prompt = f"""
            Based on the following user responses, assess their risk tolerance and provide appropriate investment guidance:

            User Responses:
            {json.dumps(answers, indent=2)}

            Please provide:
            1. Risk tolerance level (Conservative, Moderate, Aggressive)
            2. Recommended asset allocation percentages
            3. Time horizon assessment
            4. Key considerations for their situation
            5. Next steps they should take

            Remember to include all standard disclaimers about investment risk and professional consultation.
            """

            messages = [
                ChatMessage(role="system", content=self.system_instructions),
                ChatMessage(role="user", content=risk_assessment_prompt)
            ]

            messages_dict = [msg.dict() for msg in messages]

            response = await self.openai_service.create_chat_completion(
                messages=messages_dict,
                model=self.model,
                temperature=0.3,  # Lower temperature for consistent analysis
                max_tokens=1500,
            )

            logger.info("Risk profile assessment completed")
            return response

        except Exception as e:
            logger.error("Error assessing risk profile: %s", str(e))
            raise

    async def explain_financial_concept(
        self,
        concept: str,
        user_knowledge_level: str = "beginner"
    ) -> Dict[str, Any]:
        """
        Explain a financial concept at the appropriate knowledge level.

        Args:
            concept: Financial concept to explain
            user_knowledge_level: User's knowledge level (beginner, intermediate, advanced)

        Returns:
            Explanation of the financial concept
        """
        try:
            logger.info("Explaining financial concept: %s for %s level", concept, user_knowledge_level)

            explanation_prompt = f"""
            Explain the financial concept "{concept}" to a {user_knowledge_level} level investor.

            Structure your explanation:
            1. Simple definition
            2. Real-world example
            3. How it affects personal finances
            4. Key considerations or risks
            5. Related concepts they should also understand

            Use clear, simple language and avoid unnecessary jargon. If you must use technical terms, explain them immediately.
            """

            messages = [
                ChatMessage(role="system", content=self.system_instructions),
                ChatMessage(role="user", content=explanation_prompt)
            ]

            messages_dict = [msg.dict() for msg in messages]

            response = await self.openai_service.create_chat_completion(
                messages=messages_dict,
                model=self.model,
                temperature=0.5,
                max_tokens=1500,
            )

            logger.info("Financial concept explanation completed")
            return response

        except Exception as e:
            logger.error("Error explaining financial concept: %s", str(e))
            raise


# Global finance advisor service instance
_finance_advisor_service: Optional[FinanceAdvisorService] = None


def get_finance_advisor_service() -> FinanceAdvisorService:
    """Get or create global finance advisor service instance."""
    global _finance_advisor_service
    if _finance_advisor_service is None:
        _finance_advisor_service = FinanceAdvisorService()
    return _finance_advisor_service

