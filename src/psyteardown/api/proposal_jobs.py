"""Persistent proposal-job HTTP boundary."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from psyteardown.api.dependencies import get_product_job_service
from psyteardown.api.projects import ERROR_RESPONSES
from psyteardown.api.schemas import (
    CreateProposalJobRequest,
    ProductProposalJobResponse,
    ProposalJobActionRequest,
)
from psyteardown.product import ProductProposalJobService


router = APIRouter(prefix="/projects", tags=["product-proposal-jobs"])
JobService = Annotated[ProductProposalJobService, Depends(get_product_job_service)]


@router.post(
    "/{project_id}/proposal-jobs",
    response_model=ProductProposalJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
async def create_proposal_job(
    project_id: str,
    request: CreateProposalJobRequest,
    service: JobService,
) -> ProductProposalJobResponse:
    job = service.create_job(
        project_id=project_id,
        kind=request.kind,
        actor=request.actor,
        reason=request.reason,
        raw_input=request.raw_input,
        feedback_id=request.feedback_id,
    )
    return ProductProposalJobResponse.from_domain(job)


@router.get(
    "/{project_id}/proposal-jobs",
    response_model=list[ProductProposalJobResponse],
    responses=ERROR_RESPONSES,
)
async def list_proposal_jobs(
    project_id: str, service: JobService
) -> list[ProductProposalJobResponse]:
    return [
        ProductProposalJobResponse.from_domain(job)
        for job in service.list_jobs(project_id)
    ]


@router.get(
    "/{project_id}/proposal-jobs/{job_id}",
    response_model=ProductProposalJobResponse,
    responses=ERROR_RESPONSES,
)
async def get_proposal_job(
    project_id: str, job_id: str, service: JobService
) -> ProductProposalJobResponse:
    return ProductProposalJobResponse.from_domain(
        service.get_job(project_id, job_id)
    )


@router.post(
    "/{project_id}/proposal-jobs/{job_id}/runs",
    response_model=ProductProposalJobResponse,
    status_code=status.HTTP_200_OK,
    responses=ERROR_RESPONSES,
)
async def run_proposal_job(
    project_id: str,
    job_id: str,
    request: ProposalJobActionRequest,
    service: JobService,
) -> ProductProposalJobResponse:
    return ProductProposalJobResponse.from_domain(
        service.run_job(project_id, job_id, actor=request.actor)
    )


@router.post(
    "/{project_id}/proposal-jobs/{job_id}/retries",
    response_model=ProductProposalJobResponse,
    status_code=status.HTTP_200_OK,
    responses=ERROR_RESPONSES,
)
async def retry_proposal_job(
    project_id: str,
    job_id: str,
    request: ProposalJobActionRequest,
    service: JobService,
) -> ProductProposalJobResponse:
    return ProductProposalJobResponse.from_domain(
        service.retry_job(project_id, job_id, actor=request.actor)
    )
