# Scene Contract v2

这是 AI 与视频引擎之间的结构化协议。完整机器约束请看 `scene.schema.json`。

## 结构

```json
{
  "version": "2.0",
  "canvas": {"width": 960, "height": 540, "fps": 24, "duration": 4.0, "grain_seed": 47},
  "theme": {"paper": "#E7DED4", "ink": "#354047", "red": "#B75049"},
  "scenes": [{"start": 0, "duration": 4.0, "elements": []}]
}
```

元素分为容器与可绘制节点。所有根节点可设 `rect`（`x/y/w/h`），绝对数字代表画布像素；`"15%"` 这样的百分比代表父元素的比例。例如根节点 `rect:{"x":"10%","w":"80%"}` 会从画面 10% 位置开始，占画面 80% 的宽度。每个镜头使用同一坐标空间。

### 通用布局

- `absolute`：`children[*].rect` 相对于此容器；
- `row`：`children` 横向依次排列，间距 `gap`，可用 `weights` 指定每项比例；
- `column`：纵向同上；
- `grid`：`columns` 为正整数，行数 `ceil(children.length / columns)`，可设 `column_weights` / `row_weights`。

`row/column/grid` 内的子节点尺寸由布局器提供，子节点的 `rect` 在这些容器下不参与重新布局。`absolute` 内的 `rect` 则会生效。布局器按照父元素宽高和子项权重计算；不会默认为 2×3。

### 表格节点

```json
{
 "type":"table",
 "rect":{"x":"7%","y":"25%","w":"86%","h":"60%"},
 "columns":["第一列","第二列","第三列"],
 "rows":[
   ["行1A",{"type":"badge","text":"行1B"},"行1C"],
   ["行2A",{"type":"icon","symbol":"star"},"行2C"]
 ],
 "column_weights":[1,1.3,1],
 "header_ratio":0.8,
 "grid_start":0.4,"grid_duration":0.7,
 "cells_start":1.0,"cell_duration":0.35,"stagger":0.18,
 "order":"row",
 "style":{"stroke":"$red","stroke_width":2,"font_size":24}
}
```

列数 `c = columns.length`；数据行数 `r = rows.length`；渲染总行数 `r+1`，**加上表头**。`rows` 内每一行必须恰好有 `c` 个单元格。可选 `order:"row"` 或 `order:"column"` 控制错时进入顺序。`column_weights` 为正数，每列宽度：`available_width × weight / total_weight`；缺省均分。表格宽高完全来自 `rect`，行高按 `header_ratio` 归一化分配。格子位置不依赖任何特定行列数。

单元格可为字符串、数字或以下对象：

- `{"type":"text","text":"说明"}`
- `{"type":"badge","text":"重点","style":{"fill":"$gold"}}`
- `{"type":"icon","symbol":"triangle","style":{"fill":"$red"}}`
- `{"type":"image","asset":"badge_icon.svg"}`

### 图形元素

- `text`: `text` + `style.size`/`min_size`/`max_lines`/`color`/`align`。
- `card`: `text` + `style.fill`/`stroke`/`stroke_width`/`radius` 等。
- `image`: `asset` 指向与输入 JSON 同目录下的本地图片；PNG/JPG/WebP，SVG 可选 CairoSVG。
- `icon`: `symbol`：`circle`（默认）、`diamond`、`triangle`、`square`、`bars`、`star`。
- `line`: `rect.x/y` 为起点、`rect.x+w/y+h` 为终点，`draw` 控制可见线长。
- `arrow`: 基于当前 `rect` 画横向箭头；可置于 `row` 的中间节点。
- `timeline`: `items:[{"label":"2010","detail":"开始"},...]`、`line_start/line_duration/items_start/stagger`；节点等距。

### 动画

```json
"animations": [
  {"type":"fade", "start":0.2,"duration":0.5},
  {"type":"slide", "start":0.2,"duration":0.55,"from_y":-16},
  {"type":"pop", "start":0.9,"duration":0.55,"from_scale":0.65},
  {"type":"draw", "start":1.1,"duration":0.7}
]
```

进度 `p = clip((t-start)/duration, 0, 1)`；`fade` 是 alpha=p；`slide` 是偏移=(from_x,from_y)×(1-p)；`pop` 采用 out-back 过冲缓动；`draw` 线条长度为 p（经缓动）。同一元素的动画结果叠加。`t` 是本 scene 的相对秒数。不同场景按 `scene.start` 在时间线上播放。

### 视觉与边界

- 纸张纹理由固定 seed 生成，同一帧同一输入视觉一致。
- `font_path` 可指定自定义中文字体；优先安装 Noto Sans CJK。
- 极长文字可能仍然不合适。布局引擎做换行和缩小字体，但**不自动分页、不自动避让任何层叠元素**。需要 AI 主动拆镜头。
- `start+duration` 不得超过 `canvas.duration`。
- SVG 支持取决于可选依赖 `cairosvg` 是否安装。
- 本机目录以外的相对路径（例如 `../../private.png`）会被拒绝；文件资产不从网络加载。
- 默认视频没有背景音乐、配音、字幕。不应冒称和用户音轨做过对齐。

---

## 2.1 增量协议（旧版 2.0 JSON 继续兼容）

- 根字段 `version` 支持 `"2.1"`；旧版 `"2.0"` 仍按历史直接合成模式运行。
- `canvas.default_transition: {"type":"crossfade|wipe_left|slide_left|cut", "duration":0.7}`：镜头默认转场。
- `scenes[n].transition_in`：覆盖镜头进入方式；连续时间轴的转场以相邻边界为中心分配时长，显式重叠的转场直接使用重叠区间。
- `scenes[n].factual` 和 `scenes[n].claim_ids`：事实镜头绑定经过研究的声明 ID；顶层 `claims` 定义声明、状态和来源/引文。
- `narration.segments`：分句文本、`start` 或 `scene_index` + `offset`、`pause_after`。调用 `scripts/narrate.py` 根据合成音频采样确定真实分句起止；WhisperX 可选字级对齐。
- `scripts/render.py --audio output/voice.wav --timings output/timings.json`：完成 H.264/AAC 混流并按秒数烧录分句字幕。
- `--fetch-sources` 对网页引文逐字存在性检查不等同于语义事实核验；数据日期、证据关联仍需研究代理或人工判断。
