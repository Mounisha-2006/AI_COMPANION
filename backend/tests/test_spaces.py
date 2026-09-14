def test_create_and_get_space(client, user_a_headers):
    # Create space
    res = client.post("/spaces", headers=user_a_headers, json={
        "name": "Machine Learning",
        "description": "ML & Deep Learning study space"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Machine Learning"
    assert "id" in data
    space_id = data["id"]

    # Get user spaces
    list_res = client.get("/spaces", headers=user_a_headers)
    assert list_res.status_code == 200
    spaces = list_res.json()
    assert any(s["id"] == space_id for s in spaces)

    # Get single space
    get_res = client.get(f"/spaces/{space_id}", headers=user_a_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Machine Learning"

def test_update_and_delete_space(client, user_a_headers):
    res = client.post("/spaces", headers=user_a_headers, json={
        "name": "Calculus",
        "description": "Differential Calculus"
    })
    space_id = res.json()["id"]

    # Update
    put_res = client.put(f"/spaces/{space_id}", headers=user_a_headers, json={
        "name": "Advanced Calculus",
        "description": "Multivariable and Differential"
    })
    assert put_res.status_code == 200
    assert put_res.json()["name"] == "Advanced Calculus"

    # Delete
    del_res = client.delete(f"/spaces/{space_id}", headers=user_a_headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_res = client.get(f"/spaces/{space_id}", headers=user_a_headers)
    assert get_res.status_code == 404

def test_space_isolation_between_users(client, user_a_headers, user_b_headers):
    # User A creates a space
    res = client.post("/spaces", headers=user_a_headers, json={
        "name": "User A Private Space",
        "description": "Confidential"
    })
    space_a_id = res.json()["id"]

    # User B tries to view User A's space -> 404
    get_res = client.get(f"/spaces/{space_a_id}", headers=user_b_headers)
    assert get_res.status_code == 404

    # User B tries to update User A's space -> 404
    put_res = client.put(f"/spaces/{space_a_id}", headers=user_b_headers, json={
        "name": "Hacked Space"
    })
    assert put_res.status_code == 404

    # User B tries to delete User A's space -> 404
    del_res = client.delete(f"/spaces/{space_a_id}", headers=user_b_headers)
    assert del_res.status_code == 404

    # User B's space list should NOT contain User A's space
    b_spaces = client.get("/spaces", headers=user_b_headers).json()
    assert not any(s["id"] == space_a_id for s in b_spaces)
