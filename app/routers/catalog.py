from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.config import APP_VERSION, METHODS_VERSION
from app.data_store import MAP_ID, MAP_PREVIEW, SOURCES, DataStore
from app.dependencies import get_store
from app.errors import ApiError
from app.schemas import CropCatalog, FeatureCollection, Health, Location, MapLayer, Metadata, Warning

router = APIRouter(tags=["Catalog"])


@router.get("/health", response_model=Health)
def health(store: DataStore = Depends(get_store)):
    return Health(application_version=APP_VERSION, data_version=store.version)


@router.get("/api/v1/locations", response_model=list[Location])
def locations(store: DataStore = Depends(get_store)):
    return list(store.locations.values())


@router.get("/api/v1/locations.geojson", response_model=FeatureCollection)
def location_points(store: DataStore = Depends(get_store)):
    return FeatureCollection(features=[store.feature(key) for key in store.locations])


@router.get("/api/v1/crops", response_model=CropCatalog)
def crops(store: DataStore = Depends(get_store)):
    warning = Warning(code="crop_reference_only", message=(
        "Annual rainfall limits are not seasonal water demand. Broad maturity ranges "
        "and species references are not locally validated variety recommendations."
    ))
    return CropCatalog(items=store.crops, warnings=[warning])


@router.get("/api/v1/map-layers", response_model=list[MapLayer])
def map_layers(store: DataStore = Depends(get_store)):
    return store.map_layers


@router.get("/api/v1/map-layers/{layer_id}/preview", response_class=FileResponse)
def map_preview(layer_id: str, store: DataStore = Depends(get_store)):
    if layer_id != MAP_ID:
        raise ApiError(404, "unknown_layer", "This map layer does not exist.")
    path = store.root / MAP_PREVIEW
    if not path.is_file():
        raise ApiError(503, "map_unavailable", "The reference map preview is unavailable.")
    return FileResponse(path, media_type="image/png")


@router.get("/api/v1/metadata", response_model=Metadata)
def metadata(store: DataStore = Depends(get_store)):
    return Metadata(
        coverage_start=store.start_date, coverage_end=store.end_date,
        categories=["rainfall", "temperature", "soil_wetness"], intervals=["daily", "monthly"],
        series=[
            {"category": "rainfall", "unit": "mm", "monthly_aggregation": "sum"},
            {"category": "temperature", "unit": "degC", "monthly_aggregation": "mean; minimum and maximum are extremes"},
            {"category": "soil_wetness", "unit": "dimensionless_index", "monthly_aggregation": "mean"},
        ],
        features={"exploration": True, "pdf_export": True, "map_references": bool(store.map_layers),
                  "rotation_comparison": True, "reviewed_rotation_scoring": False},
        sources=SOURCES, warnings=store.warnings(), data_version=store.version, methods_version=METHODS_VERSION,
    )
