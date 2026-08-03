def test_health_response_has_request_id_and_metrics(client):
    response = client.get("/health/live", headers={"X-Request-ID": "test-request-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-1"
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "learnmate_http_requests_total" in metrics.text
    assert 'route="/health/live"' in metrics.text
