# R5 Independent Visual QA — 手动、按渲染 Run 计费（默认安全）

**当前设计目标：把 R5_ENABLED 从“自动审片总开关”改成“付费审片许可开关”。**
只修改此变量不触发任何 R5 模型调用。人工在 Actions 中明确选择**一条已经成功的 Pilot 001 PR 渲染 Run**并点击运行，才有机会消费 Gemini/OpenAI/DeepSeek Token。

> 此功能须在代码 PR 合并到默认分支 main 后才能使用。该 PR 的 CI 模拟 Gemini 等接口，不代表已经发生真实付费审片。

## 1. 为什么改变触发机制？

早期 R5 使用 on.workflow_run：每次 PR 修改触发 Pilot 001 Render 工作流，渲染成功就启动 R5。当 R5_ENABLED=true 时，多次推送或重新渲染可能造成**多笔付费 API 请求**。即使单次审核无自动重试，也不代表整个 PR 不会重复计费。

**现在 R5 使用且仅使用 on.workflow_dispatch**：

- GitHub 自动渲染、Stage C 测试以及普通回归测试可以继续执行，**都不会自动产生 R5 模型调用**。
- R5_ENABLED=false（或未设置）时：即使有人手动点击运行，也会跳过实际模型调用 Job。
- R5_ENABLED=true 时：**也绝不会因打开开关或 PR push 而自行启动**；必须由人提交具体的 `render_run_id`。
- 手动运行针对**当前仍开放、同仓库、SHA 完全匹配且成功完成**的 Pilot 001 PR 渲染 Run。不能任意使用已过期、叉仓库、失败或其他 Workflow 的制品。
- 同一个渲染 Run 的人工重试会串行执行；如果已在对应 PR 成功发布过 R5 评论，前置检查会跳过重复计费。不过**如果之前请求已计费但后续失败、还没有 PR 评论，重新手动执行仍可能再次产生费用**，因此不能保证严格财务“至多一次”。

每次用户**明确点击一次 Run workflow**，R5 最多向选中的提供商发起**一个 API 请求**，不自动重试。服务商失败、证据缺失或 QA 契约校验不通过都不会伪造 PASS。调用 Gemini 前会验证媒体、SHA 和完整的证据清单；调用后记录真实 Token usage，`cost_usd=null`（没有不实的美元成本估算）。

## 2. Repository 变量与 Secrets

GitHub → **Settings → Secrets and variables → Actions**，选择 **Repository** 级别。

| 类型 | 名称 | Gemini 示例 |
|---|---|---|
| Variable | `R5_ENABLED` | `false`（准备好审核后才设 `true`） |
| Variable | `R5_PROVIDER` | `gemini` |
| Variable | `R5_MODEL` | 该账号支持视频理解的模型 ID，例如 `gemini-2.5-flash` |
| Secret | `GEMINI_API_KEY` | 有效 Gemini API 密钥 |

其他支持选项：`R5_PROVIDER=openai` + `OPENAI_API_KEY`；或 `R5_PROVIDER=deepseek`、`R5_MODEL=deepseek-flash` + `DEEPSEEK_API_KEY`。只存实际所需的密钥，绝不提交代码或粘贴 PR。

Gemini 用原生 MP4 + 时间重点帧审核。OpenAI/DeepSeek 共享一个 OpenAI Responses 兼容客户端，只接收已校验的抽样帧与联系表，不能凭有限帧保证所有连续运动无误，应在证据不足时给出 pending。

## 3. 如何只对一条 Run 发起一次 Gemini 审片？

1. 先从原来的 **Pilot 001 Render and QA Artifact** 工作流运行记录中找到一次 **Success、事件为 pull_request** 的 Run，它应该来自待审核的、**仍为 Open 的同仓库 PR 最新源码 SHA**。
2. 打开该 Render Run 页面（例如 `https://github.com/huangyong7878/mg-animation-skill/actions/runs/39386781120`），复制地址末尾的数字，如 `39386781120`。它指向固定的一次真实视频构建，而不是“最新一次”制品。
3. 将 Repository variable `R5_ENABLED=true`；确认 `R5_PROVIDER=gemini`、`R5_MODEL` 和 Secret `GEMINI_API_KEY` 有效。
4. 打开 [Actions → R5 Independent Visual QA](https://github.com/huangyong7878/mg-animation-skill/actions/workflows/r5-visual-qa.yml)，选择 **Run workflow**，branch 选择 **main**，在 `render_run_id` 填上刚才的数字，手动运行**一次**。
5. 打开这次 R5 Actions Run：检查真实 API 步骤的结果和 Artifact 的 `qa_report.json`、`r5_audit.json`，并在对应 PR 的 Conversation 检查评论。R5 报告的 PASS 仅指 Stage B **视觉**原型；Stage C 机械配音检查和正式 Stage D 音画审核与人工发布仍然独立。
6. 如不计划继续审核，把 `R5_ENABLED=false`。新开关配置不会取消已经发出的付费 API 请求；需要取消在跑的任务时去 Actions 手工 Cancel。

**不需要为了触发 Gemini 再向 PR 反复推送空提交。** `workflow_dispatch` 会针对已经生成、经过校验的固定源 Run 工作。

### 关键区别

- **R5 Model Adapters and PR Feedback Tests**：自动运行的**模拟单元测试**，不会联系 Gemini。
- **R5 Independent Visual QA**：**仅手动触发**的真实 R5 模型审核，满足各门禁后才计费。
- **Pilot 001 Render and QA Artifact**：自动渲染真实 Stage B 视频，**不调用 Gemini**。
- **Stage C Pilot Narration and AV Draft**：独立制作离线 TTS、SRT、AV 样片，**不调用 Gemini**。

普通 CI 工作流的数量仍由各自的触发条件决定；此次修改阻断的是**因自动渲染连锁触发的 R5 付费调用**，而不是将所有无密钥测试工作流合并为一条。

## 4. 信任边界、成本与发布限制

- 审核从 main 的**可信代码**执行，永不 checkout 待审核 PR 的 Python；GitHub Artifact 视为**不可信数据**，校验文件大小、路径、证据、SHA256、源 commit 等。
- `workflow/r5_dispatch_event.py` 通过 GitHub 认证 API 检索指定 Render Run，检查其工作流名称和路径、来源仓库、完成状态、事件类型和最新 PR SHA；不信任用户输入的 repo/SHA。
- 在调用模型之前，再由 `workflow/r5_pr_feedback.py` 验证真实开放 PR、HEAD SHA、以及是否已有同一渲染 Run 的审核评论。
- 每轮最多**一笔**模型 API 请求，没有自动重试；不能保证 Gemini 认为的 PASS 完全正确，不会自动审批 PR、合并 main、批准旁白或发布成片。
- Gemini 内联 MP4 上限 16 MiB，整个请求体约 21 MiB；音视频较长时须先重新设计审核证据而不是放开无限制费用。
- Token usage 只按模型真实反馈记载；请同时在 Gemini 服务商后台设置预算/告警。
- 已有 R5 付费请求即使没有成功返回 QA 报告，也可能产生费用。**不要误把“没有评论”当成“没有计费”。**

源代码：`workflow/r5_dispatch_event.py`、`workflow/r5_pr_feedback.py`、`workflow/r5_review.py`。本工作流只负责 Stage B 草稿的独立模型视觉检查。
