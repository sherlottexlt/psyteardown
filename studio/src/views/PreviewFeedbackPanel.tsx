import { useState, type FormEvent } from "react";
import type {
  PreviewFeedback,
  PreviewFeedbackCategory,
  PreviewFeedbackDisposition,
  PreviewFeedbackPolicy,
  ProductDeliveryBundle,
  WebProductGenerationContract,
} from "../api/types";
import { Badge } from "../components/Badge";

export interface PreviewFeedbackDraft {
  screenId: string;
  taskId: string | null;
  stateId: string | null;
  category: PreviewFeedbackCategory;
  text: string;
}

const categories: Array<{ id: PreviewFeedbackCategory; label: string }> = [
  { id: "bug", label: "问题" },
  { id: "confusing", label: "困惑" },
  { id: "missing", label: "缺失" },
  { id: "works", label: "可用" },
];

const dispositionLabels: Record<PreviewFeedbackDisposition, string> = {
  pending: "待处理",
  incorporated: "已采纳",
  deferred: "暂缓",
};

export function FeedbackDispositionControls({
  item,
  busy,
  onDisposition,
}: {
  item: PreviewFeedback;
  busy: boolean;
  onDisposition: (item: PreviewFeedback, disposition: PreviewFeedbackDisposition) => void;
}) {
  return (
    <span className="feedback-disposition">
      <Badge tone={item.disposition === "incorporated" ? "good" : item.disposition === "deferred" ? "neutral" : "warn"}>
        {dispositionLabels[item.disposition]}
      </Badge>
      {(["incorporated", "deferred", "pending"] as const)
        .filter((value) => value !== item.disposition)
        .map((value) => (
          <button key={value} className="button button--quiet" type="button" disabled={busy} onClick={() => onDisposition(item, value)}>
            标记{dispositionLabels[value]}
          </button>
        ))}
    </span>
  );
}

function categoryLabel(category: PreviewFeedbackCategory | null | undefined): string {
  return categories.find((item) => item.id === category)?.label ?? "—";
}

export function PreviewFeedbackPanel({
  bundle,
  contract,
  previewUrl,
  policy,
  feedback,
  busy,
  onSubmit,
  onWithdraw,
  onIterate,
  onDisposition,
}: {
  bundle: ProductDeliveryBundle;
  contract: WebProductGenerationContract | null;
  previewUrl: string;
  policy: PreviewFeedbackPolicy | null;
  feedback: PreviewFeedback[];
  busy: boolean;
  onSubmit: (draft: PreviewFeedbackDraft) => Promise<boolean>;
  onWithdraw: (item: PreviewFeedback) => void;
  onIterate?: (item: PreviewFeedback) => void;
  onDisposition?: (item: PreviewFeedback, disposition: PreviewFeedbackDisposition) => void;
}) {
  const anchorsAvailable = Boolean(contract && contract.revision_id === bundle.web_generation_contract_revision_id);
  const screens = anchorsAvailable && contract ? contract.screens : [];
  const [screenId, setScreenId] = useState(screens[0]?.screen_id ?? "");
  const [taskId, setTaskId] = useState("");
  const [stateId, setStateId] = useState("");
  const [category, setCategory] = useState<PreviewFeedbackCategory>("confusing");
  const [text, setText] = useState("");
  const [consented, setConsented] = useState(false);
  const screen = screens.find((item) => item.screen_id === screenId) ?? screens[0];
  const tasks = !anchorsAvailable ? [] : contract?.tasks.filter((task) => screen?.task_ids.includes(task.task_id)) ?? [];
  const states = !anchorsAvailable ? [] : contract?.states.filter((state) => screen?.state_ids.includes(state.state_id)) ?? [];
  const canSubmit = Boolean(anchorsAvailable && screen && policy && consented && text.trim() && !busy);
  // B8: an iteration revises the contract this bundle was built from, so it is
  // offered only while that contract revision is still current and confirmed.
  const canIterate = Boolean(anchorsAvailable && contract?.status === "confirmed" && onIterate);

  function anchorLabel(item: PreviewFeedback): string {
    const parts = [
      contract?.screens.find((value) => value.screen_id === item.anchor.screen_id)?.title ?? item.anchor.screen_id,
      item.anchor.task_id ? contract?.tasks.find((value) => value.task_id === item.anchor.task_id)?.goal ?? item.anchor.task_id : null,
      item.anchor.state_id ? contract?.states.find((value) => value.state_id === item.anchor.state_id)?.kind ?? item.anchor.state_id : null,
    ];
    return parts.filter(Boolean).join(" / ");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit || !screen) return;
    const saved = await onSubmit({
      screenId: screen.screen_id,
      taskId: taskId || null,
      stateId: stateId || null,
      category,
      text: text.trim(),
    });
    if (saved) {
      setText("");
      // Consent is granted per report, never remembered.
      setConsented(false);
    }
  }

  return (
    <section className="preview-frame" aria-label="交付构建预览与反馈">
      <div className="preview-frame__bar">
        <span /><span /><span />
        <p>Delivered build preview · {bundle.revision_id}</p>
        <Badge tone="good">sandboxed · no network</Badge>
      </div>
      <iframe
        className="preview-frame__viewport"
        title="交付构建预览"
        src={previewUrl}
        sandbox="allow-scripts"
        referrerPolicy="no-referrer"
      />
      <div className="preview-feedback">
        <form className="preview-feedback__form" onSubmit={(event) => void submit(event)} aria-label="提交预览反馈">
          <h2>对这个 revision 留下反馈</h2>
          {!anchorsAvailable ? (
            <p className="unknown-copy">Web 契约已在导出后变化，反馈锚点无法对应这个交付包。请重新生成、验证并导出后再反馈。</p>
          ) : null}
          <div className="preview-feedback__anchors">
            <label>页面
              <select value={screen?.screen_id ?? ""} disabled={!anchorsAvailable} onChange={(event) => { setScreenId(event.target.value); setTaskId(""); setStateId(""); }}>
                {screens.map((item) => <option key={item.screen_id} value={item.screen_id}>{item.title}</option>)}
              </select>
            </label>
            <label>任务（可选）
              <select value={taskId} disabled={!anchorsAvailable} onChange={(event) => setTaskId(event.target.value)}>
                <option value="">整个页面</option>
                {tasks.map((item) => <option key={item.task_id} value={item.task_id}>{item.goal}</option>)}
              </select>
            </label>
            <label>状态（可选）
              <select value={stateId} disabled={!anchorsAvailable} onChange={(event) => setStateId(event.target.value)}>
                <option value="">未指定</option>
                {states.map((item) => <option key={item.state_id} value={item.state_id}>{item.kind} · {item.state_id}</option>)}
              </select>
            </label>
          </div>
          <fieldset className="preview-feedback__categories" disabled={!anchorsAvailable}>
            <legend>类别</legend>
            {categories.map((item) => (
              <label key={item.id} className={category === item.id ? "is-active" : ""}>
                <input type="radio" name="preview-feedback-category" value={item.id} checked={category === item.id} onChange={() => setCategory(item.id)} />
                {item.label}
              </label>
            ))}
          </fieldset>
          <label>反馈内容
            <textarea value={text} maxLength={policy?.max_text_length ?? 2000} rows={3} disabled={!anchorsAvailable} onChange={(event) => setText(event.target.value)} />
          </label>
          <label className="review-checkbox">
            <input type="checkbox" checked={consented} disabled={!anchorsAvailable || !policy} onChange={(event) => setConsented(event.target.checked)} />
            <span>我同意记录这条反馈。{policy?.statement ?? "正在读取反馈政策…"}</span>
          </label>
          <button className="button button--primary" type="submit" disabled={!canSubmit}>{busy ? "正在提交…" : "提交反馈"}</button>
          <p className="unknown-copy">反馈是 user_report，只说明你在预览里的看法，不代表任务完成或真实结果。基于反馈提出的新契约仍需你确认；反馈正文不会被复制进契约。</p>
        </form>
        <div className="preview-feedback__list">
          <h2>已提交 · {feedback.length}</h2>
          {feedback.length === 0 ? <p className="unknown-copy">这个交付包还没有反馈。</p> : null}
          <ul>
            {feedback.map((item) => (
              <li key={item.feedback_id} className={item.status === "withdrawn" ? "is-withdrawn" : ""}>
                <div>
                  <Badge tone={item.status === "withdrawn" ? "neutral" : item.category === "works" ? "good" : "warn"}>
                    {item.status === "withdrawn" ? "已撤回" : categoryLabel(item.category)}
                  </Badge>
                  <small>{anchorLabel(item)}</small>
                </div>
                <p>{item.status === "withdrawn" ? "正文已按撤回清除。" : item.text}</p>
                {item.status === "submitted" ? (
                  <div className="preview-feedback__actions">
                    {canIterate ? (
                      <button className="button button--primary" type="button" disabled={busy} onClick={() => onIterate?.(item)}>
                        基于此反馈提出新契约
                      </button>
                    ) : null}
                    {onDisposition ? <FeedbackDispositionControls item={item} busy={busy} onDisposition={onDisposition} /> : null}
                    {item.submitted_by === "local-user" ? (
                      <button className="button button--quiet" type="button" disabled={busy} onClick={() => onWithdraw(item)}>撤回</button>
                    ) : null}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
