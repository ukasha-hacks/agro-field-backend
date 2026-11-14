def test_catalog_uses_local_data(client):
    assert client.get("/health").json()["data_loaded"] is True
    locations = client.get("/api/v1/locations").json()
    assert len(locations) == 4
    points = client.get("/api/v1/locations.geojson").json()
    gulu = next(item for item in points["features"] if item["properties"]["location_id"] == "northern_gulu")
    assert gulu["geometry"]["coordinates"] == [32.299, 2.774]
    crops = client.get("/api/v1/crops").json()["items"]
    assert len(crops) == 4
    assert all(item["local_variety_validated"] is False for item in crops)


def test_map_is_an_explicit_reference(client):
    layer = client.get("/api/v1/map-layers").json()[0]
    assert layer["image_role"] == "reference_preview_not_georeferenced_overlay"
    assert client.get(layer["preview_url"]).headers["content-type"] == "image/png"
    assert client.get("/api/v1/map-layers/not-a-layer/preview").status_code == 404


def test_errors_have_a_consistent_shape(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert set(response.json()["error"]) == {"code", "message", "details"}
