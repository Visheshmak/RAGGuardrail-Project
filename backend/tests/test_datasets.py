import json
import pytest
import uuid
from uuid import UUID

from app.models.project import Project
from app.models.dataset import Dataset, DatasetVersion, EvaluationCase
from app.core.security import create_access_token
from app.services.dataset_service import DatasetParser, DatasetValidationError, DatasetService

def test_dataset_parser_json_valid():
    json_bytes = json.dumps([
        {
            "question": "What is the vacation policy?",
            "expected_answer": "20 days per year.",
            "expected_context": ["benefits.pdf"],
            "category": "benefits",
            "difficulty": "easy"
        },
        {
            "question": "What is the 401k match?",
            "expected_answer": "Up to 5% total match.",
            "expected_context": ["benefits.pdf"],
            "category": "finance",
            "difficulty": "medium"
        }
    ]).encode("utf-8")

    cases, summary = DatasetParser.parse_json(json_bytes)
    assert len(cases) == 2
    assert cases[0].question == "What is the vacation policy?"
    assert cases[0].expected_answer == "20 days per year."
    assert cases[0].expected_context == ["benefits.pdf"]
    assert cases[0].category == "benefits"
    assert cases[0].difficulty == "easy"
    assert summary.valid_cases_added == 2
    assert summary.duplicate_count == 0

def test_dataset_parser_csv_valid():
    csv_bytes = (
        'question,expected_answer,expected_context,category,difficulty\n'
        '"What is remote work policy?","Up to 3 days weekly.","policy.md;remote.pdf","policy","easy"\n'
        '"What is the office stipend?","$750 for desks.","finance.md","finance","easy"\n'
    ).encode("utf-8")

    cases, summary = DatasetParser.parse_csv(csv_bytes)
    assert len(cases) == 2
    assert cases[0].question == "What is remote work policy?"
    assert cases[0].expected_context == ["policy.md", "remote.pdf"]
    assert summary.valid_cases_added == 2

def test_dataset_parser_duplicate_and_empty_rows():
    json_bytes = json.dumps([
        {"question": "Duplicate question?"},
        {"question": "Duplicate question?"},
        {},
        {"question": "Unique question"}
    ]).encode("utf-8")

    cases, summary = DatasetParser.parse_json(json_bytes)
    assert len(cases) == 3
    assert summary.duplicate_count == 1
    assert summary.skipped_empty_rows == 1
    assert len(summary.warnings) >= 1

def test_dataset_parser_invalid_json():
    with pytest.raises(DatasetValidationError) as exc:
        DatasetParser.parse_json(b"{ invalid json }")
    assert "Invalid JSON" in str(exc.value)

def test_dataset_parser_missing_required_question():
    json_bytes = json.dumps([
        {"expected_answer": "Answer with no question."}
    ]).encode("utf-8")
    with pytest.raises(DatasetValidationError) as exc:
        DatasetParser.parse_json(json_bytes)
    assert "Failed to parse" in str(exc.value) or "Missing required" in str(exc.value)

@pytest.mark.asyncio
async def test_create_and_get_dataset(client, test_user, db_session):
    project = Project(name="Dataset Project", owner_id=test_user.id)
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Initial Policy Benchmark",
        "description": "Baseline evaluation dataset for HR guidelines",
        "initial_cases": [
            {
                "question": "How many days remote?",
                "expected_answer": "Up to 3 days",
                "expected_context": ["remote_policy.md"],
                "category": "policy",
                "difficulty": "easy"
            }
        ]
    }

    create_resp = await client.post(
        f"/api/v1/projects/{project.id}/datasets",
        json=payload,
        headers=headers
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["name"] == payload["name"]
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version"] == 1
    assert data["versions"][0]["case_count"] == 1
    dataset_id = data["id"]

    # Get dataset by ID
    get_resp = await client.get(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == dataset_id
    assert get_resp.json()["total_cases"] == 1

@pytest.mark.asyncio
async def test_dataset_ownership_isolation(client, test_user, test_user_2, db_session):
    project = Project(name="User 1 Project", owner_id=test_user.id)
    db_session.add(project)
    await db_session.commit()

    token1 = create_access_token(test_user.id)
    token2 = create_access_token(test_user_2.id)

    # Create dataset by User 1
    create_resp = await client.post(
        f"/api/v1/projects/{project.id}/datasets",
        json={"name": "Confidential Dataset"},
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert create_resp.status_code == 201
    dataset_id = create_resp.json()["id"]

    # User 2 tries to view User 1's dataset -> 403 Forbidden
    unauth_get = await client.get(
        f"/api/v1/datasets/{dataset_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert unauth_get.status_code == 403

@pytest.mark.asyncio
async def test_dataset_upload_json_and_csv_versioning(client, test_user, db_session):
    project = Project(name="Versioning Project", owner_id=test_user.id)
    db_session.add(project)
    await db_session.commit()

    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create dataset
    ds_resp = await client.post(
        f"/api/v1/projects/{project.id}/datasets",
        json={"name": "Multi-Version Dataset"},
        headers=headers
    )
    dataset_id = ds_resp.json()["id"]

    # 2. Upload JSON file -> creates version 1
    json_cases = json.dumps([
        {"question": "Q1", "expected_answer": "A1", "category": "cat1", "difficulty": "easy"},
        {"question": "Q2", "expected_answer": "A2", "category": "cat2", "difficulty": "medium"}
    ]).encode("utf-8")

    upload_json = await client.post(
        f"/api/v1/datasets/{dataset_id}/upload",
        files={"file": ("cases_v1.json", json_cases, "application/json")},
        data={"description": "Uploaded JSON benchmark"},
        headers=headers
    )
    assert upload_json.status_code == 201
    assert upload_json.json()["version"] == 1
    assert upload_json.json()["valid_cases_added"] == 2
    v1_id = upload_json.json()["version_id"]

    # 3. Upload CSV file -> creates version 2
    csv_cases = (
        'question,expected_answer,category,difficulty\n'
        '"Q3","A3","cat1","hard"\n'
        '"Q4","A4","cat3","easy"\n'
        '"Q5","A5","cat3","medium"\n'
    ).encode("utf-8")

    upload_csv = await client.post(
        f"/api/v1/datasets/{dataset_id}/upload",
        files={"file": ("cases_v2.csv", csv_cases, "text/csv")},
        data={"description": "Uploaded CSV expansion"},
        headers=headers
    )
    assert upload_csv.status_code == 201
    assert upload_csv.json()["version"] == 2
    assert upload_csv.json()["valid_cases_added"] == 3
    v2_id = upload_csv.json()["version_id"]

    # 4. Check statistics for version 2
    stats_resp = await client.get(f"/api/v1/datasets/{dataset_id}/versions/{v2_id}/stats", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_cases"] == 3
    assert stats["categories"]["cat1"] == 1
    assert stats["categories"]["cat3"] == 2
    assert stats["difficulties"]["hard"] == 1

    # 5. Check preview/list cases with category filter
    cases_resp = await client.get(
        f"/api/v1/datasets/{dataset_id}/versions/{v2_id}/cases?category=cat3",
        headers=headers
    )
    assert cases_resp.status_code == 200
    filtered_cases = cases_resp.json()
    assert len(filtered_cases) == 2
    assert all(c["category"] == "cat3" for c in filtered_cases)

@pytest.mark.asyncio
async def test_delete_dataset(client, test_user, db_session):
    project = Project(name="Delete Test Project", owner_id=test_user.id)
    db_session.add(project)
    await db_session.commit()

    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    ds_resp = await client.post(
        f"/api/v1/projects/{project.id}/datasets",
        json={"name": "Dataset to Delete"},
        headers=headers
    )
    dataset_id = ds_resp.json()["id"]

    # Delete
    del_resp = await client.delete(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert del_resp.status_code == 204

    # Confirm 404
    get_resp = await client.get(f"/api/v1/datasets/{dataset_id}", headers=headers)
    assert get_resp.status_code == 404
