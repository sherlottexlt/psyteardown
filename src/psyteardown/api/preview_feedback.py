"""HTTP boundary for B7 delivered-build preview and explicit preview feedback."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from psyteardown.api.dependencies import get_product_preview_feedback_service
from psyteardown.api.projects import ERROR_RESPONSES
from psyteardown.api.schemas import (
    PreviewFeedbackPolicyResponse,
    PreviewFeedbackResponse,
    SubmitPreviewFeedbackRequest,
    WithdrawPreviewFeedbackRequest,
)
from psyteardown.product import (
    PREVIEW_FEEDBACK_CAPTURED,
    PREVIEW_FEEDBACK_CONSENT_STATEMENT,
    PREVIEW_FEEDBACK_CONSENT_VERSION,
    PREVIEW_FEEDBACK_MAX_TEXT,
    PREVIEW_FEEDBACK_NOT_CAPTURED,
    ProductPreviewFeedbackService,
)


router = APIRouter(tags=["product-preview-feedback"])
FeedbackService = Annotated[
    ProductPreviewFeedbackService, Depends(get_product_preview_feedback_service)
]

# The delivered build runs in an opaque-origin sandbox with no network access,
# so it cannot read Studio state or call the API even when opened directly.
# Module scripts from an opaque origin are CORS requests, hence the wildcard.
PREVIEW_HEADERS = {
    "Content-Security-Policy": (
        "sandbox allow-scripts; default-src 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'none'; "
        "base-uri 'none'; frame-ancestors 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Access-Control-Allow-Origin": "*",
}


@router.get("/preview-feedback-policy", response_model=PreviewFeedbackPolicyResponse)
async def get_preview_feedback_policy() -> PreviewFeedbackPolicyResponse:
    return PreviewFeedbackPolicyResponse(
        consent_version=PREVIEW_FEEDBACK_CONSENT_VERSION,
        statement=PREVIEW_FEEDBACK_CONSENT_STATEMENT,
        captured=list(PREVIEW_FEEDBACK_CAPTURED),
        not_captured=list(PREVIEW_FEEDBACK_NOT_CAPTURED),
        max_text_length=PREVIEW_FEEDBACK_MAX_TEXT,
        evidence_level="user_report",
    )


@router.get(
    "/projects/{project_id}/delivery-bundles/{bundle_id}/preview/{path:path}",
    response_class=Response,
    responses={**ERROR_RESPONSES, 200: {"description": "Integrity-checked delivered build file"}},
)
async def get_bundle_preview_file(
    project_id: str, bundle_id: str, path: str, service: FeedbackService
) -> Response:
    data, media_type = service.preview_file(project_id, bundle_id, path)
    return Response(content=data, media_type=media_type, headers=PREVIEW_HEADERS)


@router.post(
    "/projects/{project_id}/delivery-bundles/{bundle_id}/feedback",
    response_model=PreviewFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def submit_preview_feedback(
    project_id: str,
    bundle_id: str,
    request: SubmitPreviewFeedbackRequest,
    service: FeedbackService,
) -> PreviewFeedbackResponse:
    return PreviewFeedbackResponse.from_domain(
        service.submit_feedback(
            project_id=project_id,
            bundle_id=bundle_id,
            screen_id=request.screen_id,
            task_id=request.task_id,
            state_id=request.state_id,
            category=request.category,
            text=request.text,
            actor=request.actor,
            consent_version=request.consent_version,
            consent_granted=request.consent_granted,
        )
    )


@router.get(
    "/projects/{project_id}/preview-feedback",
    response_model=list[PreviewFeedbackResponse],
    responses=ERROR_RESPONSES,
)
async def list_preview_feedback(
    project_id: str, service: FeedbackService, bundle_id: str | None = None
) -> list[PreviewFeedbackResponse]:
    return [
        PreviewFeedbackResponse.from_domain(item)
        for item in service.list_feedback(project_id, bundle_id=bundle_id)
    ]


@router.post(
    "/projects/{project_id}/preview-feedback/{feedback_id}/withdrawal",
    response_model=PreviewFeedbackResponse,
    responses=ERROR_RESPONSES,
)
async def withdraw_preview_feedback(
    project_id: str,
    feedback_id: str,
    request: WithdrawPreviewFeedbackRequest,
    service: FeedbackService,
) -> PreviewFeedbackResponse:
    return PreviewFeedbackResponse.from_domain(
        service.withdraw_feedback(
            project_id=project_id,
            feedback_id=feedback_id,
            actor=request.actor,
            expected_revision=request.expected_revision,
        )
    )
