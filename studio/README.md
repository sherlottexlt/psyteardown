# Product Studio Web

React/TypeScript/Vite shell for the Product Studio vertical slice. It uses the
existing FastAPI `/api/v1` command and projection boundary; it does not duplicate
domain rules in the browser.

## Local development

From the repository root, start the API:

```powershell
psyteardown-studio-api
```

Then start the web workspace:

```powershell
cd studio
npm install
npm run dev
```

Vite listens on `127.0.0.1:5173` and proxies `/api` to
`127.0.0.1:8000`. Set `VITE_API_BASE_URL` only when the API is intentionally
served elsewhere.

## Verification

```powershell
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

`npm run build` 会先从 FastAPI 应用导出 `openapi.json`，再生成
`src/api/schema.ts` 并进行 TypeScript/Vite 构建。生成文件受后端测试保护；API schema
发生变化时必须提交相应生成 diff。

The current shell supports project creation, proposal generation through
persisted proposal jobs, correction and human confirmation of ProductIntent,
ProblemModel and OutcomeContract, revision-conflict recovery, project
projection, thesis transitions, and the five Product Studio work areas.

After a Web generation contract is confirmed, the workbench can also enqueue
and run the local B3 generation job. It writes a fixed-template source
workspace with a manifest under the API's configured workspace root. The job is
bounded to local fixtures, no network, no secrets, and no source execution;
dependency installation, builds, previews, and Playwright validation are a
separate explicit B4 execution job. The local runner validates the manifest and
fixed package allowlist, runs install/build/loopback preview/Chromium checks,
and persists only step summaries. It is a local allowlisted subprocess, not a
container or remote multi-tenant isolation boundary.

Proposals come from a deterministic, network-free fake provider that only
restates already-confirmed user input. Its output is a proposal awaiting human
correction — never external fact, evidence or user outcome. Creating a job
returns a persisted `job_id` without running the provider; the browser then
issues the separate run command. Jobs are advanced by the client, not by a
resident worker: if the tab closes mid-run the job stays queued and the same
generate action resumes it. Real model providers, background workers, sandboxed
product builds and runnable previews remain explicit unavailable states.
