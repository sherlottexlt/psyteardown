import type {
  ApiErrorBody,
  CollaborationMode,
  ConfirmRevisionRequest,
  CreateProjectRequest,
  EditableProductIntent,
  EditableProblemModel,
  EditableOutcomeContract,
  OutcomeContract,
  ProblemModel,
  ProductProposalJob,
  ProductGenerationJob,
  ProposalJobKind,
  ProductIntent,
  ProductProject,
  ProductProjectView,
  ProductThesis,
  SubmitProductIntentRequest,
  SubmitProblemModelRequest,
  SubmitOutcomeContractRequest,
  ThesisStatus,
  TransitionProductThesisRequest,
} from "./types";

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiClientError extends Error {
  readonly code: string;
  readonly requestId: string | null;

  constructor(message: string, code = "request_failed", requestId: string | null = null) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.requestId = requestId;
  }
}

function requestId(): string {
  return `studio-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": requestId(),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiClientError(
      "无法连接 Product Studio API。请确认本地 API 已在 127.0.0.1:8000 启动。",
      "network_error",
    );
  }

  const body = (await response.json().catch(() => null)) as T | ApiErrorBody | null;
  if (!response.ok) {
    const errorBody = body as ApiErrorBody | null;
    throw new ApiClientError(
      errorBody?.error?.message ?? `请求失败（HTTP ${response.status}）`,
      errorBody?.error?.code,
      errorBody?.error?.request_id ?? response.headers.get("X-Request-ID"),
    );
  }
  if (body === null) {
    throw new ApiClientError("API 返回了空响应", "invalid_response");
  }
  return body as T;
}

export function createProject(input: {
  name: string;
  collaborationMode: CollaborationMode;
}): Promise<ProductProject> {
  const body: CreateProjectRequest = {
    name: input.name,
    collaboration_mode: input.collaborationMode,
    actor: "local-user",
    reason: "Created from Product Studio",
    created_from: [],
  };
  return request("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getProject(projectId: string): Promise<ProductProjectView> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}`);
}

export function submitInitialIntent(input: {
  projectId: string;
  desiredChange: string;
  affectedPeople: string[];
  currentSituation?: string;
}): Promise<ProductIntent> {
  const sourceId = `studio-input-${Date.now().toString(36)}`;
  const body: SubmitProductIntentRequest = {
    proposal: {
      desired_change: input.desiredChange,
      affected_people: input.affectedPeople,
      current_situation: input.currentSituation || null,
      explicit_non_goals: [],
      known_constraints: [],
      resource_preferences: [],
      source_refs: [{ source_type: "user_input", source_id: sourceId }],
    },
    actor: "local-user",
    reason: "Captured initial intent from Product Studio",
  };
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/product-intent/proposals`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function reviseProductIntent(input: {
  projectId: string;
  intent: ProductIntent;
  draft: EditableProductIntent;
}): Promise<ProductIntent> {
  const correctionSource = `studio-correction-${Date.now().toString(36)}`;
  const body: SubmitProductIntentRequest = {
    intent_id: input.intent.intent_id,
    expected_revision: input.intent.meta.revision,
    proposal: {
      desired_change: input.draft.desiredChange,
      affected_people: input.draft.affectedPeople,
      current_situation: input.draft.currentSituation || null,
      explicit_non_goals: input.draft.explicitNonGoals,
      known_constraints: input.draft.knownConstraints,
      resource_preferences: input.draft.resourcePreferences,
      source_refs: [
        ...input.intent.source_refs,
        { source_type: "user_input", source_id: correctionSource },
      ],
    },
    actor: "local-user",
    reason: "Corrected product intent in Product Studio",
  };
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/product-intent/proposals`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function reviseProblemModel(input: {
  projectId: string;
  problem: ProblemModel;
  draft: EditableProblemModel;
}): Promise<ProblemModel> {
  const correctionId = `problem-correction-${Date.now().toString(36)}`;
  const body: SubmitProblemModelRequest = {
    problem_model_id: input.problem.problem_model_id,
    expected_revision: input.problem.meta.revision,
    proposal: {
      intent_revision_id: input.problem.intent_revision_id,
      facts: input.draft.facts.map((statement, index) => ({
        fact_id: input.problem.facts[index]?.fact_id ?? `${correctionId}-fact-${index + 1}`,
        statement,
        source_refs: [{ source_type: "user_input", source_id: correctionId }],
      })),
      assumptions: input.problem.assumptions,
      unknowns: input.draft.unknowns.map((question, index) => ({
        unknown_id: input.problem.unknowns[index]?.unknown_id ?? `${correctionId}-unknown-${index + 1}`,
        question,
        decision_impact:
          input.problem.unknowns[index]?.decision_impact ??
          "This user correction may change the product path or success measure.",
        next_step:
          input.problem.unknowns[index]?.next_step ??
          "Gather the lowest-cost observation that can answer this question.",
      })),
      competing_explanations: input.draft.explanations.map((statement, index) => ({
        explanation_id:
          input.problem.competing_explanations[index]?.explanation_id ??
          `${correctionId}-explanation-${index + 1}`,
        statement,
        supporting_fact_ids:
          input.problem.facts[index]?.fact_id
            ? [input.problem.facts[index].fact_id]
            : input.problem.facts[0]?.fact_id
              ? [input.problem.facts[0].fact_id]
              : [],
        contradicting_fact_ids: [],
        cheapest_falsification:
          input.problem.competing_explanations[index]?.cheapest_falsification ??
          "Run one reversible comparison that removes only this proposed cause.",
      })),
      stakeholder_tensions: input.problem.stakeholder_tensions,
    },
    actor: "local-user",
    reason: "Corrected problem model in Product Studio",
  };
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/problem-model/proposals`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function reviseOutcomeContract(input: {
  projectId: string;
  contract: OutcomeContract;
  draft: EditableOutcomeContract;
}): Promise<OutcomeContract> {
  const correctionId = `contract-correction-${Date.now().toString(36)}`;
  const indicatorId = input.contract.success_indicators[0]?.indicator_id ?? `${correctionId}-indicator`;
  const body: SubmitOutcomeContractRequest = {
    outcome_contract_id: input.contract.outcome_contract_id,
    expected_revision: input.contract.meta.revision,
    proposal: {
      intent_revision_id: input.contract.intent_revision_id,
      problem_model_revision_id: input.contract.problem_model_revision_id,
      target_segments: input.draft.targetSegments,
      applicable_contexts: input.draft.applicableContexts,
      target_outcomes: [
        {
          outcome_id: input.contract.target_outcomes[0]?.outcome_id ?? `${correctionId}-outcome`,
          description: input.draft.targetOutcome,
          indicator_ids: [indicatorId],
        },
      ],
      success_indicators: [
        {
          indicator_id: indicatorId,
          operational_definition: input.draft.indicatorDefinition,
          observation_method: input.draft.observationMethod,
          desired_direction:
            input.contract.success_indicators[0]?.desired_direction ?? "improve",
          threshold_or_target: input.draft.thresholdOrTarget,
          required_evidence:
            input.contract.success_indicators[0]?.required_evidence ?? "real_user_observation",
        },
      ],
      prohibited_outcomes: input.draft.prohibitedOutcomes.map((description, index) => ({
        prohibited_outcome_id:
          input.contract.prohibited_outcomes[index]?.prohibited_outcome_id ??
          `${correctionId}-prohibited-${index + 1}`,
        description,
        severity: input.contract.prohibited_outcomes[index]?.severity ?? "hard",
        detection_method:
          input.contract.prohibited_outcomes[index]?.detection_method ??
          "Human review before trial and user report during trial",
        response:
          input.contract.prohibited_outcomes[index]?.response ??
          "Stop the trial and reframe the product path",
      })),
      prohibited_outcomes_reviewed: input.draft.prohibitedOutcomesReviewed,
      resource_boundary: {
        ...input.contract.resource_boundary,
        time_budget: input.draft.timeBudget || null,
        data_boundary: input.draft.dataBoundary || null,
      },
      stop_conditions: [
        {
          condition_id:
            input.contract.stop_conditions[0]?.condition_id ?? `${correctionId}-stop`,
          condition: input.draft.stopCondition,
          action: input.contract.stop_conditions[0]?.action ?? "reframe",
        },
      ],
      minimum_delivery_maturity: input.contract.minimum_delivery_maturity,
      required_real_world_evidence: input.draft.requiredRealWorldEvidence,
    },
    actor: "local-user",
    reason: "Corrected outcome contract in Product Studio",
  };
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/outcome-contract/proposals`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function createProposalJob(input: {
  projectId: string;
  kind: ProposalJobKind;
  rawInput?: string;
}): Promise<ProductProposalJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/proposal-jobs`,
    {
      method: "POST",
      body: JSON.stringify({
        kind: input.kind,
        actor: "local-user",
        reason: `Requested ${input.kind} proposal in Product Studio`,
        raw_input: input.rawInput ?? null,
      }),
    },
  );
}

export function runProposalJob(input: {
  projectId: string;
  jobId: string;
}): Promise<ProductProposalJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/proposal-jobs/${encodeURIComponent(input.jobId)}/runs`,
    { method: "POST", body: JSON.stringify({ actor: "local-worker" }) },
  );
}

export function listProposalJobs(projectId: string): Promise<ProductProposalJob[]> {
  return request(
    `/api/v1/projects/${encodeURIComponent(projectId)}/proposal-jobs`,
  );
}

export function confirmRevision(input: {
  projectId: string;
  objectType: "product-intent" | "problem-model" | "outcome-contract";
  objectId: string;
  revision: number;
  reason: string;
}): Promise<unknown> {
  const pathByType = {
    "product-intent": `product-intent/${input.objectId}`,
    "problem-model": `problem-model/${input.objectId}`,
    "outcome-contract": `outcome-contract/${input.objectId}`,
  } as const;
  const body: ConfirmRevisionRequest = {
    expected_revision: input.revision,
    actor: "local-user",
    reason: input.reason,
  };
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/${pathByType[input.objectType]}/confirmations`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function transitionThesis(input: {
  projectId: string;
  thesis: ProductThesis;
  toStatus: Exclude<ThesisStatus, "proposed">;
  reason: string;
}): Promise<ProductThesis> {
  const body: TransitionProductThesisRequest = {
    expected_revision: input.thesis.meta.revision,
    to_status: input.toStatus,
    actor: "local-user",
    actor_type: "human",
    reason: input.reason,
    authorization_ref: null,
  };
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/product-theses/${encodeURIComponent(input.thesis.thesis_id)}/transitions`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export function confirmWebGenerationContract(input: {
  projectId: string;
  contractId: string;
  revision: number;
}): Promise<unknown> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/web-generation-contract/${encodeURIComponent(input.contractId)}/confirmations`,
    {
      method: "POST",
      body: JSON.stringify({
        expected_revision: input.revision,
        actor: "local-user",
        reason: "Confirmed Web generation contract in Product Studio",
      }),
    },
  );
}

export function createGenerationJob(input: {
  projectId: string;
}): Promise<ProductGenerationJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/generation-jobs`,
    {
      method: "POST",
      body: JSON.stringify({
        actor: "local-user",
        reason: "Materialized confirmed Web contract in Product Studio",
      }),
    },
  );
}

export function runGenerationJob(input: {
  projectId: string;
  jobId: string;
}): Promise<ProductGenerationJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/generation-jobs/${encodeURIComponent(input.jobId)}/runs`,
    {
      method: "POST",
      body: JSON.stringify({ actor: "local-worker" }),
    },
  );
}

export function listGenerationJobs(projectId: string): Promise<ProductGenerationJob[]> {
  return request(
    `/api/v1/projects/${encodeURIComponent(projectId)}/generation-jobs`,
  );
}

export function createExecutionJob(input: {
  projectId: string;
  generationJobId: string;
}): Promise<import("./types").ProductExecutionJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/execution-jobs`,
    {
      method: "POST",
      body: JSON.stringify({
        generation_job_id: input.generationJobId,
        actor: "local-user",
        reason: "Run bounded B4 validation in Product Studio",
      }),
    },
  );
}

export function runExecutionJob(input: {
  projectId: string;
  jobId: string;
}): Promise<import("./types").ProductExecutionJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/execution-jobs/${encodeURIComponent(input.jobId)}/runs`,
    {
      method: "POST",
      body: JSON.stringify({ actor: "local-worker" }),
    },
  );
}

export function listExecutionJobs(projectId: string): Promise<import("./types").ProductExecutionJob[]> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/execution-jobs`);
}

export function createRepairJob(input: {
  projectId: string;
  executionJobId: string;
}): Promise<import("./types").ProductRepairJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/repair-jobs`,
    {
      method: "POST",
      body: JSON.stringify({
        execution_job_id: input.executionJobId,
        actor: "local-user",
        reason: "Repair bounded B4 validation failure in Product Studio",
      }),
    },
  );
}

export function runRepairJob(input: {
  projectId: string;
  jobId: string;
}): Promise<import("./types").ProductRepairJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/repair-jobs/${encodeURIComponent(input.jobId)}/runs`,
    {
      method: "POST",
      body: JSON.stringify({ actor: "local-worker" }),
    },
  );
}

export function retryRepairJob(input: {
  projectId: string;
  jobId: string;
}): Promise<import("./types").ProductRepairJob> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/repair-jobs/${encodeURIComponent(input.jobId)}/retries`,
    {
      method: "POST",
      body: JSON.stringify({ actor: "local-user" }),
    },
  );
}

export function listRepairJobs(projectId: string): Promise<import("./types").ProductRepairJob[]> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/repair-jobs`);
}

export function createDeliveryBundle(input: {
  projectId: string;
  executionJobId: string;
}): Promise<import("./types").ProductDeliveryBundle> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/delivery-bundles`,
    {
      method: "POST",
      body: JSON.stringify({
        execution_job_id: input.executionJobId,
        actor: "local-user",
        reason: "Export verified B6 delivery bundle in Product Studio",
      }),
    },
  );
}

export function listDeliveryBundles(projectId: string): Promise<import("./types").ProductDeliveryBundle[]> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/delivery-bundles`);
}

export function deliveryBundleArchiveUrl(projectId: string, bundleId: string): string {
  return `${apiBase}/api/v1/projects/${encodeURIComponent(projectId)}/delivery-bundles/${encodeURIComponent(bundleId)}/archive`;
}

export function deliveryBundlePreviewUrl(projectId: string, bundleId: string): string {
  // Trailing slash so the delivered build's relative asset URLs resolve inside the preview path.
  return `${apiBase}/api/v1/projects/${encodeURIComponent(projectId)}/delivery-bundles/${encodeURIComponent(bundleId)}/preview/`;
}

export function getPreviewFeedbackPolicy(): Promise<import("./types").PreviewFeedbackPolicy> {
  return request("/api/v1/preview-feedback-policy");
}

export function listPreviewFeedback(projectId: string): Promise<import("./types").PreviewFeedback[]> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/preview-feedback`);
}

export function submitPreviewFeedback(input: {
  projectId: string;
  bundleId: string;
  screenId: string;
  taskId: string | null;
  stateId: string | null;
  category: import("./types").PreviewFeedbackCategory;
  text: string;
  consentVersion: string;
}): Promise<import("./types").PreviewFeedback> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/delivery-bundles/${encodeURIComponent(input.bundleId)}/feedback`,
    {
      method: "POST",
      body: JSON.stringify({
        screen_id: input.screenId,
        task_id: input.taskId,
        state_id: input.stateId,
        category: input.category,
        text: input.text,
        actor: "local-user",
        consent_version: input.consentVersion,
        consent_granted: true,
      }),
    },
  );
}

export function withdrawPreviewFeedback(input: {
  projectId: string;
  feedbackId: string;
  expectedRevision: number;
}): Promise<import("./types").PreviewFeedback> {
  return request(
    `/api/v1/projects/${encodeURIComponent(input.projectId)}/preview-feedback/${encodeURIComponent(input.feedbackId)}/withdrawal`,
    {
      method: "POST",
      body: JSON.stringify({ actor: "local-user", expected_revision: input.expectedRevision }),
    },
  );
}
