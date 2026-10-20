# MG Animation Skill 2.1

这是 2.0 的**可运行增强版**，保留所有通用布局能力，同时新增语音合成、实际合成语音的分句级时间对齐、字幕硬烧、音轨混流、自动镜头转场和证据核查门禁。

## 相对 2.0 的变化

| 功能 | 2.0 | 2.1 |
|---|---|---|
| 表格 | 任何行列数 | 保持兼容 |
| 声音 | 无 | 本地 eSpeak、可选 Edge TTS |
| 语音对齐 | 无 | 分句级精确时间戳；可选 WhisperX 字级对齐 |
| 字幕 | 无 | SRT 文件及自动烧录 |
| 事实检查 | 无 | 事实/来源覆盖与引文核验门禁；不冒称自动判断真伪 |
| 镜头转场 | 两场景直接叠加 | 自动 Crossfade / Wipe / Slide；相邻与重叠均可 |
| 视频音轨 | 无 | H.264 + AAC |

## 依赖

- Python ≥3.10，`pip install -r requirements.txt`
- **FFmpeg**（PATH 可见）
- **eSpeak**（离线 TTS 测试，可执行文件 `espeak`；普通发行版可通过系统包安装）
- 中文字体：Noto Sans CJK 等
- 可选：`pip install edge-tts`（网络可用、正式中文发音）；WhisperX 及语音模型（字级对齐）

## 快速演练

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/validate.py examples/two_scenes_with_voice.json
python scripts/narrate.py examples/two_scenes_with_voice.json --engine espeak --audio output/voice.wav --timings output/timings.json
python scripts/render.py examples/two_scenes_with_voice.json --audio output/voice.wav --timings output/timings.json --out output/final.mp4
ffprobe -v error -show_entries stream=codec_type,codec_name -of json output/final.mp4
```

演示视频用离线发音器生成的中文语音**很机械**，不代表 Skill 的最终配音质量。正式作品请优先测试 Edge TTS 或替换专业语音后端；切换后应重新提取音频时间戳。

## 自动化第一阶段：GitHub Actions 直接渲染 Pilot 001

现在有一条**真实渲染**而不是单纯跑单元测试的流程：[Pilot 001 自动渲染与制品交接说明](docs/PILOT_CI_AUTOMATION.md)。

当 Pilot 001 的场景/动画原语在 PR 中变更时，Actions 自动生成无声 H.264 MP4、关键帧、QA 联系表、带 SHA256 的媒体清单，以及给独立强模型使用的 `qa_review.zip`，并作为保留 30 天的 Artifact 上传。它也支持 Actions 页面的 `workflow_dispatch` 手动触发。

**尚未自动调用 Muse 或多模态审片模型**，未完成的人工 QA 决策始终为 pending；不自动审批或发布。

## Stage C 配音自动化试点（测试稿，不构成正式发布批准）

新增 [Stage C 真实离线配音与 GitHub CI 测试流程](docs/STAGEC_CI_PILOT.md)：同一个 Pilot 001 测试 PR 中，自动生成测试中文解说的 `voice.wav`、可验证的分句 `timings.json`、`timings.srt` 和带 AAC 音轨的 MP4 预览；另一路继续生成 Stage B 无声视频供可选的 **手动** Gemini R5 独立视觉审查。配音按实际动画事件时间固定对齐：B 先进入补货队列、A 后到达发货站。两类制品明确隔离、绑定源代码 SHA，**正式配音仍为 draft，R5 不自动认可 Stage C 有声版本**。

## R5 手动独立视觉 QA（可切换模型，防止重复计费）

[查看 R5 模型审核配置与安全说明](docs/R5_AUTOMATION.md)。**R5 已改为只有人工点选 GitHub Actions → R5 Independent Visual QA → Run workflow，并明确输入某个已成功的 Pilot PR 渲染 Run ID 才会调用 Gemini/OpenAI/DeepSeek。** `R5_ENABLED=true` 只是允许审核，不会因为 PR push 或 Stage C 自动构建而启动付费请求；关闭时也无法手动发出模型调用。R5 前置检查校验真实 GitHub Run、同仓库开放 PR 的最新 SHA、媒体制品和已有审核评论；每轮最多一次模型 API 请求，无自动重试。不自动合并、不批准正式发布。

Gemini 原生审核 Stage B 无声 MP4；OpenAI 和 DeepSeek 共用抽帧版 OpenAI Responses 客户端。Stage C 测试音频未因此完成独立视听 QA，正式音频与 Stage D 仍需单独审批。

## 所有 AI 模型的统一入口：AGENTS.md

无论由 ChatGPT、Claude、Gemini、Muse、DeepSeek 或 Codex 接手，请先阅读 **[AGENTS.md](AGENTS.md)**，选择 R0–R7 对应角色，再跳转至 [完整多模型操作手册](docs/MULTI_MODEL_PLAYBOOK.md)。该文件不是模型厂商专属指令；无法自动读取 AGENTS.md 的平台，需要明确发送“先读 AGENTS.md”或提供文件附件。

独立审片 R5 现在还可以使用 `workflow/qa_evidence.py` 按固定时间和重点事件时间生成连续抽样帧、联系表及 SHA256 索引，并通过 `workflow/role_pack.py qa --evidence-dir ...` 附入 QA ZIP。**自动抽帧不是自动审片**。

## 多模型协作完整操作手册（从零到交付）

**[打开完整操作手册：每个角色的提示词、命令和交接规则](docs/MULTI_MODEL_PLAYBOOK.md)**。

文档包含项目调度、事实研究、创意导演、技术总导演、Muse/DeepSeek 动画实施、
独立多模态视觉 QA、定点返工、人类发布审批共 8 个角色，
并使用 [Issue #4](https://github.com/huangyong7878/mg-animation-skill/issues/4) /
[PR #7](https://github.com/huangyong7878/mg-animation-skill/pull/7) 说明真实交接。
先阅读此手册，再从各角色 `roles/` 说明和 `workflow/` 命令进入详细实现。

## 强模型总导演与跨模型替换

不使用 ChatGPT 也可以继续本项目：从 [roles/README.md](roles/README.md) 开始，按角色包让任意支持结构化文件的强模型担任**总导演、独立视觉 QA 或返工监督**。执行模型仍可选 Muse / DeepSeek。

生成完全独立于模型 API 的任务包：

```bash
python workflow/role_pack.py director --brief path/to/brief.md --out work/portable/director_001
```

得到的 ZIP 含角色说明、现有视觉/导演规范、正式 JSON Schema 和输入材料。审片时使用 `qa` 子命令，必须提供真实视频；`role_pack.py` 不会自行观看影片或调用模型。

## MP4、关键帧与媒体存储协议

渲染产物不直接提交 Git：请阅读 [ADR 0001：媒体制品存储约定](docs/adr/0001-media-artifact-policy.md)。
源码、规格和测试留在 Git；真正的 MP4、帧图片及跟随构建的 `delivery.json`、`media_manifest.json` 存储为构建制品，绑定渲染时使用的源码 commit。临时预览可使用 GitHub Actions Artifacts（建议保留 30 天），长期成片应另行归档。

`workflow/media_manifest.py` 可生成并验证媒体 SHA256 清单；它**不负责上传**，需由真实构建/存储环节处理。

## 使用在其他 AI 工具中

将本文件夹作为 `mg-infographic-animation` Skill 加入 Codex、Claude Code、Cursor 或其他能读取项目文件的 AI 编程工具。阅读 `SKILL.md`，运行已知示例，再用 `references/ai-agent-prompt.md` 创建新的场景 JSON。各工具对 Skill 目录的要求不同，可直接让 AI 在此目录工作。

## 事实核验的范围说明

`factcheck.py` 可以校验：事实镜头必须关联声明；每条声明必须在研究代理/审核者核验后标记为 `verified`；必须有 URL 与证据引文；联网模式可以检查网页是否包含引文。**仅凭这些条件不能证明声明是真的**，特别是因果推断、统计口径、过时信息。严格制作流程需要使用联网研究工具逐条审核，必要时人工复核。本包不含在线研究 API 或凭空声称已经联网核查。

## 输出示例

- `examples/two_scenes_with_voice.json`：双镜头 + 自动擦除转场 + 语音配置
- `output/mg_v2_1_with_voice.mp4`：带 AAC 音轨、字幕和自动转场的真实样片
- `output/voice.wav` / `output/timings.json` / `output/timings.srt`：音频和配套时间轴
- `tests/`：原版 6 项及 2.1 新增 7 项测试

更多详细字段请看 `SKILL.md`、`references/scene-contract.md`。

## 一键流水线

```bash
python scripts/pipeline.py examples/two_scenes_with_voice.json --engine espeak --output-dir output/oneclick
```

会依次校验场景和引用证据、合成配音、测量句段时间、导出 SRT、生成带转场/字幕/音轨的 MP4。若希望进一步核验引用的在线存在性，追加 `--fetch-sources`（需要网络）。
