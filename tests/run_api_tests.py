#!/usr/bin/env python3
"""
API Test Runner - Starts server and runs tests
"""
import subprocess
import time
import sys
import requests
from pathlib import Path

def is_server_running(url="http://localhost:8001/health", timeout=2):
    """Check if API server is running"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False

def start_server():
    """Start the API server"""
    print("🚀 Starting AkiraTV API server...")
    
    # Start server in background
    process = subprocess.Popen(
        [sys.executable, "-m", "akiratv.api_server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    for i in range(30):  # Wait up to 30 seconds
        if is_server_running():
            print("✅ API server started successfully")
            return process
        time.sleep(1)
        print(f"⏳ Waiting for server... ({i+1}/30)")
    
    print("❌ Failed to start API server")
    process.terminate()
    return None

def run_tests(test_type="quick"):
    """Run API tests"""
    if test_type == "quick":
        print("\n🧪 Running Quick API Tests...")
        result = subprocess.run([sys.executable, "test_api_quick.py"])
        return result.returncode == 0
    else:
        print("\n🧪 Running Comprehensive API Tests...")
        result = subprocess.run([sys.executable, "test_api_core.py"])
        return result.returncode == 0

def main():
    """Main test runner"""
    print("🔧 AkiraTV API Test Runner")
    print("=" * 50)
    
    # Check if server is already running
    if is_server_running():
        print("✅ API server is already running")
        server_process = None
    else:
        # Start server
        server_process = start_server()
        if not server_process:
            return 1
    
    try:
        # Run tests
        test_type = sys.argv[1] if len(sys.argv) > 1 else "quick"
        
        if test_type not in ["quick", "full"]:
            print("Usage: python run_api_tests.py [quick|full]")
            return 1
        
        success = run_tests(test_type)
        
        if success:
            print("\n🎉 All tests completed successfully!")
            return 0
        else:
            print("\n⚠️ Some tests failed. Check output above.")
            return 1
            
    finally:
        # Clean up - stop server if we started it
        if server_process:
            print("\n🛑 Stopping API server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
                print("✅ API server stopped")
            except subprocess.TimeoutExpired:
                server_process.kill()
                print("🔪 API server force killed")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)