#!/usr/bin/env python3
"""
Quick API Test - Basic functionality check
"""
import requests
import json

def quick_test():
    """Quick test of essential API endpoints"""
    base_url = "http://localhost:8001"
    
    print("🚀 AkiraTV Quick API Test")
    print("=" * 40)
    
    tests = [
        ("Health Check", "GET", "/health"),
        ("API Status", "GET", "/api/status"),
        ("Get Channels", "GET", "/api/channels"),
        ("Get Config", "GET", "/api/config"),
        ("Get TV Guide", "GET", "/api/guide"),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, method, endpoint in tests:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {name}")
                passed += 1
            else:
                print(f"❌ {name} - Status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {name} - Connection failed")
        except Exception as e:
            print(f"❌ {name} - Error: {e}")
    
    print("=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Run test_api_core.py for details.")
        return False

if __name__ == "__main__":
    success = quick_test()
    exit(0 if success else 1)