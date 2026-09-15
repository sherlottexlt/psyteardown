# V1 使用本地内容寻址资产存储

## Status

accepted

候选图片和实验资产按 SHA-256 内容寻址保存在 `.psyteardown/assets`，SQLite 只保存元数据、相对路径、隐私等级、来源和父子关系，不存媒体二进制。原始资产不可覆盖，裁剪、标注和缩略图作为 derived asset 指向父资产；ReviewItem 使用 asset_id + locator 引用证据。相同内容去重，删除默认软删除，真正清理由显式操作完成。V1 不默认上传云端，导出时生成可移植 JSON + assets 包。
