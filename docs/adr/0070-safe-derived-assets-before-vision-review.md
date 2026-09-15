# 视觉评审只读取安全派生资产

## Status

accepted

V1 只接受 PNG、JPEG、WebP、纯文本、JSON 和 Markdown 等受限格式。原始资产先经 MIME/文件头、大小/像素/帧数、解码、压缩包路径和脚本检查，再去除 EXIF/GPS/隐藏元数据并重新编码为 Safe Derived Asset；浏览器和 VisionObserver 只读取派生副本，原始资产保留父子关系。SVG、HTML、宏文档、CAD 原文件和可执行文件暂不直接支持。检查失败标记 asset_invalid，不能进入事实确认。
