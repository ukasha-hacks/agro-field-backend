from fastapi import APIRouter, Depends

from app.data_store import DataStore
from app.dependencies import get_store
from app.schemas import ExploreRequest, ExploreResponse
from app.rotation_schemas import RotationRequest, RotationResponse
from app.services.explore import explore
from app.services.rotations import compare_rotations

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


@router.post("/explore", response_model=ExploreResponse)
def explore_conditions(body: ExploreRequest, store: DataStore = Depends(get_store)):
    return explore(store, body)


@router.post("/rotation-comparisons", response_model=RotationResponse)
def rotation_comparison(body: RotationRequest, store: DataStore = Depends(get_store)):
    return compare_rotations(store, body)
