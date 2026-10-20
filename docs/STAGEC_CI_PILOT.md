# Pilot 001：Stage C 离线配音及完整自动化联调

## 状态与范围

此项目最初的 Pilot 001 无声 Stage B 渲染工作流已存在，
R5 独立视觉审核已接通 Gemini/OpenAI/DeepSeek API（由仓库变量控制）。
本 PR 新增 **Stage C 工程样例**，用测试文案、eSpeak 和 FFmpeg
真实生成音频、句级时间轴、字幕及 AV 预览，**不要求模型 API Key**。

**Stage C 绝不代表配音正式锁定或 Stage D 发布通过**。导演规格
\`examples/workflow_orders_spec.json\` 的 \`approval.status=draft\`、
\`narration.status=draft\` 未被改变；测试朗读的声音机械且不代表正式中文配音质量。

## 两条独立的 Actions 生产线

当这个测试 PR 改动 \`work/orders_pilot/stagec_narration.json\` 等 Stage C 输入：

1. **Stage C Pilot Narration and AV Draft**：使用无密钥的 PR runner，在精确源码 SHA
   上执行 \`workflow/build_stagec_artifact.py\`；使用本地 \`espeak\`、
   \`scripts/narrate.py\` 和 \`scripts/render.py\` 创建真实媒体，
   检查 WAV PCM 时长、非重叠句级时间轴、SRT 文字、
   H.264 视频 + AAC 音轨、13 秒 / 960×540 / 312 帧；
   生成 \`delivery.json\`（stage=C、status=prototype）和 SHA256 清单，
   上传保留 30 天的 GitHub Artifact。
2. **Pilot 001 Render and QA Artifact**：为了和 R5 实际审片联调，
   同一个 PR 还会独立重新渲染原来的 **Stage B 无声视频**。
   它生成源代码版本绑定的 \`media_manifest.json\`、真实 MP4、
   重点抽帧和供强模型审查的输入。

Stage C 和 Stage B 的制品各有独立 Artifact，不混淆阶段：
\`mg-orders-stagec-draft-<run>-<sha>\` vs
\`mg-orders_two_routes-r1-ci-<run>-<sha>\`。

> 为什么 R5 不是直接对 Stage C 的预览给 \`pass\`？
>
> 当前的 \`workflow/r5_review.py\` 明确只接收 \`delivery.stage=B\`，
> 处理 **视觉** 检查。Stage C 的 WAV、句级时间戳和字幕属于独立机械校验。
> Gemini 的原生视频视觉理解不等于正式的音轨理解、音画同步或配音质量 QA。
> 未扩展独立视听审查 Contract 之前，不应把测试音轨称为 Stage D 发布通过。

## 设置：这一次使用 Gemini 作为 R5

GitHub 仓库 → **Settings → Secrets and variables → Actions**，使用 **Repository** 级别：

| 类型 | 名称 | 值 |
|---|---|---|
| Repository variable | \`R5_PROVIDER\` | \`gemini\` |
| Repository variable | \`R5_MODEL\` | 与你的 Gemini API 账户兼容、支持视频理解的模型名（例 \`gemini-2.5-flash\`） |
| Repository secret | \`GEMINI_API_KEY\` | 你的真实 Gemini API Key（不要写进 PR） |
| Repository variable | \`R5_ENABLED\` | 默认 \`false\`；准备真正调用 Gemini 时改成 **\`true\`** |

**开关只影响后续 R5 触发**，不会取消已在运行的付费请求。
不要因为工作流成功就宣称 Gemini 已审片；确认 **R5 Independent Visual QA**
有真实已完成的 API 作业和独立 \`qa_report.json\`，才算联调真正打通。

为第一次付费联调，建议：

1. 提交当前 Stage C 测试 PR，确认两个无密钥渲染工作流均为 Success、
   能从 Actions Artifact 下载真实的 MP4、WAV、timings 与 manifest。
2. 再把 \`R5_PROVIDER=gemini\`、\`R5_MODEL=<已支持的视频模型>\`、
   \`GEMINI_API_KEY\` 核实好，并把 \`R5_ENABLED\` 改为 \`true\`。
3. **向同一个开放测试 PR 再提交一个影响 Pilot 渲染输入的正常变更**，
   让 \`Pilot 001 Render and QA Artifact\` 在开关打开以后启动新的 PR Run。
   （手动 \`workflow_dispatch\` 的 Run **不会**触发当前 R5，因为 R5
   安全门禁只允许上游事件是 \`pull_request\`。）
4. 等待上游无声视频构建成功，再核对
   **R5 Independent Visual QA → R5 审查 Artifact → PR Conversation 评论**；
   记录实际 Token、媒体时间戳证据及 \`pass\` / \`rework\` / \`pending\`。
5. 再把 \`R5_ENABLED\` 设回 \`false\`，可暂停后续付费模型调用。

注意：当前 R5 只能在 Stage B 的 PR 源提交做独立视觉审核；
即使 R5 模型输出 \`pass\`，Stage C 配音验收及最终人工发布审批仍是独立步骤。
保持 R4 与 R5 不同角色/上下文，且**永远不自动合并 PR**。

## 本地运行 Stage C（可选）

~~~bash
python -m pip install -r requirements.txt
# Ubuntu: sudo apt-get install espeak ffmpeg fonts-noto-cjk
SOURCE_SHA="$(git rev-parse HEAD)"
python workflow/build_stagec_artifact.py \
  --source-sha "$SOURCE_SHA" \
  --artifact-root /tmp/mg-stagec-check \
  --artifact-name mg-local-test \
  --run-url https://github.com/huangyong7878/mg-animation-skill/actions/runs/1
python workflow/media_manifest.py verify \
  --manifest /tmp/mg-stagec-check/media_manifest.json \
  --artifact-root /tmp/mg-stagec-check \
  --spec /tmp/mg-stagec-check/director_spec.json \
  --delivery /tmp/mg-stagec-check/delivery.json
~~~

查看下载制品的 \`media/stagec_av_preview.mp4\` 与
\`media/voice.wav\`，确认读音、字幕节奏、内容是否合理。
如果不满意，修改 \`work/orders_pilot/stagec_narration.json\`，重新构建并审查；
**不要直接把测试文案升级为锁定配音**。

## 安全与自动化边界

- Stage C PR 构建使用 \`contents: read\`、\`persist-credentials: false\`，
  不读取 Gemini / DeepSeek / OpenAI API 密钥，也不自动发 PR 评论。
- 单个触发 PR 的 Stage C 制品和 Stage B 无声制品都绑定**各自精确源码 SHA**。
- Stage C 只能使用内置离线 eSpeak；不会自行调用 Fish Audio、Edge TTS 或 Gemini。
- 音频/时间轴的机器校验不能证明语音自然、台词已经导演批准或严格音画匹配。
- R5 \`workflow_run\` 仍从可信 \`main\` 分支执行，
  仅读取带 SHA256 约束的无声视频 Artifact、评论当前 PR HEAD，
  不执行上游产物代码、不合并/发布。
