import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
COLLECTION_PATH = ROOT / "postman" / "collections" / "LearnMate AI API.postman_collection.json"
ENVIRONMENT_PATH = ROOT / "postman" / "environments" / "LearnMate Local.postman_environment.json"


def _requests(items: list[dict]) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if "request" in item:
            result.append(item["request"])
        result.extend(_requests(item.get("item", [])))
    return result


def test_postman_collection_is_valid_and_covers_core_routes():
    collection = json.loads(COLLECTION_PATH.read_text(encoding="utf-8"))
    assert collection["info"]["schema"].endswith("/collection/v2.1.0/collection.json")

    routes = {f"{request['method']} {request['url']}" for request in _requests(collection["item"])}
    expected = {
        "GET {{baseUrl}}/health/ready",
        "POST {{baseUrl}}/api/v1/auth/register",
        "POST {{baseUrl}}/api/v1/auth/login",
        "POST {{baseUrl}}/api/v1/analyses/writing",
        "POST {{baseUrl}}/api/v1/learning-paths/generate",
        "GET {{baseUrl}}/api/v1/learning-paths/current",
        "GET {{baseUrl}}/api/v1/admin/stats",
        "GET {{baseUrl}}/api/v1/admin/learning-paths?limit=20&offset=0",
    }
    assert expected <= routes


def test_postman_environment_contains_no_committed_credentials():
    environment = json.loads(ENVIRONMENT_PATH.read_text(encoding="utf-8"))
    values = {entry["key"]: entry.get("value") for entry in environment["values"]}

    for key in ("learnerPassword", "accessToken", "adminPassword", "adminToken"):
        assert values[key] == ""
    assert values["baseUrl"] == "http://localhost:8000"
