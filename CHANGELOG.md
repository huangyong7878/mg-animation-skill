# CHANGELOG

## Unreleased

### 新增
- `references/creative-director.md`：创意导演 Skill 1.0（语义拆解、视觉创意、Beat vs Shot、延续镜头、视觉事实检查）
- `references/technical-director.md`：技术导演 Skill 1.0（引擎能力矩阵、TTS时间轴计算、降级流程）
- `references/storyboard-contract.md`：分镜交接协议 v1.0
- `scripts/auto_pipeline.py`：两阶段流水线（prepare: 文案→TTS→导演简报；render: 场景JSON→成片）
- 移除 `references/storyboard-director.md`（已拆分为上述三份）


## v2.1 (2026-10-17)

### 新增
- `move` 动画原语：`from_x/from_y` → `to_x/to_y` 位置插值，支持 `easing`。用于元素在画布上的位移（如直线→圆圈流动）。
  - engine.py: `timeline_state` 新增 `move` 分支
  - scene.schema.json: 动画 `type` 枚举新增 `move`，新增 `to_x`/`to_y` 字段
  - validate.py: `VALID_ANIMATIONS` 新增 `move`
  - tests: 新增 `test_move_interpolates_position`

### 修复
- 多动画叠加 bug：`pop`/`fade` 在 `t < start` 时会把 alpha 乘 0，导致一个节点挂多个动画时，未开始的动画会把已显示的元素藏起来。
  - 新增可选参数 `hide_before`（默认 `True`，保持原有入场行为）；脉冲/高亮类动画设为 `False` 则开始前不影响元素。
  - tests: 新增 `test_future_pulse_does_not_hide`

### Demo
- 新增 `demos/12jingang/`：《十二金刚》15.5s 实战（计数→变形→立字），含场景 JSON、生成脚本、自制素材、成片 MP4。

## v2.0 (2026-10-17)

- 通用场景树/布局引擎：任意行列数表格、横向流程、时间轴、卡片、箭头、文字、内置图标、本地 PNG/SVG 素材
- 动画原语：fade / slide / pop / draw，可叠加，支持 easing
- JSON Schema (Draft 2020-12) + 语义校验
- 6 项自动化测试，3 个样例渲染为 960×540、24 FPS MP4
