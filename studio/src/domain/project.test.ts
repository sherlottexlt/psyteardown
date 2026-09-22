import { describe, expect, it } from "vitest";
import { currentStage, humanDecisionCount, unresolvedUnknownCount } from "./project";
import type { ProductProjectView } from "../api/types";

const baseView = {
  project: {
    project_id: "project-1",
    revision_id: "project-1.r1",
    meta: { revision: 1, parent_revision_id: null, created_at: "2026-09-20T00:00:00Z", created_by: "user", reason: "test" },
    name: "Test",
    collaboration_mode: "managed",
    status: "active",
    created_from: [],
    content_hash: "hash",
  },
  product_intent: null,
  problem_model: null,
  outcome_contract: null,
  product_theses: [],
  recorded_impacts: [],
} satisfies ProductProjectView;

describe("project projections", () => {
  it("reports intent as the first incomplete stage", () => {
    expect(currentStage(baseView)).toBe("intent");
    expect(humanDecisionCount(baseView)).toBe(0);
    expect(unresolvedUnknownCount(baseView)).toBe(0);
  });

  it("does not invent progress from a project shell", () => {
    const view = {
      ...baseView,
      product_intent: {
        project_id: "project-1", intent_id: "intent-1", revision_id: "intent-1.r1",
        meta: baseView.project.meta, status: "proposed" as const,
        desired_change: "change", affected_people: ["people"], current_situation: null,
        explicit_non_goals: [], known_constraints: [], resource_preferences: [],
        source_refs: [{ source_type: "user_input" as const, source_id: "message-1" }],
        confirmation: null, content_hash: "hash",
      },
    };
    expect(currentStage(view)).toBe("problem");
    expect(humanDecisionCount(view)).toBe(1);
  });

  it("counts each still-actionable thesis separately", () => {
    const view = {
      ...baseView,
      product_theses: [
        { status: "proposed" },
        { status: "exploring" },
        { status: "selected" },
        { status: "rejected" },
      ],
    } as unknown as ProductProjectView;
    expect(humanDecisionCount(view)).toBe(2);
  });
});
