#!/usr/bin/env python3
"""
Test script for folder scanning functionality
"""
import requests
import json

def test_folder_scan():
    """Test the folder scanning API endpoint"""
    
    # Test with a common Windows folder
    test_folders = [
        "C:\\Videos\\anime",  # User's folder
        "C:\\Windows\\System32",  # Should exist but no videos
        "C:\\NonExistentFolder"  # Should not exist
    ]
    
    api_url = "http://localhost:8001/api/wizard/scan-folder"
    
    for folder_path in test_folders:
        print(f"\n🔍 Testing folder: {folder_path}")
        
        try:
            response = requests.post(
                api_url,
                json={"folder_path": folder_path},
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: {data.get('message', 'No message')}")
                if 'data' in data:
                    video_count = data['data'].get('video_count', 0)
                    total_size = data['data'].get('total_size', 0)
                    print(f"   📁 Videos found: {video_count}")
                    print(f"   💾 Total size: {total_size:,} bytes")
                    
                    if video_count > 0:
                        print("   🎬 Sample videos:")
                        for video in data['data']['videos'][:3]:  # Show first 3
                            print(f"      - {video['name']} ({video['format']}, {video['size']:,} bytes)")
            else:
                error_data = response.json()
                print(f"❌ Error: {error_data.get('detail', 'Unknown error')}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection failed - make sure API server is running on port 8001")
            break
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    test_folder_scan()