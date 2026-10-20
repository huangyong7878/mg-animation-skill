# R5 自动视觉审核：可切换的模型适配器、可信 CI 和 PR 反馈

**状态：等待该 PR 合并、配置 GitHub Variables/Secrets 并进行真实 API 验证。**

本实现不涉及任何写在代码中的 API Key；不设置固定 USD 费用上限。**不会自动合并 PR、批准分镜、修改 main、发布视频或代替人类发布审核。**

## 1. 一图看懂信任边界

~~~text
Muse/DeepSeek 开发 PR (不可信代码)
  └─ Pilot 001 Render and QA Artifact (pull_request, 无 Secrets, contents: read)
       └─ 真实无声 MP4 + keyframes + delivery.json + media_manifest.json
          └─ GitHub Actions Artifact，绑定精确源代码 commit
             └─ R5 Independent Visual QA (workflow_run, 从 main 检出可信代码)
                  ├─ 只下载源 run 上传的媒体，校验 SHA、Schema、视频证据
                  ├─ 调用 R5_PROVIDER 对应 API（只请求一次，无自动重试）
                  ├─ 检查所有视觉 contract，生成 qa_report.json + r5_audit.json
                  ├─ 把报告保存为新的 Actions Artifact（30天）
                  └─ 复核当前 PR HEAD 未改变，只发表一次 Issue Comment
                       └─ pass / rework / pending / blocked
~~~

**关键安全前提：** R5 的 \`workflow_run\` 工作流必须存在于仓库默认分支 \`main\`，并且**只从 main checkout**。PR 内的任何 \`*.py\`、\`qa_review.zip\`、脚本或文本都只当作不可信**数据**，绝不在拥有 API Secrets 的 Runner 上执行。不要改成 \`pull_request_target\`。

## 2. 开启自动审核：需要你在 GitHub 做的配置

打开仓库 → Settings → Secrets and variables → Actions。

### R5 总开关（默认关闭）

在 GitHub 仓库的 **Settings → Secrets and variables → Actions → Variables** 中创建 **`R5_ENABLED`**，它是唯一的自动审片总开关：

- **`false`（默认推荐）**：完全不运行 R5 审片 Job，**不会调用收费 API，也不会发布 R5 评论**；PR #12 的自动渲染与视频 Artifact 仍然正常。
- **`true`**：允许 R5 自动审核，但仍需有效的 `R5_PROVIDER`、`R5_MODEL` 和相应 API Secret，以及渲染 Workflow 成功。
- **未设置或任何其他值（包括 `TRUE`、`1`）**：视为关闭，避免意外计费。

**切换方法**：打开仓库 → Settings → Secrets and variables → Actions → Variables → `R5_ENABLED` → 编辑 Value → `true` 或 `false` → Save。

这是针对**新触发**审核的开关；已经进入运行状态的付费请求不会被变量切换追溯取消。需要立即停止当前运行，请在 **Actions → R5 Independent Visual QA** 手动取消对应 Run，或临时 Disable workflow。

在 **Variables**（不是 Secrets）添加：

| 名称 | 取值 | 用途 |
|---|---|---|
| `R5_ENABLED` | `false` / `true`（默认关闭） | R5 的显式总开关，只有 `true` 才可能调用付费模型 |
| `R5_PROVIDER` | `gemini`、`openai` 或 `deepseek` | 三选一，审查模型可切换 |
| `R5_MODEL` | `gemini-2.5-flash`、`gpt-4.1` 或 **`deepseek-flash`** | DeepSeek R5 请使用支持图片的 `deepseek-flash`，非 `deepseek-v4-pro` |

在 **Secrets** 添加与你选择的服务商一致的一项：

| 名称 | 用途 |
|---|---|
| \`GEMINI_API_KEY\` | Gemini API 认证；Gemini 能收到原生 MP4 + 重点帧 |
| `OPENAI_API_KEY` | OpenAI Responses API 认证；OpenAI 收到视频连续抽帧/时间联系表 |
| `DEEPSEEK_API_KEY` | DeepSeek Responses API 认证；DeepSeek Flash 收到带时间戳的抽样帧与联系表 |

只需提供实际选择的服务商 Secret，**不要把密钥贴入 Issue、PR、代码、聊天记录或 Artifact**。为了比较两种模型，可之后切换 \`R5_PROVIDER\` 和 \`R5_MODEL\`；同一轮触发只调用一个配置的模型。

**即便已配置 API Key，只要 `R5_ENABLED=false` 或未设置，就绝不会由此工作流启动新的付费 R5 请求。**

若未配置 \`R5_PROVIDER\` 或值无效，Workflow 的 QA 作业会**跳过**；若提供商有效但模型名/Secret 缺失，会**失败并阻断评论**，不会伪造 pass。

> 依赖关系：首先合并 [PR #12](https://github.com/huangyong7878/mg-animation-skill/pull/12)（自动渲染），再合并包含 R5 的 PR。因为 GitHub 要求 \`workflow_run\` 文件在默认分支才会自动触发，**本分支自身的绿色单元测试不等于已经发生了真实付费审片**。

### DeepSeek R5 具体设置（使用 Repository 级别）

仓库 **Settings → Secrets and variables → Actions → Variables**：

- `R5_ENABLED = false`（配置完成、准备试运行后才改为 `true`）
- `R5_PROVIDER = deepseek`
- `R5_MODEL = deepseek-flash`

仓库 **Settings → Secrets and variables → Actions → Secrets**：

- `DEEPSEEK_API_KEY = <你的有效 DeepSeek API Key>`，绝不能写进仓库或粘贴到 PR。

官方参考：[DeepSeek 图像理解](https://api-docs.deepseek.com/zh-cn/guides/vision/)、[Responses API](https://api-docs.deepseek.com/zh-cn/guides/responses_api/)、[定价](https://api-docs.deepseek.com/quick_start/pricing/)。**不支持把纯文本模型配置成视觉 R5；DeepSeek 官方目前只列出 Flash 支持图像，V4 Pro 不支持。**

若 R4 实现者也采用 DeepSeek，R5 仍需与执行上下文隔离，并且最好抽样交叉使用其他提供商或人工复审，避免同模型对自身模式的盲区。

## 3. 将会发生什么？

当 Pilot 001 源码在 PR 发生变化时，先触发原来的无密钥渲染工作流。成功生成 Artifact 后，只要已按上面配置好 Variable/Secret：

1. GitHub 自动启动 \`R5 Independent Visual QA\`，下载**此 Run**的 Artifact（不是“最新成功文件”）。
2. 首先检查 \`delivery.implementation_commit\`、\`spec_sha256\`、\`media_manifest.json\`、\`qa_evidence\` 的字节校验；不匹配则**不给模型发费率 API 请求**。
3. Gemini 适配器将实际 MP4 以内联方式交给 API，并附加高密度节点时间窗的图片；OpenAI 适配器将抽样帧及联系表交给 Responses API，并明示没有原生视频访问的限制。
4. 模型必须逐条返回 \`must_show\` / \`continuous_motion\`，附时间戳证据。
5. 本地运行 \`validate_bundle\` 以及 \`workflow/check_handoff.py\`，不允许缺要求、错 SHA、未检查就 pass 或严重 P0/P1 下 pass。
6. 产出 \`qa_report.json\` 和 \`r5_audit.json\`（包含模型名称、如服务商返回则含 Token 使用量和视频 SHA256）。
7. 如原 PR 仍然 open、同仓库、HEAD SHA 未变化，自动发表 PR 评论。PR 更新后旧 QA **不发送到新版本**。
8. 即使模型结论是 PASS，也只表示**Stage B 无声原型**的模型视觉质量审核通过；不能算有声成片发布批准。

GitHub Action 通过 \`workflow_run\` 配合 \`issues: write\` 完成评论，不需要另配个人访问令牌。只发表评论，不给 PR Approval、Label 或 Merge。重复运行同一个 Render Run 会检查评论 Marker，尽量避免重复评论。

## 4. 费率与资源限制

你选择了“**暂不设置固定美元费用上限**”，因此不会做虚假的预算保证；\`r5_audit.json\` 只记录服务商真实返回的 Token 使用量，USD 为 \`null\`，需要结合提供商当时价格结算。

但是为了控制误触发和滥用，仍内建非金钱型资源保护：

- **每轮最多一次付费 API 调用**，无自动重试；HTTP 出错则失败且不宣告通过。
- Gemini **inline MP4 ≤16 MiB**，整体请求体限制约 21 MiB；媒体清单总计 ≤65 MiB，超过则直接阻断，不能切换到不受控的上传接口。
- OpenAI 模式最多发送 3 张联系表与 16 张按优先级选择的时间帧；视觉得分不清的连续运动必须 \`needs_review\` / \`pending\`。
- 每个 PR push 可能引发一轮独立审片并计费，用户可以禁用该 Workflow 或删除 \`R5_PROVIDER\` 暂停。不同模型单价和图像/视频 Token 可能差异很大，请在服务商后台另行设置使用额度提醒/预算。

**该上限仅针对本阶段 Pilot；后续更长视频需先明确媒体分片和审片设计，而不是提高上限就放开无限账单。**

## 5. 模型替换与范围限制

模型适配器位于 \`workflow/r5_review.py\`：

- \`gemini\`：Gemini \`generateContent\` REST，原生视频 + 时间证据，输出 JSON。
- `openai`：OpenAI `responses` REST，图像时间证据，输出 JSON。
- `deepseek`：DeepSeek `https://api.deepseek.com/responses` REST，**`deepseek-flash` 支持的图像输入**与时间证据、JSON 输出。此接口不原生上传 MP4，因此不保证能从有限图片判断全部连续运动；证据不足时 R5 必须给出 `pending`，不得冒称已经完整观看视频。
- 新适配器：遵循函数约定 \`(prompt, video, evidence_root, model, api_key, transport) → (json_text, usage)\`，注册在 \`ADAPTERS\` 并提供对应 Secret；不要绕过 \`parse_model_report\`/PR SHA 校验。

**音轨不受影响。** 当前只审 Stage B 无声原型；Stage C/D 将继续使用原有 TTS、音画同步、字幕机制；为有声版本写 R5 接口需进一步扩展同步契约和可验证视听证据。

目前在 GitHub CI 的模型接口测试使用**模拟 HTTP 响应**，因此不会产生付费 API 调用。GitHub R5 工作流首次实际运行后，才可以确认真实 API/模型输出兼容性。模型处理媒体、视觉质量判断和时间戳准确性均需要继续抽样复核，不能把“JSON 可校验”当成“真实人类已审”。

## 6. 触发后到哪里查看

- **Actions → Pilot 001 Render and QA Artifact**：源代码对应的真实视频/媒体 Artifact。
- **Actions → R5 Independent Visual QA**：模型调用过程、校验结果、\`r5-review-<run_id>-<sha>\` 审查报告 Artifact（保留 30 天）。
- **原 PR → Conversation**：机器人自动评论，给出 PASS、REWORK、PENDING 或 BLOCKED、发现摘要、时间点和修复要求。

如果没有模型密钥、有无效模型名、缺少 Artifact、视频超限或 PR 已更新，则自动审核不会发布虚假的 PASS。完整错误原因可在 Actions 查看。

## 7. 权限、审核和边界检查

- 渲染 Workflow：保持 \`contents: read\`，**绝不传入模型 Key**。
- R5 Workflow：\`contents: read\`、\`actions: read\`、\`pull-requests: read\`、\`issues: write\`；只从 \`main\` 运行可信代码。
- R5 API Key 只通过环境变量传给可信脚本，不加入任何模型提示词、日志或生成文件；HTTP 出错不输出返回体以免泄漏。
- 所有外部媒体都视为可能携带对抗提示/恶意内容的数据，不赋予模型 GitHub 操作工具权限。
- 不检出 PR 的 Python、不开启自动合并，不触及 \`main\` 代码修改。
- 不跨 SHA 复用 QA：更新源码后必须重新生成视频和证据，再审片。
- 需要真正发布时仍按既有 \`workflow/check_handoff.py --release\` 执行人工批准、正式音频和 Stage D 门禁。

仓库已有 [多模型操作手册](MULTI_MODEL_PLAYBOOK.md)、[R5 角色](../roles/REVIEWER.md)、[媒体存储 ADR](adr/0001-media-artifact-policy.md)。本页仅解释新增的**真实 API 驱动**自动化。
