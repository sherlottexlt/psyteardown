import type { ProductProjectView } from "../api/types";
import { ApiClientError } from "../api/client";

export const stageOrder = ["intent", "problem", "contract", "theses", "prototype"] as const;
export type ProductStage = (typeof stageOrder)[number];

export function currentStage(view: ProductProjectView): ProductStage {
  if (!view.product_intent) return "intent";
  if (!view.problem_model) return "problem";
  if (!view.outcome_contract) return "contract";
  if (view.product_theses.length === 0) return "theses";
  return "prototype";
}

export function humanDecisionCount(view: ProductProjectView): number {
  let count = 0;
  if (view.product_intent?.status === "proposed") count += 1;
  if (view.problem_model?.status === "proposed") count += 1;
  if (view.outcome_contract?.status === "proposed") count += 1;
  count += view.product_theses.filter(
    (thesis) => thesis.status !== "selected" && thesis.status !== "rejected",
  ).length;
  return count;
}

export function unresolvedUnknownCount(view: ProductProjectView): number {
  const problemUnknowns = view.problem_model?.unknowns.length ?? 0;
  const thesisUnknowns = view.product_theses.reduce(
    (total, thesis) => total + thesis.key_unknowns.length,
    0,
  );
  return problemUnknowns + thesisUnknowns;
}

export function formatApiError(error: unknown): string {
  if (error instanceof ApiClientError) {
    const messages: Record<string, string> = {
      domain_validation_error: "领域契约尚未满足。请检查必填字段、禁止结果审查和现实证据要求。",
      domain_gate: "当前步骤的上游内容尚未确认，不能继续推进。",
      revision_conflict: "服务端 revision 已更新，请刷新并复核后重试。",
      not_found: "请求的项目或对象不存在。",
    };
    return messages[error.code] ?? error.message;
  }
  return error instanceof Error ? error.message : "操作失败，请稍后重试。";
}
