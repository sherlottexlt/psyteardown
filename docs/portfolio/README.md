# Transit Anchor 作品集维护说明

这份作品集不是手写一次性的案例页，而是从 experience SQLite revision 链生成的投影。每次新增 `VariablePatch`、重新生成 Blender blockout 或运行验证协议后，重新执行：

```powershell
python -m psyteardown.cli design-portfolio `
  --db output/experience/transit-anchor-portfolio-demo/case.db `
  --model-id scaffold-r1-1.model `
  --format md `
  --out docs/portfolio/transit-anchor-case-study.md
```

同时生成可供后续同步和前端读取的 JSON 源文件：

```powershell
python -m psyteardown.cli design-portfolio `
  --db output/experience/transit-anchor-portfolio-demo/case.db `
  --model-id scaffold-r1-1.model `
  --format json `
  --out docs/portfolio/transit-anchor-case-study.json
```

## 页面结构

1. 设计挑战与当前产品方向
2. 产品与图形演化：baseline → VariablePatch revision → Blender 派生资产 → prototype validation plan
3. 场景状态机：高风险移动阶段抑制 routine 介入，安全边界后恢复
4. 样机验证协议：位移、旋转、误触、取消成功率、触觉检出、接触边界和隐私泄漏
5. 未声明/未验证边界

## 更新原则

- 只通过新 revision 记录变化，不覆盖历史候选或图片。
- 图片和 GLB 只用于形态、可达性和结构讨论，不能作为尺寸、舒适度或运动稳定性证据。
- 每个产品变化都应对应一个明确的 `VariablePatch`，并保留 parent candidate、parent model 和 patch revision。
- 样机数据完成前，验证协议只能显示为 `planned`，不能写成“已证明”。
- 作品集可选择展示完整 revision 树，也可只展示当前方向；隐藏历史不等于删除历史。
