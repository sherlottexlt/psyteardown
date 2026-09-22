"""FastAPI dependency providers."""

from fastapi import Request

from psyteardown.product import (
    ProductApplicationService,
    ProductGenerationJobService,
    ProductProposalJobService,
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
