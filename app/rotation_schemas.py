from datetime import date
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas import ExploreRequest, ExploreResponse, Model, Source, Warning

CheckStatus = Literal["pass", "fail", "unknown"]
AssessmentStatus = Literal["assessed", "provisional", "reference_only", "insufficient_evidence"]


class CropHistory(Model):
    season_label: str = Field(min_length=1, max_length=100)
    crops: list[str] = Field(max_length=12)

    @field_validator("crops")
    @classmethod
    def normalize_crops(cls, crops):
        cleaned = [crop.strip().lower() for crop in crops]
        if any(not crop or len(crop) > 80 for crop in cleaned):
            raise ValueError("Crop names must contain 1-80 characters")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Do not repeat a crop within one season")
        if "unknown" in cleaned and len(cleaned) != 1:
            raise ValueError("Use unknown by itself for an unknown season")
        return cleaned


class PlannedSeason(CropHistory):
    season_label: str = "Planned season"
    season: int = Field(ge=1, le=3)
    planting_date: date | None = None
    harvest_date: date | None = None

    @model_validator(mode="after")
    def check_dates(self):
        if self.planting_date and self.harvest_date and self.harvest_date < self.planting_date:
            raise ValueError("harvest_date cannot precede planting_date")
        return self


class SoilInput(Model):
    ph: float | None = Field(default=None, ge=0, le=14)
    texture: str | None = Field(default=None, max_length=100)
    organic_carbon_percent: float | None = Field(default=None, ge=0, le=100)
    use_area_estimate: bool = True


class RotationRequest(Model):
    exploration: ExploreRequest
    crop_history: list[CropHistory] = Field(min_length=1, max_length=20)
    baseline_sequence: list[PlannedSeason] = Field(min_length=3, max_length=3)
    water_supply: Literal["rainfall_only", "limited_irrigation", "reliable_irrigation", "unknown"] = "unknown"
    priority: Literal["improve_soil", "conserve_water", "reduce_pests", "income", "general"] = "general"
    excluded_crops: list[str] = Field(default_factory=list, max_length=30)
    preferred_crops: list[str] = Field(default_factory=list, max_length=30)
    soil: SoilInput = Field(default_factory=SoilInput)
    repeats: bool = False

    @field_validator("excluded_crops", "preferred_crops")
    @classmethod
    def clean_choices(cls, choices):
        cleaned = [item.strip().lower() for item in choices]
        if any(not item or len(item) > 80 for item in cleaned):
            raise ValueError("Crop choices must contain 1-80 characters")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Crop choices must be unique")
        return cleaned

    @model_validator(mode="after")
    def check_sequence(self):
        if [item.season for item in self.baseline_sequence] != [1, 2, 3]:
            raise ValueError("baseline_sequence must contain seasons 1, 2, 3 in order")
        if set(self.excluded_crops) & set(self.preferred_crops):
            raise ValueError("A crop cannot be both preferred and excluded")
        return self


class AgriculturalRule(Model):
    rule_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1000)
    criterion: str = Field(min_length=1, max_length=100)
    kind: Literal["minimum_crop_break", "soil_ph_range", "requires_irrigation"]
    crops: list[str] = Field(min_length=1, max_length=20)
    source_url: str = Field(min_length=1, max_length=2000)
    applicability: str = Field(min_length=1, max_length=1000)
    review_status: Literal["pending", "reviewed"] = "pending"
    min_break_seasons: int | None = Field(default=None, ge=0, le=20)
    minimum: float | None = Field(default=None, ge=0, le=14)
    maximum: float | None = Field(default=None, ge=0, le=14)

    @model_validator(mode="after")
    def check_parameters(self):
        if not self.source_url.startswith(("https://", "http://")):
            raise ValueError("Rules need a traceable source URL; it is never fetched at runtime")
        if self.kind == "minimum_crop_break" and self.min_break_seasons is None:
            raise ValueError("A crop-break rule needs min_break_seasons")
        if self.kind == "soil_ph_range":
            if self.minimum is None or self.maximum is None or self.minimum > self.maximum:
                raise ValueError("A pH rule needs ordered minimum and maximum values")
        return self


class RuleSet(Model):
    version: str
    review_status: Literal["pending", "reviewed"]
    notes: str
    rules: list[AgriculturalRule]
    reference_checks: list[Literal["soil_ph", "minimum_cycle_days", "historical_temperature"]] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_rules(self):
        if len({rule.rule_id for rule in self.rules}) != len(self.rules):
            raise ValueError("Agricultural rule IDs must be unique")
        return self

    def reviewed_rules(self):
        if self.review_status != "reviewed":
            return []
        return [rule for rule in self.rules if rule.review_status == "reviewed"]


class CriterionCheck(Model):
    criterion: str
    status: CheckStatus
    reason: str
    rule_id: str | None = None
    source_url: str | None = None
    gap_type: Literal["farmer_input", "missing_reference", "local_review", "missing_observation"] | None = None


class Strategy(Model):
    strategy_id: str
    sequence: list[PlannedSeason]
    feasibility_status: Literal["feasible_for_declared_checks", "infeasible", "unknown"]
    checks: list[CriterionCheck]
    explanations: list[str]
    potential_benefits: list[str] | None = None
    tradeoffs: list[str] | None = None
    local_review_required: bool = True
    summary: str | None = None
    next_step: str | None = None


class AlternativeSlot(Model):
    strategy_id: str
    reason: str


class RotationConclusion(Model):
    title: str
    detail: str
    tone: Literal["attention", "review", "complete"]
    next_steps: list[str] = Field(max_length=3)


class RotationResponse(Model):
    assessment_id: str
    status: AssessmentStatus
    baseline: Strategy
    alternatives: list[Strategy]
    unfilled_alternative_slots: list[AlternativeSlot]
    environmental_context: ExploreResponse
    priority: str
    rules_version: str
    criteria: list[str]
    missing_information: list[str]
    sources: list[Source]
    warnings: list[Warning]
    candidate_counts: dict[str, int]
    conclusion: RotationConclusion
    selection_method: str = "constraint_checks_then_explicit_crop_preferences; no agronomic overall score"


class ExportRequest(Model):
    exploration: ExploreRequest
    rotation: RotationRequest | None = None

    @model_validator(mode="after")
    def matching_context(self):
        if self.rotation and self.rotation.exploration != self.exploration:
            raise ValueError("The report and rotation must use the same exploration selections")
        return self
