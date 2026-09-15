# 合成基准双人独立标注并在运行前冻结

## Status

accepted

Synthetic Benchmark Case 在运行 psyteardown 或基线前，由案例作者和至少一位不参与对应评审逻辑实现的标注者独立标注，再通过证据回查、情境拆分或竞争假设处置分歧并冻结版本哈希。答案分为 Hard Ground Truth、Adjudicated Judgement 和 Open Evaluation Question；只有硬真值用于 accuracy/precision/recall，审议判断报告一致率和分歧，开放问题以能否正确进入 explore 评测。修改答案创建新版本，不为提高成绩临时调整。
