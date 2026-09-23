import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  ProductDeliveryBundle,
  ProductExecutionJob,
  ProductGenerationJob,
  ProductProjectView,
} from "../api/types";
import { WorkbenchView } from "./WorkbenchView";

const view = {
  project: { project_id: "project-1" },
  product_intent: null,
  problem_model: null,
  outcome_contract: null,
  product_theses: [{ thesis_id: "thesis-1", status: "selected", name: "Focus guard", product_promise: "promise", realization_modes: [], differentiation: "d", key_unknowns: ["u"], falsifiable_predictions: [], validation_strategy: [], delivery_estimate: { maintenance_burden: "low" } }],
  web_generation_contract: { status: "confirmed", app_title: "Focus guard", template_id: "react_typescript_vite_spa", template_version: "b2-v1", screens: [], tasks: [] },
  recorded_impacts: [],
} as unknown as ProductProjectView;

const generationJob = { status: "succeeded", consumed_files: 10, consumed_bytes: 100, sandbox: { network_policy: "none", execution_policy: "not_executed" }, budget: { max_bytes: 1000 } } as unknown as ProductGenerationJob;
const executionJob = { job_id: "execution-job-1", revision_id: "execution-job-1.r7", status: "succeeded", checkpoint_step: "browser" } as unknown as ProductExecutionJob;
const bundle = {
  bundle_id: "delivery-bundle-1",
  execution_job_revision_id: "execution-job-1.r7",
  web_generation_contract_revision_id: "web-contract-1.r1",
  materialization_kind: "template",
  archive_sha256: "a".repeat(64),
  archive_bytes: 4096,
  files: [{}, {}],
  outcome_evidence_level: "none",
  unverified_claims: ["No real-user evidence."],
} as unknown as ProductDeliveryBundle;

function renderWorkbench(props: Partial<Parameters<typeof WorkbenchView>[0]> = {}) {
  const onExportProduct = vi.fn();
  render(
    <WorkbenchView
      view={view}
      busy={false}
      onGenerate={vi.fn()}
      onGenerateWeb={vi.fn()}
      onConfirmWeb={vi.fn()}
      generationJob={generationJob}
      executionJob={executionJob}
      onGenerateProduct={vi.fn()}
      onExecuteProduct={vi.fn()}
      onRepairProduct={vi.fn()}
      onExportProduct={onExportProduct}
      deliveryArchiveUrl={(id) => `/archive/${id}`}
      {...props}
    />,
  );
  return onExportProduct;
}

describe("WorkbenchView delivery export", () => {
  afterEach(cleanup);

  it("offers export only after a succeeded execution", async () => {
    const onExport = renderWorkbench();
    await userEvent.click(screen.getByRole("button", { name: "导出交付包" }));
    expect(onExport).toHaveBeenCalledOnce();
    expect(screen.queryByRole("link", { name: /下载交付包/ })).toBeNull();
  });

  it("hides export for an unverified execution", () => {
    renderWorkbench({ executionJob: { ...executionJob, status: "failed" } as ProductExecutionJob });
    expect(screen.queryByRole("button", { name: "导出交付包" })).toBeNull();
  });

  it("shows the matching bundle with download link and unverified claims", () => {
    renderWorkbench({ deliveryBundle: bundle });
    expect(screen.getByRole("link", { name: /下载交付包/ })).toHaveAttribute("href", "/archive/delivery-bundle-1");
    expect(screen.getByText("No real-user evidence.")).toBeInTheDocument();
  });

  it("opens the delivered build preview only for the current bundle", () => {
    const preview = { url: (id: string) => `/preview/${id}/`, policy: null, feedback: [], onSubmit: vi.fn(), onWithdraw: vi.fn() };
    renderWorkbench({ deliveryBundle: bundle, preview });
    expect(screen.getByTitle("交付构建预览")).toHaveAttribute("src", "/preview/delivery-bundle-1/");
    cleanup();
    renderWorkbench({ deliveryBundle: { ...bundle, execution_job_revision_id: "execution-job-0.r7" }, preview });
    expect(screen.queryByTitle("交付构建预览")).toBeNull();
    expect(screen.getByText("还没有可预览的交付构建")).toBeInTheDocument();
  });

  it("does not present a bundle from an older execution as current", () => {
    renderWorkbench({ deliveryBundle: { ...bundle, execution_job_revision_id: "execution-job-0.r7" } });
    expect(screen.queryByRole("link", { name: /下载交付包/ })).toBeNull();
    expect(screen.getByRole("button", { name: "导出交付包" })).toBeInTheDocument();
  });
});
