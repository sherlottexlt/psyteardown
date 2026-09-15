# MVP 使用本地 Web Review Workspace

## Status

accepted

V1 以本地 FastAPI + React/Vite Review Workspace 作为主要人工界面，提供 Brief、Candidates、Facts、Review、Compare & Iterate 五个最小工作区；SQLite 保存状态。CLI 继续负责批处理、评测、导入导出和管理操作。首版不做账号、实时协作、云部署或复杂仪表盘。这样视觉候选、证据冲突和多轮比较可以在同一工作台完成；代价是需要同时维护 API 和前端状态模型。
