# ReviewItem 以情境化介入事件为主要组织单位

## Status

accepted

V1 的 ReviewItem 围绕 InterventionEvent 创建，而不是围绕灯带、扬声器或按钮等部件。事件明确 trigger、criticality、inferred_context、user_task、feedback_modality、timing、user_action、纠正/撤销/延后路径、public_visibility 和误判后果；物理部件作为事件引用的 DesignFact。这样同一部件在不同任务和情境下可以产生不同评审、风险与实验，也与“AI 何时、为何、如何介入”的核心场景一致。
