import pytest
import uuid
from app.core.security import create_access_token
from app.models.project import Project

@pytest.mark.asyncio
async def test_create_project_success(client, test_user):
    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "Finance RAG Guardrail",
        "description": "Evaluation set for financial queries and compliance"
    }
    response = await client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["owner_id"] == str(test_user.id)
    assert "id" in data

@pytest.mark.asyncio
async def test_create_project_validation_empty_name(client, test_user):
    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "",  # Min length is 1
        "description": "No name project"
    }
    response = await client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_list_projects_owner_isolation(client, test_user, test_user_2, db_session):
    # Create project for user 1
    p1 = Project(name="User1 Project", description="P1", owner_id=test_user.id)
    # Create project for user 2
    p2 = Project(name="User2 Project", description="P2", owner_id=test_user_2.id)
    db_session.add_all([p1, p2])
    await db_session.commit()

    # User 1 lists projects -> should only see p1
    token1 = create_access_token(test_user.id)
    resp1 = await client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token1}"})
    assert resp1.status_code == 200
    p1_list = resp1.json()
    assert any(p["id"] == str(p1.id) for p in p1_list)
    assert not any(p["id"] == str(p2.id) for p in p1_list)

    # User 2 lists projects -> should only see p2
    token2 = create_access_token(test_user_2.id)
    resp2 = await client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token2}"})
    assert resp2.status_code == 200
    p2_list = resp2.json()
    assert any(p["id"] == str(p2.id) for p in p2_list)
    assert not any(p["id"] == str(p1.id) for p in p2_list)

@pytest.mark.asyncio
async def test_get_project_by_id_owner(client, test_user, db_session):
    p = Project(name="Specific Project", description="Test desc", owner_id=test_user.id)
    db_session.add(p)
    await db_session.commit()

    token = create_access_token(test_user.id)
    response = await client.get(f"/api/v1/projects/{p.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == str(p.id)

@pytest.mark.asyncio
async def test_get_project_unauthorized_access(client, test_user, test_user_2, db_session):
    p = Project(name="Private Project", description="Private", owner_id=test_user.id)
    db_session.add(p)
    await db_session.commit()

    # User 2 attempts to get User 1's project -> 403 Forbidden
    token2 = create_access_token(test_user_2.id)
    response = await client.get(f"/api/v1/projects/{p.id}", headers={"Authorization": f"Bearer {token2}"})
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]

@pytest.mark.asyncio
async def test_admin_can_access_any_project(client, test_user, test_admin, db_session):
    p = Project(name="User Project", description="Desc", owner_id=test_user.id)
    db_session.add(p)
    await db_session.commit()

    admin_token = create_access_token(test_admin.id)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin GET specific user project
    get_resp = await client.get(f"/api/v1/projects/{p.id}", headers=admin_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == str(p.id)

    # Admin LIST all projects
    list_resp = await client.get("/api/v1/projects", headers=admin_headers)
    assert list_resp.status_code == 200
    assert any(proj["id"] == str(p.id) for proj in list_resp.json())

@pytest.mark.asyncio
async def test_update_project_by_owner(client, test_user, db_session):
    p = Project(name="Initial Name", description="Initial Desc", owner_id=test_user.id)
    db_session.add(p)
    await db_session.commit()

    token = create_access_token(test_user.id)
    update_payload = {"name": "Updated Name", "description": "Updated Desc"}
    response = await client.put(
        f"/api/v1/projects/{p.id}", 
        json=update_payload, 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated Desc"

@pytest.mark.asyncio
async def test_update_project_unauthorized(client, test_user, test_user_2, db_session):
    p = Project(name="Original Name", description="Desc", owner_id=test_user.id)
    db_session.add(p)
    await db_session.commit()

    token2 = create_access_token(test_user_2.id)
    response = await client.put(
        f"/api/v1/projects/{p.id}",
        json={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_delete_project_by_owner(client, test_user, db_session):
    p = Project(name="To Delete", description="Desc", owner_id=test_user.id)
    db_session.add(p)
    await db_session.commit()

    token = create_access_token(test_user.id)
    response = await client.delete(f"/api/v1/projects/{p.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204

    # Verify project is gone
    get_resp = await client.get(f"/api/v1/projects/{p.id}", headers={"Authorization": f"Bearer {token}"})
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_project_unauthorized(client, test_user, test_user_2, db_session):
    p = Project(name="Keep Safe", description="Desc", owner_id=test_user.id)
    db_session.add(p)
    await db_session.commit()

    token2 = create_access_token(test_user_2.id)
    response = await client.delete(f"/api/v1/projects/{p.id}", headers={"Authorization": f"Bearer {token2}"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_project_not_found(client, test_user):
    token = create_access_token(test_user.id)
    random_id = uuid.uuid4()
    response = await client.get(f"/api/v1/projects/{random_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
