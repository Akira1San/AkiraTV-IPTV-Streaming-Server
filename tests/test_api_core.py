#!/usr/bin/env python3
"""
Comprehensive API Core Test Suite for AkiraTV
Tests all major API endpoints to ensure functionality
"""
import requests
import json
import time
import sys
from pathlib import Path

class AkiraTVAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.failed_tests = []
        
    def log(self, message, level="INFO"):
        """Log test messages"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def test_endpoint(self, name, method, endpoint, data=None, expected_status=200, should_succeed=True):
        """Test a single API endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            self.log(f"Testing {name}: {method} {endpoint}")
            
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers={"Content-Type": "application/json"})
            elif method.upper() == "PATCH":
                response = self.session.patch(url, json=data, headers={"Content-Type": "application/json"})
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Check status code
            status_ok = response.status_code == expected_status
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                json_ok = True
            except:
                response_data = {"raw_response": response.text}
                json_ok = False
            
            # Determine if test passed
            if should_succeed:
                test_passed = status_ok and json_ok
                if response_data.get("success") is False and expected_status == 200:
                    test_passed = False
            else:
                # For tests that should fail, we expect the expected_status
                test_passed = response.status_code == expected_status
            
            # Log result
            if test_passed:
                self.log(f"✅ {name} - PASSED", "SUCCESS")
                self.test_results.append({"name": name, "status": "PASSED", "response": response_data})
            else:
                self.log(f"❌ {name} - FAILED", "ERROR")
                self.log(f"   Status: {response.status_code}, Expected: {expected_status}", "ERROR")
                self.log(f"   Response: {json.dumps(response_data, indent=2)[:200]}...", "ERROR")
                self.failed_tests.append({"name": name, "status": response.status_code, "response": response_data})
                self.test_results.append({"name": name, "status": "FAILED", "response": response_data})
            
            return test_passed, response_data
            
        except requests.exceptions.ConnectionError:
            self.log(f"❌ {name} - CONNECTION FAILED", "ERROR")
            self.failed_tests.append({"name": name, "status": "CONNECTION_FAILED", "response": None})
            self.test_results.append({"name": name, "status": "CONNECTION_FAILED", "response": None})
            return False, None
        except Exception as e:
            self.log(f"❌ {name} - EXCEPTION: {str(e)}", "ERROR")
            self.failed_tests.append({"name": name, "status": "EXCEPTION", "response": str(e)})
            self.test_results.append({"name": name, "status": "EXCEPTION", "response": str(e)})
            return False, None
    
    def run_all_tests(self):
        """Run comprehensive API test suite"""
        self.log("🚀 Starting AkiraTV API Core Test Suite")
        self.log("=" * 60)
        
        # 1. Health Check
        self.test_endpoint("Health Check", "GET", "/health")
        
        # 2. Status Endpoints
        self.test_endpoint("Get Status", "GET", "/api/status")
        self.test_endpoint("Get Stats", "GET", "/api/stats")
        
        # 3. Configuration Endpoints
        self.test_endpoint("Get Config", "GET", "/api/config")
        self.test_endpoint("Get Default Config", "GET", "/api/config/defaults")
        self.test_endpoint("Get Config File Info", "GET", "/api/config/file")
        
        # 4. Channel Management
        self.test_endpoint("Get Channels", "GET", "/api/channels")
        self.test_endpoint("Get All Channel URLs", "GET", "/api/channels/urls")
        
        # Test adding a channel
        passed, response = self.test_endpoint(
            "Add Test Channel", 
            "POST", 
            "/api/channels?channel_name=api_test_channel&channel_type=vod"
        )
        
        if passed:
            # Test channel-specific operations
            self.test_endpoint("Get Specific Channel", "GET", "/api/channels/api_test_channel")
            self.test_endpoint("Enable Channel", "POST", "/api/channels/api_test_channel/enable")
            self.test_endpoint("Disable Channel", "POST", "/api/channels/api_test_channel/disable")
            
            # Test channel settings update
            self.test_endpoint(
                "Update Channel Settings",
                "PATCH",
                "/api/channels/api_test_channel",
                {"transcoding": "enabled", "subtitles": "disabled"}
            )
            
            # Test channel operations
            self.test_endpoint("Reload Channel Schedule", "POST", "/api/channels/api_test_channel/reload-schedule")
            
            # Clean up - delete test channel
            self.test_endpoint("Delete Test Channel", "DELETE", "/api/channels/api_test_channel")
        
        # 5. Utility Endpoints
        self.test_endpoint("Clear Cache", "POST", "/api/cache/clear")
        self.test_endpoint("Reload All Schedules", "POST", "/api/schedule/reload")
        self.test_endpoint("Generate XMLTV", "POST", "/api/xmltv/generate")
        self.test_endpoint("Get Logs Info", "GET", "/api/logs")
        
        # 6. TV Guide Endpoints
        self.test_endpoint("Get TV Guide", "GET", "/api/guide")
        self.test_endpoint("Get Weekly TV Guide", "GET", "/api/guide/weekly")
        
        # 7. Playlist Endpoints
        self.test_endpoint("Get Playlist Videos", "GET", "/api/playlist/videos")
        
        # 8. Wizard Endpoints
        # Test folder scanning (will fail but should return proper error)
        self.test_endpoint(
            "Wizard Folder Scan (Invalid Path)",
            "POST",
            "/api/wizard/scan-folder",
            {"folder_path": "/nonexistent/path"},
            expected_status=400,
            should_succeed=False
        )
        
        # Test wizard logging
        self.test_endpoint(
            "Wizard Logging",
            "POST",
            "/api/wizard/log",
            {
                "timestamp": "2025-01-31T10:00:00Z",
                "level": "info",
                "message": "API test log entry",
                "data": {"test": True}
            }
        )
        
        # 9. Configuration Update Test
        self.test_endpoint(
            "Update Config",
            "PATCH",
            "/api/config",
            {
                "updates": {
                    "ui": {"test_mode": True}
                }
            }
        )
        
        # 10. Error Handling Tests
        self.test_endpoint("Invalid Endpoint", "GET", "/api/nonexistent", expected_status=404, should_succeed=False)
        self.test_endpoint("Invalid Channel", "GET", "/api/channels/nonexistent_channel", expected_status=404, should_succeed=False)
        
        # Summary
        self.print_summary()
    
    def test_wizard_functionality(self):
        """Test wizard-specific functionality"""
        self.log("🧙‍♂️ Testing Wizard Functionality")
        self.log("-" * 40)
        
        # Test collection creation with mock data
        collection_data = {
            "collection_name": "API Test Collection",
            "channel_name": "api_test_collection",
            "channel_type": "vod",
            "folder_path": "C:\\Test\\Videos",
            "collection_data": {
                "name": "API Test Collection",
                "videos": [
                    {"name": "test1.mp4", "size": 1000000, "format": "MP4", "path": "C:\\Test\\Videos\\test1.mp4"},
                    {"name": "test2.mkv", "size": 2000000, "format": "MKV", "path": "C:\\Test\\Videos\\test2.mkv"}
                ],
                "created": "2025-01-31T10:00:00Z",
                "metadata": {"total_videos": 2, "formats": ["MP4", "MKV"]}
            }
        }
        
        passed, response = self.test_endpoint(
            "Create Collection via Wizard",
            "POST",
            "/api/wizard/collection/create",
            collection_data
        )
        
        if passed:
            # Clean up - delete the test collection channel
            self.test_endpoint("Delete Test Collection Channel", "DELETE", "/api/channels/api_test_collection")
            
            # Clean up collection file
            try:
                collection_file = Path("user/collections/collections_api_test_collection.json")
                if collection_file.exists():
                    collection_file.unlink()
                    self.log("🗑️ Cleaned up test collection file")
            except Exception as e:
                self.log(f"⚠️ Could not clean up collection file: {e}")
    
    def print_summary(self):
        """Print test summary"""
        self.log("=" * 60)
        self.log("📊 TEST SUMMARY")
        self.log("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["status"] == "PASSED"])
        failed_tests = len(self.failed_tests)
        
        self.log(f"Total Tests: {total_tests}")
        self.log(f"Passed: {passed_tests} ✅")
        self.log(f"Failed: {failed_tests} ❌")
        self.log(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                self.log(f"   • {test['name']} - {test['status']}")
        
        if failed_tests == 0:
            self.log("\n🎉 ALL TESTS PASSED! API is working correctly.")
        elif failed_tests <= 2:
            self.log(f"\n⚠️ Minor issues detected. {failed_tests} tests failed.")
        else:
            self.log(f"\n🚨 Major issues detected. {failed_tests} tests failed.")
        
        # Save detailed results
        self.save_test_results()
    
    def save_test_results(self):
        """Save test results to file"""
        try:
            results = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_tests": len(self.test_results),
                "passed": len([t for t in self.test_results if t["status"] == "PASSED"]),
                "failed": len(self.failed_tests),
                "results": self.test_results,
                "failed_tests": self.failed_tests
            }
            
            with open("api_test_results.json", "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.log("💾 Test results saved to api_test_results.json")
        except Exception as e:
            self.log(f"⚠️ Could not save test results: {e}")

def main():
    """Main test runner"""
    print("🧪 AkiraTV API Core Test Suite")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        print("✅ API server is running")
    except:
        print("❌ API server is not running on localhost:8001")
        print("Please start the server with: python -m akiratv.api_server")
        return 1
    
    # Run tests
    tester = AkiraTVAPITester()
    tester.run_all_tests()
    tester.test_wizard_functionality()
    
    # Return exit code based on results
    if len(tester.failed_tests) == 0:
        return 0  # Success
    elif len(tester.failed_tests) <= 2:
        return 1  # Minor issues
    else:
        return 2  # Major issues

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)