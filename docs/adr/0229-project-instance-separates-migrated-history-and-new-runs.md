# Project Instance 隔离迁移历史与新运行

## Status

accepted

项目迁移后使用独立 Project Instance 区分源项目历史和新设备运行。历史候选、评审、实验和分析标记 imported_history，保留 origin_project_id/source_bundle_id；新设备维护独立 current、Job、评审和结果，不覆盖源项目。跨实例比较必须通过兼容性检查，并显示实例、设备、版本、资产和恢复状态。
