from io import BytesIO

from pypdf import PdfReader

from tests.test_explore import selection


def test_pdf_matches_selected_data(client):
    body = selection()
    result = client.post("/api/v1/explore", json=body).json()
    response = client.post("/api/v1/exports/pdf", json={"exploration": body})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Gulu vicinity" in text
    assert "2024-01-01 to 2024-01-31" in text
    assert "39.590" in text
    assert result["analysis_id"] in text
    assert "NASA" in text and "baseline 2010" in text


def test_pdf_rejects_calculated_client_payloads(client):
    response = client.post("/api/v1/exports/pdf", json={"exploration": selection(), "statistics": []})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"


def test_pdf_without_optional_map(client, monkeypatch, tmp_path):
    monkeypatch.setattr(client.app.state.store, "root", tmp_path)
    response = client.post("/api/v1/exports/pdf", json={"exploration": selection(categories=["rainfall"])})
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
    assert response.status_code == 200
    assert "Reference map unavailable" in text


def test_pdf_embeds_readable_fonts_and_uses_plain_wetness_units(client):
    response = client.post("/api/v1/exports/pdf", json={"exploration": selection()})
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "dimensionless_index" not in text
    assert "Surface wetness: average" in text
    assert "Root-zone wetness: average" in text
    assert "/ 1" in text
    fonts = {}
    for page in reader.pages:
        for ref in page["/Resources"].get("/Font", {}).values():
            font = ref.get_object()
            if "DMSans" in str(font.get("/BaseFont", "")):
                descriptor = font["/FontDescriptor"].get_object()
                assert descriptor["/FontFile2"].get_object().get_data()
                fonts[str(font["/BaseFont"])] = font
    assert len(fonts) >= 2
