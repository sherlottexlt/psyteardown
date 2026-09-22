import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import type {
  EditableProductIntent,
  ProductIntent,
  RevisionWriteResult,
} from "../api/types";

function lines(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function people(value: string): string[] {
  return value
    .split(/[,，、\r\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

interface IntentFormState {
  desiredChange: string;
  affectedPeople: string;
  currentSituation: string;
  explicitNonGoals: string;
  knownConstraints: string;
  resourcePreferences: string;
}

function initialState(intent: ProductIntent): IntentFormState {
  return {
    desiredChange: intent.desired_change,
    affectedPeople: intent.affected_people.join("，"),
    currentSituation: intent.current_situation ?? "",
    explicitNonGoals: intent.explicit_non_goals.join("\n"),
    knownConstraints: intent.known_constraints.join("\n"),
    resourcePreferences: intent.resource_preferences.join("\n"),
  };
}

export function IntentEditor({
  intent,
  busy,
  onCancel,
  onSave,
}: {
  intent: ProductIntent;
  busy: boolean;
  onCancel: () => void;
  onSave: (draft: EditableProductIntent) => Promise<RevisionWriteResult>;
}) {
  const [form, setForm] = useState(() => initialState(intent));
  const [message, setMessage] = useState<string | null>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => titleRef.current?.focus(), []);

  function update(field: keyof IntentFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const result = await onSave({
      desiredChange: form.desiredChange.trim(),
      affectedPeople: people(form.affectedPeople),
      currentSituation: form.currentSituation.trim(),
      explicitNonGoals: lines(form.explicitNonGoals),
      knownConstraints: lines(form.knownConstraints),
      resourcePreferences: lines(form.resourcePreferences),
    });
    if (result.status === "saved") {
      onCancel();
      return;
    }
    if (result.status === "conflict") {
      setMessage(
        `服务端已有更新，已刷新到 r${result.latestRevision}。你的草稿仍保留；请复核后再次保存。`,
      );
      titleRef.current?.focus();
      return;
    }
    setMessage(result.message);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLFormElement>) {
    if (event.key === "Escape" && !busy) {
      event.preventDefault();
      onCancel();
    }
  }

  const valid = Boolean(form.desiredChange.trim() && people(form.affectedPeople).length);
  return (
    <form
      className="intent-editor"
      aria-labelledby="intent-editor-title"
      onSubmit={(event) => void submit(event)}
      onKeyDown={handleKeyDown}
    >
      <header>
        <div>
          <p className="eyebrow">Correct current understanding</p>
          <h3 id="intent-editor-title" ref={titleRef} tabIndex={-1}>
            纠正产品意图
          </h3>
          <p>保存会创建新的 proposal revision；若当前意图已确认，纠正后需要重新确认。</p>
        </div>
        <span className="revision">基于服务端 r{intent.meta.revision}</span>
      </header>

      <div className="intent-editor__grid">
        <label className="intent-editor__wide">
          希望什么发生改变？
          <textarea
            required
            rows={3}
            value={form.desiredChange}
            onChange={(event) => update("desiredChange", event.target.value)}
          />
        </label>
        <label>
          受到影响的人
          <input
            required
            value={form.affectedPeople}
            onChange={(event) => update("affectedPeople", event.target.value)}
            aria-describedby="affected-people-help"
          />
          <small id="affected-people-help">多人可用逗号分隔</small>
        </label>
        <label>
          当前情境
          <input
            value={form.currentSituation}
            onChange={(event) => update("currentSituation", event.target.value)}
          />
        </label>
        <label>
          明确不做什么
          <textarea
            rows={4}
            value={form.explicitNonGoals}
            onChange={(event) => update("explicitNonGoals", event.target.value)}
            aria-describedby="non-goals-help"
          />
          <small id="non-goals-help">每行一项</small>
        </label>
        <label>
          已知约束
          <textarea
            rows={4}
            value={form.knownConstraints}
            onChange={(event) => update("knownConstraints", event.target.value)}
            aria-describedby="constraints-help"
          />
          <small id="constraints-help">每行一项</small>
        </label>
        <label className="intent-editor__wide">
          资源倾向
          <textarea
            rows={3}
            value={form.resourcePreferences}
            onChange={(event) => update("resourcePreferences", event.target.value)}
            aria-describedby="resource-preferences-help"
          />
          <small id="resource-preferences-help">时间、成本、注意力或维护倾向；每行一项</small>
        </label>
      </div>

      {message ? <p className="intent-editor__message" role="alert">{message}</p> : null}
      <footer>
        <span>按 Esc 取消，不会写入任何 revision</span>
        <div>
          <button className="button button--quiet" disabled={busy} onClick={onCancel} type="button">
            取消
          </button>
          <button className="button button--primary" disabled={busy || !valid} type="submit">
            {busy ? "正在保存…" : "保存为新提案"}
          </button>
        </div>
      </footer>
    </form>
  );
}
