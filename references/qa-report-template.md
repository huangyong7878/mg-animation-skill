# 独立 QA 报告约定 v1.0

格式：\`contracts/qa.schema.json\`；示例：\`examples/workflow_orders_qa.json\`（示意数据，**未执行审查**）。

独立审查需要：当前 \`director_spec.json\`、本次 \`delivery.json\`、真实视频、连续帧、解说与时间轴。不要先阅读实现源代码，以免把代码中的标签误判为观众看得到的效果。

按每个 shot 的 \`must_show\` / \`continuous_motion\` 写一个 \`checks[]\` 项，要求 \`shot_id + requirement_id\` 唯一，记 \`pass / needs_review / fail\` 和**来自实际画面的证据及时间戳**。连续运动要看连续帧，不能只凭一张截图。

问题放 \`findings[]\`，给出 P0（事实、路径、核心对象错误）、P1（明显影响理解/同步）、P2（局部美术）、\`timestamp_s\`、\`expected\`、\`observed\` 和具体 \`fix_request\`。未看过的视频不得假称已检查。存在未解决 P0/P1 必须 \`rework\` 或 \`blocked\`。未检查完设 \`pending\`。

返工：将 QA 原文交给实现模型，只修改不合格项；每次重新提交新的 \`implementation_commit\`、更新 delivery、重新生成 QA。**上一轮代码对应的 QA 不能用于本轮交付。**

\`workflow/check_handoff.py\` 仅验证报告的结构、一致性、覆盖情况与发布限制；不能代替真正的视觉审查。
