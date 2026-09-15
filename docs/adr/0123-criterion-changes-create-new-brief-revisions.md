# Criterion 变化通过 Brief revision 局部失效

## Status

accepted

修改 ExperienceCriterion 的定义、可观察/禁止指标、适用场景或优先级必须创建新的 DesignBrief revision。事实、Confirmed Observation、机制卡和原始 ReviewItem 保留；受影响的 Criterion Mapping、Design Alignment、Candidate Partial Order、人工选择上下文、实验优先级和 Next Prompt 局部标记 stale 并重新确认。增加准则只生成受影响的新 ReviewItem，删除准则停止新排序引用但保留历史。已发送提示不修改，新 Brief 需重新确认选择和反馈。
