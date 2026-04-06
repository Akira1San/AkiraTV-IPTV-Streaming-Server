#!/usr/bin/env python3
"""
Test script for collection creation functionality
"""
import requests
import json

def test_collection_create():
    """Test the collection creation API endpoint"""
    
    api_url = "http://localhost:8001/api/wizard/collection/create"
    
    test_data = {
        "collection_name": "Test Collection",
        "channel_name": "test_collection",
        "channel_type": "vod",
        "folder_path": "C:\\Videos\\Test",
        "collection_data": {
            "name": "Test Collection",
            "videos": [
                {"name": "test1.mp4", "size": 1000000, "format": "MP4"},
                {"name": "test2.mkv", "size": 2000000, "format": "MKV"}
            ],
            "created": "2025-01-31T10:00:00Z",
            "metadata": {
                "total_videos": 2,
                "formats": ["MP4", "MKV"]
            }
        }
    }
    
    print(f"🧪 Testing collection creation API")
    print(f"URL: {api_url}")
    print(f"Data: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(
            api_url,
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📊 Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"JSON Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Raw Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure API server is running on port 8001")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    test_collection_create()