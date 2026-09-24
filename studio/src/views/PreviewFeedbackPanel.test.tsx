import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  PreviewFeedback,
  PreviewFeedbackPolicy,
  ProductDeliveryBundle,
  WebProductGenerationContract,
} from "../api/types";
import { PreviewFeedbackPanel } from "./PreviewFeedbackPanel";

const bundle = {
  bundle_id: "delivery-bundle-1",
  revision_id: "delivery-bundle-1.r1",
  web_generation_contract_revision_id: "web-contract-1.r2",
} as unknown as ProductDeliveryBundle;

const contract = {
  revision_id: "web-contract-1.r2",
  screens: [
    { screen_id: "focus", title: "Focus session", task_ids: ["start"], state_ids: ["ready", "stopped"] },
    { screen_id: "contacts", title: "Urgent contacts", task_ids: ["allow"], state_ids: ["ready"] },
  ],
  tasks: [
    { task_id: "start", goal: "Start a focus block" },
    { task_id: "allow", goal: "Allow an urgent contact" },
  ],
  states: [
    { state_id: "ready", kind: "ready" },
    { state_id: "stopped", kind: "stopped" },
  ],
} as unknown as WebProductGenerationContract;

const policy = {
  consent_version: "b7-explicit-v1",
  statement: "Only what you write here is recorded.",
  captured: [],
  not_captured: ["clicks"],
  max_text_length: 2000,
  evidence_level: "user_report",
} as PreviewFeedbackPolicy;

function renderPanel(props: Partial<Parameters<typeof PreviewFeedbackPanel>[0]> = {}) {
  const onSubmit = vi.fn().mockResolvedValue(true);
  const onWithdraw = vi.fn();
  render(
    <PreviewFeedbackPanel
      bundle={bundle}
      contract={contract}
      previewUrl="/preview/delivery-bundle-1/"
      policy={policy}
      feedback={[]}
      busy={false}
      onSubmit={onSubmit}
      onWithdraw={onWithdraw}
      {...props}
    />,
  );
  return { onSubmit, onWithdraw };
}

describe("PreviewFeedbackPanel", () => {
  afterEach(cleanup);

  it("renders the delivered build in a script-only sandbox", () => {
    renderPanel();
    const frame = screen.getByTitle("交付构建预览");
    expect(frame).toHaveAttribute("src", "/preview/delivery-bundle-1/");
    expect(frame).toHaveAttribute("sandbox", "allow-scripts");
  });

  it("requires explicit consent for every report and sends the chosen anchor", async () => {
    const { onSubmit } = renderPanel();
    const submit = screen.getByRole("button", { name: "提交反馈" });
    await userEvent.type(screen.getByLabelText("反馈内容"), "  Hard to find the stop button  ");
    expect(submit).toBeDisabled();

    await userEvent.selectOptions(screen.getByLabelText("页面"), "contacts");
    await userEvent.selectOptions(screen.getByLabelText("任务（可选）"), "allow");
    await userEvent.click(screen.getByLabelText("缺失"));
    await userEvent.click(screen.getByRole("checkbox", { name: /我同意记录这条反馈/ }));
    await userEvent.click(submit);

    expect(onSubmit).toHaveBeenCalledWith({
      screenId: "contacts",
      taskId: "allow",
      stateId: null,
      category: "missing",
      text: "Hard to find the stop button",
    });
    expect(screen.getByRole("checkbox", { name: /我同意记录这条反馈/ })).not.toBeChecked();
    expect(screen.getByLabelText("反馈内容")).toHaveValue("");
  });

  it("disables anchoring when the contract changed after export", () => {
    renderPanel({ contract: { ...contract, revision_id: "web-contract-1.r3" } });
    expect(screen.getByText(/Web 契约已在导出后变化/)).toBeInTheDocument();
    expect(screen.getByLabelText("反馈内容")).toBeDisabled();
    expect(screen.getByRole("button", { name: "提交反馈" })).toBeDisabled();
  });

  it("offers withdrawal for own reports and shows withdrawn tombstones without text", async () => {
    const submitted = {
      feedback_id: "preview-feedback-1",
      status: "submitted",
      category: "bug",
      text: "Stop button does nothing",
      submitted_by: "local-user",
      anchor: { screen_id: "focus", task_id: "start", state_id: null },
      meta: { revision: 1 },
    } as unknown as PreviewFeedback;
    const withdrawn = {
      ...submitted,
      feedback_id: "preview-feedback-2",
      status: "withdrawn",
      category: null,
      text: null,
    } as unknown as PreviewFeedback;
    const { onWithdraw } = renderPanel({ feedback: [submitted, withdrawn] });

    expect(screen.getByText("Stop button does nothing")).toBeInTheDocument();
    expect(screen.getByText("正文已按撤回清除。")).toBeInTheDocument();
    const buttons = screen.getAllByRole("button", { name: "撤回" });
    expect(buttons).toHaveLength(1);
    await userEvent.click(buttons[0]!);
    expect(onWithdraw).toHaveBeenCalledWith(submitted);
  });

  it("offers iteration only on a confirmed current contract and records disposition explicitly", async () => {
    const submitted = {
      feedback_id: "preview-feedback-1",
      status: "submitted",
      category: "confusing",
      text: "Where is urgent contact?",
      submitted_by: "local-user",
      disposition: "pending",
      anchor: { screen_id: "focus", task_id: null, state_id: null },
      meta: { revision: 1 },
    } as unknown as PreviewFeedback;
    const onIterate = vi.fn();
    const onDisposition = vi.fn();
    renderPanel({
      contract: { ...contract, status: "confirmed" } as WebProductGenerationContract,
      feedback: [submitted],
      onIterate,
      onDisposition,
    });

    expect(screen.getByText("待处理")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "基于此反馈提出新契约" }));
    expect(onIterate).toHaveBeenCalledWith(submitted);
    await userEvent.click(screen.getByRole("button", { name: "标记暂缓" }));
    expect(onDisposition).toHaveBeenCalledWith(submitted, "deferred");

    cleanup();
    renderPanel({
      contract: { ...contract, status: "proposed" } as WebProductGenerationContract,
      feedback: [submitted],
      onIterate,
      onDisposition,
    });
    expect(screen.queryByRole("button", { name: "基于此反馈提出新契约" })).not.toBeInTheDocument();
  });
});
