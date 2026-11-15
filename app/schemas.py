from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["rainfall", "temperature", "soil_wetness"]
Interval = Literal["daily", "monthly"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Warning(Model):
    code: str
    message: str
    field: str | None = None


class Source(Model):
    source_id: str
    name: str
    url: str
    period: str
    limitations: str
    license: str | None = None


class SoilReference(Model):
    ph: float = Field(ge=0, le=14)
    depth_cm: tuple[int, int]
    mapping_unit_id: int
    component_share_percent: float = Field(gt=0, le=100)
    source_url: str
    resolution: str
    method: str
    latitude: float
    longitude: float


class Location(Model):
    location_id: str
    name: str
    region: str
    latitude: float
    longitude: float
    coverage_start: Date
    coverage_end: Date
    spatial_scope: str = "gridded_point_sample"
    soil_reference: SoilReference | None = None


class Geometry(Model):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]


class Feature(Model):
    type: Literal["Feature"] = "Feature"
    geometry: Geometry
    properties: dict[str, object]


class FeatureCollection(Model):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature]


class CropReference(Model):
    crop_id: str
    crop_name: str
    scientific_name: str
    ecocrop_id: int
    temperature_c_optimal_min: float
    temperature_c_optimal_max: float
    temperature_c_absolute_min: float
    temperature_c_absolute_max: float
    annual_rainfall_mm_optimal_min: float
    annual_rainfall_mm_optimal_max: float
    annual_rainfall_mm_absolute_min: float
    annual_rainfall_mm_absolute_max: float
    soil_ph_optimal_min: float
    soil_ph_optimal_max: float
    soil_ph_absolute_min: float
    soil_ph_absolute_max: float
    crop_cycle_days_min: int
    crop_cycle_days_max: int
    soil_texture_optimal: str | None
    soil_texture_absolute: str | None
    soil_drainage_optimal: str | None
    soil_drainage_absolute: str | None
    source_resource: str
    source_url: str
    local_variety_validated: bool
    life_span: Literal["annual", "perennial", "annual_or_perennial", "unknown"] = "unknown"
    rotation_candidate: bool = True
    life_span_source_url: str | None = None


class CropCatalog(Model):
    items: list[CropReference]
    warnings: list[Warning]


class Health(Model):
    status: str = "ok"
    data_loaded: bool = True
    application_version: str
    data_version: str


class LegendEntry(Model):
    class_code: int
    source_label: str
    red: int
    green: int
    blue: int
    alpha: int


class MapLayer(Model):
    layer_id: str
    name: str
    crop: str
    management: str
    water_supply: str
    baseline: str
    resolution: str
    source_raster_bbox: list[float]
    crs: str
    legend: list[LegendEntry]
    preview_url: str | None
    image_role: str = "reference_preview_not_georeferenced_overlay"
    source: Source
    limitations: str


class ExploreRequest(Model):
    location_id: str = Field(min_length=1, max_length=80)
    start_date: Date
    end_date: Date
    categories: list[Category] = Field(min_length=1, max_length=3)
    interval: Interval = "monthly"

    @model_validator(mode="after")
    def check_selection(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if len(set(self.categories)) != len(self.categories):
            raise ValueError("categories must not contain duplicates")
        days = (self.end_date - self.start_date).days + 1
        if self.interval == "daily" and days > 366:
            raise ValueError("Daily views support up to 366 days; select monthly for a longer period")
        return self


class SeriesPoint(Model):
    period_start: Date
    period_end: Date
    value: float | None
    expected_days: int
    valid_days: int
    coverage_fraction: float
    partial_calendar_month: bool


class Series(Model):
    series_id: str
    label: str
    unit: str
    aggregation: str
    visible_by_default: bool = True
    points: list[SeriesPoint]


class Panel(Model):
    category: Category
    title: str
    x_axis_label: str = "Date (UTC)"
    y_axis_label: str
    series: list[Series]


class Statistic(Model):
    metric_id: str
    label: str
    value: float | None
    unit: str
    aggregation: str
    expected_days: int
    valid_days: int
    date: Date | None = None
    note: str | None = None


class Description(Model):
    text: str
    evidence_ids: list[str]


class ExploreResponse(Model):
    analysis_id: str
    request: ExploreRequest
    location: Location
    panels: list[Panel]
    statistics: list[Statistic]
    descriptions: list[Description]
    selected_location_geojson: Feature
    map_references: list[MapLayer]
    sources: list[Source]
    warnings: list[Warning]
    data_version: str
    methods_version: str


class Metadata(Model):
    coverage_start: Date
    coverage_end: Date
    time_standard: str = "UTC"
    categories: list[str]
    intervals: list[str]
    series: list[dict[str, str]]
    features: dict[str, bool]
    sources: list[Source]
    warnings: list[Warning]
    data_version: str
    methods_version: str
