"""HTTP boundary for bounded Web source-generation jobs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from psyteardown.api.dependencies import get_product_generation_job_service
from psyteardown.api.projects import ERROR_RESPONSES
from psyteardown.api.schemas import (
    CreateGenerationJobRequest,
    GenerationJobActionRequest,
    ProductGenerationJobResponse,
)
from psyteardown.product import GenerationBudget, ProductGenerationJobService


router = APIRouter(prefix="/projects", tags=["product-generation-jobs"])
GenerationService = Annotated[
    ProductGenerationJobService, Depends(get_product_generation_job_service)
]


@router.post(
    "/{project_id}/generation-jobs",
    response_model=ProductGenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
async def create_generation_job(
    project_id: str,
    request: CreateGenerationJobRequest,
    service: GenerationService,
) -> ProductGenerationJobResponse:
    budget = GenerationBudget(**request.budget.model_dump()) if request.budget else None
    return ProductGenerationJobResponse.from_domain(
        service.create_job(
            project_id=project_id,
            actor=request.actor,
            reason=request.reason,
            budget=budget,
        )
    )


@router.get(
    "/{project_id}/generation-jobs",
    response_model=list[ProductGenerationJobResponse],
    responses=ERROR_RESPONSES,
)
async def list_generation_jobs(
    project_id: str, service: GenerationService
) -> list[ProductGenerationJobResponse]:
    return [
        ProductGenerationJobResponse.from_domain(job)
        for job in service.list_jobs(project_id)
    ]


@router.get(
    "/{project_id}/generation-jobs/{job_id}",
    response_model=ProductGenerationJobResponse,
    responses=ERROR_RESPONSES,
)
async def get_generation_job(
    project_id: str, job_id: str, service: GenerationService
) -> ProductGenerationJobResponse:
    return ProductGenerationJobResponse.from_domain(service.get_job(project_id, job_id))


@router.post(
    "/{project_id}/generation-jobs/{job_id}/runs",
    response_model=ProductGenerationJobResponse,
    responses=ERROR_RESPONSES,
)
async def run_generation_job(
    project_id: str,
    job_id: str,
    request: GenerationJobActionRequest,
    service: GenerationService,
) -> ProductGenerationJobResponse:
    return ProductGenerationJobResponse.from_domain(
        service.run_job(project_id, job_id, actor=request.actor)
    )


@router.post(
    "/{project_id}/generation-jobs/{job_id}/pauses",
    response_model=ProductGenerationJobResponse,
    responses=ERROR_RESPONSES,
)
async def pause_generation_job(
    project_id: str,
    job_id: str,
    request: GenerationJobActionRequest,
    service: GenerationService,
) -> ProductGenerationJobResponse:
    return ProductGenerationJobResponse.from_domain(
        service.pause_job(project_id, job_id, actor=request.actor)
    )


@router.post(
    "/{project_id}/generation-jobs/{job_id}/resumes",
    response_model=ProductGenerationJobResponse,
    responses=ERROR_RESPONSES,
)
async def resume_generation_job(
    project_id: str,
    job_id: str,
    request: GenerationJobActionRequest,
    service: GenerationService,
) -> ProductGenerationJobResponse:
    return ProductGenerationJobResponse.from_domain(
        service.resume_job(project_id, job_id, actor=request.actor)
    )


@router.post(
    "/{project_id}/generation-jobs/{job_id}/cancellations",
    response_model=ProductGenerationJobResponse,
    responses=ERROR_RESPONSES,
)
async def cancel_generation_job(
    project_id: str,
    job_id: str,
    request: GenerationJobActionRequest,
    service: GenerationService,
) -> ProductGenerationJobResponse:
    return ProductGenerationJobResponse.from_domain(
        service.cancel_job(project_id, job_id, actor=request.actor)
    )


@router.post(
    "/{project_id}/generation-jobs/{job_id}/retries",
    response_model=ProductGenerationJobResponse,
    responses=ERROR_RESPONSES,
)
async def retry_generation_job(
    project_id: str,
    job_id: str,
    request: GenerationJobActionRequest,
    service: GenerationService,
) -> ProductGenerationJobResponse:
    return ProductGenerationJobResponse.from_domain(
        service.retry_job(project_id, job_id, actor=request.actor)
    )
