---
name: mg-infographic-animation-v2
version: 2.0.0
description: 将中文脚本、数据或分镜转成可编辑的 2D 复古信息图 MG 动画。通用场景树/布局引擎支持任意列数和行数的表格、横向流程、时间轴、卡片、箭头、文字、内置图标和本地 PNG/SVG 素材；AI 规划 JSON、程序确定性生成 PNG/MP4，并验证结果。适用于 AI 自动生成讲解动画、科普财经图解视频、或将固定 MG 模板改为可组合动画。
---

# MG Animation Skill 2.0 — 可组合信息图动画

## 使命与边界

用户提供文案、数据、主题或参考画面后，**你（AI Agent）负责构思动画结构和编写 JSON，已有引擎负责绘制与编码视频**。不要退回仅制作 PPT 截图的做法，也不要将固定 2×3 表格误称为通用渲染器。

此包包括经过验证的通用 **Python/Pillow + FFmpeg** 小型渲染引擎，不需要使用 AE。若项目已有 React，允许另行将 `scene.schema.json` 迁移到 Remotion，但本包**没有声称内置 Remotion 实现**。本包**没有内置 TTS、语音自动对齐、外部事实检查、自动分页或自动化视觉评分**；AI Agent 可以在此基础上继续开发。

## 首选工作步骤

1. 查看 `README.md` 和 `references/scene-contract.md`，读取 `examples/` 里的三个 JSON。
2. 确认用户需要的动画信息：标题、数据、镜头时长、画面比例、可用视觉资产。默认 16:9、960×540、24fps、复古纸张质感，无配音。
3. 将内容拆成**语义结构**：场景、文本、图标、表格、流程、时间轴、动画顺序。不要人为限制 2 列 × 3 行。
4. 选用组件并生成**版本为 `2.0` 的 JSON**。AI 不能把冗长随意生成的 Python 片段直接塞进场景 JSON；输出限定的节点和时间轴参数。
5. 先验证、渲染关键帧，再渲染 MP4：

```bash
python -m pip install -r requirements.txt
python scripts/validate.py examples/table_4x5.json
python scripts/render.py examples/table_4x5.json --time 4.7 --out output/check.png
python scripts/render.py examples/table_4x5.json --out output/table_4x5.mp4
```

6. 用图像逐帧检查：画面是否重叠、标签是否在格内、标题是否遮挡、长文字是否可读、是否与内容相符；失败时修改场景或时长后再渲染。对行列数多、内容多的表格，主动拆分成多镜头，不要强行缩字到不可读。
7. 交付 JSON、MP4、源代码或技能包和调整说明。给用户准确地说明哪些功能已实现，哪些仍需开发。

## V2 组件：任意组合，不设固定画面结构

**布局容器（负责计算子元素的几何位置）**：

- `absolute`：子元素使用相对于父容器的 `rect`（数值像素或百分比）。
- `row`：横向布局，`children` 任意数量，支持 `gap` 和 `weights`。
- `column`：纵向布局，`children` 任意数量。
- `grid`：均匀或加权网格，`columns` 为任意正整数，行数自动由 `children` 数计算。

**可绘制元素（负责视觉和时间轴）**：

- `text`：标题、说明、数字或标签；自动分行并按空间缩放字体。
- `card`：圆角卡片，可淡入、上移、弹出。
- `icon`：内置扁平矢量形状：`circle / square / diamond / triangle / star / bars`。
- `image`：加载与 JSON 同目录（或子目录）里的 PNG/JPG/WebP/SVG 本地素材。SVG 需要 `cairosvg` 可选依赖。
- `line`：端点由 `rect` 决定，支持线条绘制。
- `arrow`：横向箭头，适合置于 `row` 容器里。
- `table`：从 `columns` 和 `rows` 计算表格尺寸，**无需改代码即可支持不同列数、行数和列宽权重**；表头计为总行数的一行；单元格可为普通文本、`badge`、内置 `icon` 或本地 `image`。
- `timeline`：任意数量的时间节点和说明，自动计算节点中心。

**动画原语（可叠加到每个节点）**：

- `fade`：透明度 0→1。
- `slide`：偏移 `from_x/from_y` → 0。
- `pop`：缩放由 `from_scale` 经轻微过冲回到 1，并淡入。
- `draw`：将线/箭头长度由 0→100%。
- `move`：位置由 `from_x/from_y` 插值到 `to_x/to_y`（v2.1 新增，用于元素位移如直线→圆圈）。

每个动画都支持 `start`、`duration` 和 `easing`（`linear` / `out_cubic` / `in_out` / `out_back`）。**`start` 指当前镜头内的秒数**。`pop`/`fade` 支持可选 `hide_before`（默认 `true`）：设为 `false` 时，未开始的动画不隐藏元素，适合在已显示元素上做脉冲/高亮。容器的动画会追加到其各子节点的动画列表（子节点分别执行），如需整组以统一中心缩放，必须另行扩展引擎。

## 视觉语言：原视频风格的参考规则

- 配色：暖纸张 `#E7DED4`、炭灰 `#354047`、砖红 `#B75049`、金黄 `#AF8741`、浅米白 `#F4EEE5`。
- 背景：微弱固定颗粒纹理，**每帧相同**，避免雪花闪烁。
- 表格：细砖红边线，线条逐笔生成；图标或文本错时入场，不要全部一瞬间出现。
- 字体：优先 Noto Sans CJK/PingFang/微软雅黑，适度留白；禁止文字越框。
- 节奏：标题 0.5～0.8 秒、表格描线 0.5～1.0 秒、图标弹出 0.35～0.6 秒、单元格错峰 0.08～0.25 秒；镜头最后应留足 0.5～1 秒静止展示。
- 内容严谨：地图、数字、地名、比例与法律分类应查证，素材授权单独处理。不要把演示数据当事实。

## AI 分镜规划准则

- 选择**最符合信息结构**的镜头：对比→`table`，步骤→`row` + `card` + `arrow`，顺序/历史→`timeline`，结论→`text` + `icon` / `card`。
- AI 生成每个镜头的布局、数据、相对定位、开始时间及动画类别；程序进行几何计算和帧渲染。
- 全片如果有多个镜头，在 `scenes` 数组写 `start` 与 `duration`；重叠场景直接叠加绘制，不会自动生成专业镜头转场。
- 内容过多时由 AI 分镜器**拆成多个 scene**，而不是隐性假设表格滚动、自动分页。
- 优先 JSON Schema 校验；绝不忽略验证器报错。不要让 AI 生成未知组件或不存在的动画类型。
- 图形素材放进 `examples/` 同级目录，`image.asset` 路径始终相对于场景 JSON 文件所在目录，不能访问父目录或在线 URL。

## JSON 示例：同一个 `table` 渲染器，不同表格尺寸

2 列、总计 3 行（包含表头）：

```json
{
  "type": "table",
  "rect": {"x": "15%", "y": "29%", "w": "70%", "h": "53%"},
  "columns": ["指标", "结论"],
  "rows": [["A", "上升"], ["B", "平稳"]],
  "grid_start": 0.5,
  "cells_start": 1.2,
  "stagger": 0.18
}
```

4 列、总计 5 行：把 `columns` 改成 4 个标题，将 `rows` 设为 4 个、每行 4 个单元格，并适当调整 `rect`。**所有坐标和边框由渲染引擎自动计算**。完整有效示例：`examples/table_4x5.json`。

不是表格的流程/时间轴范例：`examples/flow_and_timeline.json`。

## 质量保障与交付检查

- [ ] `python scripts/validate.py <scene.json>` 成功，无不支持的节点或缺失数据。
- [ ] `python -m unittest discover -s tests -v` 通过。
- [ ] 至少预览首帧、中间关键帧、最后展示帧；中文字不溢出、图标没有遮挡。
- [ ] 同一帧重绘像素一致；背景纹理不随帧变化。
- [ ] 渲染的 MP4 确认帧数、分辨率、时长正确，文件可播放。
- [ ] 使用不同于参考 2×3 的表格，以及一种非表格场景验证可组合能力。

## 文件导航

- `README.md`：安装、运行、用户交付方法。
- `references/scene-contract.md`：字段、布局数学、限制与扩展规范。
- `references/scene.schema.json`：JSON Schema（Draft 2020-12）。
- `references/ai-agent-prompt.md`：直接复制给其他 AI 编程工具的提示词。
- `scripts/engine.py`：通用确定性布局 + 动画渲染引擎。
- `scripts/validate.py`：JSON Schema 和语义校验。
- `scripts/render.py`：导出单帧 PNG 或 MP4。
- `examples/`：2×3、4×5、非表格三套场景 + SVG 例子。
- `tests/`：核心布局、大小无关性、验证、确定性测试。
