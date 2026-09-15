# V1 工作台只在本机访问并使用本地会话边界

## Status

accepted

V1 不实现账号系统，FastAPI 默认只监听 127.0.0.1，CORS 仅允许本地前端 origin，并使用随机 Local Session token 保护写操作。前端不接触模型 API key；资产接口只接受已登记 asset_id，不允许任意文件路径；上传和导入包校验 MIME、大小、文件头并防路径穿越。审计 actor_id 暂为 local-user。未来开放局域网或多人使用时必须新增真实认证授权，不能直接暴露本地模式。
