#!/usr/bin/env python3
"""
Example script for using the Finance Advisor AI API

This script demonstrates how to interact with the finance advisor endpoints
using the o3-mini model with specialized financial prompts.
"""

import asyncio
import json
import os
from typing import Dict, List, Any

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("OPENAI_API_KEY")  # For authentication if needed

class FinanceAdvisorClient:
    """Client for interacting with the Finance Advisor API."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_financial_advice(
        self,
        query: str,
        conversation_history: List[Dict[str, str]] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Get financial advice from the AI advisor."""
        url = f"{self.base_url}/finance-advisor/advice"

        payload = {
            "query": query,
            "temperature": temperature
        }

        if conversation_history:
            payload["conversation_history"] = conversation_history

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    async def assess_risk_profile(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Assess user's financial risk profile."""
        url = f"{self.base_url}/finance-advisor/risk-assessment"

        payload = {"answers": answers}

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    async def explain_concept(
        self,
        concept: str,
        knowledge_level: str = "beginner"
    ) -> Dict[str, Any]:
        """Explain a financial concept."""
        url = f"{self.base_url}/finance-advisor/explain-concept"

        payload = {
            "concept": concept,
            "knowledge_level": knowledge_level
        }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    async def get_capabilities(self) -> Dict[str, Any]:
        """Get finance advisor capabilities."""
        url = f"{self.base_url}/finance-advisor/capabilities"

        response = await self.client.get(url)
        response.raise_for_status()

        return response.json()

    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        url = f"{self.base_url}/finance-advisor/health"

        response = await self.client.get(url)
        response.raise_for_status()

        return response.json()


async def main():
    """Main example function demonstrating finance advisor usage."""

    print("🤖 Finance Advisor AI Demo")
    print("=" * 50)

    async with FinanceAdvisorClient() as client:
        try:
            # Check service health
            print("\n1. Checking service health...")
            health = await client.check_health()
            print(f"✅ Service Status: {health['status']}")
            print(f"📅 Timestamp: {health['timestamp']}")
            print(f"🤖 Model: {health.get('version', 'N/A')}")

            # Get capabilities
            print("\n2. Getting capabilities...")
            capabilities = await client.get_capabilities()
            print(f"🤖 Model: {capabilities['model']}")
            print("📋 Capabilities:")
            for cap in capabilities['capabilities']:
                print(f"   • {cap}")
            print("⚠️  Limitations:")
            for lim in capabilities['limitations']:
                print(f"   • {lim}")

            # Example 1: Basic financial advice
            print("\n3. Getting financial advice...")
            advice = await client.get_financial_advice(
                "I'm 25 years old and just started my first job. How should I manage my money?"
            )
            print("💬 AI Response:")
            print(advice['choices'][0]['message']['content'][:500] + "...")

            # Example 2: Risk assessment
            print("\n4. Risk profile assessment...")
            risk_answers = {
                "age": 25,
                "investment_experience": "beginner",
                "risk_tolerance": "moderate",
                "investment_horizon": "long_term",
                "emergency_fund": "yes",
                "debt_level": "low"
            }
            risk_assessment = await client.assess_risk_profile(risk_answers)
            print("📊 Risk Assessment:")
            print(risk_assessment['choices'][0]['message']['content'][:500] + "...")

            # Example 3: Concept explanation
            print("\n5. Explaining financial concepts...")
            explanation = await client.explain_concept(
                "compound interest",
                knowledge_level="beginner"
            )
            print("📚 Concept Explanation:")
            print(explanation['choices'][0]['message']['content'][:500] + "...")

            # Example 4: Conversation with history
            print("\n6. Conversational advice with history...")
            conversation_history = [
                {
                    "role": "user",
                    "content": "I want to start investing but I'm scared of losing money."
                },
                {
                    "role": "assistant",
                    "content": "That's a common concern! Let's discuss risk management strategies..."
                }
            ]

            follow_up = await client.get_financial_advice(
                "What about index funds? Are they safer?",
                conversation_history=conversation_history
            )
            print("💬 Follow-up Response:")
            print(follow_up['choices'][0]['message']['content'][:500] + "...")

            print("\n🎉 Demo completed successfully!")
            print("\n💡 Key Features Demonstrated:")
            print("   • Educational financial advice")
            print("   • Risk assessment capabilities")
            print("   • Concept explanations")
            print("   • Conversational context")
            print("   • Safety disclaimers and warnings")

        except Exception as e:
            print(f"❌ Error: {e}")
            print("\n🔧 Troubleshooting:")
            print("   • Make sure the backend server is running")
            print("   • Check your OPENAI_API_KEY environment variable")
            print("   • Verify the API endpoints are accessible")


def print_usage_examples():
    """Print usage examples for different scenarios."""
    print("\n📖 Usage Examples:")
    print("=" * 50)

    examples = [
        {
            "title": "Basic Financial Advice",
            "code": '''
curl -X POST http://localhost:8000/finance-advisor/advice \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "How should I start saving for retirement?",
    "temperature": 0.7
  }'
            '''
        },
        {
            "title": "Risk Assessment",
            "code": '''
curl -X POST http://localhost:8000/finance-advisor/risk-assessment \\
  -H "Content-Type: application/json" \\
  -d '{
    "answers": {
      "age": 30,
      "investment_experience": "intermediate",
      "risk_tolerance": "moderate",
      "time_horizon": "10_years"
    }
  }'
            '''
        },
        {
            "title": "Concept Explanation",
            "code": '''
curl -X POST http://localhost:8000/finance-advisor/explain-concept \\
  -H "Content-Type: application/json" \\
  -d '{
    "concept": "diversification",
    "knowledge_level": "beginner"
  }'
            '''
        }
    ]

    for example in examples:
        print(f"\n{example['title']}:")
        print("-" * len(example['title']))
        print(example['code'].strip())


if __name__ == "__main__":
    # Print usage examples first
    print_usage_examples()

    # Run the interactive demo
    print("\n🚀 Running Interactive Demo...")
    print("Make sure your backend server is running on http://localhost:8000")
    input("\nPress Enter to start the demo...")

    asyncio.run(main())
