import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { EditableProductIntent, ProductIntent, RevisionWriteResult } from "../api/types";
import { IntentEditor } from "./IntentEditor";

function intent(revision: number): ProductIntent {
  return {
    project_id: "project-1",
    intent_id: "intent-1",
    revision_id: `intent-1.r${revision}`,
    meta: {
      revision,
      parent_revision_id: revision > 1 ? `intent-1.r${revision - 1}` : null,
      created_at: "2026-09-20T00:00:00Z",
      created_by: "user",
      reason: "test",
    },
    status: "proposed",
    desired_change: "减少工作打断",
    affected_people: ["独立工作者"],
    current_situation: "消息来自多个工具",
    explicit_non_goals: [],
    known_constraints: [],
    resource_preferences: [],
    source_refs: [{ source_type: "user_input", source_id: "message-1" }],
    confirmation: null,
    content_hash: "hash",
  };
}

function ConflictHarness({ onDraft }: { onDraft: (draft: EditableProductIntent) => void }) {
  const [current, setCurrent] = useState(intent(1));
  const [attempt, setAttempt] = useState(0);
  async function save(draft: EditableProductIntent): Promise<RevisionWriteResult> {
    onDraft(draft);
    if (attempt === 0) {
      setAttempt(1);
      setCurrent(intent(2));
      return { status: "conflict", latestRevision: 2 };
    }
    return { status: "saved" };
  }
  return <IntentEditor intent={current} busy={false} onCancel={() => undefined} onSave={save} />;
}

describe("IntentEditor", () => {
  it("keeps the local draft while refreshing the conflicting server revision", async () => {
    const onDraft = vi.fn();
    const user = userEvent.setup();
    render(<ConflictHarness onDraft={onDraft} />);

    const desiredChange = screen.getByLabelText("希望什么发生改变？");
    await user.clear(desiredChange);
    await user.type(desiredChange, "减少打断但保留紧急联系");
    await user.click(screen.getByRole("button", { name: "保存为新提案" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("已刷新到 r2");
    expect(desiredChange).toHaveValue("减少打断但保留紧急联系");
    expect(screen.getByText("基于服务端 r2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "保存为新提案" }));
    await waitFor(() => expect(onDraft).toHaveBeenCalledTimes(2));
  });

  it("cancels with Escape without writing", async () => {
    const onCancel = vi.fn();
    const onSave = vi.fn();
    const user = userEvent.setup();
    render(<IntentEditor intent={intent(1)} busy={false} onCancel={onCancel} onSave={onSave} />);

    await user.tab();
    await user.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();
    expect(onSave).not.toHaveBeenCalled();
  });
});
