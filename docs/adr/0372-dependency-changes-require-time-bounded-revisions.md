# 依赖变化须创建带时间边界的修订

## Status

accepted

实验期间关键架构、配置、访问权限或故障依赖变化时，必须建立带时间边界的 dependency-graph revision 并隔离变更前后运行；不同 revision 不得共用同一独立性结论。未及时记录的变化导致受影响时段标记 `dependency_revision_unknown`，除非预注册允许且证明关键错误路径未改变，否则不得计入严格资格。
