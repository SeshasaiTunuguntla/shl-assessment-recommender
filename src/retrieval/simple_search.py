"""
Simple keyword-based search (no vector embeddings needed)
Fallback for deployment environments without heavy ML dependencies
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class SimpleRetriever:
    """Simple keyword-based search for assessments."""
    
    def __init__(self, catalog_path: str = "data/catalog/shl_catalog.json"):
        self.catalog_path = Path(catalog_path)
        self.assessments: List[Dict[str, Any]] = []
        
    def load_catalog(self):
        """Load assessment catalog from JSON."""
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            self.assessments = json.load(f)
        print(f"Loaded {len(self.assessments)} assessments from catalog")
        
    def build_index(self, force_rebuild: bool = False):
        """Compatibility method - no index needed for simple search."""
        pass
        
    def search(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Simple keyword-based search.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional metadata filters
            
        Returns:
            List of matching assessments
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        for assessment in self.assessments:
            # Apply filters first
            if filters and not self._matches_filters(assessment, filters):
                continue
            
            # Calculate simple relevance score
            score = self._calculate_score(assessment, query_words, query_lower)
            
            if score > 0:
                assessment_copy = assessment.copy()
                assessment_copy['similarity_score'] = score
                results.append(assessment_copy)
        
        # Sort by score
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:k]
    
    def _calculate_score(self, assessment: Dict[str, Any], query_words: set, query_lower: str) -> float:
        """Calculate relevance score based on keyword matches."""
        score = 0.0
        
        # Check name
        name_lower = assessment.get('name', '').lower()
        if query_lower in name_lower:
            score += 5.0
        score += sum(2.0 for word in query_words if word in name_lower)
        
        # Check description
        desc_lower = assessment.get('description', '').lower()
        if query_lower in desc_lower:
            score += 3.0
        score += sum(1.0 for word in query_words if word in desc_lower)
        
        # Check category
        category_lower = assessment.get('category', '').lower()
        score += sum(1.5 for word in query_words if word in category_lower)
        
        # Check test type keywords
        test_type = assessment.get('test_type', '')
        type_keywords = self._get_type_keywords(test_type)
        score += sum(2.0 for word in query_words if word in type_keywords)
        
        return score
    
    def _get_type_keywords(self, test_type: str) -> set:
        """Get keywords associated with test type."""
        type_map = {
            'K': {'knowledge', 'technical', 'coding', 'programming', 'java', 'python'},
            'P': {'personality', 'behavioral', 'traits', 'opq'},
            'A': {'ability', 'cognitive', 'numerical', 'verbal', 'reasoning'},
            'S': {'situational', 'judgment', 'sjt', 'decision'},
        }
        return type_map.get(test_type, set())
    
    def _matches_filters(self, assessment: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if assessment matches filters."""
        for key, value in filters.items():
            if key not in assessment:
                continue
            
            assessment_value = assessment[key]
            
            if isinstance(value, list):
                if assessment_value not in value:
                    return False
            elif assessment_value != value:
                return False
        
        return True
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve assessment by exact name."""
        for assessment in self.assessments:
            if assessment['name'].lower() == name.lower():
                return assessment.copy()
        return None
    
    def compare_assessments(self, names: List[str]) -> List[Dict[str, Any]]:
        """Retrieve multiple assessments for comparison."""
        results = []
        for name in names:
            assessment = self.get_by_name(name)
            if assessment:
                results.append(assessment)
        return results
    
    def rerank_by_context(
        self,
        results: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Re-rank results based on conversation context."""
        for result in results:
            boost = 0.0
            
            # Boost technical tests for technical roles
            if context.get('role_category') == 'technical':
                if result.get('test_type') == 'K':
                    boost += 0.15
            
            # Boost personality tests for leadership roles
            if context.get('seniority') in ['senior', 'lead', 'manager']:
                if result.get('test_type') == 'P':
                    boost += 0.1
            
            # Boost based on skills match
            skills = context.get('skills', [])
            assessment_text = f"{result.get('name', '')} {result.get('description', '')}".lower()
            for skill in skills:
                if skill.lower() in assessment_text:
                    boost += 0.05
            
            result['similarity_score'] += boost
        
        # Re-sort
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results


# Alias for compatibility
AssessmentRetriever = SimpleRetriever
