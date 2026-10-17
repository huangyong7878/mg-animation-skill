# MG Infographic Animation Skill 2.0

AI 可编排的通用复古二维信息图动画。AI 负责把文案转换为受约束的 JSON 场景，Python 引擎负责布局和逐帧视频渲染。

> **v2.1 更新**：新增 `move` 动画原语（A→B 位置插值），修复多动画叠加时 `pop`/`fade` 误隐藏元素的 bug（新增 `hide_before` 参数）。详见 `CHANGELOG.md`。

## 和 1.0 的本质区别

| 项目 | 1.0 | 2.0 |
|---|---|---|
| 表格 | 固定 2 列 × 3 行 | `columns`、`rows` 数据驱动，任意数量，只受画布可读性限制 |
| 坐标 | 渲染程序固定数值 | 自动网格、绝对/相对坐标、横向纵向布局 |
| 画面类型 | 预设表格 | 表格、流程、时间轴、卡片、文字、线条、SVG/PNG |
| 动画 | 写死时间点 | JSON 里自定义动画的开始、时长、缓动 |
| 开发扩展 | 修改固定模板 | 增加节点/布局实现并扩展 Schema |
| 输出 | 固定样片 | 每个 JSON 均可渲染独立视频 |

## 依赖

- Python 3.10 及以上
- FFmpeg：必须在 PATH 中，运行 `ffmpeg -version` 可用
- `python -m pip install -r requirements.txt`
- 中文字体：优先 Noto Sans CJK、PingFang 或微软雅黑。自定义路径可设置 `canvas.font_path`。
- SVG 素材：可选 `pip install cairosvg`。不用 SVG 时不需要安装。

## 立即体验

在这个文件夹里运行：

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v

python scripts/validate.py examples/table_2x3.json
python scripts/render.py examples/table_2x3.json --out output/table_2x3.mp4
python scripts/render.py examples/table_4x5.json --out output/table_4x5.mp4
python scripts/render.py examples/flow_and_timeline.json --out output/flow_and_timeline.mp4

# 指定某一时刻，输出单帧 PNG
python scripts/render.py examples/table_4x5.json --time 4.6 --out output/check.png
```

你可以将**整个文件夹**放到其他 AI 支持读取 Skills 的目录（具体路径依工具而异），或直接让 AI 阅读 `SKILL.md` 并在此目录工作。

## 生成新的动画

1. 复制 `examples/table_4x5.json` → `my-scene.json`。
2. 更改 `canvas`、`scenes` 和 `elements`：要几列写几个 `columns`，要几行写几组 `rows`。
3. 运行 `python scripts/validate.py my-scene.json`。
4. 运行 `python scripts/render.py my-scene.json --out output/my-scene.mp4`。

参见 `references/ai-agent-prompt.md` 让 AI 自动完成步骤 1～4。

## 实战 Demo

`demos/12jingang/` — 《十二金刚》15.5 秒动画：12 人排队 → 正向/逆向计数 → 流动成圆圈 → 圆心升起"12金刚"。非表格场景，演示 `move` 原语和多 scene 衔接。详见该目录 README。

## 已验证 VS 未实现

**已实现**：任意行列数表格、自适应表格分格、`absolute/row/column/grid`、字体包裹与缩小、文字/卡片/图标/本地图片/箭头/线条/时间轴、进入/缩放/淡入/画线/**位移**动画、固定纸纹、结构校验、MP4 渲染、单帧预览、基本测试（8 项）。

**未实现**：自动在超大表格分页、音频与字幕同步、AI 模型调用、AE/Remotion 完整迁移、复杂矢量路径变形、专业镜头转场。Skill 指导 AI 生成 JSON，但**不包含自动调用 GPT 的服务或 API Key**。

## 许可与安全

本 Skill 的示例用虚构/示意数据。地图、品牌等外部素材需额外确认准确性、授权及使用条件。只接受本地 `asset` 路径，禁止从场景 JSON 任意执行 Python/JS 代码。
