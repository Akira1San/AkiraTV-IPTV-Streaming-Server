"""
Test guide routes to verify refactoring
"""
from fastapi.testclient import TestClient
from akiratv.api_server import app

client = TestClient(app)

def test_guide_endpoints_exist():
    """Test that guide endpoints are accessible"""
    # Test current guide endpoint (GET)
    response = client.get("/api/guide")
    assert response.status_code == 200
    data = response.json()
    assert "guide" in data
    assert "current_time" in data
    assert "current_day" in data
    assert "timestamp" in data
    print("✅ GET /api/guide works")
    
    # Test weekly guide endpoint (GET)
    response = client.get("/api/guide/weekly")
    assert response.status_code == 200
    data = response.json()
    assert "weekly_guide" in data
    assert "current_time" in data
    assert "current_day" in data
    assert "days_order" in data
    assert "timestamp" in data
    print("✅ GET /api/guide/weekly works")
    
    # Test date-specific guide endpoint (GET)
    response = client.get("/api/guide/date/2026-03-07")
    assert response.status_code == 200
    data = response.json()
    assert "guide" in data
    assert "selected_date" in data
    assert "day_name" in data
    assert "timestamp" in data
    print("✅ GET /api/guide/date/{date_str} works")
    
    # Test invalid date format
    response = client.get("/api/guide/date/invalid-date")
    assert response.status_code == 400
    print("✅ GET /api/guide/date/{date_str} validates date format")

if __name__ == "__main__":
    test_guide_endpoints_exist()
    print("\n✅ All guide endpoint tests passed!")
