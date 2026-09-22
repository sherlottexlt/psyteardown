import type { ProductProjectView, ProductThesis } from "../api/types";
import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";

interface DecisionAction {
  key: string;
  eyebrow: string;
  title: string;
  why: string;
  consequence: string;
  recommendation: string;
  label: string;
  secondaryLabel?: string;
  onPrimary: () => void;
  onSecondary?: () => void;
}

export function DecisionsView({
  view,
  busy,
  onConfirm,
  onThesisTransition,
}: {
  view: ProductProjectView;
  busy: boolean;
  onConfirm: (type: "product-intent" | "problem-model" | "outcome-contract") => void;
  onThesisTransition: (thesis: ProductThesis, status: "exploring" | "selected") => void;
}) {
  const decisions: DecisionAction[] = [];
  if (view.product_intent?.status === "proposed") {
    decisions.push({
      key: "intent",
      eyebrow: "价值边界 · 需要你决定",
      title: "这是不是你真正希望改变的现实？",
      why: "平台无权替你决定什么值得追求。",
      consequence: "确认后，问题研究会以这份意图为上游；后续修订会触发影响复核。",
      recommendation: "只确认目标方向，不必假装已经知道解决方案。",
      label: "确认产品意图",
      onPrimary: () => onConfirm("product-intent"),
    });
  }
  if (view.problem_model?.status === "proposed") {
    decisions.push({
      key: "problem",
      eyebrow: "现实理解 · 需要你纠正",
      title: "问题模型是否遗漏了关键情境？",
      why: "事实来源和竞争解释需要你的现实情境校正。",
      consequence: "确认不会证明某个解释为真，只会批准它作为结果契约的当前基础。",
      recommendation: "仅在事实有来源、至少两个竞争解释仍被保留时确认。",
      label: "确认当前问题模型",
      onPrimary: () => onConfirm("problem-model"),
    });
  }
  if (view.outcome_contract?.status === "proposed") {
    decisions.push({
      key: "contract",
      eyebrow: "结果边界 · 需要你决定",
      title: "成功、伤害与停止条件是否可接受？",
      why: "这是价值取舍和现实风险边界，不能由 AI 自动批准。",
      consequence: "确认后才允许扩大产品论点搜索，并以其中指标作为验收边界。",
      recommendation: "确认前检查禁止结果和现实证据要求，不要只看目标结果。",
      label: "确认结果契约",
      onPrimary: () => onConfirm("outcome-contract"),
    });
  }
  if (view.product_theses.length) {
    view.product_theses
      .filter((item) => item.status !== "rejected" && item.status !== "selected")
      .forEach((thesis) => {
        const isExploring = thesis.status === "exploring";
        decisions.push({
          key: `thesis-${thesis.thesis_id}`,
          eyebrow: "探索分支 · 需要你授权",
          title: `如何推进「${thesis.name}」？`,
          why: "候选机制和风险不同，平台不能替你决定哪一种价值权衡值得承担。",
          consequence: "探索只授权最低成本验证；选择会创建具名的人类决定，并把后续实现绑定到这条路径。",
          recommendation: `先看最低成本证伪：${thesis.falsifiable_predictions[0]?.cheapest_test ?? "待定义"}`,
          label: isExploring ? "选择此论点" : "授权低成本探索",
          secondaryLabel: isExploring ? undefined : "选择此论点",
          onPrimary: () => onThesisTransition(thesis, isExploring ? "selected" : "exploring"),
          onSecondary: isExploring ? undefined : () => onThesisTransition(thesis, "selected"),
        });
      });
  }

  if (!decisions.length) {
    return <EmptyState eyebrow="Decisions & tasks" title="现在不需要你做决定" description="平台应继续推进可以自行研究和验证的工作，直到出现真正需要价值判断、授权或现实资源的事项。" />;
  }

  return (
    <div className="view-stack">
      <section className="view-hero"><div><p className="eyebrow">Decisions & tasks</p><h1>只把必要决定交还给人</h1><p>每项决定都说明为什么需要你、会改变什么，以及不决定的后果。</p></div><Badge tone="warn">{decisions.length} 项待办</Badge></section>
      <div className="decision-list">
        {decisions.map((decision) => (
          <article className="decision-card" key={decision.key}>
            <div className="decision-card__number">{String(decisions.indexOf(decision) + 1).padStart(2, "0")}</div>
            <div className="decision-card__body">
              <p className="eyebrow">{decision.eyebrow}</p><h2>{decision.title}</h2>
              <dl><div><dt>为什么需要你</dt><dd>{decision.why}</dd></div><div><dt>确认后会发生什么</dt><dd>{decision.consequence}</dd></div><div><dt>平台建议</dt><dd>{decision.recommendation}</dd></div></dl>
              <div className="decision-card__actions"><button className="button button--primary" disabled={busy} onClick={decision.onPrimary}>{decision.label}</button>{decision.secondaryLabel && decision.onSecondary ? <button className="button button--quiet" disabled={busy} onClick={decision.onSecondary}>{decision.secondaryLabel}</button> : null}</div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
