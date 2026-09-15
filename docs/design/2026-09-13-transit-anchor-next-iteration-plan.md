# Transit Anchor 下一轮设计迭代计划

当前 Blender 设计已经足够进入评审，但还没有进入样机证据阶段。下一轮应优先验证控制权，而不是继续增加功能或美化形态。

优先级：

1. 停止路径：确认 side press-hold 是否可达、可盲操作、低误触。
2. 表带与快拆：确认低轮廓 strap 是否稳定且可快速移除。
3. 触觉与隐私：确认 private haptic 在振动、袖口、汗湿下可检出，且旁观者不能推断私人内容。

停止路径先标记 exploratory，不直接声称 supported。记录 completion rate、completion time、false activation 和失败原因；双手不可用阶段验证抑制/延后/超时策略，不算作物理控件失败。

如果停止路径失败，先区分控件位置、guard 几何、hold duration、袖口干涉和场景策略问题，再创建下一轮 patch。不要静默覆盖旧 revision。
