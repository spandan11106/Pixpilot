from fastapi import APIRouter
from pydantic import BaseModel

from app.core.run_manager import run_manager

router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRunResponse(BaseModel):
    run_id: str


@router.post("", response_model=CreateRunResponse, status_code=201)
async def create_run() -> CreateRunResponse:
    run_id = run_manager.create_run()
    return CreateRunResponse(run_id=run_id)


@router.get("/{run_id}/metadata")
async def get_run_metadata(run_id: str) -> dict:
    return run_manager.get_metadata(run_id)
