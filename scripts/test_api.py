#!/usr/bin/env python3
"""
Simple script to test the /chat API endpoint
"""

import requests
import json
import sys


def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chat(messages):
    """Test chat endpoint with messages."""
    print("\nTesting /chat endpoint...")
    print(f"Messages: {json.dumps(messages, indent=2)}")
    
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={"messages": messages},
            timeout=30
        )
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nReply: {result['reply']}")
            print(f"Recommendations: {len(result.get('recommendations', []))}")
            
            if result.get('recommendations'):
                print("\nRecommendations:")
                for i, rec in enumerate(result['recommendations'], 1):
                    print(f"  {i}. {rec['name']} ({rec['test_type']})")
                    print(f"     {rec['url']}")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run test scenarios."""
    # Test health
    if not test_health():
        print("\nAPI is not running or not healthy!")
        print("Start it with: uvicorn src.api.main:app --reload")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Test 1: Initial vague query")
    print("="*60)
    
    messages = [
        {"role": "user", "content": "I need an assessment"}
    ]
    test_chat(messages)
    
    print("\n" + "="*60)
    print("Test 2: Specific query")
    print("="*60)
    
    messages = [
        {"role": "user", "content": "I'm hiring a senior Java developer who will work with stakeholders and manage a small team. They need AWS experience."}
    ]
    test_chat(messages)
    
    print("\n" + "="*60)
    print("Test 3: Multi-turn conversation")
    print("="*60)
    
    messages = [
        {"role": "user", "content": "Hiring a Java developer"},
        {"role": "assistant", "content": "Great! To recommend the right assessments, could you tell me more about the seniority level and key responsibilities?"},
        {"role": "user", "content": "Senior level, they'll be leading backend development and working with product managers"}
    ]
    test_chat(messages)
    
    print("\n" + "="*60)
    print("Test 4: Comparison request")
    print("="*60)
    
    messages = [
        {"role": "user", "content": "What's the difference between OPQ32r and MQ?"}
    ]
    test_chat(messages)


if __name__ == "__main__":
    main()
