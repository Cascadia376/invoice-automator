def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["status"] == "ok"
    assert response_json["version"] == "1.0.0"
    assert "database" in response_json

def test_read_vendors_empty(client):
    response = client.get("/api/vendors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_read_invoices_empty(client):
    response = client.get("/api/invoices")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_gl_categories_crud(client):
    # Create
    response = client.post("/api/gl-categories", json={
        "code": "5000",
        "name": "COGS",
        "full_name": "Cost of Goods Sold"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "5000"
    category_id = data["id"]
    
    # Read
    response = client.get("/api/gl-categories")
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    # Delete
    response = client.delete(f"/api/gl-categories/{category_id}")
    assert response.status_code == 200
