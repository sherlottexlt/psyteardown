import type { ProductProjectView } from "../api/types";
import { Badge } from "../components/Badge";

export function CommandView({ view }: { view: ProductProjectView }) {
  const intent = view.product_intent;
  return (
    <div className="command-layout">
      <section className="conversation-panel">
        <header>
          <div><p className="eyebrow">Conversation & command</p><h1>把不完整的想法留在这里</h1></div>
          <Badge tone="accent">结构化记忆</Badge>
        </header>
        <div className="conversation-stream">
          <div className="system-note">
            <span>Studio</span>
            <p>我会先区分你说的是事实、解释、约束还是价值选择。被接受的内容将成为可追踪对象，而不会只留在聊天记录里。</p>
          </div>
          {intent ? (
            <div className="message message--user">
              <span>你希望改变</span>
              <p>{intent.desired_change}</p>
              {intent.current_situation ? <small>{intent.current_situation}</small> : null}
            </div>
          ) : null}
          <div className="message message--studio">
            <span>当前理解</span>
            {intent ? (
              <>
                <p>目标是为 <strong>{intent.affected_people.join("、")}</strong> 改变上述现实。</p>
                <small>这仍是 {intent.status === "confirmed" ? "已确认意图" : "待你确认的提案"}，不会被当作已经验证的问题解释。</small>
              </>
            ) : <p>尚未收到初始意图。</p>}
          </div>
        </div>
        <div className="composer composer--disabled" aria-disabled="true">
          <textarea disabled placeholder="后续迭代将把自然语言补充转换为可审阅的结构化提案…" />
          <div><span>对话提案生成尚未接入</span><button disabled aria-label="发送">↑</button></div>
        </div>
      </section>
      <aside className="context-rail">
        <p className="eyebrow">Current understanding</p>
        <h2>平台现在知道什么</h2>
        <div className="context-item"><span>目标人群</span><strong>{intent?.affected_people.join(" · ") || "待明确"}</strong></div>
        <div className="context-item"><span>明确拒绝</span><strong>{intent?.explicit_non_goals.length ? `${intent.explicit_non_goals.length} 项` : "待明确"}</strong></div>
        <div className="context-item"><span>已知约束</span><strong>{intent?.known_constraints.length ? `${intent.known_constraints.length} 项` : "待明确"}</strong></div>
        <div className="context-item"><span>来源</span><strong>{intent?.source_refs.length ?? 0} 条</strong></div>
        <div className="boundary-note"><span aria-hidden="true">◇</span><p>平台尚未自动研究、调用模型或执行外部工具。本页不会把演示文案伪装成 AI 已完成的工作。</p></div>
      </aside>
    </div>
  );
}
