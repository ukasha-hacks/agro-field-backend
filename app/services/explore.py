import calendar
import hashlib
import json
from dataclasses import dataclass

import pandas as pd

from app.config import METHODS_VERSION
from app.data_store import SOURCES, DataStore
from app.errors import ApiError
from app.schemas import ExploreRequest, ExploreResponse, Panel, Series, SeriesPoint, Statistic, Warning
from app.services.describe import describe


@dataclass(frozen=True)
class SeriesSpec:
    category: str
    series_id: str
    column: str
    label: str
    unit: str
    method: str
    visible: bool = True


SERIES = [
    SeriesSpec("rainfall", "rainfall_total_mm", "rainfall_mm", "Rainfall", "mm", "sum"),
    SeriesSpec("temperature", "temperature_mean_c", "temperature_mean_c", "Mean temperature", "degC", "mean"),
    SeriesSpec("temperature", "temperature_minimum_c", "temperature_min_c", "Minimum temperature", "degC", "min", False),
    SeriesSpec("temperature", "temperature_maximum_c", "temperature_max_c", "Maximum temperature", "degC", "max", False),
    SeriesSpec("soil_wetness", "surface_soil_wetness", "surface_soil_wetness", "Surface wetness", "dimensionless_index", "mean"),
    SeriesSpec("soil_wetness", "root_zone_soil_wetness", "root_zone_soil_wetness", "Root-zone wetness", "dimensionless_index", "mean"),
]

PANEL_LABELS = {
    "rainfall": ("Rainfall", "Rainfall depth (mm)"),
    "temperature": ("Air temperature", "Temperature (degC)"),
    "soil_wetness": ("Modelled soil wetness", "Wetness index (0-1)"),
}


def fingerprint(request, data_version, rules_version=None):
    parts = {"request": request.model_dump(mode="json"), "data": data_version, "methods": METHODS_VERSION}
    if rules_version is not None:
        parts["rules"] = rules_version
    content = json.dumps(parts, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()[:24]


def selected_days(store: DataStore, request: ExploreRequest):
    store.location(request.location_id)
    if request.start_date < store.start_date or request.end_date > store.end_date:
        message = f"Choose dates between {store.start_date} and {store.end_date}."
        raise ApiError(422, "date_outside_coverage", message)
    selected = store.daily[store.daily["sample_id"] == request.location_id]
    calendar_days = pd.date_range(request.start_date, request.end_date, freq="D")
    # Reindex before grouping so a missing source day still counts as expected.
    return selected.set_index("date").reindex(calendar_days)


def aggregate(values: pd.Series, method: str):
    if values.count() != len(values):
        return None
    value = getattr(values, method)()
    return round(float(value), 4)


def series_points(frame, spec, interval):
    if interval == "monthly":
        groups = frame.groupby(frame.index.to_period("M"), sort=True)
    else:
        groups = frame.groupby(frame.index, sort=True)
    points = []
    for _, group in groups:
        start = group.index[0].date()
        end = group.index[-1].date()
        values = group[spec.column]
        expected = len(group)
        valid = int(values.count())
        full_month = start.day == 1 and end.day == calendar.monthrange(end.year, end.month)[1]
        points.append(SeriesPoint(
            period_start=start, period_end=end, value=aggregate(values, spec.method),
            expected_days=expected, valid_days=valid,
            coverage_fraction=round(valid / expected, 4),
            partial_calendar_month=interval == "monthly" and not full_month,
        ))
    return points


def statistic(frame, metric_id, column, label, method, unit):
    values = frame[column]
    value = aggregate(values, method)
    observed_date = None
    note = None
    if value is not None and method in {"min", "max"}:
        index = values.idxmin() if method == "min" else values.idxmax()
        observed_date = index.date()
        note = "Earliest date is shown when the extreme occurs more than once."
    return Statistic(
        metric_id=metric_id, label=label, value=value, unit=unit, aggregation=method,
        expected_days=len(frame), valid_days=int(values.count()), date=observed_date, note=note,
    )


def period_statistics(frame, categories):
    definitions = {
        "rainfall": [
            ("rainfall_total_mm", "rainfall_mm", "Selected-period rainfall", "sum", "mm"),
            ("rainfall_daily_mean_mm", "rainfall_mm", "Mean daily rainfall", "mean", "mm/day"),
            ("rainfall_daily_max_mm", "rainfall_mm", "Highest daily rainfall", "max", "mm/day"),
        ],
        "temperature": [
            ("temperature_mean_c", "temperature_mean_c", "Mean air temperature", "mean", "degC"),
            ("temperature_minimum_c", "temperature_min_c", "Lowest daily minimum", "min", "degC"),
            ("temperature_maximum_c", "temperature_max_c", "Highest daily maximum", "max", "degC"),
        ],
        "soil_wetness": [],
    }
    for column, label in [("surface_soil_wetness", "Surface wetness"), ("root_zone_soil_wetness", "Root-zone wetness")]:
        for method in ["mean", "min", "max"]:
            definitions["soil_wetness"].append(
                (f"{column}_{method}", column, f"{label}: {method}", method, "dimensionless_index")
            )
    return [statistic(frame, *item) for category in categories for item in definitions[category]]


def explore(store: DataStore, request: ExploreRequest) -> ExploreResponse:
    frame = selected_days(store, request)
    panels = []
    warnings = store.warnings()
    if "soil_wetness" in request.categories:
        warnings.append(Warning(code="wetness_is_modelled", message="Wetness is a modelled relative-saturation index, not a soil-health score."))
    for category in request.categories:
        series = []
        for spec in SERIES:
            if spec.category != category:
                continue
            points = series_points(frame, spec, request.interval)
            series.append(Series(
                series_id=spec.series_id, label=spec.label, unit=spec.unit,
                aggregation="daily_observation" if request.interval == "daily" else spec.method,
                visible_by_default=spec.visible, points=points,
            ))
            if frame[spec.column].count() != len(frame):
                warnings.append(Warning(code="incomplete_data", message=(
                    f"{spec.label} has missing observations. Incomplete aggregates remain null."
                ), field=spec.series_id))
        title, axis = PANEL_LABELS[category]
        panels.append(Panel(category=category, title=title, y_axis_label=axis, series=series))
    statistics = period_statistics(frame, request.categories)
    source_ids = set()
    if "rainfall" in request.categories:
        source_ids.add("gpm_imerg")
    if "temperature" in request.categories or "soil_wetness" in request.categories:
        source_ids.add("nasa_power_merra2")
    if store.map_layers:
        source_ids.add("fao_gaez")
    return ExploreResponse(
        analysis_id=fingerprint(request, store.version), request=request,
        location=store.location(request.location_id), panels=panels, statistics=statistics,
        descriptions=describe(statistics), selected_location_geojson=store.feature(request.location_id),
        map_references=store.map_layers, sources=[s for s in SOURCES if s.source_id in source_ids],
        warnings=warnings, data_version=store.version, methods_version=METHODS_VERSION,
    )
