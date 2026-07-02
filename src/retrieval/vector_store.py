"""
Vector Store for Assessment Retrieval

Uses sentence transformers + FAISS for semantic search over SHL assessments.
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


class AssessmentRetriever:
    """Vector-based semantic search for SHL assessments."""
    
    def __init__(
        self,
        catalog_path: str = "data/catalog/shl_catalog.json",
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize retriever with catalog and embedding model.
        
        Args:
            catalog_path: Path to catalog JSON file
            model_name: Sentence transformer model name
        """
        self.catalog_path = Path(catalog_path)
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        
        self.assessments: List[Dict[str, Any]] = []
        self.index: Optional[faiss.Index] = None
        self.embeddings: Optional[np.ndarray] = None
        
    def load_catalog(self):
        """Load assessment catalog from JSON."""
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            self.assessments = json.load(f)
        print(f"Loaded {len(self.assessments)} assessments from catalog")
        
    def build_index(self, force_rebuild: bool = False):
        """
        Build FAISS index from assessment embeddings.
        
        Args:
            force_rebuild: Rebuild even if cached index exists
        """
        cache_path = self.catalog_path.parent / "index.faiss"
        embeddings_path = self.catalog_path.parent / "embeddings.pkl"
        
        # Try loading cached index
        if not force_rebuild and cache_path.exists() and embeddings_path.exists():
            print("Loading cached index...")
            self.index = faiss.read_index(str(cache_path))
            with open(embeddings_path, 'rb') as f:
                self.embeddings = pickle.load(f)
            print("Index loaded from cache")
            return
        
        # Build fresh index
        print("Building vector index...")
        texts = [self._create_search_text(assessment) for assessment in self.assessments]
        
        self.embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        
        # Create FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product = cosine similarity with normalized vectors
        self.index.add(self.embeddings.astype('float32'))
        
        # Cache index
        faiss.write_index(self.index, str(cache_path))
        with open(embeddings_path, 'wb') as f:
            pickle.dump(self.embeddings, f)
        
        print(f"Index built with {len(self.assessments)} assessments")
        
    def _create_search_text(self, assessment: Dict[str, Any]) -> str:
        """
        Create searchable text representation of an assessment.
        
        Combines name, description, and metadata into a single string for embedding.
        """
        parts = [
            assessment.get('name', ''),
            assessment.get('description', ''),
            assessment.get('full_description', ''),
            f"Category: {assessment.get('category', '')}",
            f"Type: {self._expand_test_type(assessment.get('test_type', ''))}",
        ]
        
        if assessment.get('features'):
            parts.append("Features: " + " ".join(assessment['features']))
        
        if assessment.get('competencies'):
            parts.append(f"Measures: {assessment['competencies']}")
        
        return " ".join(filter(None, parts))
    
    def _expand_test_type(self, test_type: str) -> str:
        """Expand test type code to full text for better embedding."""
        type_map = {
            'P': 'Personality Behavioral Motivation',
            'K': 'Knowledge Technical Coding Programming',
            'A': 'Ability Cognitive Numerical Verbal',
            'S': 'Situational Judgment',
            'O': 'Other'
        }
        return type_map.get(test_type, 'Assessment')
    
    def search(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant assessments.
        
        Args:
            query: Search query (natural language)
            k: Number of results to return
            filters: Optional metadata filters (test_type, category, etc.)
            
        Returns:
            List of assessment dictionaries with similarity scores
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        # Encode query
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True
        ).astype('float32')
        
        # Search FAISS index
        # Get more candidates for filtering
        search_k = k * 3 if filters else k
        scores, indices = self.index.search(query_embedding, search_k)
        
        # Get results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= len(self.assessments):
                continue
                
            assessment = self.assessments[idx].copy()
            assessment['similarity_score'] = float(score)
            
            # Apply filters
            if filters and not self._matches_filters(assessment, filters):
                continue
            
            results.append(assessment)
            
            if len(results) >= k:
                break
        
        return results
    
    def _matches_filters(self, assessment: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if assessment matches all filters."""
        for key, value in filters.items():
            if key not in assessment:
                continue
            
            assessment_value = assessment[key]
            
            # Handle list filters (OR logic)
            if isinstance(value, list):
                if assessment_value not in value:
                    return False
            # Handle exact match
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
        """
        Retrieve multiple assessments for comparison.
        
        Args:
            names: List of assessment names to compare
            
        Returns:
            List of assessment dictionaries
        """
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
        """
        Re-rank results based on conversation context.
        
        Args:
            results: Initial search results
            context: Conversation context (role, seniority, skills, etc.)
            
        Returns:
            Re-ranked results
        """
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
            
            # Boost based on specific skills match
            skills = context.get('skills', [])
            assessment_text = self._create_search_text(result).lower()
            for skill in skills:
                if skill.lower() in assessment_text:
                    boost += 0.05
            
            result['similarity_score'] += boost
        
        # Re-sort by adjusted score
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results


def main():
    """Test the retriever."""
    retriever = AssessmentRetriever()
    retriever.load_catalog()
    retriever.build_index()
    
    # Test search
    results = retriever.search("Java developer mid-level", k=5)
    print("\nSearch results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['name']} (score: {result['similarity_score']:.3f})")
        print(f"   Type: {result['test_type']}, URL: {result['url']}")


if __name__ == "__main__":
    main()
