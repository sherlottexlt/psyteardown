# 超容忍时钟漂移须标记时间戳完整性失败

## Status

accepted

时钟漂移超过预先容忍度或事件顺序无法可靠重建时，受影响时段标记 `timestamp_integrity_failure`，不得用于严格运行分段或独立资格。只有预注册独立时钟源、校准方法、最大误差，并以不依赖受影响日志的外部证据重建顺序，才可通过 correction/reanalysis revision 处理；受污染时间戳不能自证校准成功。
