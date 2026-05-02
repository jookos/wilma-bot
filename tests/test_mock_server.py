import pytest
from fastapi.testclient import TestClient
from wilma_bot.mock_server.server import app, configure_server, _sessions
import os

@pytest.fixture(scope="module")
def client():
    # Ensure config is loaded before testing
    config_path = "mock-config.yaml"
    if not os.path.exists(config_path):
        pytest.skip(f"Mock config not found at {config_path}")
    configure_server(config_path)
    return TestClient(app)

def test_index_json(client):
    response = client.get("/index_json")
    assert response.status_code == 200
    data = response.json()
    assert data["LoginResult"] == "Failed"
    assert "SessionID" in data
    assert data["ApiVersion"] == 20

def test_login_failed(client):
    response = client.post("/index_json", data={"Login": "wrong", "Password": "user"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/LoginFailed"

def test_login_success(client):
    # Based on mock-config.yaml: testuser / testpass
    response = client.post("/index_json", data={"Login": "testuser", "Password": "testpass"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert "Wilma2SID" in response.cookies

def test_api_me_unauthorized(client):
    # Create a fresh client to ensure no cookies are carried over
    from fastapi.testclient import TestClient
    from wilma_bot.mock_server.server import app
    local_client = TestClient(app)
    response = local_client.get("/api/v1/accounts/me")
    assert response.status_code == 401

def test_api_me_authorized(client):
    client.post("/index_json", data={"Login": "testuser", "Password": "testpass"})
    response = client.get("/api/v1/accounts/me")
    assert response.status_code == 200
    data = response.json()
    assert data["payload"]["username"] == "eero.esimerkki"

def test_api_roles(client):
    client.post("/index_json", data={"Login": "testuser", "Password": "testpass"})
    response = client.get("/api/v1/accounts/me/roles")
    assert response.status_code == 200
    data = response.json()
    assert len(data["payload"]) == 2
    assert data["payload"][0]["type"] == "student"

def test_messages_list(client):
    client.post("/index_json", data={"Login": "testuser", "Password": "testpass"})
    response = client.get("/messages/list")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "Messages" in data
    assert data["Status"] == 200
    msgs = data["Messages"]
    assert len(msgs) > 0
    assert "Subject" in msgs[0]
    assert "TimeStamp" in msgs[0]
    assert "Sender" in msgs[0]

def test_news_list(client):
    client.post("/index_json", data={"Login": "testuser", "Password": "testpass"})
    response = client.get("/news")
    assert response.status_code == 200
    assert "Pysyän ilmoitus" in response.text

def test_schedule(client):
    client.post("/index_json", data={"Login": "testuser", "Password": "testpass"})
    response = client.get("/schedule")
    assert response.status_code == 200
    assert "Viikkonakyma" in response.text

def test_schedule_export(client):
    client.post("/index_json", data={"Login": "testuser", "Password": "testpass"})
    # The route is profiles/<id>/schedule/export/students/<id>
    # In mock-config.yaml, slug is profiles/42
    response = client.get("/profiles/42/schedule/export/students/42")
    assert response.status_code == 200
    data = response.json()
    assert "Terms" in data
    assert len(data["Terms"]) > 0

def test_logout(client):
    client.post("/index_json", data={"Login": "testuser", "Password": "testpass"})
    sid = client.cookies["Wilma2SID"]
    response = client.get("/logout")
    assert response.status_code == 200
    assert sid not in _sessions
