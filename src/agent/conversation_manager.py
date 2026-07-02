"""
Conversation Manager

Handles agent state, context extraction, and decision-making logic.
"""

import re
from typing import List, Dict, Any, Optional
from enum import Enum


class ConversationState(Enum):
    """Agent conversation states."""
    CLARIFYING = "clarifying"
    RECOMMENDING = "recommending"
    REFINING = "refining"
    COMPARING = "comparing"
    REFUSING = "refusing"
    COMPLETE = "complete"


class ConversationContext:
    """Extract and maintain conversation context."""
    
    def __init__(self):
        self.role: Optional[str] = None
        self.role_category: Optional[str] = None  # technical, leadership, sales, etc.
        self.seniority: Optional[str] = None  # junior, mid, senior, lead, manager
        self.skills: List[str] = []
        self.team_context: Optional[str] = None
        self.additional_requirements: List[str] = []
        self.test_type_preferences: List[str] = []  # P, K, A, S
        
    def has_minimum_context(self) -> bool:
        """Check if we have enough context to make recommendations."""
        return bool(self.role or len(self.skills) >= 2)
    
    def update_from_message(self, message: str):
        """Extract context from a user message."""
        message_lower = message.lower()
        
        # Extract role
        role_patterns = [
            r"(?:hiring|looking for|need|want)\s+(?:a\s+)?(\w+\s+)?(\w+)",
            r"(\w+)\s+(?:developer|engineer|manager|analyst|designer)",
        ]
        for pattern in role_patterns:
            match = re.search(pattern, message_lower)
            if match:
                self.role = match.group(0)
                break
        
        # Infer role category
        if any(kw in message_lower for kw in ['developer', 'engineer', 'programmer', 'technical', 'software']):
            self.role_category = 'technical'
        elif any(kw in message_lower for kw in ['manager', 'lead', 'director', 'executive']):
            self.role_category = 'leadership'
        elif any(kw in message_lower for kw in ['sales', 'account', 'business development']):
            self.role_category = 'sales'
        
        # Extract seniority
        seniority_map = {
            'junior': ['junior', 'entry', 'entry-level', '0-2 years'],
            'mid': ['mid-level', 'intermediate', '2-5 years', '3-6 years'],
            'senior': ['senior', 'sr', '5+ years', 'experienced'],
            'lead': ['lead', 'principal', 'staff'],
            'manager': ['manager', 'head', 'director']
        }
        for level, keywords in seniority_map.items():
            if any(kw in message_lower for kw in keywords):
                self.seniority = level
                break
        
        # Extract skills (common technologies and domains)
        skill_keywords = [
            'java', 'python', 'javascript', 'react', 'angular', 'node',
            'aws', 'azure', 'gcp', 'cloud', 'docker', 'kubernetes',
            'sql', 'nosql', 'mongodb', 'postgresql',
            'microservices', 'rest', 'api', 'backend', 'frontend', 'full-stack',
            'machine learning', 'data science', 'analytics',
            'agile', 'scrum', 'leadership', 'communication'
        ]
        for skill in skill_keywords:
            if skill in message_lower and skill not in self.skills:
                self.skills.append(skill)
        
        # Extract team context
        if 'team' in message_lower or 'stakeholder' in message_lower:
            self.team_context = 'collaborative'
        
        # Extract test type preferences
        if any(kw in message_lower for kw in ['personality', 'behavioral', 'opq']):
            if 'P' not in self.test_type_preferences:
                self.test_type_preferences.append('P')
        if any(kw in message_lower for kw in ['technical', 'coding', 'programming']):
            if 'K' not in self.test_type_preferences:
                self.test_type_preferences.append('K')
        if any(kw in message_lower for kw in ['cognitive', 'ability', 'numerical', 'verbal']):
            if 'A' not in self.test_type_preferences:
                self.test_type_preferences.append('A')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'role': self.role,
            'role_category': self.role_category,
            'seniority': self.seniority,
            'skills': self.skills,
            'team_context': self.team_context,
            'test_type_preferences': self.test_type_preferences
        }
    
    def to_query_string(self) -> str:
        """Convert context to a search query."""
        parts = []
        if self.role:
            parts.append(self.role)
        if self.seniority:
            parts.append(self.seniority)
        if self.skills:
            parts.extend(self.skills[:3])  # Top 3 skills
        if self.team_context:
            parts.append('teamwork collaboration')
        return ' '.join(parts)


class ConversationManager:
    """Manages conversation state and decision logic."""
    
    def __init__(self):
        self.state = ConversationState.CLARIFYING
        self.context = ConversationContext()
        self.last_recommendations: List[Dict[str, Any]] = []
        self.turn_count = 0
        
    def update_from_history(self, messages: List[Dict[str, str]]):
        """Update state from conversation history."""
        self.turn_count = len([m for m in messages if m['role'] == 'user'])
        
        # Extract context from user messages
        for message in messages:
            if message['role'] == 'user':
                self.context.update_from_message(message['content'])
        
        # Determine current state
        self._update_state(messages)
    
    def _update_state(self, messages: List[Dict[str, str]]):
        """Infer conversation state from history."""
        if not messages:
            self.state = ConversationState.CLARIFYING
            return
        
        last_user_msg = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), '')
        last_user_lower = last_user_msg.lower()
        
        # Check for comparison request
        comparison_patterns = [
            r"difference between",
            r"compare",
            r"vs",
            r"versus",
            r"which is better"
        ]
        if any(re.search(pattern, last_user_lower) for pattern in comparison_patterns):
            self.state = ConversationState.COMPARING
            return
        
        # Check for refinement
        refinement_keywords = ['add', 'also', 'include', 'plus', 'additionally', 'remove', 'without', 'except']
        if self.last_recommendations and any(kw in last_user_lower for kw in refinement_keywords):
            self.state = ConversationState.REFINING
            return
        
        # Check if we have enough context to recommend
        if self.context.has_minimum_context() and self.state == ConversationState.CLARIFYING:
            self.state = ConversationState.RECOMMENDING
            return
        
        # Default to clarifying if not enough context
        if not self.context.has_minimum_context():
            self.state = ConversationState.CLARIFYING
    
    def should_recommend(self) -> bool:
        """Check if agent should provide recommendations."""
        return (
            self.state in [ConversationState.RECOMMENDING, ConversationState.REFINING]
            and self.context.has_minimum_context()
        )
    
    def should_ask_clarifying_question(self) -> bool:
        """Check if agent should ask for more context."""
        return (
            self.state == ConversationState.CLARIFYING
            and not self.context.has_minimum_context()
            and self.turn_count < 3  # Don't drag on too long
        )
    
    def is_comparison_request(self, message: str) -> Optional[List[str]]:
        """
        Check if message is asking to compare assessments.
        
        Returns:
            List of assessment names if comparison request, None otherwise
        """
        message_lower = message.lower()
        
        # Check for comparison keywords
        comparison_patterns = [
            r"difference between (.+?) and (.+)",
            r"compare (.+?) (?:and|vs|versus) (.+)",
            r"what(?:'s| is) (.+?) vs (.+)"
        ]
        
        for pattern in comparison_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Extract assessment names
                names = [match.group(1).strip(), match.group(2).strip()]
                return [self._clean_assessment_name(name) for name in names]
        
        return None
    
    def _clean_assessment_name(self, name: str) -> str:
        """Clean up extracted assessment name."""
        # Remove common prefixes/suffixes
        name = re.sub(r'^(?:the|an|a)\s+', '', name)
        name = re.sub(r'\s+(?:test|assessment|questionnaire)$', '', name)
        return name.title()
    
    def get_next_clarifying_question(self) -> str:
        """Generate next clarifying question based on missing context."""
        if not self.context.role and not self.context.skills:
            return "What role are you hiring for?"
        
        if not self.context.seniority and self.context.role_category == 'technical':
            return "What's the seniority level you're looking for? (e.g., junior, mid-level, senior)"
        
        if self.context.role_category == 'technical' and len(self.context.skills) < 2:
            return "What are the key technical skills or technologies they'll need?"
        
        if self.context.seniority in ['senior', 'lead', 'manager'] and not self.context.team_context:
            return "Will they be working with a team or stakeholders?"
        
        # Generic fallback
        return "Can you tell me more about the role's responsibilities and required skills?"
    
    def extract_assessment_names_from_text(self, text: str) -> List[str]:
        """Extract assessment names mentioned in text."""
        # Common SHL assessment patterns
        patterns = [
            r'\b[A-Z]{2,5}\d*[a-z]?\b',  # OPQ32r, GSA, MQ, etc.
            r'\b(?:Java|Python|C\+\+|JavaScript)\s+\d+(?:\s+\([^)]+\))?\b',  # Java 8 (New)
            r'Verify\s+[A-Z]\+?',  # Verify G+
        ]
        
        names = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            names.extend(matches)
        
        return list(set(names))  # Deduplicate
