# 迁移保留同意历史但不继承远程传输授权

## Status

accepted

项目迁移保留原 Consent Record、用途范围和撤回状态，作为历史研究记录；remote_model_processing 授权绑定 provider/model/policy、资产派生版本和设备/项目 context，不因换设备或导入项目包自动继承。新设备、provider、模型、政策或资产版本都进入 awaiting_consent 并重新确认，参与者撤回/限制/过期状态优先，迁移不能恢复权限；已完成运行保留原授权/政策快照。
