"""
Test library and monitoring routes to verify refactoring
"""
from fastapi.testclient import TestClient
from akiratv.api_server import app

client = TestClient(app)

def test_library_endpoints_exist():
    """Test that library endpoints are accessible"""
    # Test library stats endpoint (GET)
    response = client.get("/api/library/stats")
    assert response.status_code in [200, 503]  # 503 if engine not running
    print("✅ GET /api/library/stats responds")
    
    # Test library scan endpoint (POST)
    response = client.post("/api/library/scan")
    assert response.status_code in [200, 400, 503]
    print("✅ POST /api/library/scan responds")

def test_monitoring_endpoints_exist():
    """Test that monitoring endpoints are accessible"""
    # Test stats endpoint (GET)
    response = client.get("/api/stats")
    assert response.status_code == 200
    print("✅ GET /api/stats responds")
    
    # Test viewers endpoint (GET)
    response = client.get("/api/viewers")
    assert response.status_code == 200
    data = response.json()
    assert "viewers" in data
    print("✅ GET /api/viewers responds")
    
    # Test viewer details endpoint (GET)
    response = client.get("/api/viewers/detail")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "viewers" in data
    assert "per_channel" in data
    print("✅ GET /api/viewers/detail responds")
    
    # Test channel viewers endpoint (GET)
    response = client.get("/api/viewers/channel/test_channel")
    assert response.status_code == 200
    data = response.json()
    assert "channel" in data
    assert "viewers" in data
    assert "count" in data
    print("✅ GET /api/viewers/channel/{channel_name} responds")
    
    # Test logs endpoint (GET)
    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "count" in data
    print("✅ GET /api/logs responds")

if __name__ == "__main__":
    test_library_endpoints_exist()
    test_monitoring_endpoints_exist()
    print("\n✅ All library and monitoring endpoint tests passed!")
