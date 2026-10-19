# 强模型总导演角色包（模型无关）v1.0

这个目录让 **ChatGPT、Claude、Gemini 或任何其他具备足够推理/媒体能力的模型**扮演同一个“总导演 / 独立 QA / 返工负责人”角色。它不是训练新模型，而是提供角色规范、交付 Schema、真实资料及验收方式。

## 从仓库入口自动找到适合的角色

建议所有能够读取此仓库的模型先读根目录 **[AGENTS.md](../AGENTS.md)**，根据任务意图选择 R0–R7，再读取对应角色的完整规范与 [操作手册](../docs/MULTI_MODEL_PLAYBOOK.md)。对不能自动加载 AGENTS.md 的平台，明确发送“请先阅读仓库根目录 AGENTS.md，并担任 R5 独立视觉 QA”等启动指令。

R5 可以使用 `workflow/qa_evidence.py create` 从实际 MP4 抽取等间隔和重点时间段的帧与联系表，再用 `workflow/role_pack.py qa --evidence-dir` 一并打包。但前者只制作证据，不会代替视频观看和独立 QA。

## 为什么不能只有一个「你是资深导演」Prompt？

强模型必须共享**可验收的工作协议**，不能要求它猜测我们前面几十轮对话的内容。关键内容：

- `DIRECTOR.md`：创意、技术判断、过程建模、每镜头可验收 Contract
- `REVIEWER.md`：真实视频检查、逐条 requirement、时间戳证据、P0/P1/P2
- `REWORK_SUPERVISOR.md`：定点返工、规格/代码版本一致、超限升级
- `QUALITY_RUBRIC.md`：模型之间可复用的验收标准
- `contracts/director_spec.schema.json` / `qa.schema.json`：机器可检查的最终格式

把角色文档当作**系统/项目层长期指令**，把视频、文案、导演规格当作**每次任务数据**。若所用平台不支持长期指令，就上传 ZIP、首先要求阅读 `START_HERE.md` 和 `role.md`。

## 最简用法：不运行任何程序

在另一个模型里打开仓库：<https://github.com/huangyong7878/mg-animation-skill>

- 让它担任总导演：先读 `roles/DIRECTOR.md`、`roles/QUALITY_RUBRIC.md`、`contracts/director_spec.schema.json`，再给它真实文案/素材和 `references/creative-director.md`、`references/technical-director.md`。让它产出 `storyboard.md`、`director_spec.json`、`director_notes.md`。
- 让它独立审片：**另开新对话或独立 Agent**，给它 `roles/REVIEWER.md`、`contracts/qa.schema.json`、当前 `director_spec.json`、`delivery.json` 和**实际视频/连续帧**，让它产出 `qa_report.json`。
- 若 QA 不合格，再给执行模型 `roles/REWORK_SUPERVISOR.md`、规格、交付、QA 报告，要求新 commit + 新视频。

切忌一边让模型写实现代码，一边用同一上下文充当“独立 QA”。单纯换一个角色名但不隔离上下文，也不够。

## 推荐：生成可携带的任务 ZIP（不依赖模型提供商 API）

在本仓库根目录运行：

```bash
python -m pip install -r requirements.txt

# 1. 给任意强模型做导演：输入是真实的解说文案/需求
python workflow/role_pack.py director \
  --brief path/to/brief.md \
  --out work/portable/director_001

# 2. 给另一模型做独立 QA：必须有真实视频和当前版本交付文件
python workflow/role_pack.py qa \
  --spec path/to/director_spec.json \
  --delivery path/to/delivery.json \
  --video path/to/rendered_shot.mp4 \
  --frame path/to/frame_1.png \
  --out work/portable/qa_001

# 3. 将 QA 的返工报告打包发回低成本执行模型
python workflow/role_pack.py rework \
  --spec path/to/director_spec.json \
  --delivery path/to/delivery.json \
  --qa path/to/qa_report.json \
  --out work/portable/rework_001
```

以上会生成目录和 ZIP，供人工上传到任何能处理这些文件的模型。**命令本身不调用任何模型，不会自动提交 PR、产生视频或宣布审查通过。** QA 包在 `outputs/qa_template.json` 给出 `pending`/未审核模版；审查模型必须实际打开视频后填入真实证据。

包内的 `manifest.json` 会记录输入媒体的字节 SHA256，但**不会保证视频来自声称的 Git commit**。必要时由执行环境验证 PR 提交、视频构建日志和媒体来源。

## 使用其他大模型时的能力要求

| 角色 | 必须具备什么 |
|---|---|
| 总导演 | 强推理、长文档处理、结构化输出；需要核实实时事实时需有检索 |
| 独立 QA | **真正的视觉/视频输入**，或可按时间序列分析连续抽帧；只看几张封面不够 |
| 工程执行 | 仓库读写、运行代码、渲染并查看视频、提交 PR |
| 返工监督 | 结构化读取 spec/delivery/QA，严格遵守版本和最小修改原则 |

若模型不支持直接播放视频，可以先用 FFmpeg 抽取**有时间标注的连续帧**再审；没有媒体输入时必须 `pending`，不能假装检查通过。静态物体画得好与动态连续正确是两个不同的问题。

## 模型替换验收

先用 Issue #4 《两张订单，两条路径》做试点。采用相同仓库版本、Brief、可用工具、执行者、验收标准和迭代预算，让两种强模型分别生成规格；由同一执行者做实现，并以独立评审者盲评。比较首版质量、严重问题数量、返工次数和总成本，避免仅凭几次对话感觉评价模型强弱。

## 与已有工作流的关系

- 已有 `workflow/check_handoff.py` 验证 JSON 与版本/发布门禁；它不等于视觉 QA。
- `workflow/orchestrator.py` 负责把执行者交付、GitHub Issue/PR 与 QA 状态连接起来。
- **角色包生成工具**只负责让不同强模型能收到相同说明和材料。它不替换动画引擎，不写自定义动画代码。
- `roles/DIRECTOR.md` 是跨阶段的总导演角色；而 `references/creative-director.md` 禁止技术词，专门用于`storyboard.md`的创意阶段。两者并不冲突：总导演可以在第二阶段将创意转换为 JSON。
