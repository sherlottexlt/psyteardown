import type { ProductProjectView } from "../api/types";
import { Badge, statusLabel } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { PreviewFeedbackPanel, type PreviewFeedbackDraft } from "./PreviewFeedbackPanel";

export function WorkbenchView({
  view,
  busy,
  onGenerate,
  onGenerateWeb,
  onConfirmWeb,
  generationJob,
  executionJob,
  repairJob,
  deliveryBundle,
  deliveryArchiveUrl,
  onGenerateProduct,
  onExecuteProduct,
  onRepairProduct,
  onExportProduct,
  preview,
}: {
  view: ProductProjectView;
  busy: boolean;
  onGenerate: () => void;
  onGenerateWeb: () => void;
  onConfirmWeb: () => void;
  generationJob?: import("../api/types").ProductGenerationJob | null;
  executionJob?: import("../api/types").ProductExecutionJob | null;
  repairJob?: import("../api/types").ProductRepairJob | null;
  deliveryBundle?: import("../api/types").ProductDeliveryBundle | null;
  deliveryArchiveUrl?: (bundleId: string) => string;
  onGenerateProduct: () => void;
  onExecuteProduct: () => void;
  onRepairProduct: () => void;
  onExportProduct?: () => void;
  preview?: {
    url: (bundleId: string) => string;
    policy: import("../api/types").PreviewFeedbackPolicy | null;
    feedback: import("../api/types").PreviewFeedback[];
    onSubmit: (bundleId: string, draft: PreviewFeedbackDraft) => Promise<boolean>;
    onWithdraw: (item: import("../api/types").PreviewFeedback) => void;
  };
}) {
  const bundleMatchesExecution = Boolean(
    deliveryBundle && executionJob && deliveryBundle.execution_job_revision_id === executionJob.revision_id,
  );
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
      {bundleMatchesExecution && deliveryBundle && preview ? (
        <PreviewFeedbackPanel
          key={deliveryBundle.bundle_id}
          bundle={deliveryBundle}
          contract={view.web_generation_contract ?? null}
          previewUrl={preview.url(deliveryBundle.bundle_id)}
          policy={preview.policy}
          feedback={preview.feedback.filter((item) => item.delivery_bundle_id === deliveryBundle.bundle_id)}
          busy={busy}
          onSubmit={(draft) => preview.onSubmit(deliveryBundle.bundle_id, draft)}
          onWithdraw={preview.onWithdraw}
        />
      ) : (
        <section className="preview-frame">
          <div className="preview-frame__bar"><span /><span /><span /><p>Runnable product preview</p><Badge tone="warn">尚未交付</Badge></div>
          <div className="preview-frame__empty"><div className="preview-glyph">↗</div><h2>还没有可预览的交付构建</h2><p>完成生成、隔离构建与浏览器验证并导出交付包后，已交付的构建物会在这里打开，你可以对页面和任务留下反馈。</p></div>
        </section>
      )}
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
          {generationJob?.status === "succeeded" ? (
            <div className="panel__actions">
              <button className="button button--quiet" disabled={busy} onClick={onExecuteProduct}>
                {busy ? "正在执行 sandbox…" : "构建并验证 workspace"}
              </button>
              {executionJob ? <Badge tone={executionJob.status === "succeeded" ? "good" : "warn"}>{executionJob.status} · {executionJob.checkpoint_step ?? "queued"}</Badge> : null}
            </div>
          ) : null}
          {executionJob ? <p className="unknown-copy">B4 执行边界：依赖安装、构建、loopback 预览与 Chromium/axe 检查；无 Secret，运行时无外网。执行日志仅保留安全摘要。</p> : null}
          {executionJob && ["failed", "budget_exhausted"].includes(executionJob.status) ? (
            <div className="panel__actions">
              <button className="button button--quiet" disabled={busy} onClick={onRepairProduct}>
                {busy ? "正在准备修复…" : "定位并尝试受限修复"}
              </button>
              {repairJob ? <Badge tone={repairJob.status === "succeeded" ? "good" : "warn"}>{repairJob.status} · {repairJob.attempts.length} attempts</Badge> : null}
            </div>
          ) : null}
          {repairJob ? (
            <>
              <p className="unknown-copy">B5 只允许确定性白名单补丁；原始 workspace 保持不变。每次诊断、补丁、验证 Job 与成本都会保留。</p>
              {repairJob.attempts.at(-1) ? (
                <dl className="definition-grid definition-grid--three">
                  <div><dt>最近诊断</dt><dd>{repairJob.attempts.at(-1)?.diagnosis}</dd></div>
                  <div><dt>尝试成本</dt><dd>{repairJob.attempts.at(-1)?.cost_units} / {repairJob.budget.max_cost_units} units</dd></div>
                  <div><dt>补丁 / 验证</dt><dd>{repairJob.attempts.at(-1)?.patches.length} patches · {repairJob.attempts.at(-1)?.output_execution_job_id ?? "not started"}</dd></div>
                  {repairJob.error_code ? <div><dt>安全错误</dt><dd>{repairJob.error_code}</dd></div> : null}
                </dl>
              ) : null}
            </>
          ) : null}
          {executionJob?.status === "succeeded" && onExportProduct ? (
            <div className="panel__actions">
              <button className="button button--quiet" disabled={busy} onClick={onExportProduct}>
                {busy ? "正在打包…" : bundleMatchesExecution ? "重新获取交付包" : "导出交付包"}
              </button>
              {bundleMatchesExecution && deliveryBundle ? <Badge tone="good">{deliveryBundle.files.length} files · {Math.ceil(deliveryBundle.archive_bytes / 1024)} KiB</Badge> : null}
            </div>
          ) : null}
          {bundleMatchesExecution && deliveryBundle ? (
            <section aria-label="交付包">
              <dl className="definition-grid definition-grid--three">
                <div><dt>包 sha256</dt><dd><code>{deliveryBundle.archive_sha256.slice(0, 16)}…</code></dd></div>
                <div><dt>来源</dt><dd>{deliveryBundle.materialization_kind === "repair" ? "B5 修复 lineage" : "B3 模板生成"} · {deliveryBundle.execution_job_revision_id}</dd></div>
                <div><dt>结果证据</dt><dd>{deliveryBundle.outcome_evidence_level}</dd></div>
              </dl>
              {deliveryArchiveUrl ? <a className="button button--primary" href={deliveryArchiveUrl(deliveryBundle.bundle_id)} download>下载交付包 (.zip)</a> : null}
              <p className="unknown-copy">交付包只证明本机覆盖范围内的软件验证。未验证声明：</p>
              <ul className="unknown-copy">{deliveryBundle.unverified_claims.map((claim) => <li key={claim}>{claim}</li>)}</ul>
            </section>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
