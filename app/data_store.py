import hashlib
import json
from pathlib import Path

import pandas as pd

from app.errors import ApiError
from app.schemas import CropReference, Feature, Geometry, Location, MapLayer, Source, Warning

DAILY_FILE = "inputs/environment/daily_environment_2016_2025.csv"
LOCATION_FILE = "inputs/maps/sample_locations.csv"
CROP_FILE = "inputs/crops/crop_reference_requirements.csv"
MAP_ID = "gaez_maize_soil_terrain_low_inputs"
MAP_PREVIEW = "previews/maize_soil_terrain_map.png"
ENV_COLUMNS = [
    "temperature_mean_c", "temperature_min_c", "temperature_max_c", "rainfall_mm",
    "surface_soil_wetness", "root_zone_soil_wetness", "relative_humidity_percent",
    "wind_speed_2m_m_s", "solar_radiation_mj_m2_day",
]

SOURCES = [
    Source(source_id="nasa_power_merra2", name="NASA POWER / MERRA-2",
           url="https://power.larc.nasa.gov/", period="2016-2025",
           limitations="Gridded historical point samples; wetness is a modelled index, not a farm soil test."),
    Source(source_id="gpm_imerg", name="GPM IMERG through NASA POWER",
           url="https://gpm.nasa.gov/data", period="2016-2025",
           limitations="Gridded precipitation estimates; not district averages."),
    Source(source_id="fao_ecocrop", name="FAO GAEZ / ECOCROP",
           url="https://gaez.fao.org/pages/ecocrop-find-plant", period="Legacy species references",
           limitations="Annual rainfall and broad crop-cycle ranges; local varieties are not validated."),
    Source(source_id="fao_gaez", name="FAO / IIASA GAEZ v4",
           url="https://gaez.fao.org/", period="Land-resource baseline 2010",
           limitations="Rain-fed, low-input maize soil/terrain reference, including neighboring territory.",
           license="CC-BY-NC-SA-4.0"),
]


def read_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


class DataStore:
    def __init__(self, root: Path):
        self.root = root
        self.daily = pd.read_csv(root / DAILY_FILE)
        self._validate_daily()
        self.start_date = self.daily["date"].min().date()
        self.end_date = self.daily["date"].max().date()
        self.soil_points = self._load_soil_points()
        self.locations = self._load_locations()
        self.crops = self._load_crops()
        try:
            self.map_layers = self._load_map_layers()
        except (OSError, ValueError, KeyError, TypeError):
            # A broken optional map must not prevent access to the daily series.
            self.map_layers = []
        self.version = self._fingerprint()

    def _validate_daily(self):
        if self.daily.empty:
            raise ValueError("Daily data contains no observations")
        required = {"sample_id", "date", "latitude", "longitude", *ENV_COLUMNS}
        missing = required - set(self.daily.columns)
        if missing:
            raise ValueError(f"Daily data is missing columns: {sorted(missing)}")
        self.daily["date"] = pd.to_datetime(self.daily["date"], format="%Y-%m-%d", errors="raise")
        if self.daily["date"].isna().any() or self.daily["sample_id"].isna().any():
            raise ValueError("Daily keys cannot be empty")
        if self.daily.duplicated(["sample_id", "date"]).any():
            raise ValueError("Daily data contains duplicate location/date keys")
        for column in ENV_COLUMNS + ["latitude", "longitude"]:
            values = pd.to_numeric(self.daily[column], errors="raise")
            if values.isin([float("inf"), float("-inf"), -999]).any():
                raise ValueError(f"Invalid numeric values in {column}")
            self.daily[column] = values
        for column in ["rainfall_mm", "wind_speed_2m_m_s", "solar_radiation_mj_m2_day"]:
            if (self.daily[column].dropna() < 0).any():
                raise ValueError(f"Negative values in {column}")
        for column in ["surface_soil_wetness", "root_zone_soil_wetness"]:
            if not self.daily[column].dropna().between(0, 1).all():
                raise ValueError(f"Wetness outside 0-1 in {column}")
        if not self.daily["relative_humidity_percent"].dropna().between(0, 100).all():
            raise ValueError("Relative humidity outside 0-100")
        temperatures = self.daily[["temperature_min_c", "temperature_mean_c", "temperature_max_c"]].dropna()
        ordered = temperatures["temperature_min_c"] <= temperatures["temperature_mean_c"]
        ordered &= temperatures["temperature_mean_c"] <= temperatures["temperature_max_c"]
        if not ordered.all():
            raise ValueError("Daily minimum/mean/maximum temperatures are out of order")
        self.daily = self.daily.sort_values(["sample_id", "date"]).reset_index(drop=True)

    def _load_locations(self):
        rows = pd.read_csv(self.root / LOCATION_FILE)
        if rows["sample_id"].duplicated().any():
            raise ValueError("Duplicate location IDs")
        if set(rows["sample_id"]) != set(self.daily["sample_id"]):
            raise ValueError("Location catalog and environmental data do not match")
        locations = {}
        for row in rows.to_dict("records"):
            location = Location(
                location_id=row["sample_id"], name=row["sample_name"], region=row["region"],
                latitude=row["latitude"], longitude=row["longitude"],
                coverage_start=self.start_date, coverage_end=self.end_date,
                soil_reference=self.soil_points.get(row["sample_id"]),
            )
            if not -90 <= location.latitude <= 90 or not -180 <= location.longitude <= 180:
                raise ValueError("Invalid location coordinates")
            soil = location.soil_reference
            if soil and (soil.latitude != location.latitude or soil.longitude != location.longitude):
                raise ValueError("Soil reference coordinates differ from the sample location")
            samples = self.daily[self.daily["sample_id"] == location.location_id]
            if not samples["latitude"].eq(location.latitude).all():
                raise ValueError("Latitude differs between catalog and daily data")
            if not samples["longitude"].eq(location.longitude).all():
                raise ValueError("Longitude differs between catalog and daily data")
            locations[location.location_id] = location
        return locations

    def _load_crops(self):
        rows = pd.read_csv(self.root / CROP_FILE, dtype={"local_variety_validated": "string"})
        rows = rows.astype(object).where(rows.notna(), None)
        crops = []
        for row in rows.to_dict("records"):
            value = str(row["local_variety_validated"]).lower()
            if value not in {"true", "false"}:
                raise ValueError("Crop validation flag must be true or false")
            row["local_variety_validated"] = value == "true"
            crops.append(CropReference(**row))
        extra = self.root / "supplemental/crops.json"
        if extra.is_file():
            crops.extend(CropReference(**row) for row in read_json(extra))
        if len({crop.crop_id for crop in crops}) != len(crops):
            raise ValueError("Duplicate crop IDs")
        return crops

    def _load_soil_points(self):
        path = self.root / "supplemental/soil_points.json"
        return read_json(path) if path.is_file() else {}

    def _load_map_layers(self):
        metadata = self.root / "inputs/maps/gaez_map_metadata.json"
        legend_file = self.root / "inputs/maps/gaez_maize_map_legend.csv"
        if not metadata.exists() or not legend_file.exists():
            return []
        info = read_json(metadata)
        legend = pd.read_csv(legend_file).to_dict("records")
        preview_url = None
        if (self.root / MAP_PREVIEW).is_file():
            preview_url = f"/api/v1/map-layers/{MAP_ID}/preview"
        return [MapLayer(
            layer_id=MAP_ID, name="Maize soil and terrain suitability",
            crop=info["crop"], management=info["management"], water_supply=info["water_supply"],
            baseline=info["land_resource_baseline"], resolution=info["native_resolution_label"],
            source_raster_bbox=info["actual_bbox_west_south_east_north"], crs=info["crs"],
            legend=legend, preview_url=preview_url, source=SOURCES[3], limitations=info["important_limit"],
        )]

    def _fingerprint(self):
        digest = hashlib.sha256()
        paths = [DAILY_FILE, LOCATION_FILE, CROP_FILE, "inputs/maps/gaez_map_metadata.json",
                 "inputs/maps/gaez_maize_map_legend.csv", MAP_PREVIEW,
                 "supplemental/crops.json", "supplemental/soil_points.json"]
        for name in sorted(paths):
            path = self.root / name
            digest.update(name.encode())
            digest.update(path.read_bytes() if path.is_file() else b"missing")
        return digest.hexdigest()[:16]

    def location(self, location_id: str):
        if location_id not in self.locations:
            raise ApiError(404, "unknown_location", "Choose a supported location ID.")
        return self.locations[location_id]

    def feature(self, location_id: str):
        location = self.location(location_id)
        return Feature(
            geometry=Geometry(coordinates=(location.longitude, location.latitude)),
            properties=location.model_dump(mode="json"),
        )

    def warnings(self):
        items = [
            Warning(code="historical_data", message="Historical data, 2016-2025; not current weather or a forecast."),
            Warning(code="point_coverage", message="Gridded sample points are not farm measurements or district averages."),
        ]
        if not self.map_layers or not self.map_layers[0].preview_url:
            items.append(Warning(code="map_unavailable", message="The optional reference map preview is unavailable."))
        return items
