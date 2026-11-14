from fastapi import APIRouter, Depends, Response

from app.data_store import DataStore
from app.dependencies import get_store
from app.rotation_schemas import ExportRequest
from app.services.explore import explore
from app.services.reports import report_bytes
from app.services.rotations import compare_rotations

router = APIRouter(prefix="/api/v1/exports", tags=["Exports"])


@router.post("/pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def export_pdf(body: ExportRequest, store: DataStore = Depends(get_store)):
    result = explore(store, body.exploration)
    comparison = compare_rotations(store, body.rotation) if body.rotation else None
    content = report_bytes(store, result, comparison)
    selected = body.exploration
    name = f"agro-field-{selected.location_id}-{selected.start_date}-{selected.end_date}.pdf"
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{name}"',
    })
