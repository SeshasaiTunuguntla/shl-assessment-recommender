try:
    from .vector_store import AssessmentRetriever
except ImportError:
    # Fallback to simple search if vector dependencies not available
    from .simple_search import SimpleRetriever as AssessmentRetriever

__all__ = ['AssessmentRetriever']
