# 事后分层一致性不计入复现

## Status

accepted

新实验确认调节变量后，对旧实验未预注册分层的重算只能标记 `retrospective_consistency` 或 `retrospective_conflict`，不能回填确认性支持或复现计数。新条件假设须创建独立 revision，以新的预注册分层实验建立 `supported`，并至少再经一次独立确认性实验才能标记 `replicated`。
