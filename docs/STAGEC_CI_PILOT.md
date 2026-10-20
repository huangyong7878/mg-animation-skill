# Pilot 001 — Stage C 离线有声预览、视觉事件对齐验证

## 范围

本 PR 产生真实 Stage C **测试**配音与有声 MP4，并行运行原有的 Stage B 无声视频渲染。
依然保持导演规格 approval=draft、narration=draft；不自动批准、锁定配音，也不进入 Stage D 正式发布。

## 修复：两张订单的旁白应跟随画面，而非按文案顺序立即播完

历史制品 run `39386781102` 的实际时间轴为：

| ID | 旧音频时间 | 画面实际事件 |
|---|---|---|
| intro | 0.000–2.8585 s | 两张订单从 1–1.8 s 陆续出现 |
| in_stock（A） | 3.2585–7.6906 s | A 7.2 s 抵达拣货站、10.0 s 抵达发货站 |
| out_of_stock（B） | 8.0906–12.1235 s | B 8.4 s 到达待补货队列 |

原先的 `scripts/narrate.py` 会依照 `segments` 数组顺序合成，除非显式填写
`start`；旧测试只验证音频时长、字幕、A/V 编解码器，没有核对画面事件与台词对应关系。
这会导致“先说 A 发货、后说 B 缺货”，而画面结局是 B 先抵达队列、A 后完成发货。

现在 Stage C 专用 `stagec_narration.json` 的朗读顺序改为
**intro → out_of_stock（B 缺货）→ in_stock（A 发货）**。
三段均有显式的 `start`：

- intro：0.0 s
- B 缺货：**5.9 s**（5.8 s 开始分支，8.4 s 抵达待补货队列）
- A 发货：**9.55 s**（10.0 s 抵达发货站，10.4–11.2 s 显示已发货标记）

由于测试使用系统 eSpeak，实际结束时间以 GitHub Artifact 的 `timings.json` 为准。
为留出空间，示例句子缩短为“库存不足，订单B等待补货。”及
“库存充足，订单A发货。”。其机械发音只是 CI 测试数据，不代表正式配音质量。

`scripts/primitives/orderflow.py` 将真实运动关键帧导出为
`PILOT_EVENT_SECONDS`（5.8 / 8.4 / 10.0 s）。`workflow/build_stagec_artifact.py`
的 `CUE_WINDOWS` 由这些关键帧推导，强制检查：

1. segment IDs 的顺序必须是 intro → B → A，文字里的“库存不足/订单B”、“库存充足/订单A”必须和 ID 一致。
2. `start` 必须明确写出，而且落在对应动画事件窗口。
3. 合成之后实际 `timings.json` 的起点必须和计划吻合，结尾不能超出该事件窗口或 13 s 视频长度。
4. 继续核查 WAV PCM 时长、字幕文本、H.264/AAC、视频帧数、Sha256 清单。

无论技术测试有多少项通过，仍然**不保证 TTS 人声自然，也不保证每一个音素与画面精确对齐**；这里只验证已定义的 Pilot 事件对应关系。

## 防止再次发生：R3 ↔ R4 两层机器可检验的交接

**R3 总导演 / 技术规格负责人** 增加独立的
`work/orders_pilot/stagec_av_cues.json` **草稿音画提示契约**。
它描述每段解说的 `segment_id` 对应哪个动画事件、起始允许偏移、
最后结束期限、必须提及的对象与期望画面。
结构约束位于 `contracts/av_sync_cues.schema.json`。
R3 应在分镜审查时明确审核这个契约；当前契约仍是 `draft`，
绝不代替人的批准或正式配音锁定。

**R4 实现工程师** 要从动画程序的真实时间事件表
`PILOT_EVENT_SECONDS` 中读取事件位置（包括 A/B 出现、
5.8 s 分流、8.4 s B 抵达队列、10.0 s A 抵达发货）。
通用门禁 `workflow/av_sync_contract.py` 在调用 TTS **之前**
验证文案/事件 ID/起始偏移与导演契约一一对应；在生成语音**之后**
使用实际 `timings.json` 核查每段准确开始、结束和无重叠。

每次 Stage C Artifact 新增 `av_sync_report.json`，
绑定源代码提交及 `media_manifest.json` 的 SHA256。
报告使用 `result=mechanical_pass`，
并明确 `verified_video_pixels=false`、
`verified_spoken_audio_semantics=false`、
`independent_audiovisual_review=false`。
**不要把这个通过结果称作“R5 已观看视频、听懂音轨并验收通过”。**

**R5 视听 QA** 仍应在未来 Stage D 的手动审核流程里
独立获取完整有声 MP4、锁定的台词/时间轴、以及契约，
逐段听读/看画面并给出可核对的发现与问题时间戳。
目前的 R5 Gemini Workflow 只能为 Stage B 无声视频做视觉 QA。
在真正实现并独立验证 Stage D 视听审查之前，不得自动将 Stage C
机械门禁通过升格为音画质量 PASS。

## Actions 产出

GitHub Actions 的 **Stage C Pilot Narration and AV Draft** 在无 Secrets 的 PR Runner 上调用离线 eSpeak 和 FFmpeg。Artifact 里包含：

- `media/voice.wav`
- `media/timings.json` 和 `media/timings.srt`
- `media/stagec_av_preview.mp4`（13 秒、960×540、24 FPS、有 AAC 音轨）
- `delivery.json`（stage=C、status=prototype）、`director_spec.json`、
  `media_manifest.json`、`av_sync_report.json`、`build_log.txt` 和源输入文件

**Pilot 001 Render and QA Artifact** 是另一条独立的真实 Stage B 无声视频构建，
输出带 SHA256 的视频、关键帧及证据。两种制品不可混为同一个“已审片成片”。

## Gemini R5（PR #15 已将模型调用改为仅手动运行）

普通 PR push、Stage B / Stage C 构建、或单独设置 `R5_ENABLED=true`
**均不会自动触发 Gemini**。只在需要视觉审片时：

1. 确认已经在 `main` 部署 PR #15 的 R5 手动版；
2. 仓库 Repository variables 设 `R5_ENABLED=true`、`R5_PROVIDER=gemini`，
   `R5_MODEL` 为支持原生 MP4 视觉理解的有效 Gemini 模型；
   Repository secret 设置 `GEMINI_API_KEY`；
3. 从成功的 **Pilot 001 Render and QA Artifact**（事件是 pull_request、
   来源为尚在 Open 状态的 PR 最新 SHA）复制 Run ID；
4. Actions → **R5 Independent Visual QA** → Run workflow，
   选择 `main`，填一次 `render_run_id`，人工运行；
5. 检查实际的 `qa_report.json`、`r5_audit.json` 和 PR 评论；
   R5 只审核 Stage B 的视觉，不审核 Stage C 的中文配音准确性或音画同步。

详情见 [R5 自动审核安全指南](R5_AUTOMATION.md)。不需要为了付费审片向 PR
反复提交空改动；避免浪费 GitHub Actions 和 Gemini 资源。

## 本地测试

```bash
python -m pip install -r requirements.txt
# Ubuntu: sudo apt-get install -y espeak ffmpeg fonts-noto-cjk
python -m unittest tests.test_stagec_ci_build -v
```

完整 GitHub CI 会在精确 PR 源 SHA 上生成音频和 MP4，运行
`python workflow/media_manifest.py verify ...` 校验制品来源和字节哈希。
