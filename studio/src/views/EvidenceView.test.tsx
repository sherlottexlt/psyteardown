import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ProductProjectView } from "../api/types";
import { EvidenceView } from "./EvidenceView";

const plan = {
  measurement_plan_id: "measurement-plan-1",
  revision_id: "measurement-plan-1.r1",
  project_id: "project-1",
  outcome_contract_revision_id: "contract-1.r2",
  meta: { revision: 1, parent_revision_id: null, created_at: "2026-09-25T00:00:00Z", created_by: "studio", reason: "derive" },
  status: "proposed",
  plan_version: "c2-v1",
  origin: "deterministic_derivation",
  measures: [
    {
      measure_id: "indicator-1-observed",
      label: "Observed session",
      operational_definition: "Unplanned switches",
      method: "Observe a consented task session",
      unit: null,
      primary: true,
      missingness_policy: "record missingness",
      indicator_id: "indicator-1",
      source_layer: "research_observation",
      value_kind: "count",
      desired_direction: "decrease",
      threshold_or_target: "Must be set by a human before confirmation",
      blocked_reason: null,
      on_contradiction: "product_thesis",
      collectable: true,
      evidence_ceiling: "observed",
    },
  ],
  guardrails: [],
  stop_condition_ids: ["stop-1"],
  sample_plan: { target_population: "knowledge workers", minimum_n: 3, maximum_n: 8, allocation: "one session", inclusion_criteria: ["desktop work"], exclusion_criteria: [] },
  observation_window: "one session",
  consent_scope: "explicit consent",
  withdrawal_policy: "withdraw at any time",
  dependencies: [],
  confirmation: null,
  blockers: ["measure indicator-1-observed still needs a human-set threshold"],
  content_hash: "hash",
};

const view = {
  project: { project_id: "project-1" },
  product_intent: null,
  problem_model: null,
  outcome_contract: { status: "confirmed", success_indicators: [{ indicator_id: "indicator-1" }], prohibited_outcomes: [], stop_conditions: [] },
  outcome_measurement_plan: plan,
  measurement_plan_blockers: plan.blockers,
  product_theses: [],
  recorded_impacts: [],
} as unknown as ProductProjectView;

describe("EvidenceView measurement plan", () => {
  afterEach(cleanup);

  it("shows source layer, evidence ceiling, collectability and allows threshold correction", async () => {
    const onRevise = vi.fn().mockResolvedValue({ status: "saved" });
    const user = userEvent.setup();
    render(<EvidenceView view={view} busy={false} onReviseMeasurementPlan={onRevise} />);

    expect(screen.getByText("研究观察")).toBeInTheDocument();
    expect(screen.getByText("observed")).toBeInTheDocument();
    expect(screen.getByText("observed")).toHaveAttribute("title", expect.stringContaining("人工 EvidenceReview 决定"));
    expect(screen.getByText("可收集")).toBeInTheDocument();
    expect(screen.getByText(/仍需处理 1 项/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "修改阈值" }));
    const input = screen.getByRole("textbox", { name: "Observed session threshold" });
    await user.clear(input);
    await user.type(input, "no more than 3 switches");
    await user.click(screen.getByRole("button", { name: "保存阈值" }));
    expect(onRevise).toHaveBeenCalledWith({ "indicator-1-observed": "no more than 3 switches" });
  });

  it("offers confirmation only when the plan has no blockers", async () => {
    const onConfirm = vi.fn();
    render(<EvidenceView view={{ ...view, measurement_plan_blockers: [], outcome_measurement_plan: { ...plan, blockers: [], status: "proposed" } } as unknown as ProductProjectView} onConfirmMeasurementPlan={onConfirm} />);
    await userEvent.click(screen.getByRole("button", { name: "确认测量计划" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
