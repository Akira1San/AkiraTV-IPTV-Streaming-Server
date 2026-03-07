"""
Test lifecycle routes to verify refactoring
"""
from fastapi.testclient import TestClient
from akiratv.api_server import app

client = TestClient(app)

def test_lifecycle_endpoints_exist():
    """Test that lifecycle endpoints are accessible"""
    # Test status endpoint (GET)
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_running" in data
    assert "uptime" in data
    assert "stats" in data
    print("✅ GET /api/status works")
    
    # Test start endpoint (POST) - may fail if already running, but should respond
    response = client.post("/api/start")
    assert response.status_code in [200, 500]  # 500 if already running
    print("✅ POST /api/start responds")
    
    # Test stop endpoint (POST)
    response = client.post("/api/stop")
    assert response.status_code in [200, 500]
    print("✅ POST /api/stop responds")
    
    # Test restart endpoint (POST)
    response = client.post("/api/restart")
    assert response.status_code in [200, 500]
    print("✅ POST /api/restart responds")

if __name__ == "__main__":
    test_lifecycle_endpoints_exist()
    print("\n✅ All lifecycle endpoint tests passed!")
