import type { ProductProjectView } from "../api/types";
import { Badge, statusLabel } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";

export function WorkbenchView({
  view,
  busy,
  onGenerate,
  onGenerateWeb,
  onConfirmWeb,
  generationJob,
  onGenerateProduct,
}: {
  view: ProductProjectView;
  busy: boolean;
  onGenerate: () => void;
  onGenerateWeb: () => void;
  onConfirmWeb: () => void;
  generationJob?: import("../api/types").ProductGenerationJob | null;
  onGenerateProduct: () => void;
}) {
  if (!view.product_theses.length) {
    return (
      <EmptyState
        eyebrow="Product workbench"
        title="先比较几条真正不同的产品路径"
        description={view.outcome_contract?.status === "confirmed"
          ? "结果契约已经确认。平台会生成三条机制不同、可证伪且保留未知的候选；这不是研究结论，也不会自动选择赢家。"
          : "产品论点尚未形成。先确认结果契约，平台才会进入差异化路径搜索。"}
        action={view.outcome_contract?.status === "confirmed" ? (
          <button className="button button--primary" disabled={busy} onClick={onGenerate}>
            {busy ? "正在生成候选…" : "生成 3 条产品论点"}
          </button>
        ) : null}
      />
    );
  }
  return (
    <div className="view-stack">
      <section className="view-hero">
        <div><p className="eyebrow">Product workbench</p><h1>产品论点与实现分支</h1><p>这些路径保留各自的机制、未知和证伪方式，不通过总分强行合并。</p></div>
        <div className="panel__actions">
          <Badge tone="accent">{view.product_theses.length} 条路径</Badge>
          {view.product_theses.some((thesis) => thesis.status === "exploring" || thesis.status === "selected") && !view.web_generation_contract ? (
            <button className="button button--primary" disabled={busy} onClick={onGenerateWeb}>
              {busy ? "正在准备契约…" : "生成 Web 契约"}
            </button>
          ) : null}
        </div>
      </section>
      <div className="thesis-grid">
        {view.product_theses.map((thesis, index) => (
          <article className={`thesis-card ${thesis.status === "selected" ? "is-selected" : ""}`} key={thesis.thesis_id}>
            <header><span className="thesis-card__index">0{index + 1}</span><Badge tone={thesis.status === "selected" ? "good" : thesis.status === "rejected" ? "danger" : "neutral"}>{statusLabel(thesis.status)}</Badge></header>
            <h2>{thesis.name}</h2>
            <p className="thesis-card__promise">{thesis.product_promise}</p>
            <div className="thesis-card__modes">{thesis.realization_modes.map((mode) => <span key={mode}>{mode}</span>)}</div>
            <dl>
              <div><dt>差异</dt><dd>{thesis.differentiation}</dd></div>
              <div><dt>最大未知</dt><dd>{thesis.key_unknowns[0]}</dd></div>
              <div><dt>最低成本证伪</dt><dd>{thesis.falsifiable_predictions[0]?.cheapest_test ?? "待定义"}</dd></div>
              <div><dt>验证层级</dt><dd>{statusLabel(thesis.validation_strategy[0]?.evidence_level ?? "unknown")}</dd></div>
              <div><dt>交付负担</dt><dd>{thesis.delivery_estimate.maintenance_burden}</dd></div>
            </dl>
          </article>
        ))}
      </div>
      <section className="preview-frame">
        <div className="preview-frame__bar"><span /><span /><span /><p>Runnable product preview</p><Badge tone="warn">尚未构建</Badge></div>
        <div className="preview-frame__empty"><div className="preview-glyph">↗</div><h2>运行环境尚未接入</h2><p>完成生成 Job、隔离构建和 Playwright 验证后，真实产物会在这里打开。</p></div>
      </section>
      {view.web_generation_contract ? (
        <section className="panel contract-card contract-card--wide" aria-label="Web 生成契约">
          <div className="panel__heading">
            <div><p className="eyebrow">Web generation contract</p><h2>{view.web_generation_contract.app_title}</h2></div>
            <Badge tone={view.web_generation_contract.status === "confirmed" ? "good" : "warn"}>{statusLabel(view.web_generation_contract.status)}</Badge>
          </div>
          <dl className="definition-grid definition-grid--three">
            <div><dt>模板</dt><dd>{view.web_generation_contract.template_id} · {view.web_generation_contract.template_version}</dd></div>
            <div><dt>页面 / 任务</dt><dd>{view.web_generation_contract.screens.length} / {view.web_generation_contract.tasks.length}</dd></div>
            <div><dt>运行边界</dt><dd>local fixture only · no network</dd></div>
          </dl>
          <p className="unknown-copy">这是待确认的生成输入，不是源码、运行实例或真实结果。确认后仍需 B3 的 workspace、预算和沙箱 Gate。</p>
          {view.web_generation_contract.status === "proposed" ? (
            <button className="button button--primary" disabled={busy} onClick={onConfirmWeb}>确认 Web 生成契约</button>
          ) : null}
          {view.web_generation_contract.status === "confirmed" ? (
            <div className="panel__actions">
              <button className="button button--primary" disabled={busy} onClick={onGenerateProduct}>
                {busy ? "正在生成 workspace…" : "生成受限 Web workspace"}
              </button>
              {generationJob ? <Badge tone={generationJob.status === "succeeded" ? "good" : "warn"}>{generationJob.status} · {generationJob.consumed_files} files</Badge> : null}
            </div>
          ) : null}
          {generationJob ? <p className="unknown-copy">B3 本地边界：{generationJob.sandbox.network_policy} network · {generationJob.sandbox.execution_policy} · budget {generationJob.consumed_bytes}/{generationJob.budget.max_bytes} bytes。源码尚未执行或预览。</p> : null}
        </section>
      ) : null}
    </div>
  );
}
