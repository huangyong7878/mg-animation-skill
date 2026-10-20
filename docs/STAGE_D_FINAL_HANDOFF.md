# Stage D 正式有声成片：R3/R4 锁定、独立 R5 审核、R7 人类发布

> **状态：实现了 Stage D Pilot 001 的离线构建器和阻断式发布交接。**
> **当前仓库中的 director_spec、旁白、音画契约仍为 draft / test_only。**
> 因此不能用原 Stage C 样片假冒 Stage D 的已批准成片。
> 本文件没有给予任何 AI 或 Actions 人类审批权。

## 1. 责任与分工

- **R3 + R7**：先由人观看分镜、审稿、决定正式声音与时间轴。
  将正式的 director_spec.json 的 approval.status 设为 approved，
  同时记录真实 approved_by / approved_at。此动作由人完成，不由构建器代签。
  审核过的 narration.txt、voice.wav 和 timings.json 锁定后，用原始
  字节 SHA256 填 director_spec.narration.audio_sha256 /
  timings_sha256，设置 narration.status=locked。
- **R3**：独立检查旁白→画面事件契约，再将
  stagec_av_cues.json 的 status 从 draft 升级成 approved；
  narration_plan.json 的 test_only 必须明确为 false。
  三段内容和时间线必须保持 B 缺货在前、A 发货在后；若修改语速、
  配音人或解说词，需要重新录音、对齐并重新走人类审批。
- **R4**：以 approved 的导演规格、已锁定 WAV、计时文件以及真实场景
  运行本地 Stage D 工具；工具不会合成新音频，**只使用已锁定的音轨**。
- **独立 R5**：打开 Stage D 的原始 MP4 听音、逐项检查要求，
  用标准 contracts/qa.schema.json 输出完整 qa_report.json；
  不可以拿 Stage C 的 av_qa_report.json 改名冒充 Stage D 全项 QA。
- **R0 + R7**：R0 用 orchestrator 接收交付并导入独立 QA；
  只有 R7 可以在核查发布清单后决定是否发布和长期归档。

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
  --workdir /path/to/stage_d_r0 --executor muse

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
