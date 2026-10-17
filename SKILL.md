---
name: mg-infographic-animation
version: 2.1.0
description: 将文字脚本和结构化资料制作成复古信息图 MG 动画；支持任意行列数表格、流程图和时间轴、程序化关键帧、相邻/重叠镜头自动转场、TTS 配音、按实际合成语音分句对齐、SRT 字幕、可选 WhisperX 强制对齐、事实证据门禁和 MP4 输出。适用于希望用 AI 编程工具批量生成解释型动画的工作流。
---

# MG Animation Skill 2.1 — 有声、可编排、可审核的信息图动画

## 使用原则

本技能以 **AI 导演 + JSON 场景描述 + 确定性 Python 渲染** 为核心。优先复用本包中的工具，而不是每条视频都写死表格坐标或重写渲染程序。

**真实能力边界：**
- 已实现：离线 `eSpeak` TTS、可选 `edge-tts` 在线语音、每个独立合成语句的**实际音频时长对齐**、SRT 字幕、音轨混合、字幕硬烧、`crossfade/wipe_left/slide_left` 自动转场、引用/证据门禁。
- 可选但需另外安装且需要运行模型：`WhisperX` 逐字/字级强制对齐（`scripts/align.py`）；质量随语言和模型而异。
- **没有声称完全自动事实核实**：`scripts/factcheck.py` 验证声明覆盖、人工/研究代理标记状态、来源 URL、证据摘录格式；`--fetch-sources` 还可检查网页上是否真的出现指定原文。它**不能**仅凭匹配文字判定一个事实为真，也无法检查来源是否可靠或是否曲解。事实性内容必须由 AI 研究代理用真实资料核实，并让人审核重要结论。
- AI 从文案自动分镜仍由**调用本技能的 AI Agent** 完成；本包不包含自动调用 OpenAI/Claude 的 API Key 或云端后台。

## 首选工作流（Agent 应按顺序执行）

1. **拆解文案**：区分可展示的图形与事实性陈述。表格比较用 `table`，步骤流程用 `row/arrow/card`，历史演变用 `timeline`，数字结论用 `text/card`。
2. **事实研究**：事实性镜头设置 `factual:true`，添加 `claim_ids` 和顶层 `claims`，为每条 `verified` 声明保存至少一条**真实、可核验**的来源 URL 和原文摘录。不要编造来源、摘录或验证状态。涉及重要事实时必须有人工或可靠研究代理确认。
3. **生成 JSON**：版本为 `2.1`，在 `canvas` 定义总时长、帧率和默认转场；`scenes` 列表定义镜头结构和持续时间；`narration.segments` 给出中文配音与镜头锚点。每个镜头都可以有任意数量的元素，不要把表格固定成 2×3。
4. **运行校验**：`python scripts/validate.py examples/two_scenes_with_voice.json`；如果包含事实性陈述，运行 `python scripts/factcheck.py your.json --fetch-sources`，修复报错。无法验证的内容应标为“未经核实”并禁止发布，不能偷偷更改为 `verified`。
5. **合成语音**：运行 `scripts/narrate.py` 生成音频、精确分句时间 JSON、SRT。中文正式版优先选择 `--engine edge`；eSpeak 不需要云服务但中文机械，有些系统不完整支持中文词典。
6. **检查时间轴**：语音长度超出视频总时长时，**延长镜头或缩短脚本**；不要直接裁断结尾。分句时间来自实际音频采样，不是按字数猜测；若需单字卡点，再运行可选 WhisperX 对齐并人工抽查。
7. **渲染并验收**：用 `render.py` 混合音轨、绘制字幕、自动转场；检查分镜边界前后各数帧、朗读与字幕一致性、事实引用、文字越框、源媒体版权。
8. **交付**：MP4、场景 JSON、WAV、timings.json、SRT、来源审查报告和可执行源代码。

## 直接运行（在 Skill 文件夹根目录）

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/validate.py examples/two_scenes_with_voice.json

# 不联网的演示语音：eSpeak（中文音质较机械）
python scripts/narrate.py examples/two_scenes_with_voice.json \
  --engine espeak --audio output/voice.wav --timings output/timings.json

# 自动场景转场 + 配音 + 同步的字幕硬烧 + H.264/AAC
python scripts/render.py examples/two_scenes_with_voice.json \
  --audio output/voice.wav --timings output/timings.json \
  --out output/final.mp4

# 可选高质量在线 TTS，需要网络并安装 edge-tts
python -m pip install edge-tts
python scripts/narrate.py examples/two_scenes_with_voice.json \
  --engine edge --voice zh-CN-XiaoxiaoNeural \
  --audio output/voice.wav --timings output/timings.json

# 如需额外验证文字引用可以真的从网页读取（要求联网）
python scripts/factcheck.py your_project.json --fetch-sources --report output/facts.json

# 可选字级强制对齐，需要另行安装 WhisperX、相应语音模型及其依赖
python scripts/align.py --audio output/voice.wav --timings output/timings.json --out output/aligned.json
```

## `2.1` JSON 新增字段

```json
{
  "version": "2.1",
  "canvas": {
    "width": 960, "height": 540, "fps": 24, "duration": 13,
    "default_transition": {"type": "crossfade", "duration": 0.7}
  },
  "scenes": [
    {"id": "intro", "start": 0, "duration": 6.5, "factual": false, "elements": []},
    {"id": "detail", "start": 6.5, "duration": 6.5,
     "transition_in": {"type": "wipe_left", "duration": 1.0}, "elements": []}
  ],
  "narration": {
    "segments": [
      {"id": "a", "scene_index": 0, "offset": 0.5, "text": "这是第一段解说。"},
      {"id": "b", "scene_index": 1, "offset": 0.8, "text": "这是第二段解说。"}
    ]
  },
  "claims": []
}
```

### 自动转场规则

- **镜头首尾相接**（`next.start == prev.start+prev.duration`）时，转场自动以剪辑点为中心占用前后各一半时长，画面不再直接硬切。
- **显式重叠**（`next.start < prev.end`）时，用完整重叠区间进行转场，不再粗暴地将两个场景叠加成一张。
- **镜头之间有空白**时，显示底纸背景，不凭空创造转场；需要 AI 导演补齐时间轴或明确留白。对于特别短的镜头，自动限制转场时长。
- 每个镜头 `transition_in` 可覆盖画布默认设置：`crossfade` 交叉淡化、`wipe_left` 左向揭示、`slide_left` 水平推入、`cut` 硬切。
- 重叠多个镜头的复杂多路复合不是本版能力，AI 应避免连续转场互相覆盖。

### TTS 与时间轴规则

- `narration.segments[*].scene_index` 是所属镜头的索引；`offset` 是从该镜头 `start` 开始的秒数；也可以用绝对 `start`。
- 合成模块单独制作每段语音，读取 WAV 真正的采样数，插入必要静音，然后写出起止时间。语音不能彼此重叠；碰到重叠会报错。
- `output/timings.json` 的 `alignment` 是 `synthesized_segment_exact`，**只保证句段级别**；不是字级强制对齐，不应作为卡拉 OK 逐字高亮依据。
- `scripts/render.py --timings` 负责按实际时间显示完整句段字幕，`--audio` 负责混流输出 MP4。

### 事实与证据规则

事实性镜头：

```json
{
  "factual": true,
  "claim_ids": ["claim_001"]
}
```

顶层声明：

```json
{
  "claims": [
    {
      "id": "claim_001",
      "statement": "需要独立核验的一个具体事实",
      "status": "unverified",
      "evidence": []
    }
  ]
}
```

未核实时故意使用 `unverified` 会让验证失败，这正是**阻止错误事实被直接做成视频**的目的。只有找到真实来源、记录证据并完成审核后，才可改为 `verified`。URL、摘录必须真实；自动抓取确认原文存在**不代表语义正确**，也不能消除过时数据问题。建议将来源与核验日期留在项目元数据中。

## V2 继续支持的所有组件

`absolute/row/column/grid` 布局；`text/card/icon/image/line/arrow/table/timeline` 元素；`fade/slide/pop/draw/move` 动画；统一纸纹、字体、尺寸与每个组件的入场时间。读取 `references/scene-contract.md` 和 `references/scene.schema.json` 获取完整规范。所有旧版 `version: "2.0"` 场景仍按旧规则渲染，不会被静默更改。

## 验收清单

- [ ] `python -m unittest discover -s tests -v` 通过（包括原版的任意行列数测试）。
- [ ] 任意 4×5 表格与非表格场景都能正常渲染，旧版场景兼容。
- [ ] 转场首、中、尾帧检查，不发生意外黑屏或双重叠加；镜头设计不出现三镜头交叉。
- [ ] 音频时长不超过总片长，字幕与对应语句的开始/结束时间一致。
- [ ] 事实场景的每个 `claim_id` 均有真实证据，证据失效或逻辑不匹配时停止交付。
- [ ] 使用第三方图像、字体和音频之前检查使用授权；不能编造第三方版权许可。

## 文件导航

- `README.md`：安装与一键验证指令。
- `scripts/engine.py`：布局、动画、场景全帧渲染。
- `scripts/transitions.py`：镜头转场窗口和画面混合。
- `scripts/narrate.py`：离线/在线 TTS，分句精确对齐，WAV/SRT。
- `scripts/align.py`：可选 WhisperX 强制对齐。
- `scripts/factcheck.py`：证据与事实审查门禁。
- `scripts/render.py`：最终字幕绘制、音视频 MP4 合成。
- `references/ai-agent-prompt.md`：复制到其他 AI 编程工具的提示词。
- `references/fact-research-protocol.md`：事实研究的工作规范。
- `examples/two_scenes_with_voice.json`：带转场与旁白的两镜头示例。

### 一键执行入口（推荐 Agent 优先使用）

```bash
# 完整执行“场景校验 → 引用门禁 → TTS → 分句时间/SRT → 转场/字幕/音视频渲染”
python scripts/pipeline.py examples/two_scenes_with_voice.json --engine espeak --output-dir output/oneclick

# 正式中文作品（需要 edge-tts 依赖及网络）
python scripts/pipeline.py your_project.json --engine edge --voice zh-CN-XiaoxiaoNeural --output-dir output/release --fetch-sources
```

注意 `--fetch-sources` 会对来源 URL 做在线引文检查（验证失败即中断），不是自动判断真假。每次选择新的 TTS 后需重新生成 timings，勿复用其他音频的句段时间。
