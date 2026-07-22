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
        "POST {{baseUrl}}/api/v1/classes",
        "GET {{baseUrl}}/api/v1/classes/managed?limit=20&offset=0",
        "GET {{baseUrl}}/api/v1/classes/{{classId}}",
        "PATCH {{baseUrl}}/api/v1/classes/{{classId}}",
        "POST {{baseUrl}}/api/v1/classes/{{classId}}/join-code/rotate",
        "POST {{baseUrl}}/api/v1/classes/join",
        "GET {{baseUrl}}/api/v1/classes/mine?limit=20&offset=0",
        "GET {{baseUrl}}/api/v1/classes/{{classId}}/assignments?limit=20&offset=0",
        "POST {{baseUrl}}/api/v1/classes/{{classId}}/assignments",
        "GET {{baseUrl}}/api/v1/assignments/{{assignmentId}}",
        "PATCH {{baseUrl}}/api/v1/assignments/{{assignmentId}}",
        "POST {{baseUrl}}/api/v1/assignments/{{assignmentId}}/submissions",
        "GET {{baseUrl}}/api/v1/assignments/{{assignmentId}}/submissions?limit=20&offset=0",
        "DELETE {{baseUrl}}/api/v1/classes/{{classId}}/membership",
        "GET {{baseUrl}}/api/v1/admin/stats",
        "GET {{baseUrl}}/api/v1/admin/learning-paths?limit=20&offset=0",
    }
    assert expected <= routes

    classroom_folder = next(item for item in collection["item"] if item["name"] == "Classrooms")
    classroom_source = json.dumps(classroom_folder, ensure_ascii=False)
    for assertion in (
        "Learner writing analysis succeeds",
        "membership_status).to.eql('pending')",
        "status).to.eql('active')",
        "Learner submission is created",
        "attempt_number).to.be.at.least(1)",
        "Teacher submission list succeeds",
    ):
        assert assertion in classroom_source


def test_postman_environment_contains_no_committed_credentials():
    environment = json.loads(ENVIRONMENT_PATH.read_text(encoding="utf-8"))
    values = {entry["key"]: entry.get("value") for entry in environment["values"]}

    for key in (
        "learnerPassword",
        "accessToken",
        "adminPassword",
        "adminToken",
        "teacherPassword",
        "teacherToken",
        "joinCode",
    ):
        assert values[key] == ""
    assert values["baseUrl"] == "http://localhost:8000"
