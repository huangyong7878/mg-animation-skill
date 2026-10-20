# Pilot 001 · R3 Script Lock 审批材料（候选，未批准）

> **NON-APPROVAL / REVIEW ONLY**：用户已认可三句台词和候选分镜的方向，**未签发正式 Script Lock**。本分支不包含 script_lock.json、Voice Lock、正式音频或发布批准。现有 Stage C 的 draft/test_only 文件不修改。

## 待审核资产

- 台词原文：`work/orders_pilot/script_candidate.txt`，三句逐字不变。
- 分镜原文：`work/orders_pilot/storyboard_candidate.md`，Shot 01，13 秒，三个 Beat。
- 导演规格候选：`examples/workflow_orders_spec.json`，`approval.status=draft`；project_id `orders_two_routes`, spec_id `orders_shot_001`, revision `1`。
- 正式用途的旁白计划**候选**：`work/orders_pilot/formal_narration_candidate.json`，`test_only=false`，仍未审批。
- AV Cue **候选**：`work/orders_pilot/formal_av_cues_candidate.json`，`status=draft`，未取得人类批准。

## R3 语义、顺序及时间对应

| 句 | 文字 | 计划开始 | 画面依据 | 时间窗 |
|---|---|---:|---|---|
| intro | 两张订单，同时下单。 | 0.00s | A 在 1.00s 出现；B 在 1.20s 出现 | 0.00–0.30s |
| out_of_stock | 库存不足，订单B等待补货。 | 5.90s | 5.80s 分流；B 8.40s 进入补货队列 | 5.80–6.15s |
| in_stock | 库存充足，订单A发货。 | 9.55s | A 10.00s 到发货站；后续出现已发货标签 | 9.40–9.90s |

**注意**：事件时间来源于当前 `scripts/primitives/orderflow.py:PILOT_EVENT_SECONDS`。声音的实际长度、停顿和同步，仍需试听及 Voice Lock 后重新按实测 timings 验证。分镜已明确 B 先入补货队列，A 后发货；A/B 颜色、身份和持续运动不可交换或瞬移。

## 必须通过的锁定前检查

1. 确认以上五类资产最终版本及 R3 故事板、画面、时序语义一致。
2. 批准前将最终 AV cue 从 `draft` 升级成 `approved`，并核对 `validate_av_cues(..., expected_status="approved")`；不得把当前 draft 候选当作已批准契约。
3. 用最终**原始文件字节**计算 script、storyboard、plan、cues 四项 SHA256；从最终导演规格计算 `director_storyboard_sha256`，验证项目 ID、spec ID、revision。
4. 人类另行明确签署 `contracts/script_lock.schema.json` 中的 `approved_by`、`approved_at`、`status=approved`、`revision` 等字段。绝不可自动填写签署者或伪造批准时间。
5. 随后才制作 XiaoxiaoNeural 专业平稳女声试听；尚未试听通过，**不得**生成 Voice Lock 或进行正式 R4。
6. 一旦上游文案、分镜、AV cue 或视觉导演契约变化，先更新版本、重新审批、重算哈希，下游锁不复用。

## 当前检查结果与局限

- 三句文案与旁白计划文本完全一致；顺序为 intro → out_of_stock → in_stock。
- 计划开始时刻落在 AV cue 所规定的事件窗口内：0.00s、5.90s、9.55s。
- 只有单个 13 秒连续 Shot，呈现 B 缺货排队、A 正常发货。
- 当前规范 **尚未**人类批准。此文档并非正式签署，也不证明语音听感、最终真实媒体或 R5 质量审核。
