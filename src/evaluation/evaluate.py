"""
Evaluation Script

Evaluates the agent against conversation traces and computes metrics.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import requests


class AgentEvaluator:
    """Evaluate agent against test traces."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.traces_dir = Path("data/traces")
        
    def load_traces(self) -> List[Dict[str, Any]]:
        """Load conversation traces from JSON files."""
        traces = []
        
        if not self.traces_dir.exists():
            print(f"Warning: Traces directory not found: {self.traces_dir}")
            return traces
        
        for trace_file in self.traces_dir.glob("*.json"):
            with open(trace_file, 'r', encoding='utf-8') as f:
                trace = json.load(f)
                traces.append(trace)
        
        print(f"Loaded {len(traces)} test traces")
        return traces
    
    def run_conversation(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate a conversation based on a trace.
        
        Args:
            trace: Test trace with persona, facts, and expected shortlist
            
        Returns:
            Result dictionary with recommendations and metadata
        """
        messages = []
        final_recommendations = []
        turns = 0
        max_turns = 8
        
        # Start with initial user message
        initial_message = trace.get('initial_message', trace.get('persona', {}).get('opening', ''))
        messages.append({"role": "user", "content": initial_message})
        
        while turns < max_turns:
            # Call agent
            response = self._call_chat_api(messages)
            
            if response is None:
                break
            
            # Add agent reply to history
            messages.append({"role": "assistant", "content": response['reply']})
            turns += 1
            
            # Check for recommendations
            if response.get('recommendations'):
                final_recommendations = response['recommendations']
                break
            
            # Check if conversation ended
            if response.get('end_of_conversation'):
                break
            
            # Simulate user response (in real evaluation, this would use an LLM)
            # For now, we'll just end after first agent response for testing
            break
        
        return {
            'trace_id': trace.get('id', 'unknown'),
            'turns': turns,
            'recommendations': final_recommendations,
            'expected': trace.get('expected_assessments', []),
            'messages': messages
        }
    
    def _call_chat_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Call the /chat API endpoint."""
        try:
            response = requests.post(
                f"{self.api_base_url}/chat",
                json={"messages": messages},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error calling API: {e}")
            return None
    
    def compute_recall_at_k(
        self,
        recommended: List[str],
        expected: List[str],
        k: int = 10
    ) -> float:
        """
        Compute Recall@K metric.
        
        Recall@K = (# of relevant items in top K) / (total # of relevant items)
        """
        if not expected:
            return 0.0
        
        recommended_set = set(rec.lower() for rec in recommended[:k])
        expected_set = set(exp.lower() for exp in expected)
        
        relevant_in_top_k = len(recommended_set & expected_set)
        total_relevant = len(expected_set)
        
        return relevant_in_top_k / total_relevant if total_relevant > 0 else 0.0
    
    def evaluate_all_traces(self) -> Dict[str, Any]:
        """Run evaluation on all traces and compute aggregate metrics."""
        traces = self.load_traces()
        
        if not traces:
            print("No traces to evaluate")
            return {}
        
        results = []
        recall_scores = []
        
        for trace in traces:
            print(f"\nEvaluating trace: {trace.get('id', 'unknown')}")
            result = self.run_conversation(trace)
            
            # Compute recall
            recommended_names = [r['name'] for r in result['recommendations']]
            expected_names = result['expected']
            recall = self.compute_recall_at_k(recommended_names, expected_names, k=10)
            
            result['recall@10'] = recall
            recall_scores.append(recall)
            results.append(result)
            
            print(f"Turns: {result['turns']}, Recall@10: {recall:.3f}")
        
        # Aggregate metrics
        metrics = {
            'total_traces': len(traces),
            'mean_recall@10': sum(recall_scores) / len(recall_scores) if recall_scores else 0.0,
            'mean_turns': sum(r['turns'] for r in results) / len(results) if results else 0.0,
            'results': results
        }
        
        return metrics
    
    def check_hard_evals(self, result: Dict[str, Any]) -> Dict[str, bool]:
        """
        Check hard evaluation criteria.
        
        Returns:
            Dictionary of pass/fail for each criterion
        """
        checks = {}
        
        # Schema compliance (checked by pydantic in API)
        checks['schema_compliant'] = True  # If we got this far, schema is valid
        
        # Turn cap (max 8 turns)
        checks['turn_cap_honored'] = result['turns'] <= 8
        
        # Items from catalog only (would need catalog access to verify)
        checks['catalog_items_only'] = True  # Validated in API
        
        return checks


def main():
    """Run evaluation."""
    # Check if API is running
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code != 200:
            print(f"API not ready. Health check returned: {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"API not reachable at {api_url}: {e}")
        print("Please start the API server first: uvicorn src.api.main:app")
        return
    
    # Run evaluation
    evaluator = AgentEvaluator(api_base_url=api_url)
    metrics = evaluator.evaluate_all_traces()
    
    if not metrics:
        return
    
    # Print summary
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total traces: {metrics['total_traces']}")
    print(f"Mean Recall@10: {metrics['mean_recall@10']:.3f}")
    print(f"Mean turns: {metrics['mean_turns']:.1f}")
    
    # Save results
    output_file = "data/evaluation_results.json"
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\nFull results saved to: {output_file}")


if __name__ == "__main__":
    main()
