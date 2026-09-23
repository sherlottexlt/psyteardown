"""HTTP boundary for B5 bounded repair jobs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from psyteardown.api.dependencies import get_product_repair_job_service
from psyteardown.api.projects import ERROR_RESPONSES
from psyteardown.api.schemas import (
    CreateRepairJobRequest,
    RepairJobActionRequest,
    RepairJobResponse,
)
from psyteardown.product import ProductRepairJobService, RepairBudget


router = APIRouter(prefix="/projects", tags=["product-repair-jobs"])
RepairService = Annotated[
    ProductRepairJobService, Depends(get_product_repair_job_service)
]


@router.post(
    "/{project_id}/repair-jobs",
    response_model=RepairJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
async def create_repair_job(
    project_id: str,
    request: CreateRepairJobRequest,
    service: RepairService,
) -> RepairJobResponse:
    budget = RepairBudget(**request.budget.model_dump()) if request.budget else None
    return RepairJobResponse.from_domain(
        service.create_job(
            project_id=project_id,
            execution_job_id=request.execution_job_id,
            actor=request.actor,
            reason=request.reason,
            budget=budget,
        )
    )


@router.get(
    "/{project_id}/repair-jobs",
    response_model=list[RepairJobResponse],
    responses=ERROR_RESPONSES,
)
async def list_repair_jobs(
    project_id: str, service: RepairService
) -> list[RepairJobResponse]:
    return [RepairJobResponse.from_domain(job) for job in service.list_jobs(project_id)]


@router.get(
    "/{project_id}/repair-jobs/{job_id}",
    response_model=RepairJobResponse,
    responses=ERROR_RESPONSES,
)
async def get_repair_job(
    project_id: str, job_id: str, service: RepairService
) -> RepairJobResponse:
    return RepairJobResponse.from_domain(service.get_job(project_id, job_id))


@router.post(
    "/{project_id}/repair-jobs/{job_id}/runs",
    response_model=RepairJobResponse,
    responses=ERROR_RESPONSES,
)
async def run_repair_job(
    project_id: str,
    job_id: str,
    request: RepairJobActionRequest,
    service: RepairService,
) -> RepairJobResponse:
    return RepairJobResponse.from_domain(service.run_job(project_id, job_id, actor=request.actor))


@router.post(
    "/{project_id}/repair-jobs/{job_id}/retries",
    response_model=RepairJobResponse,
    responses=ERROR_RESPONSES,
)
async def retry_repair_job(
    project_id: str,
    job_id: str,
    request: RepairJobActionRequest,
    service: RepairService,
) -> RepairJobResponse:
    return RepairJobResponse.from_domain(service.retry_job(project_id, job_id, actor=request.actor))


@router.post(
    "/{project_id}/repair-jobs/{job_id}/cancellations",
    response_model=RepairJobResponse,
    responses=ERROR_RESPONSES,
)
async def cancel_repair_job(
    project_id: str,
    job_id: str,
    request: RepairJobActionRequest,
    service: RepairService,
) -> RepairJobResponse:
    return RepairJobResponse.from_domain(service.cancel_job(project_id, job_id, actor=request.actor))
