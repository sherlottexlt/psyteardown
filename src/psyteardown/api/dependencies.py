"""FastAPI dependency providers."""

from fastapi import Request

from psyteardown.product import (
    ProductApplicationService,
    ProductGenerationJobService,
    ProductProposalJobService,
    ProductExecutionJobService,
    ProductRepairJobService,
    ProductDeliveryBundleService,
    ProductPreviewFeedbackService,
)


async def get_product_service(request: Request) -> ProductApplicationService:
    service = getattr(request.app.state, "product_service", None)
    if service is None:
        raise RuntimeError("Product Studio application service is not initialized")
    return service


async def get_product_job_service(request: Request) -> ProductProposalJobService:
    service = getattr(request.app.state, "product_job_service", None)
    if service is None:
        raise RuntimeError("Product Studio job service is not initialized")
    return service


async def get_product_generation_job_service(
    request: Request,
) -> ProductGenerationJobService:
    service = getattr(request.app.state, "product_generation_job_service", None)
    if service is None:
        raise RuntimeError("Product Studio generation service is not initialized")
    return service


async def get_product_execution_job_service(
    request: Request,
) -> ProductExecutionJobService:
    service = getattr(request.app.state, "product_execution_job_service", None)
    if service is None:
        raise RuntimeError("Product Studio execution service is not initialized")
    return service


async def get_product_repair_job_service(
    request: Request,
) -> ProductRepairJobService:
    service = getattr(request.app.state, "product_repair_job_service", None)
    if service is None:
        raise RuntimeError("Product Studio repair service is not initialized")
    return service


async def get_product_delivery_bundle_service(
    request: Request,
) -> ProductDeliveryBundleService:
    service = getattr(request.app.state, "product_delivery_bundle_service", None)
    if service is None:
        raise RuntimeError("Product Studio delivery service is not initialized")
    return service


async def get_product_preview_feedback_service(
    request: Request,
) -> ProductPreviewFeedbackService:
    service = getattr(request.app.state, "product_preview_feedback_service", None)
    if service is None:
        raise RuntimeError("Product Studio preview feedback service is not initialized")
    return service
