import copy
import json
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.rotation_schemas import RotationRequest, RuleSet
from app.services.rotations import compare_rotations


def rotation_body():
    return json.loads(Path("examples/rotation.json").read_text())


def fixture_rules():
    # Synthetic rules exercise the engine; they are not agricultural advice.
    return RuleSet(
        version="test-fixture", review_status="reviewed", notes="Test fixture only",
        rules=[{
            "rule_id": "fixture-break", "description": "Synthetic one-season break",
            "criterion": "crop_break", "kind": "minimum_crop_break",
            "crops": ["maize", "beans", "groundnut", "sorghum"],
            "source_url": "https://example.invalid/test-fixture", "applicability": "Tests only",
            "review_status": "reviewed", "min_break_seasons": 1,
        }],
    )


def test_default_local_references_offer_options_without_claiming_validation(client):
    response = client.post("/api/v1/rotation-comparisons", json=rotation_body())
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "reference_only"
    assert len(result["alternatives"]) == 2
    assert result["unfilled_alternative_slots"] == []
    assert result["baseline"]["sequence"][0]["crops"] == ["maize"]
    assert result["candidate_counts"]["evaluated"] == 63
    assert any("No reviewed" in item for item in result["missing_information"])
    assert "not agronomic ranking" in result["selection_method"]
    combinations = []
    for option in result["alternatives"]:
        crops = frozenset(crop for season in option["sequence"] for crop in season["crops"])
        assert crops <= {"maize", "beans", "groundnut", "sorghum"}
        assert len(crops) >= 2
        combinations.append(crops)
        assert option["feasibility_status"] == "unknown"
        assert option["potential_benefits"] is None
        assert any(check["criterion"].endswith("historical_temperature") and check["status"] == "pass" for check in option["checks"])
    assert len(set(combinations)) == 2


def test_reviewed_fixture_checks_preferences_and_exclusions(client):
    store = copy.copy(client.app.state.store)
    store.rules = fixture_rules()
    body = rotation_body()
    body["excluded_crops"] = ["groundnut"]
    body["preferred_crops"] = ["sorghum"]
    result = compare_rotations(store, RotationRequest(**body))
    assert result.status == "provisional"
    assert result.baseline.feasibility_status == "infeasible"
    assert len(result.alternatives) == 2
    seen = set()
    for alternative in result.alternatives:
        crops = tuple(season.crops[0] for season in alternative.sequence)
        assert "groundnut" not in crops
        assert crops not in seen and crops != ("maize", "maize", "maize")
        seen.add(crops)
        assert crops[0] != "maize" and all(crops[i] != crops[i - 1] for i in range(1, 3))
        assert alternative.potential_benefits is None


def test_unknown_and_mixed_baseline_is_retained(client):
    body = rotation_body()
    body["crop_history"] = [{"season_label": "Previous", "crops": ["unknown"]}]
    body["baseline_sequence"][0]["crops"] = ["banana", "beans"]
    result = client.post("/api/v1/rotation-comparisons", json=body).json()
    assert result["baseline"]["sequence"][0]["crops"] == ["banana", "beans"]
    assert result["status"] == "insufficient_evidence"


@pytest.mark.parametrize("change", ["order", "dates", "soil", "preferences"])
def test_invalid_rotation_inputs(client, change):
    body = rotation_body()
    if change == "order":
        body["baseline_sequence"][0]["season"] = 2
    elif change == "dates":
        body["baseline_sequence"][0].update(planting_date="2027-06-01", harvest_date="2027-01-01")
    elif change == "soil":
        body["soil"]["ph"] = 20
    else:
        body["excluded_crops"] = ["maize"]
        body["preferred_crops"] = ["maize"]
    assert client.post("/api/v1/rotation-comparisons", json=body).status_code == 422


def test_combined_report_preserves_evidence_status(client):
    body = rotation_body()
    response = client.post("/api/v1/exports/pdf", json={"exploration": body["exploration"], "rotation": body})
    assert response.status_code == 200
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
    assert "reference only" in text
    assert "not validated rotation recommendations" in text
    assert "No reviewed agricultural rules" in text
    assert "Existing Rotation" in text


def test_combined_report_requires_same_selection(client):
    body = rotation_body()
    selection = body["exploration"] | {"location_id": "central_masaka"}
    response = client.post("/api/v1/exports/pdf", json={"exploration": selection, "rotation": body})
    assert response.status_code == 422
