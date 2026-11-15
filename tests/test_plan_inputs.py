import pytest

from tests.test_rotations import rotation_body


def assess(client, body):
    response = client.post("/api/v1/rotation-comparisons", json=body)
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("seasons", [[3], [1, 2, 3]])
def test_incomplete_plans_ask_for_crops_before_comparing(client, seasons):
    body = rotation_body()
    for season in seasons:
        body["baseline_sequence"][season - 1]["crops"] = ["unknown"]
    result = assess(client, body)
    assert result["status"] == "needs_input"
    assert result["alternatives"] == result["unfilled_alternative_slots"] == []
    assert result["candidate_counts"]["evaluated"] == 0
    assert result["conclusion"]["title"].endswith(", ".join(map(str, seasons)))
    assert "Choose" in result["conclusion"]["detail"]
    coverage = next(c for c in result["baseline"]["checks"] if c["criterion"] == "reference_rule_coverage")
    assert coverage["gap_type"] == "farmer_input"


def test_unknown_past_crop_does_not_block_a_complete_plan(client):
    body = rotation_body()
    body["crop_history"][0]["crops"] = ["unknown"]
    result = assess(client, body)
    assert result["status"] == "reference_only"
    assert len(result["alternatives"]) == 2


@pytest.mark.parametrize("days, expected", [(89, "fail"), (90, "pass"), (120, "pass")])
def test_growing_days_check_the_saved_groundnut_minimum(client, days, expected):
    body = rotation_body()
    for season in body["baseline_sequence"]:
        season.update(crops=["groundnut"], planned_days=days)
    result = assess(client, body)
    check = next(c for c in result["baseline"]["checks"] if c["criterion"] == "groundnut_minimum_cycle_days")
    assert check["status"] == expected
    assert check["source_url"]
    if expected == "pass":
        assert "variety maturity is still unverified" in check["reason"]
    for option in result["alternatives"]:
        assert all(season["planned_days"] == days for season in option["sequence"])
        if days < 150:
            assert all("cotton" not in season["crops"] for season in option["sequence"])


def test_exact_dates_take_priority_over_available_days(client):
    body = rotation_body()
    body["baseline_sequence"][0].update(
        crops=["groundnut"], planned_days=120,
        planting_date="2027-03-01", harvest_date="2027-05-28",  # 89 days
    )
    result = assess(client, body)
    assert next(c["status"] for c in result["baseline"]["checks"] if c["criterion"] == "groundnut_minimum_cycle_days") == "fail"


def test_known_overlap_is_caught_even_with_another_undated_season(client):
    body = rotation_body()
    body["baseline_sequence"][0].update(planting_date="2027-03-01", harvest_date="2027-06-30")
    body["baseline_sequence"][1].update(planting_date="2027-06-30", harvest_date="2027-09-30")
    result = assess(client, body)
    assert next(c["status"] for c in result["baseline"]["checks"] if c["criterion"] == "calendar_overlap") == "fail"


@pytest.mark.parametrize("days", [0, -1, 1.5, 3661])
def test_invalid_growing_days_are_rejected(client, days):
    body = rotation_body()
    body["baseline_sequence"][0]["planned_days"] = days
    assert client.post("/api/v1/rotation-comparisons", json=body).status_code == 422


def test_fallow_is_a_known_choice_without_crop_range_validation(client):
    body = rotation_body()
    for season in body["baseline_sequence"]:
        season["crops"] = []
    result = assess(client, body)
    assert result["status"] != "needs_input"
    assert result["conclusion"]["title"] == "Your fallow plan is recorded"
    assert next(c["status"] for c in result["baseline"]["checks"] if c["criterion"] == "crop_reference_coverage") == "unknown"
