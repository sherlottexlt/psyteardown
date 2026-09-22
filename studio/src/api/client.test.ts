import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClientError, createProject, getProject, reviseProductIntent } from "./client";
import type { ProductIntent } from "./types";

afterEach(() => vi.unstubAllGlobals());

describe("Product Studio API client", () => {
  it("creates a project through the versioned API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ project_id: "project-1" }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(createProject({ name: "Focus", collaborationMode: "managed" })).resolves.toMatchObject({ project_id: "project-1" });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/projects", expect.objectContaining({ method: "POST" }));
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(JSON.parse(String(init.body))).toMatchObject({ name: "Focus", collaboration_mode: "managed" });
  });

  it("keeps the server request id on a structured failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: "not_found", message: "unknown project", request_id: "req-1", issues: [] },
    }), { status: 404, headers: { "Content-Type": "application/json" } })));
    const error = await getProject("missing").catch((cause: unknown) => cause);
    expect(error).toBeInstanceOf(ApiClientError);
    expect(error).toMatchObject({ code: "not_found", requestId: "req-1", message: "unknown project" });
  });

  it("explains how to recover from a network boundary failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(getProject("project-1")).rejects.toMatchObject({ code: "network_error" });
  });

  it("revises the stable intent with optimistic concurrency and provenance", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ intent_id: "intent-1" }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    const intent = {
      project_id: "project-1",
      intent_id: "intent-1",
      revision_id: "intent-1.r2",
      meta: { revision: 2 },
      source_refs: [{ source_type: "user_input", source_id: "message-1" }],
    } as ProductIntent;

    await reviseProductIntent({
      projectId: "project-1",
      intent,
      draft: {
        desiredChange: "保护专注，同时保留紧急联系",
        affectedPeople: ["独立工作者"],
        currentSituation: "多个工具持续产生消息",
        explicitNonGoals: ["监控个人生产力"],
        knownConstraints: ["本地优先"],
        resourcePreferences: ["一天内获得原型"],
      },
    });

    const body = JSON.parse(String((fetchMock.mock.calls[0]?.[1] as RequestInit).body));
    expect(body).toMatchObject({
      intent_id: "intent-1",
      expected_revision: 2,
      proposal: {
        desired_change: "保护专注，同时保留紧急联系",
        explicit_non_goals: ["监控个人生产力"],
        known_constraints: ["本地优先"],
      },
    });
    expect(body.proposal.source_refs).toHaveLength(2);
  });
});
