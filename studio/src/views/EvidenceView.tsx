import { useEffect, useState } from "react";
import type { ProductProjectView, RevisionWriteResult } from "../api/types";
import { Badge, statusLabel } from "../components/Badge";
import { unresolvedUnknownCount } from "../domain/project";

type EvidenceViewProps = {
  view: ProductProjectView;
  busy?: boolean;
  onDeriveMeasurementPlan?: () => void;
  onReviseMeasurementPlan?: (thresholds: Record<string, string>) => Promise<RevisionWriteResult>;
  onConfirmMeasurementPlan?: () => void;
};

const sourceLayerLabels: Record<string, string> = {
  software_check: "软件检查",
  runtime_event: "运行事件",
  user_report: "用户报告",
  research_observation: "研究观察",
  expert_review: "专家审查",
};

const sourceLayerDescriptions: Record<string, string> = {
  software_check: "构建、自动化测试或静态检查；只能说明软件检查结果，不构成现实结果证据。",
  runtime_event: "产品运行事件；当前未获准自动采集，任何此类测量必须保持 blocked。",
  user_report: "参与者主动提供的报告；保留用户报告来源，不自动升级为因果结论。",
  research_observation: "研究者在明确任务和情境中记录的观察；需留存观察者与任务来源。",
  expert_review: "具名专家按预先写明的标准审查；专家意见不替代用户结果。",
};

export function EvidenceView({
  view,
  busy = false,
  onDeriveMeasurementPlan,
  onReviseMeasurementPlan,
  onConfirmMeasurementPlan,
}: EvidenceViewProps) {
  const facts = view.problem_model?.facts ?? [];
  const indicators = view.outcome_contract?.success_indicators ?? [];
  const unknowns = unresolvedUnknownCount(view);
  const plan = view.outcome_measurement_plan;
  const [editing, setEditing] = useState(false);
  const [thresholds, setThresholds] = useState<Record<string, string>>({});
  const [planError, setPlanError] = useState<string | null>(null);

  useEffect(() => {
    setThresholds(
      Object.fromEntries((plan?.measures ?? []).map((measure) => [measure.measure_id, measure.threshold_or_target])),
    );
    setEditing(false);
    setPlanError(null);
  }, [plan?.revision_id]);

  async function savePlan() {
    if (!onReviseMeasurementPlan) return;
    setPlanError(null);
    const result = await onReviseMeasurementPlan(thresholds);
    if (result.status === "saved") {
      setEditing(false);
      return;
    }
    setPlanError(
      result.status === "conflict"
        ? `测量计划已被更新到 r${result.latestRevision}，请刷新后重试。`
        : result.message,
    );
  }

  const contractConfirmed = view.outcome_contract?.status === "confirmed";
  const planStale = Boolean(plan && view.outcome_contract?.revision_id !== plan.outcome_contract_revision_id);
  return (
    <div className="view-stack">
      <section className="view-hero"><div><p className="eyebrow">Evidence & progress</p><h1>进度不是一个虚假的百分比</h1><p>这里追踪关键未知是否被消除，以及当前 revision 到底能够声称什么。</p></div><Badge tone={unknowns ? "warn" : "good"}>{unknowns} 个已记录未知</Badge></section>
      <div className="metric-row">
        <article><span>有来源事实</span><strong>{facts.length}</strong><p>不等同于因果解释</p></article>
        <article><span>结果指标</span><strong>{indicators.length}</strong><p>需要可观察定义</p></article>
        <article><span>现实证据</span><strong>0</strong><p>尚未执行真实试用</p></article>
        <article><span>失效影响</span><strong>{view.recorded_impacts.length}</strong><p>上游修订产生</p></article>
      </div>
      <div className="evidence-grid">
        <section className="panel evidence-section evidence-section--wide measurement-plan-panel">
          <div className="panel__heading">
            <div><p className="eyebrow">C2 · Measurement plan</p><h2>怎样观察结果，而不把解释冒充证据</h2></div>
            <div className="panel__actions">
              {plan ? <><Badge tone={plan.status === "confirmed" ? "good" : "warn"}>{statusLabel(plan.status)}</Badge><span className="revision">r{plan.meta.revision}</span></> : null}
              {contractConfirmed && (!plan || planStale) ? <button className="button button--quiet" disabled={busy} onClick={onDeriveMeasurementPlan}>{planStale ? "按新契约重建" : "生成测量计划"}</button> : null}
            </div>
          </div>
          {!plan ? (
            <p className="unknown-copy">Outcome Contract 已确认后，在这里生成一份待人工确认的测量计划。当前没有计划，也没有任何现实结果证据。</p>
          ) : (
            <>
              <p className="measurement-plan-intro">计划固定每项指标的观察方法、来源层和证据上限；模型解释不属于测量来源。它只声明如何收集，不声明结果已经成立。</p>
              {view.measurement_plan_blockers.length ? (
                <div className="measurement-blockers" role="status">
                  <strong>确认前仍需处理 {view.measurement_plan_blockers.length} 项</strong>
                  <ul>{view.measurement_plan_blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>
                </div>
              ) : <p className="measurement-ready">计划满足当前确认门槛；{plan.status === "confirmed" ? "已由人确认，尚未采集现实结果。" : "仍需由人确认。"}</p>}
              <div className="measurement-table">
                {plan.measures.map((measure) => (
                  <article className="measurement-row" key={measure.measure_id}>
                    <div className="measurement-row__main">
                      <div className="measurement-row__heading"><strong>{measure.label}</strong>{measure.primary ? <Badge tone="good">主测量</Badge> : null}</div>
                      <p>{measure.operational_definition}</p>
                      <small>{measure.method}</small>
                      <p>缺失处理：{measure.missingness_policy} · 结果矛盾时回退：{measure.on_contradiction}</p>
                    </div>
                    <div className="measurement-row__meta">
                      <span title={sourceLayerDescriptions[measure.source_layer] ?? "测量来源定义"}><em>来源层</em>{sourceLayerLabels[measure.source_layer] ?? measure.source_layer}</span>
                      <span title={`来源层最高只能支持 ${measure.evidence_ceiling}；实际证据等级必须由人工 EvidenceReview 决定。`}><em>证据上限</em>{measure.evidence_ceiling}</span>
                      <span><em>可收集</em>{measure.collectable ? "是" : "否"}</span>
                      <span><em>值类型</em>{measure.value_kind}</span>
                      {editing ? (
                        <label className="measurement-threshold"><em>阈值 / 目标</em><input
                          aria-label={`${measure.label} threshold`}
                          value={thresholds[measure.measure_id] ?? measure.threshold_or_target}
                          onChange={(event) => setThresholds((current) => ({ ...current, [measure.measure_id]: event.target.value }))}
                        /></label>
                      ) : <span><em>阈值 / 目标</em>{measure.threshold_or_target}</span>}
                    </div>
                    {measure.blocked_reason ? <p className="measurement-row__blocked">{measure.blocked_reason}</p> : null}
                  </article>
                ))}
              </div>
              <div className="model-columns measurement-plan-details">
                <div><h3>样本边界</h3><p>{plan.sample_plan.minimum_n}–{plan.sample_plan.maximum_n} 人；{plan.sample_plan.inclusion_criteria.join("、") || "未写明纳入条件"}</p></div>
                <div><h3>同意与撤回</h3><p>{plan.consent_scope}</p><p>{plan.withdrawal_policy}</p></div>
                <div><h3>禁止结果护栏</h3>{(plan.guardrails ?? []).length ? (plan.guardrails ?? []).map((guardrail) => <div key={guardrail.guardrail_id}><p>{guardrail.prohibited_outcome_id}：{guardrail.detection_method} · {sourceLayerLabels[guardrail.source_layer] ?? guardrail.source_layer} · 上限 {guardrail.evidence_ceiling} · {guardrail.collectable ? "可收集" : "当前阻塞"} · {guardrail.response}</p>{guardrail.blocked_reason ? <p className="measurement-row__blocked">{guardrail.blocked_reason}</p> : null}</div>) : <p>契约未声明禁止结果</p>}</div>
                <div><h3>停止条件与观察窗口</h3><p>{(plan.stop_condition_ids ?? []).length ? (plan.stop_condition_ids ?? []).join(" · ") : "未引用"}</p><p>{plan.observation_window}</p></div>
              </div>
              {planError ? <p className="action-error" role="alert">{planError}</p> : null}
              <div className="measurement-plan-actions">
                {editing ? <><button className="button button--quiet" disabled={busy} onClick={() => setEditing(false)}>取消</button><button className="button button--primary" disabled={busy} onClick={() => void savePlan()}>保存阈值</button></> : <button className="button button--quiet" disabled={busy || !onReviseMeasurementPlan} onClick={() => setEditing(true)}>修改阈值</button>}
                {plan.status === "proposed" && view.measurement_plan_blockers.length === 0 ? <button className="button button--primary" disabled={busy} onClick={onConfirmMeasurementPlan}>确认测量计划</button> : null}
              </div>
            </>
          )}
        </section>
        <section className="panel evidence-section"><div className="panel__heading"><div><p className="eyebrow">Grounded</p><h2>当前有来源的事实</h2></div><Badge tone="good">{facts.length}</Badge></div>{facts.length ? <div className="evidence-rows">{facts.map((fact) => <article key={fact.fact_id}><span className="evidence-dot evidence-dot--good" /><div><h3>{fact.statement}</h3><p>{fact.source_refs.length} 个来源引用</p></div></article>)}</div> : <p className="unknown-copy">尚无事实记录。用户陈述也必须保留来源边界。</p>}</section>
        <section className="panel evidence-section"><div className="panel__heading"><div><p className="eyebrow">Unknown</p><h2>最值得消除的不确定性</h2></div><Badge tone="warn">{unknowns}</Badge></div><div className="evidence-rows">{view.problem_model?.unknowns.map((item) => <article key={item.unknown_id}><span className="evidence-dot evidence-dot--warn" /><div><h3>{item.question}</h3><p>下一步：{item.next_step}</p></div></article>)}{view.product_theses.flatMap((thesis) => thesis.key_unknowns.map((item) => <article key={`${thesis.thesis_id}-${item}`}><span className="evidence-dot evidence-dot--warn" /><div><h3>{item}</h3><p>来自产品论点：{thesis.name}</p></div></article>))}{unknowns === 0 ? <p className="unknown-copy">尚未结构化记录未知；这不表示未知已经消失。</p> : null}</div></section>
        <section className="panel evidence-section evidence-section--wide"><div className="panel__heading"><div><p className="eyebrow">Claims boundary</p><h2>当前不能声称什么</h2></div></div><div className="claim-boundary"><p>没有真实用户观察，不能声称产品改变了用户行为或体验。</p><p>没有成功构建与浏览器测试，不能声称存在可运行原型。</p><p>内部分析和模型提案不能升级为现实结果证据。</p></div></section>
        {view.recorded_impacts.length ? <section className="panel evidence-section evidence-section--wide"><div className="panel__heading"><div><p className="eyebrow">Revision impact</p><h2>上游变化影响</h2></div></div><div className="impact-table">{view.recorded_impacts.map((impact) => <div key={`${impact.dependent_revision_id}-${impact.reason}`}><Badge tone="danger">{statusLabel(impact.impact)}</Badge><strong>{impact.dependent_type} · {impact.dependent_revision_id}</strong><p>{impact.reason}</p></div>)}</div></section> : null}
      </div>
    </div>
  );
}
