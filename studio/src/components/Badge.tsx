import type { ReactNode } from "react";

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn" | "danger" | "accent";
}) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: "进行中",
    paused: "已暂停",
    archived: "已归档",
    proposed: "待确认",
    confirmed: "已确认",
    exploring: "探索中",
    selected: "已选择",
    rejected: "已淘汰",
    review_required: "需复核",
    stale: "已过期",
    concept: "概念",
    runnable_prototype: "可运行原型",
    field_trial: "实地试用",
    operational_candidate: "运营候选",
    released_product: "已发布产品",
    queued: "已排队",
    running: "执行中",
    succeeded: "提案已生成",
    failed: "执行失败",
    stale_input: "输入已过期",
    deterministic_check: "确定性检查",
    real_user_observation: "真实用户观察",
    operational_result: "运行结果",
    expert_review: "专家审查",
    tool_result: "工具结果",
  };
  return labels[status] ?? status;
}
