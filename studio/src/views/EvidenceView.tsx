import type { ProductProjectView } from "../api/types";
import { Badge, statusLabel } from "../components/Badge";
import { unresolvedUnknownCount } from "../domain/project";

export function EvidenceView({ view }: { view: ProductProjectView }) {
  const facts = view.problem_model?.facts ?? [];
  const indicators = view.outcome_contract?.success_indicators ?? [];
  const unknowns = unresolvedUnknownCount(view);
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
        <section className="panel evidence-section"><div className="panel__heading"><div><p className="eyebrow">Grounded</p><h2>当前有来源的事实</h2></div><Badge tone="good">{facts.length}</Badge></div>{facts.length ? <div className="evidence-rows">{facts.map((fact) => <article key={fact.fact_id}><span className="evidence-dot evidence-dot--good" /><div><h3>{fact.statement}</h3><p>{fact.source_refs.length} 个来源引用</p></div></article>)}</div> : <p className="unknown-copy">尚无事实记录。用户陈述也必须保留来源边界。</p>}</section>
        <section className="panel evidence-section"><div className="panel__heading"><div><p className="eyebrow">Unknown</p><h2>最值得消除的不确定性</h2></div><Badge tone="warn">{unknowns}</Badge></div><div className="evidence-rows">{view.problem_model?.unknowns.map((item) => <article key={item.unknown_id}><span className="evidence-dot evidence-dot--warn" /><div><h3>{item.question}</h3><p>下一步：{item.next_step}</p></div></article>)}{view.product_theses.flatMap((thesis) => thesis.key_unknowns.map((item) => <article key={`${thesis.thesis_id}-${item}`}><span className="evidence-dot evidence-dot--warn" /><div><h3>{item}</h3><p>来自产品论点：{thesis.name}</p></div></article>))}{unknowns === 0 ? <p className="unknown-copy">尚未结构化记录未知；这不表示未知已经消失。</p> : null}</div></section>
        <section className="panel evidence-section evidence-section--wide"><div className="panel__heading"><div><p className="eyebrow">Claims boundary</p><h2>当前不能声称什么</h2></div></div><div className="claim-boundary"><p>没有真实用户观察，不能声称产品改变了用户行为或体验。</p><p>没有成功构建与浏览器测试，不能声称存在可运行原型。</p><p>内部分析和模型提案不能升级为现实结果证据。</p></div></section>
        {view.recorded_impacts.length ? <section className="panel evidence-section evidence-section--wide"><div className="panel__heading"><div><p className="eyebrow">Revision impact</p><h2>上游变化影响</h2></div></div><div className="impact-table">{view.recorded_impacts.map((impact) => <div key={`${impact.dependent_revision_id}-${impact.reason}`}><Badge tone="danger">{statusLabel(impact.impact)}</Badge><strong>{impact.dependent_type} · {impact.dependent_revision_id}</strong><p>{impact.reason}</p></div>)}</div></section> : null}
      </div>
    </div>
  );
}
