# R5 Stage C 独立视听审核：Gemini 手动审片 + 本地导入外部审核

> 本功能单独以 PR 交付；先将依赖的 Stage C PR #14 合并，
> 再审核并合并 R5 AV PR。部署前不会自动调用 Gemini、合并代码或批准发布。

## 两种完全等价的 R5 审核入口

**A. 手动调用 Gemini（使用 GitHub Actions）**：
在 Actions → R5 Independent Stage C Audiovisual QA → Run workflow，
选 main 并输入某个成功完成的 Stage C PR 构建 `stagec_run_id`。
仅当以下两个 Repository variables 都是精确的 `true` 才可能计费：

- `R5_ENABLED=true`（原有通用模型审核开关）
- `R5_AV_ENABLED=true`（新增的 Stage C 专属审核开关）

同时要求 `R5_PROVIDER=gemini`、正确的 `R5_MODEL` 和
Repository Secret `GEMINI_API_KEY`。此工作流仅有 `workflow_dispatch`
触发器；**打开任何变量、PR push、重新渲染都不会触发付费审片**。
同一个 Run 已成功发表评论后再次执行会跳过模型；但已计费后、
PR 评论尚未成功时手动重试仍可能再次计费。

**B. 完全不使用 GitHub Actions 的人工/外部模型审核**：
任何独立审核者拿到真实的 MP4/WAV/导演规格/时间轴/事件契约，
都可以自行审片并填写原始观察 JSON，然后用本地程序导入：

~~~bash
python workflow/r5_av_manual.py \
  --artifact-root /path/to/stagec-artifact \
  --observations /path/to/external-av-observations.json \
  --reviewer "Independent QA Reviewer" \
  --attest-independent \
  --out /path/to/review-results
~~~

上述命令不需要 GitHub/Gemini 账号、Token 或联网，不调用任何收费模型。
`--artifact-root` 既可以是下载解压后的 Stage C CI Artifact，
也可以是自建的 `local` 或 `external` 后端媒体交付目录，只要包含
合法的 `media_manifest.json`、`director_spec.json`、`delivery.json`、
`av_sync_report.json`、`stagec_narration.json`、`stagec_av_cues.json`、
真实 MP4/WAV/timings，且通过 SHA256 校验。不能仅上传一份任意 JSON
就跳过视频来源校验。

观察结果的结构定义：
[`contracts/av_qa_observation.schema.json`](../contracts/av_qa_observation.schema.json)。
每条 `checks` 须指定 segment_id、听到的实际文本、观察到的画面、
时间戳、是否能够确认两个媒介，以及 reason。
如果只是阅读了字幕/稿件、未实际听辨，则应标记
`audio_verified=false` / `needs_review`，总体 `pending`。
要导入 `pass` 必须有独立审片者的明确声明 `--attest-independent`；
这个声明是人工责任留痕，**不是机器验证其身份或真实性**。

两种入口都输出 `av_qa_report.json` 和 `av_r5_audit.json`，
包括原始媒体字节 SHA256、对应提交、审核来源、判定和证据。
**没有自动把人工报告冒充 Gemini 报告**。

## 继续现有 R0–R7 人工交接 / 发布

项目本来就有无需 Actions 的通用审核路线：

~~~bash
python workflow/orchestrator.py review-package --workdir work/orders_test
python workflow/orchestrator.py record-qa \
  --workdir work/orders_test \
  --qa /path/to/qa_report.json
python workflow/orchestrator.py release-check \
  --workdir work/orders_test --artifact-root /path/to/final-stage-d
~~~

`record-qa` 接收的是
[标准 `contracts/qa.schema.json`](../contracts/qa.schema.json)
中的 **完整独立 QA**，并要求该工作区已接收交付并进入
`review_pending`，否则会拒绝。它与 Stage C 新增的逐句
`av_qa_report.json` **不是同一个 schema**；不能简单改名后假装完成
全项视觉审查。最终 `release-check` 还必须满足已批准导演规格、
正式锁定配音、Stage D 交付、源版本与全部必要的 QA 检查。
`Stage C prototype` 的任何自动/人工审核通过，都不能直接允许发布。

因此可以做到：**没有 Actions、没有模型 API，也能完成 R5 人工审核与
后续交接；但仍不能省略独立审核、真实媒体证据或人类发布审批。**

## 实际 Gemini 审片范围

单次 Gemini 调用同时接收真正包含 AAC 音轨的 Stage C MP4，
以及原始 `audio/wav`。同时带上分句时序和期望画面作为
**待检数据**，要求每句报告听到的文本、看到的订单及时间戳。
使用 [Gemini 视频理解](https://ai.google.dev/gemini-api/docs/video-understanding)
及 [音频理解](https://ai.google.dev/gemini-api/docs/audio)。
无论模型还是人工，若不能确认音轨/画面内容，就只能输出 pending。

**可信边界**：Gemini Actions 从 main 加载可信代码，不执行 PR 的脚本，
通过 GitHub API 核实指定 Run 为成功的 PR 构建且为当前开放 PR HEAD，
检查媒体哈希、静音/流/时长门禁后才可能调用模型。
超过 9 MiB MP4、4 MiB WAV 或 21 MiB 总请求体则拒绝。
付费审核完成后不自动合并 PR、不自动锁定解说稿、不批准 Stage D 发布。

## Gemini 已完成但 PR 评论遇到 403 的恢复流程

**不要重新运行 Gemini 审核来补发评论。** 已付费的审核可能已经生成
`av_qa_report.json` 和 `av_r5_audit.json`，只是最后一步 PR 评论失败。

1. 从失败的 R5 Run 下载并保存已上传的审核报告和用量审计。
2. 新的审核工作流同时声明 `issues: write` 与
   `pull-requests: write`，修复 PR 评论权限组合；
   如果仍是 403，检查仓库 Settings → Actions → General
   的工作流权限以及组织/仓库 Ruleset 限制。
3. 使用 **R5 Stage C Publish Existing QA (no model calls)** 工作流，
   手动选择主分支并填写原 `stagec_run_id` 和已保存报告的
   `reviewed_run_id`。该流程只下载旧报告和原视频/WAV、
   复核 SHA256/PR HEAD 并尝试补发，不注入 `GEMINI_API_KEY`，
   **不会再次调用模型、不会产生新增 Gemini Token**。
4. 如果审核评论已经成功发布，恢复流程会检查唯一标记并跳过。
   如果 GitHub 权限仍不允许自动评论，可使用授权人的 GitHub
   账户手动发布已核实的报告并附上原审核 Run 链接，不应伪称
   GitHub Actions 自动评论成功。

2026-10-20，R5 Run `39407922464` 在 Gemini 调用成功、
审核制品归档成功后，向 PR #18 评论时被 GitHub HTTP 403 拒绝。
这不是模型审片失败；可能已经产生真实用量，不能直接重复调用。

## 文件

- `.github/workflows/r5-stagec-av-qa.yml`：手动选 Run / 双开关
- `workflow/r5_av_control.py`：同仓库 SHA、开放 PR 和重复评论门禁
- `workflow/r5_av_review.py`：真实 MP4+WAV Gemini、独立音画报告
- `workflow/r5_av_manual.py`：**不依赖 Actions 的本地审核报告导入**
- `contracts/av_qa_observation.schema.json`：逐句观察标准
- `tests/test_r5_stagec_av.py`：离线接口、错误语义、篡改和付费防护测试
