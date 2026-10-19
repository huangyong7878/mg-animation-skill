# MG 多模型交接协议 v1.0

用途：**强模型负责导演规格 → Muse / DeepSeek 负责工程实现 → 强模型独立审查实际视频**。

本阶段交付的是文件协议与结构门禁，不包含云端模型 API 调度、自动观看视频、GitHub PR 自动发布或模型计费管理。

## 三份文件

- \`director_spec.json\`：创意目标、观众、视觉风格、逐镜头描述、状态模型、Visual Contract、验收标准，\`approval\` 和 \`narration\` 的锁定状态。
- \`delivery.json\`：实现者交付的视频、源码、关键帧、检查结果、偏离项、轮次，绑定 \`spec_revision\`、\`spec_sha256\` 和 \`implementation_commit\`。
- \`qa_report.json\`：独立审查者对每条 \`must_show\` 与 \`continuous_motion\` 的评估，证据、问题（P0/P1/P2）、定点修复要求和通过/返工决定。

三份 JSON 的正式 Schema 在 \`contracts/\` 中。现有 \`references/visual-contract.md\` 字段沿用不变；\`director_spec.shots[*].visual_contract\` 可以单独导出为 \`shot.json\` 给 PR #1 的 \`scripts/contract_check.py\` 进行场景元素**结构**核对。

## 操作流程

1. 强模型生成分镜及 \`director_spec.json\`，默认 \`approval.status=draft\`、\`narration.status=draft\`。草稿可以制作**无声原型**。
2. 用户批准分镜后，正式配音生成 \`voice.wav\`、\`timings.json\`。填写这些文件的真实 SHA256、\`approval.approved_by\` / \`approved_at\`，设置 \`narration.status=locked\`、\`approval.status=approved\`，并提高 \`revision\`。
3. 实现模型在新 Git 分支编程、渲染、测试，交付 \`delivery.json\`。必须使用当前规格的指纹和**实际 commit SHA**；不得静默删减视觉要求。
4. 独立 QA 上下文阅读**规格 + 真实视频 + 连续帧 + 时间轴**，不先看实现代码；逐条填 \`qa_report.json\`。未完成检查不得填 \`pass\`，P0/P1 未修复不得验收通过。
5. 返工只修复具体 finding，产生新的实现 commit 与 delivery；原 QA 不再适用。建议两轮之后再由强模型重新定位设计或引擎缺口。
6. 正式发布前运行 \`--release\` 门禁。通过后仍要由真实多模态 QA / 人工判断画面是否清晰、物理过程是否连续、声画是否同步、事实及素材是否正确。

## 命令

\`\`\`bash
pip install -r requirements.txt
python workflow/check_handoff.py --spec examples/workflow_orders_spec.json
python workflow/check_handoff.py --spec examples/workflow_orders_spec.json --delivery examples/workflow_orders_delivery.json --qa examples/workflow_orders_qa.json
# 草稿样例会被正式发布门禁阻断，这是预期行为
python workflow/check_handoff.py --spec examples/workflow_orders_spec.json --delivery examples/workflow_orders_delivery.json --qa examples/workflow_orders_qa.json --release --artifact-root .
\`\`\`

真实成片的发布门禁：

\`\`\`bash
python workflow/check_handoff.py --spec work/ep01/director_spec.json --delivery work/ep01/delivery.json --qa work/ep01/qa_report.json --release --artifact-root work/ep01
\`\`\`

\`spec_sha256\` 为 JSON 的**规范化对象 SHA256**：Unicode UTF-8、键排序、紧凑分隔符。计算命令：

\`\`\`bash
python -c 'import json; from workflow.check_handoff import canonical_digest; print(canonical_digest(json.load(open("examples/workflow_orders_spec.json",encoding="utf-8"))))'
\`\`\`

规格内容变化（包括配音锁定）都需提高 \`revision\`、更新 SHA，并使之前交付与 QA 失效。

\`--release\` 除结构校验，还要求：人类已审批、配音和时间轴已锁定、Stage D、真实视频与源码路径存在且非空、配音/时间轴 SHA256 匹配、独立 QA 已逐条覆盖且无未解决 P0/P1。文件路径相对于 \`--artifact-root\`，不得越界。**这不验证视频能否解码、视觉效果、数学因果、音频对齐或 QA 真实性**。

示例《两张订单，两条路径》的路径是示意用占位内容，**不存在已渲染的视频**，QA 状态是 \`pending\`。

## GitHub 约定

- 导演、实现、QA 都尽量绑定同一规格版本和 Git commit。
- 实现者在分支提 PR，代码进 Git；大型视频放到带 commit 索引的 Actions Artifacts 或明确的外部存储，不建议每次直接提交 MP4。
- \`main\` 和最终发布由用户审批，本工具不自动合并。
- \`reviewer.independent_context\` 是审查者声明，尚未实现技术认证；不能仅据此证明独立审查发生。
