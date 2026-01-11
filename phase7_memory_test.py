#!/usr/bin/env python3
"""
Phase 7 Memory API Test Script
actorIdパラメータを含む正しいAPI呼び出しをテスト
"""

import boto3
import json
import os

def test_memory_api():
    # 環境変数から設定を取得
    memory_id = os.environ.get('AGENTCORE_MEMORY_ID', 'your-memory-id-here')
    session_id = "device-hplc_001-session-hplc_001-00000000"
    
    # Bedrock AgentCore クライアント作成
    client = boto3.client('bedrock-agentcore', region_name='us-west-2')
    
    try:
        print(f"Testing Memory API with:")
        print(f"  Memory ID: {memory_id}")
        print(f"  Session ID: {session_id}")
        print()
        
        # Step 1: List actors
        print("1. Listing actors...")
        actors_response = client.list_actors(memoryId=memory_id)
        print(f"Actors response: {json.dumps(actors_response, indent=2, default=str)}")
        
        if not actors_response.get('actorSummaries'):
            print("No actors found!")
            return
        
        # Step 2: Use first actor for list_events
        actor_id = actors_response['actorSummaries'][0]['actorId']
        print(f"\n2. Using actor ID: {actor_id}")
        
        # Step 3: List events with all required parameters
        print("3. Listing events...")
        events_response = client.list_events(
            memoryId=memory_id,
            sessionId=session_id,
            actorId=actor_id,
            maxResults=10
        )
        
        print(f"Events response: {json.dumps(events_response, indent=2, default=str)}")
        
        # Step 4: Display results
        events = events_response.get('events', [])
        print(f"\n4. Found {len(events)} events:")
        for i, event in enumerate(events):
            print(f"  Event {i+1}:")
            print(f"    ID: {event['eventId']}")
            print(f"    Timestamp: {event['eventTimestamp']}")
            print(f"    Actor: {event['actorId']}")
            if event.get('payload'):
                for payload in event['payload']:
                    if 'conversational' in payload:
                        content = payload['conversational']['content']
                        role = payload['conversational']['role']
                        if 'text' in content:
                            text = content['text'][:100] + "..." if len(content['text']) > 100 else content['text']
                            print(f"    {role}: {text}")
            print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_memory_api()