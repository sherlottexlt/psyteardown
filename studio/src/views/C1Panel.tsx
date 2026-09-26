import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  enrollC1Participant,
  getC1Policy,
  listC1Envelopes,
  listC1Observations,
  listC1Participants,
  presentC1Task,
  recordC1Observation,
  reviewC1Evidence,
  startC1Envelope,
  withdrawC1Participant,
} from "../api/client";
import type { C1TrialEnvelope, OutcomeMeasurementPlan, ProductDeliveryBundle, ProductExecutionJob, ProductProjectView } from "../api/types";
import { Badge } from "../components/Badge";

export function C1Panel({
  projectId,
  view,
  plan,
  deliveryBundle,
  executionJob,
  busy = false,
  onChanged,
  onError,
}: {
  projectId: string;
  view: ProductProjectView;
  plan: OutcomeMeasurementPlan;
  deliveryBundle: ProductDeliveryBundle | null;
  executionJob: ProductExecutionJob | null;
  busy?: boolean;
  onChanged: () => Promise<unknown>;
  onError: (message: string) => void;
}) {
  const policyQuery = useQuery({ queryKey: ["c1-policy"], queryFn: getC1Policy, retry: false });
  const envelopesQuery = useQuery({ queryKey: ["c1-envelopes", projectId], queryFn: () => listC1Envelopes(projectId), retry: false });
  const envelope = (envelopesQuery.data ?? []).at(-1) ?? null;
  const participantsQuery = useQuery({
    queryKey: ["c1-participants", projectId, envelope?.envelope_id],
    queryFn: () => listC1Participants(projectId, envelope!.envelope_id),
    enabled: Boolean(envelope),
    retry: false,
  });
  const observationsQuery = useQuery({
    queryKey: ["c1-observations", projectId, envelope?.envelope_id],
    queryFn: () => listC1Observations(projectId, envelope!.envelope_id),
    enabled: Boolean(envelope),
    retry: false,
  });
  const [participantId, setParticipantId] = useState("");
  const [presentationId, setPresentationId] = useState("");
  const [taskId, setTaskId] = useState(view.web_generation_contract?.tasks[0]?.task_id ?? "");
  const [measureId, setMeasureId] = useState(plan.measures.find((item) => item.source_layer === "research_observation")?.measure_id ?? "");
  const [value, setValue] = useState("true");
  const [status, setStatus] = useState<"observed" | "task_abandonment" | "technical_failure" | "skipped_by_protocol" | "no_response" | "not_applicable" | "unknown">("observed");
  const [reviewer, setReviewer] = useState("named-reviewer");
  const [reviewDecision, setReviewDecision] = useState<"accepted" | "modified" | "rejected" | "insufficient">("accepted");
  const [reviewLevel, setReviewLevel] = useState<"none" | "exploratory" | "observed">("observed");
  const [reviewRationale, setReviewRationale] = useState("Reviewed the structured task record");
  const [consentChecked, setConsentChecked] = useState(false);
  const policy = policyQuery.data;
  const currentParticipant = (participantsQuery.data ?? []).find((item) => item.participant_id === participantId) ?? (participantsQuery.data ?? []).at(-1) ?? null;
  const observations = observationsQuery.data ?? [];
  const contract = view.web_generation_contract;
  const researchMeasures = plan.measures.filter((item) => item.source_layer === "research_observation");

  async function run(action: () => Promise<unknown>) {
    try {
      await action();
      await Promise.all([envelopesQuery.refetch(), participantsQuery.refetch(), observationsQuery.refetch(), onChanged()]);
    } catch (error) {
      onError(error instanceof Error ? error.message : "C1 操作失败，请检查后端状态。");
    }
  }

  const canStart = plan.status === "confirmed" && deliveryBundle?.contract_is_current && executionJob?.status === "succeeded" && Boolean(contract);
  return (
    <section className="panel evidence-section evidence-section--wide c1-panel" aria-labelledby="c1-panel-title">
      <div className="panel__heading">
        <div><p className="eyebrow">C1 · Local task observation</p><h2 id="c1-panel-title">只在明确同意后记录一条人工观察</h2></div>
        <Badge tone={envelope?.status === "active" ? "warn" : "good"}>{envelope ? envelope.status : "未开始"}</Badge>
      </div>
      <p className="measurement-plan-intro">本地主持、随机参与者 ID、结构化 measure 和具名 reviewer。不会采集屏幕、键鼠、通知、遥测或参与者原始文本；C1 只接受 research_observation，证据上限为 observed。</p>
      {policy ? <div className="c1-policy"><strong>{policy.consent_policy_revision}</strong><span>{policy.statement}</span><small>访问：{policy.access_policy.join("、")} · 保留：{policy.retention_policy}</small></div> : null}
      {!envelope ? (
        <div className="c1-actions"><button className="button button--primary" disabled={busy || !canStart} onClick={() => deliveryBundle && executionJob && void run(() => startC1Envelope({ projectId, measurementPlanRevisionId: plan.revision_id, deliveryBundleId: deliveryBundle.bundle_id, executionJobRevisionId: deliveryBundle.execution_job_revision_id, webGenerationContractRevisionId: deliveryBundle.web_generation_contract_revision_id }))}>开始本地 C1 试用</button>{!canStart ? <span className="unknown-copy">需要确认的 C2 计划、当前 Web 契约和成功的 B6 交付包。</span> : null}</div>
      ) : (
        <div className="c1-stack">
          <div className="c1-grid">
            <div><h3>1 · 参与者同意</h3><label className="checkbox-label"><input type="checkbox" checked={consentChecked} onChange={(event) => setConsentChecked(event.target.checked)} />我已向参与者展示完整同意说明，并获得明确授权。</label><button className="button button--quiet" disabled={busy || !consentChecked} onClick={() => void run(async () => { const result = await enrollC1Participant({ projectId, envelopeId: envelope.envelope_id, policyRevision: policy?.consent_policy_revision ?? "" }); setParticipantId(result.participant.participant_id); setConsentChecked(false); })}>生成随机参与者 ID</button>{currentParticipant ? <code className="c1-participant-id">{currentParticipant.participant_id}</code> : null}</div>
            <div><h3>2 · 主持任务</h3><label>任务<select value={taskId} onChange={(event) => setTaskId(event.target.value)}>{(contract?.tasks ?? []).map((task) => <option value={task.task_id} key={task.task_id}>{task.task_id}</option>)}</select></label><button className="button button--quiet" disabled={busy || !currentParticipant || !taskId} onClick={() => void run(async () => { const result = await presentC1Task({ projectId, envelopeId: envelope.envelope_id, participantId: currentParticipant!.participant_id, taskId }); setParticipantId(currentParticipant!.participant_id); setPresentationId(result.presentation_id); })}>开始任务 presentation</button>{presentationId ? <small>presentation：{presentationId}</small> : null}</div>
          </div>
          <div className="c1-grid">
            <div><h3>3 · 结构化观察</h3><label>measure<select value={measureId} onChange={(event) => setMeasureId(event.target.value)}>{researchMeasures.map((measure) => <option value={measure.measure_id} key={measure.measure_id}>{measure.label}</option>)}</select></label><label>结果值<input value={value} onChange={(event) => setValue(event.target.value)} aria-label="C1 observation value" /></label><label>状态<select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="observed">observed</option><option value="task_abandonment">task_abandonment</option><option value="technical_failure">technical_failure</option><option value="skipped_by_protocol">skipped_by_protocol</option><option value="no_response">no_response</option><option value="not_applicable">not_applicable</option><option value="unknown">unknown</option></select></label><button className="button button--quiet" disabled={busy || !currentParticipant || !presentationId || !measureId} onClick={() => void run(() => recordC1Observation({ projectId, envelopeId: envelope.envelope_id, participantId: currentParticipant!.participant_id, presentationId, measureId, value: status === "observed" ? (value === "true" ? true : value === "false" ? false : Number.isNaN(Number(value)) ? value : Number(value)) : null, status }))}>保存观察</button></div>
            <div><h3>4 · 人工 EvidenceReview</h3><label>reviewer（需与 host 分离）<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label><label>判断<select value={reviewDecision} onChange={(event) => setReviewDecision(event.target.value as typeof reviewDecision)}><option value="accepted">accepted</option><option value="modified">modified</option><option value="rejected">rejected</option><option value="insufficient">insufficient</option></select></label><label>等级<select value={reviewLevel} onChange={(event) => setReviewLevel(event.target.value as typeof reviewLevel)}><option value="observed">observed</option><option value="exploratory">exploratory</option><option value="none">none</option></select></label><label>理由<input value={reviewRationale} onChange={(event) => setReviewRationale(event.target.value)} /></label><button className="button button--quiet" disabled={busy || !observations.length} onClick={() => void run(() => reviewC1Evidence({ projectId, envelopeId: envelope.envelope_id, observationIds: observations.map((item) => item.observation_id), reviewer, decision: reviewDecision, evidenceLevelAfter: reviewLevel, rationale: reviewRationale }))}>提交人工 review</button></div>
          </div>
          {observations.length ? <div className="c1-observations"><h3>当前未撤回观察</h3>{observations.map((item) => <div key={item.observation_id}><Badge tone={item.status === "observed" ? "good" : "warn"}>{item.status}</Badge><span>{item.measure_id} · {String(item.value ?? "—")}</span><small>{item.recorded_at}</small></div>)}</div> : null}
          {currentParticipant ? <button className="button button--quiet c1-withdraw" disabled={busy} onClick={() => void run(() => withdrawC1Participant({ projectId, envelopeId: envelope.envelope_id, participantId: currentParticipant.participant_id }))}>记录参与者撤回并擦除源记录</button> : null}
        </div>
      )}
    </section>
  );
}
