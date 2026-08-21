from app.dash_app import server


def test_dash_health_endpoint() -> None:
    response = server.test_client().get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {
        "service": "cakrawala-dash",
        "status": "ok",
    }
