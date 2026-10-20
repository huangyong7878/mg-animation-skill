# Stage D 正式有声成片：R3/R4 锁定、独立 R5 审核、R7 人类发布

> **状态：实现了 Stage D Pilot 001 的离线构建器和阻断式发布交接。**
> **当前仓库中的 director_spec、旁白、音画契约仍为 draft / test_only。**
> 因此不能用原 Stage C 样片假冒 Stage D 的已批准成片。
> 本文件没有给予任何 AI 或 Actions 人类审批权。

## 1. 生产阶段必须前移的两个锁

**这是两条正式生产门禁，不只是 R4 制片完成后的交付手续。**

1. **R2 → R3 → 人类 Script Lock**：R2 确定准确解说句子、叙事顺序；
   R3 将其与正式 storyboard、导演镜头规格、音画事件契约一一对应。
   人类在**正式配音和 R4 开始前**核对并签发
   `script_lock.json`（`contracts/script_lock.schema.json`）。
   包含 script/plan/cues/storyboard 原始字节 SHA256、
   不受后续音轨变化影响的导演分镜指纹、规格 revision、
   人类审批人和时间。用户只确定了三句话，
   **不代表已经正式批准分镜**；不能由 AI 自签。
2. **试听 → 人类 Voice Lock**：基于已锁定文案制作可反复试听的语音候选，
   获得用户明确“这版声音/语速/停顿可用”的决定后，
   由人签发 `voice_lock.json`（`contracts/voice_lock.schema.json`），
   绑定前一份 Script Lock、选中的 voice_id/style、真正 WAV 及
   measured timings 的原始字节 SHA256。**试听选 XiaoxiaoNeural
   只代表声音方向，不是试听后的 Voice Lock 批准。**
3. **R0 正式派单前检查两份锁**；没有锁时只允许明确的 Stage B/C
   原型／测试，而不能称为已进入正式 R4。之后 R4/Stage D
   只能使用锁定内容，不得临时改解说稿。
4. **R5 / R7**：Stage D 有声成片制作后独立审阅完整画面和音轨，
   再进行完整 QA 与 R7 最终发布批准。前两个锁不替代质量审核。

现有导演 Schema 要求 `approval=approved` 时
`narration=locked`。因此正式文件中的 director_spec 最终在
**Voice Lock 获准后**更新为双 approved/locked；
早期 **Script Lock** 单独锁定导演分镜指纹，避免因后面
填写音频 SHA 而造成导演版本哈希循环依赖。

本次 Pilot 候选内容在
`work/orders_pilot/script_candidate.txt` 和
`work/orders_pilot/storyboard_candidate.md`。
两者不是已批准文件；原 Stage C 的 `test_only=true` 不变。

### 标准生产的 CLI 预检查

```bash
# 先经人类审定 script_lock.json，检查 R2/R3 文案与导演分镜不变
python workflow/production_gates.py --stage script \
  --spec /approved/director_spec.json \
  --plan /approved/narration_plan.json \
  --plan-path /approved/narration_plan.json \
  --cues /approved/av_cues.json \
  --cues-path /approved/av_cues.json \
  --script /approved/narration.txt --storyboard /approved/storyboard.md \
  --script-lock /approved/script_lock.json

# 真正试听并经人类批准后，再额外检查 Voice Lock
python workflow/production_gates.py --stage voice \
  --spec /approved/director_spec.json \
  --plan /approved/narration_plan.json \
  --plan-path /approved/narration_plan.json \
  --cues /approved/av_cues.json \
  --cues-path /approved/av_cues.json \
  --script /approved/narration.txt --storyboard /approved/storyboard.md \
  --script-lock /approved/script_lock.json \
  --audio /approved/voice.wav --timings /approved/timings.json \
  --voice-lock /approved/voice_lock.json

# 正式 R0 → R4 派单，同样必须验证两份锁
python workflow/orchestrator.py prepare \
  --spec /approved/director_spec.json --workdir work/formal_r4 --executor muse \
  --formal \
  --script /approved/narration.txt --storyboard /approved/storyboard.md \
  --plan /approved/narration_plan.json --cues /approved/av_cues.json \
  --script-lock /approved/script_lock.json \
  --audio /approved/voice.wav --timings /approved/timings.json \
  --voice-lock /approved/voice_lock.json
```

这些 CLI 验证的是**人类声明的审批信息 + 原始字节哈希**，
无法通过代码单独确认批准者身份或代替真正试听。

### 修改后的返工范围（不会让所有工作一律作废）

- 仅重配音、音频哈希或语速变化：必须重新 **Voice Lock**、音画成片及其
  QA；未变化的 Script Lock/分镜可以继续使用。
- 改台词、句序、R3 事件契约或分镜内容：必须**重审 Script Lock**；
  原 Voice Lock 因绑定旧 Script Lock 同时失效，受影响的 R4
  渲染和 R5 QA 必须重新进行。
- 不改变两份锁但修正纯图像实现：R4 生成新源码 SHA、新视频，
  重新执行受影响的镜头 QA；不能沿用旧 commit 的通过记录。
- 核心目标变化：回到 R1/R2/R3 审稿与分镜，不能绕过上游审批。

## 2. 无需 GitHub Actions 的正式离线构建

为防止工具随意批准作品，Pilot Stage D 使用固定输出路径：

- narration.txt （审核过的正式台词，每句一行）
- media/voice.wav （22050 Hz PCM16 单声道，13 秒真实音频）
- media/timings.json （三句，起止时间来自该锁定音频）
- media/stage_d_final.mp4 （实际 H.264 视频 + AAC 音轨）
- source/scene.json，source/narration_plan.json，
  source/approved_av_cues.json （审核后的源场景和 R3 契约）

例子（命令行中的批准文件和音频**必须是真正审核后的独立资产**）：

~~~bash
SOURCE_SHA="$(git rev-parse HEAD)"

python workflow/build_stage_d_artifact.py \
  --spec /path/to/approved_director_spec.json \
  --scene work/orders_pilot/scene.json \
  --plan /path/to/approved_narration_plan.json \
  --cue-contract /path/to/approved_av_cues.json \
  --script /path/to/approved_narration.txt \
  --storyboard /path/to/approved_storyboard.md \
  --script-lock /path/to/script_lock.json \
  --voice-lock /path/to/voice_lock.json \
  --audio /path/to/locked_voice.wav \
  --timings /path/to/locked_timings.json \
  --source-sha "$SOURCE_SHA" \
  --out /path/to/empty-stage-d-delivery
~~~

无需 API Key、Gemini Token、GitHub Actions 或网络 TTS。必须有 FFmpeg、
Python、Pillow、numpy、jsonschema 及中文字体，参见 README。

**故意失败的例子**：如果直接使用仓库现有
examples/workflow_orders_spec.json（approval=draft）和
work/orders_pilot/stagec_narration.json（test_only=true），
构建器应立即拒绝，不产生冒充正式获批的成片。

前置检查包括：
0. 独立 Script Lock 与 Voice Lock 均存在、结构有效、和真实
   文案/分镜/AV cue/WAV/timings SHA256 一致；
1. approved_by / approved_at、narration.status=locked 及锁定文件相对路径；
2. WAV 和 timings JSON 的真实字节 SHA256 与 director_spec 一致；
3. 正式稿与计划中的所有文字完全一致（不接受文字被偷偷替换）；
4. approved 的音画契约引用真实 orderflow.py 事件；
5. B 缺货 / A 发货语义、开始/结束、语音重叠以及 13 秒时长；
6. 真实 WAV 非静音，时长、采样率、通道数/位深正确；
7. 当前 Git HEAD 与命令里 source_sha 完全一致、输出目录不可覆盖；
8. 真正调用 FFmpeg 渲染 H.264/AAC，再用 ffprobe 检查帧数和时长；
9. 提取四张实际视频帧、生成 Stage D delivery.json、av_sync_report.json、
   qa_template.json、release_checklist.md 及 media_manifest.json，
   并校验产物全量文件哈希。

**注意**：符合这些机器规则，并不证明批准人的真实身份（当前没有数字签名）、
中文语音内容正确，也不证明成片艺术质量。R5/R7 是独立门禁。

## 3. 独立 R5 QA 与离线交接

生成成功的输出只标记为
delivery.stage=D、delivery.status=ready_for_qa。它含有
qa_template.json，但模板中的
decision=pending / reviewer.independent_context=false /
所有 visual_contract 检查都是 needs_review。
**不能将这份模板当作已审核通过的 qa_report.json。**

将真实视频、导演规格和 delivery 发给独立审片者；通过现有
roles/REVIEWER.md 和 roles/QUALITY_RUBRIC.md，
检查每个 required_checks，包括两张订单的身份、路径、动态连续性，
以及旁白与画面的对应关系。R5 输出完整 qa_report.json。

现有 R0 路线完全无需 Actions：

~~~bash
python workflow/orchestrator.py prepare \
  --spec /path/to/approved_director_spec.json \
  --workdir /path/to/stage_d_r0 --executor muse --formal \
  --script /path/to/approved_narration.txt \
  --storyboard /path/to/approved_storyboard.md \
  --plan /path/to/approved_narration_plan.json \
  --cues /path/to/approved_av_cues.json \
  --script-lock /path/to/script_lock.json \
  --audio /path/to/locked_voice.wav \
  --timings /path/to/locked_timings.json \
  --voice-lock /path/to/voice_lock.json

python workflow/orchestrator.py receive \
  --workdir /path/to/stage_d_r0 \
  --delivery /path/to/empty-stage-d-delivery/delivery.json \
  --artifact-root /path/to/empty-stage-d-delivery

python workflow/orchestrator.py review-package \
  --workdir /path/to/stage_d_r0

# 独立 R5 实际审片并填写 qa_report.json 后，再导入：
python workflow/orchestrator.py record-qa \
  --workdir /path/to/stage_d_r0 \
  --qa /path/to/independent_stage_d_qa_report.json

python workflow/orchestrator.py release-check \
  --workdir /path/to/stage_d_r0 \
  --artifact-root /path/to/empty-stage-d-delivery
~~~

请保留报告生成时的源码 SHA，并用
workflow/media_manifest.py verify 复核所有交付媒体。
qa_report.json 的 pass 必须覆盖所有
director_spec.shots[].visual_contract.must_show 和 continuous_motion；
未真实审片、存在 needs_review 或 P0/P1 问题时不得标记 pass。

**R7 最后的人类批准不由 release-check CLI 代替。**
CLI 通过表示元数据、文件/锁定音频等必要条件满足，仍需人亲自批准。
这条 Stage D 路线不调用 Gemini。如希望用模型审 Stage D，
应设计单独的 Stage D 模型审核版本，不能将 Stage C 原型结果沿用。

## 4. 技术实现与限制

- workflow/build_stage_d_artifact.py：只接收锁定声轨、正式稿、导演规格、场景和 AV cue；
- workflow/av_sync_contract.py：Stage C 继续要求 draft；Stage D 明确要求 approved；
- tests/test_stage_d_build.py：合成的 UNIT_TEST_ONLY_FAKE_APPROVER 只用来验证元数据
  拦截逻辑；其短媒体为 mocked 的单元测试占位符，**不是正式批准或真实成片**。
- 当前为 Pilot 001 的固定路径 / 13 秒 orderflow 版本。未来扩展为任意
  剧本/多个场景时应改进通用导演事件注册表、审批身份签名和审片证据流程。
- **不新增自动付费 GitHub Actions**；无需开启 R5_ENABLED 或 R5_AV_ENABLED。
