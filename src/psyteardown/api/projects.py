"""Version 1 Product Studio project routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from psyteardown.api.dependencies import get_product_service
from psyteardown.api.schemas import (
    ApiErrorResponse,
    ChangeProjectStatusRequest,
    ConfirmRevisionRequest,
    CreateProjectRequest,
    OutcomeContractResponse,
    ProblemModelResponse,
    ProductIntentResponse,
    ProductProjectResponse,
    ProductProjectViewResponse,
    ProductThesisResponse,
    SubmitOutcomeContractRequest,
    SubmitProblemModelRequest,
    SubmitProductIntentRequest,
    SubmitProductThesisRequest,
    TransitionProductThesisRequest,
)
from psyteardown.product import (
    ChangeProductProjectStatus,
    ConfirmOutcomeContract,
    ConfirmProblemModel,
    ConfirmProductIntent,
    CreateProductProject,
    ProductApplicationService,
    SubmitOutcomeContractProposal,
    SubmitProblemModelProposal,
    SubmitProductIntentProposal,
    SubmitProductThesisProposal,
    TransitionProductThesis,
)


ERROR_RESPONSES = {
    404: {"model": ApiErrorResponse, "description": "Resource not found"},
    409: {"model": ApiErrorResponse, "description": "Revision or domain-state conflict"},
    422: {"model": ApiErrorResponse, "description": "Request or domain validation failed"},
}


router = APIRouter(prefix="/projects", tags=["product-projects"])
Service = Annotated[ProductApplicationService, Depends(get_product_service)]


@router.post(
    "",
    response_model=ProductProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def create_project(
    request: CreateProjectRequest, service: Service
) -> ProductProjectResponse:
    project = service.create_project(
        CreateProductProject(
            name=request.name,
            collaboration_mode=request.collaboration_mode,
            actor=request.actor,
            reason=request.reason,
            created_from=request.created_from,
        )
    )
    return ProductProjectResponse.from_domain(project)


@router.get(
    "/{project_id}",
    response_model=ProductProjectViewResponse,
    responses=ERROR_RESPONSES,
)
async def get_project(
    project_id: str, service: Service
) -> ProductProjectViewResponse:
    return ProductProjectViewResponse.from_domain(
        service.get_project_view(project_id)
    )


@router.post(
    "/{project_id}/status",
    response_model=ProductProjectResponse,
    responses=ERROR_RESPONSES,
)
async def change_project_status(
    project_id: str,
    request: ChangeProjectStatusRequest,
    service: Service,
) -> ProductProjectResponse:
    project = service.change_project_status(
        ChangeProductProjectStatus(
            project_id=project_id,
            expected_revision=request.expected_revision,
            to_status=request.to_status,
            actor=request.actor,
            reason=request.reason,
        )
    )
    return ProductProjectResponse.from_domain(project)


@router.post(
    "/{project_id}/product-intent/proposals",
    response_model=ProductIntentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def submit_product_intent(
    project_id: str,
    request: SubmitProductIntentRequest,
    service: Service,
) -> ProductIntentResponse:
    value = service.submit_product_intent(
        SubmitProductIntentProposal(
            project_id=project_id,
            proposal=request.proposal,
            actor=request.actor,
            reason=request.reason,
            intent_id=request.intent_id,
            expected_revision=request.expected_revision,
        )
    )
    return ProductIntentResponse.from_domain(value)


@router.post(
    "/{project_id}/product-intent/{intent_id}/confirmations",
    response_model=ProductIntentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def confirm_product_intent_revision(
    project_id: str,
    intent_id: str,
    request: ConfirmRevisionRequest,
    service: Service,
) -> ProductIntentResponse:
    value = service.confirm_product_intent(
        ConfirmProductIntent(
            project_id=project_id,
            intent_id=intent_id,
            expected_revision=request.expected_revision,
            actor=request.actor,
            reason=request.reason,
        )
    )
    return ProductIntentResponse.from_domain(value)


@router.post(
    "/{project_id}/problem-model/proposals",
    response_model=ProblemModelResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def submit_problem_model(
    project_id: str,
    request: SubmitProblemModelRequest,
    service: Service,
) -> ProblemModelResponse:
    value = service.submit_problem_model(
        SubmitProblemModelProposal(
            project_id=project_id,
            proposal=request.proposal,
            actor=request.actor,
            reason=request.reason,
            problem_model_id=request.problem_model_id,
            expected_revision=request.expected_revision,
        )
    )
    return ProblemModelResponse.from_domain(value)


@router.post(
    "/{project_id}/problem-model/{problem_model_id}/confirmations",
    response_model=ProblemModelResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def confirm_problem_model_revision(
    project_id: str,
    problem_model_id: str,
    request: ConfirmRevisionRequest,
    service: Service,
) -> ProblemModelResponse:
    value = service.confirm_problem_model(
        ConfirmProblemModel(
            project_id=project_id,
            problem_model_id=problem_model_id,
            expected_revision=request.expected_revision,
            actor=request.actor,
            reason=request.reason,
        )
    )
    return ProblemModelResponse.from_domain(value)


@router.post(
    "/{project_id}/outcome-contract/proposals",
    response_model=OutcomeContractResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def submit_outcome_contract(
    project_id: str,
    request: SubmitOutcomeContractRequest,
    service: Service,
) -> OutcomeContractResponse:
    value = service.submit_outcome_contract(
        SubmitOutcomeContractProposal(
            project_id=project_id,
            proposal=request.proposal,
            actor=request.actor,
            reason=request.reason,
            outcome_contract_id=request.outcome_contract_id,
            expected_revision=request.expected_revision,
        )
    )
    return OutcomeContractResponse.from_domain(value)


@router.post(
    "/{project_id}/outcome-contract/{outcome_contract_id}/confirmations",
    response_model=OutcomeContractResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def confirm_outcome_contract_revision(
    project_id: str,
    outcome_contract_id: str,
    request: ConfirmRevisionRequest,
    service: Service,
) -> OutcomeContractResponse:
    value = service.confirm_outcome_contract(
        ConfirmOutcomeContract(
            project_id=project_id,
            outcome_contract_id=outcome_contract_id,
            expected_revision=request.expected_revision,
            actor=request.actor,
            reason=request.reason,
        )
    )
    return OutcomeContractResponse.from_domain(value)


@router.post(
    "/{project_id}/product-theses/proposals",
    response_model=ProductThesisResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def submit_product_thesis(
    project_id: str,
    request: SubmitProductThesisRequest,
    service: Service,
) -> ProductThesisResponse:
    value = service.submit_product_thesis(
        SubmitProductThesisProposal(
            project_id=project_id,
            proposal=request.proposal,
            actor=request.actor,
            reason=request.reason,
            thesis_id=request.thesis_id,
            expected_revision=request.expected_revision,
        )
    )
    return ProductThesisResponse.from_domain(value)


@router.post(
    "/{project_id}/product-theses/{thesis_id}/transitions",
    response_model=ProductThesisResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def transition_product_thesis_revision(
    project_id: str,
    thesis_id: str,
    request: TransitionProductThesisRequest,
    service: Service,
) -> ProductThesisResponse:
    value = service.transition_product_thesis(
        TransitionProductThesis(
            project_id=project_id,
            thesis_id=thesis_id,
            expected_revision=request.expected_revision,
            to_status=request.to_status,
            actor=request.actor,
            actor_type=request.actor_type,
            reason=request.reason,
            authorization_ref=request.authorization_ref,
        )
    )
    return ProductThesisResponse.from_domain(value)
