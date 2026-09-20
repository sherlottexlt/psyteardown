"""FastAPI dependency providers."""

from fastapi import Request

from psyteardown.product import ProductApplicationService


async def get_product_service(request: Request) -> ProductApplicationService:
    service = getattr(request.app.state, "product_service", None)
    if service is None:
        raise RuntimeError("Product Studio application service is not initialized")
    return service
