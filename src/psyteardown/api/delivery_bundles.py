"""HTTP boundary for immutable B6 delivery bundles."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse

from psyteardown.api.dependencies import get_product_delivery_bundle_service
from psyteardown.api.projects import ERROR_RESPONSES
from psyteardown.api.schemas import (
    CreateDeliveryBundleRequest,
    DeliveryBundleDiffResponse,
    DeliveryBundleFileChange,
    DeliveryBundleResponse,
)
from psyteardown.product import ProductDeliveryBundleService


router = APIRouter(prefix="/projects", tags=["product-delivery-bundles"])
DeliveryService = Annotated[
    ProductDeliveryBundleService, Depends(get_product_delivery_bundle_service)
]


@router.post(
    "/{project_id}/delivery-bundles",
    response_model=DeliveryBundleResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def create_delivery_bundle(
    project_id: str,
    request: CreateDeliveryBundleRequest,
    service: DeliveryService,
) -> DeliveryBundleResponse:
    return DeliveryBundleResponse.from_domain(
        service.create_bundle(
            project_id=project_id,
            execution_job_id=request.execution_job_id,
            actor=request.actor,
            reason=request.reason,
        )
    )


@router.get(
    "/{project_id}/delivery-bundles",
    response_model=list[DeliveryBundleResponse],
    responses=ERROR_RESPONSES,
)
async def list_delivery_bundles(
    project_id: str, service: DeliveryService
) -> list[DeliveryBundleResponse]:
    return [DeliveryBundleResponse.from_domain(item) for item in service.list_bundles(project_id)]


@router.get(
    "/{project_id}/delivery-bundles/{bundle_id}/diff",
    response_model=DeliveryBundleDiffResponse,
    responses=ERROR_RESPONSES,
)
async def diff_delivery_bundles(
    project_id: str, bundle_id: str, base_bundle_id: str, service: DeliveryService
) -> DeliveryBundleDiffResponse:
    diff = service.diff_bundles(project_id, base_bundle_id, bundle_id)
    return DeliveryBundleDiffResponse(
        base_bundle_id=diff.base.bundle_id,
        target_bundle_id=diff.target.bundle_id,
        base_contract_revision_id=diff.base.web_generation_contract_revision_id,
        target_contract_revision_id=diff.target.web_generation_contract_revision_id,
        contract_changes=list(diff.contract_changes),
        files=[
            DeliveryBundleFileChange(path=path, change=change, base_sha256=before, target_sha256=after)
            for path, change, before, after in diff.files
        ],
    )


@router.get(
    "/{project_id}/delivery-bundles/{bundle_id}",
    response_model=DeliveryBundleResponse,
    responses=ERROR_RESPONSES,
)
async def get_delivery_bundle(
    project_id: str, bundle_id: str, service: DeliveryService
) -> DeliveryBundleResponse:
    return DeliveryBundleResponse.from_domain(service.get_bundle(project_id, bundle_id))


@router.get(
    "/{project_id}/delivery-bundles/{bundle_id}/archive",
    response_class=FileResponse,
    responses={
        **ERROR_RESPONSES,
        200: {"content": {"application/zip": {}}, "description": "Integrity-checked delivery archive"},
    },
)
async def download_delivery_bundle(
    project_id: str, bundle_id: str, service: DeliveryService
) -> FileResponse:
    bundle = service.get_bundle(project_id, bundle_id)
    path = service.archive_path(project_id, bundle_id)
    return FileResponse(
        path,
        media_type="application/zip",
        filename=f"{bundle.bundle_id}.zip",
        headers={"X-Content-SHA256": bundle.archive_sha256},
    )
