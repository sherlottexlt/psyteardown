import type { components } from "./schema";

type Schemas = components["schemas"];
type RequiredKeys<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;

export type CollaborationMode = Schemas["CreateProjectRequest"]["collaboration_mode"];
export type ConfirmationStatus = Schemas["ProductIntentResponse"]["status"];
export type ThesisStatus = Schemas["ProductThesisResponse"]["status"];
export type RevisionMeta = Schemas["RevisionMetaResponse"];
export type SourceReference = Schemas["SourceReference"];
export type HumanConfirmation = Schemas["HumanConfirmation"];
export type ProductProject = Schemas["ProductProjectResponse"];
export type ProductIntentProposal = RequiredKeys<
  Schemas["ProductIntentProposal"],
  | "current_situation"
  | "explicit_non_goals"
  | "known_constraints"
  | "resource_preferences"
>;
export type ProductIntent = RequiredKeys<
  Schemas["ProductIntentResponse"],
  | "current_situation"
  | "explicit_non_goals"
  | "known_constraints"
  | "resource_preferences"
>;
export type ProblemFact = Schemas["ProblemFact"];
export type ProblemAssumption = Schemas["ProblemAssumption"];
export type ProblemUnknown = Schemas["ProblemUnknown"];
export type CompetingExplanation = Schemas["CompetingExplanation"];
export type ProblemModel = RequiredKeys<
  Schemas["ProblemModelResponse"],
  | "assumptions"
  | "competing_explanations"
  | "facts"
  | "stakeholder_tensions"
  | "unknowns"
>;
export type SuccessIndicator = Schemas["SuccessIndicator"];
export type OutcomeContract = RequiredKeys<
  Schemas["OutcomeContractResponse"],
  | "applicable_contexts"
  | "prohibited_outcomes"
  | "required_real_world_evidence"
  | "stop_conditions"
  | "success_indicators"
  | "target_outcomes"
  | "target_segments"
>;
export type ProductThesis = Schemas["ProductThesisResponse"];
export type WebProductGenerationContract = Schemas["WebProductGenerationContractResponse"];
export type RevisionImpact = Schemas["RevisionImpactResponse"];

export interface ProductProjectView
  extends Omit<
    Schemas["ProductProjectViewResponse"],
    "product_intent" | "problem_model" | "outcome_contract" | "web_generation_contract"
  > {
  product_intent: ProductIntent | null;
  problem_model: ProblemModel | null;
  outcome_contract: OutcomeContract | null;
  web_generation_contract?: WebProductGenerationContract | null;
}

export type ApiErrorBody = Schemas["ApiErrorResponse"];
export type CreateProjectRequest = Schemas["CreateProjectRequest"];
export type SubmitProductIntentRequest = Schemas["SubmitProductIntentRequest"];
export type ConfirmRevisionRequest = Schemas["ConfirmRevisionRequest"];
export type TransitionProductThesisRequest = Schemas["TransitionProductThesisRequest"];
export type ProductProposalJob = Schemas["ProductProposalJobResponse"];
export type ProductGenerationJob = Schemas["ProductGenerationJobResponse"];
export type ModelCallRecord = Schemas["ModelCallRecord"];
export type SourceModelPolicy = Schemas["SourceModelPolicyResponse"];
export type ProductExecutionJob = Schemas["ExecutionJobResponse"];
export type ProductRepairJob = Schemas["RepairJobResponse"];
export type ProductDeliveryBundle = Schemas["DeliveryBundleResponse"];
export type PreviewFeedback = Schemas["PreviewFeedbackResponse"];
export type PreviewFeedbackPolicy = Schemas["PreviewFeedbackPolicyResponse"];
export type PreviewFeedbackCategory = Schemas["SubmitPreviewFeedbackRequest"]["category"];
export type PreviewFeedbackDisposition = Schemas["PreviewFeedbackDispositionRequest"]["disposition"];
export type DeliveryBundleDiff = Schemas["DeliveryBundleDiffResponse"];
export type ProposalJobKind = Schemas["CreateProposalJobRequest"]["kind"];
export type SubmitProblemModelRequest = Schemas["SubmitProblemModelRequest"];
export type SubmitOutcomeContractRequest = Schemas["SubmitOutcomeContractRequest"];

export interface EditableProductIntent {
  desiredChange: string;
  affectedPeople: string[];
  currentSituation: string;
  explicitNonGoals: string[];
  knownConstraints: string[];
  resourcePreferences: string[];
}

export type RevisionWriteResult =
  | { status: "saved" }
  | { status: "conflict"; latestRevision: number }
  | { status: "error"; message: string };

export interface EditableProblemModel {
  facts: string[];
  explanations: string[];
  unknowns: string[];
}

export interface EditableOutcomeContract {
  targetSegments: string[];
  applicableContexts: string[];
  targetOutcome: string;
  indicatorDefinition: string;
  observationMethod: string;
  thresholdOrTarget: string;
  prohibitedOutcomes: string[];
  timeBudget: string;
  dataBoundary: string;
  stopCondition: string;
  requiredRealWorldEvidence: string[];
  prohibitedOutcomesReviewed: boolean;
}
