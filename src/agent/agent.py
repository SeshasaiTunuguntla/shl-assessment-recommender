"""
Main Agent Logic

Orchestrates conversation management, retrieval, and LLM calls.
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
import anthropic

from .prompts import build_system_message, get_few_shot_examples, should_refuse
from .conversation_manager import ConversationManager, ConversationState
from ..retrieval.vector_store import AssessmentRetriever


class AssessmentAgent:
    """Main conversational agent for SHL assessment recommendations."""
    
    def __init__(
        self,
        retriever: AssessmentRetriever,
        llm_provider: str = "openai",
        model: str = "gpt-4-turbo-preview"
    ):
        """
        Initialize agent with retriever and LLM client.
        
        Args:
            retriever: AssessmentRetriever instance
            llm_provider: 'openai', 'anthropic', 'groq', or 'gemini'
            model: Model name
        """
        self.retriever = retriever
        self.llm_provider = llm_provider
        self.model = model
        
        # Initialize LLM client
        if llm_provider == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif llm_provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif llm_provider == "groq":
            # Groq uses OpenAI-compatible API
            self.client = OpenAI(
                api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1"
            )
        elif llm_provider == "gemini":
            # For future Gemini support
            raise ValueError("Gemini provider not yet implemented. Use 'openai' or 'groq'")
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        self.system_message = build_system_message()
        
    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Process a conversation turn.
        
        Args:
            messages: List of conversation messages (role, content)
            
        Returns:
            {
                "reply": str,
                "recommendations": List[Dict],
                "end_of_conversation": bool
            }
        """
        # Initialize conversation manager
        manager = ConversationManager()
        manager.update_from_history(messages)
        
        # Get last user message
        last_user_message = next(
            (m['content'] for m in reversed(messages) if m['role'] == 'user'),
            ""
        )
        
        # Check for refusal triggers
        should_refuse_flag, refusal_response = should_refuse(last_user_message)
        if should_refuse_flag:
            return {
                "reply": refusal_response,
                "recommendations": [],
                "end_of_conversation": False
            }
        
        # Handle different conversation states
        if manager.state == ConversationState.COMPARING:
            return self._handle_comparison(last_user_message, manager)
        
        elif manager.should_recommend():
            return self._handle_recommendation(messages, manager)
        
        elif manager.should_ask_clarifying_question():
            return self._handle_clarification(messages, manager)
        
        else:
            # General conversation - let LLM handle
            return self._handle_general_conversation(messages, manager)
    
    def _handle_clarification(
        self,
        messages: List[Dict[str, str]],
        manager: ConversationManager
    ) -> Dict[str, Any]:
        """Handle clarification phase - ask questions to gather context."""
        # Generate clarifying question using LLM
        clarification_prompt = f"""The user needs help finding SHL assessments but hasn't provided enough information yet.

Current context:
- Role: {manager.context.role or 'unknown'}
- Seniority: {manager.context.seniority or 'unknown'}
- Skills: {', '.join(manager.context.skills) or 'unknown'}

Ask a natural, conversational follow-up question to gather missing information. Keep it concise and friendly."""
        
        full_messages = self._build_messages(messages, clarification_prompt)
        reply = self._call_llm(full_messages)
        
        return {
            "reply": reply,
            "recommendations": [],
            "end_of_conversation": False
        }
    
    def _handle_recommendation(
        self,
        messages: List[Dict[str, str]],
        manager: ConversationManager
    ) -> Dict[str, Any]:
        """Handle recommendation phase - provide assessment shortlist."""
        # Search for relevant assessments
        query = manager.context.to_query_string()
        
        # Determine filters
        filters = {}
        if manager.context.test_type_preferences:
            filters['test_type'] = manager.context.test_type_preferences
        
        # Retrieve candidates
        results = self.retriever.search(query, k=15, filters=filters if filters else None)
        
        # Re-rank based on context
        results = self.retriever.rerank_by_context(results, manager.context.to_dict())
        
        # Select top 5-8 for recommendation
        num_recommendations = min(len(results), 8)
        top_results = results[:num_recommendations]
        
        # Build recommendation prompt
        recommendations_text = self._format_results_for_prompt(top_results)
        
        recommendation_prompt = f"""Based on the conversation, recommend appropriate SHL assessments to the user.

User requirements:
{json.dumps(manager.context.to_dict(), indent=2)}

Available assessments (ranked by relevance):
{recommendations_text}

Provide a natural, helpful response that:
1. Acknowledges their requirements
2. Recommends 1-8 most relevant assessments
3. Explains why each assessment fits their needs
4. Groups by category (technical/personality/cognitive) if helpful

Be specific about assessment names and cite them exactly as shown above."""
        
        full_messages = self._build_messages(messages, recommendation_prompt)
        reply = self._call_llm(full_messages)
        
        # Structure recommendations
        recommendations = [
            {
                "name": r['name'],
                "url": r['url'],
                "test_type": r['test_type']
            }
            for r in top_results
        ]
        
        return {
            "reply": reply,
            "recommendations": recommendations,
            "end_of_conversation": False
        }
    
    def _handle_comparison(
        self,
        message: str,
        manager: ConversationManager
    ) -> Dict[str, Any]:
        """Handle comparison requests between assessments."""
        # Extract assessment names to compare
        assessment_names = manager.is_comparison_request(message)
        
        if not assessment_names or len(assessment_names) < 2:
            return {
                "reply": "I'd be happy to compare assessments for you! Could you specify which two assessments you'd like me to compare?",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        # Retrieve assessments
        assessments = self.retriever.compare_assessments(assessment_names)
        
        if len(assessments) < 2:
            return {
                "reply": f"I couldn't find one or more of those assessments in the SHL catalog. Could you check the names and try again? The assessments should be from the SHL Individual Test Solutions catalog.",
                "recommendations": [],
                "end_of_conversation": False
            }
        
        # Build comparison prompt
        comparison_data = self._format_results_for_prompt(assessments)
        comparison_prompt = f"""The user wants to compare these SHL assessments:

{comparison_data}

Provide a clear comparison highlighting:
1. What each assessment measures
2. Key differences in focus and use cases
3. Which situations each is best for

Base your answer ONLY on the catalog data provided. Be specific and helpful."""
        
        messages = [{"role": "user", "content": message}]
        full_messages = self._build_messages(messages, comparison_prompt)
        reply = self._call_llm(full_messages)
        
        return {
            "reply": reply,
            "recommendations": [],
            "end_of_conversation": False
        }
    
    def _handle_general_conversation(
        self,
        messages: List[Dict[str, str]],
        manager: ConversationManager
    ) -> Dict[str, Any]:
        """Handle general conversation flow."""
        full_messages = self._build_messages(messages)
        reply = self._call_llm(full_messages)
        
        return {
            "reply": reply,
            "recommendations": [],
            "end_of_conversation": False
        }
    
    def _build_messages(
        self,
        conversation: List[Dict[str, str]],
        additional_context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build full message list for LLM including system prompt."""
        messages = [{"role": "system", "content": self.system_message}]
        
        # Add few-shot examples
        for example in get_few_shot_examples()[:3]:  # Limit to save tokens
            messages.append({"role": "user", "content": example["user"]})
            messages.append({"role": "assistant", "content": example["assistant"]})
        
        # Add conversation history
        messages.extend(conversation)
        
        # Add additional context if provided
        if additional_context:
            messages.append({"role": "system", "content": additional_context})
        
        return messages
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call LLM and return response text."""
        if self.llm_provider in ["openai", "groq"]:
            # Both OpenAI and Groq use the same API format
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            return response.choices[0].message.content
        
        elif self.llm_provider == "anthropic":
            # Anthropic uses different message format
            system = next((m['content'] for m in messages if m['role'] == 'system'), None)
            conversation_messages = [m for m in messages if m['role'] != 'system']
            
            response = self.client.messages.create(
                model=self.model,
                system=system,
                messages=conversation_messages,
                temperature=0.7,
                max_tokens=800
            )
            return response.content[0].text
        
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
    
    def _format_results_for_prompt(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for inclusion in prompt."""
        formatted = []
        for i, result in enumerate(results, 1):
            entry = f"""{i}. {result['name']}
   URL: {result['url']}
   Type: {result['test_type']}
   Description: {result.get('description', 'N/A')}"""
            
            if result.get('features'):
                entry += f"\n   Features: {', '.join(result['features'][:3])}"
            
            formatted.append(entry)
        
        return "\n\n".join(formatted)
