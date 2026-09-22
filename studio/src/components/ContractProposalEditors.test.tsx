import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { OutcomeContract } from "../api/types";
import { OutcomeContractEditor } from "./ContractProposalEditors";

const contract = {
  outcome_contract_id: "contract-1",
  revision_id: "contract-1.r1",
  project_id: "project-1",
  intent_revision_id: "intent-1.r2",
  problem_model_revision_id: "problem-1.r2",
  meta: { revision: 1, parent_revision_id: null, created_at: "2026-09-20T00:00:00Z", created_by: "provider", reason: "proposal" },
  status: "proposed",
  target_segments: ["independent workers"],
  applicable_contexts: ["desktop work"],
  target_outcomes: [{ outcome_id: "outcome-1", description: "fewer interruptions", indicator_ids: ["indicator-1"] }],
  success_indicators: [{ indicator_id: "indicator-1", operational_definition: "unplanned switches", observation_method: "task observation", desired_direction: "decrease", threshold_or_target: "human must set", required_evidence: "real_user_observation" }],
  prohibited_outcomes: [], prohibited_outcomes_reviewed: false,
  resource_boundary: { time_budget: null, economic_budget: null, user_attention_budget: null, maintenance_budget: null, data_boundary: null, explicit_unknowns: ["limits unknown"] },
  stop_conditions: [{ condition_id: "stop-1", condition: "pressure increases", action: "reframe" }],
  minimum_delivery_maturity: "concept", required_real_world_evidence: ["one real task"],
  dependencies: [], confirmation: null, content_hash: "hash",
} satisfies OutcomeContract;

describe("OutcomeContractEditor", () => {
  it("keeps prohibited-outcome review as an explicit human field", async () => {
    const onSave = vi.fn().mockResolvedValue({ status: "saved" });
    const user = userEvent.setup();
    render(<OutcomeContractEditor contract={contract} busy={false} onCancel={() => undefined} onSave={onSave} />);

    const review = screen.getByLabelText(/我已审查禁止结果与伤害边界/);
    expect(review).not.toBeChecked();
    await user.click(review);
    await user.click(screen.getByRole("button", { name: "保存结果契约提案" }));
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ prohibitedOutcomesReviewed: true }));
  });
});
