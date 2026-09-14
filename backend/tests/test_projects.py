def test_create_and_get_project(client, user_a_headers):
    # Create space
    space_res = client.post("/spaces", headers=user_a_headers, json={
        "name": "Data Structures",
        "description": "DS & Algorithms"
    })
    space_id = space_res.json()["id"]

    # Create project in space
    proj_res = client.post(f"/spaces/{space_id}/projects", headers=user_a_headers, json={
        "name": "Binary Trees",
        "description": "Tree traversals and AVL balance",
        "learning_goal": "Master tree algorithms"
    })
    assert proj_res.status_code == 201
    proj_data = proj_res.json()
    assert proj_data["name"] == "Binary Trees"
    assert proj_data["space_id"] == space_id
    project_id = proj_data["id"]

    # Get space projects
    list_res = client.get(f"/spaces/{space_id}/projects", headers=user_a_headers)
    assert list_res.status_code == 200
    assert any(p["id"] == project_id for p in list_res.json())

    # Get single project
    get_res = client.get(f"/projects/{project_id}", headers=user_a_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Binary Trees"

def test_project_isolation_and_ownership(client, user_a_headers, user_b_headers):
    # User A creates space and project
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "Space A"}).json()
    proj_a = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={
        "name": "Secret Project",
        "learning_goal": "Top secret"
    }).json()

    project_a_id = proj_a["id"]

    # User B tries to view User A's project -> 404
    assert client.get(f"/projects/{project_a_id}", headers=user_b_headers).status_code == 404

    # User B tries to list projects in User A's space -> 404
    assert client.get(f"/spaces/{space_a['id']}/projects", headers=user_b_headers).status_code == 404

    # User B tries to create a project in User A's space -> 404
    bad_create = client.post(f"/spaces/{space_a['id']}/projects", headers=user_b_headers, json={
        "name": "Injected Project"
    })
    assert bad_create.status_code == 404

    # User B tries to update User A's project -> 404
    assert client.put(f"/projects/{project_a_id}", headers=user_b_headers, json={
        "name": "Hijacked Project"
    }).status_code == 404

    # User B tries to delete User A's project -> 404
    assert client.delete(f"/projects/{project_a_id}", headers=user_b_headers).status_code == 404
