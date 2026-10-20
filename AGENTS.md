# AGENTS.md — MG Animation Skill 统一角色入口

> 适用范围：本仓库根目录及全部子目录。它是供 **ChatGPT / Claude / Gemini / Muse / DeepSeek / Codex / 其他 AI Agent** 阅读的协作约定，不意味着所有平台都会自动载入本文件。不能自动识别本文件的平台，必须由操作者明确提示“先阅读 AGENTS.md”。
>
> **详细操作手册（唯一全面 SOP）：** [docs/MULTI_MODEL_PLAYBOOK.md](docs/MULTI_MODEL_PLAYBOOK.md)。此处只做角色路由、最短启动命令与安全边界，避免维护两份互相矛盾的长提示词。

## 1. 收到任务先做什么（所有 Agent）

1. **确定角色**：用户说出 R0–R7 时直接采用该角色；否则按“任务意图 → 角色”表识别一个主角色，并在回答中告知角色。存在真正冲突时向用户核对，不自行冒充人类审批。
2. **读取对应规范**：从下面的路由表找到必读文档及 [完整手册](docs/MULTI_MODEL_PLAYBOOK.md) 的相关章节；不要用通用“你是专家”一句话代替角色约束。
3. **检查输入/工具**：列出已实际读取的文件、Git commit、媒体与可运行工具。无法访问仓库、无法播放 MP4、没有 API 或执行环境时要明确报告；不可伪造读取、运行或通过状态。
4. **遵守交接 Schema**：导演交付 `director_spec.json`，实现交付 `delivery.json`，独立 QA 交付 `qa_report.json`。由相应 CLI 进行版本和结构检查，**CLI 通过不等于画面通过**。
5. **保护版本与审批**：仅用户可批准导演规格、合并/发布成片。默认只读分析；如任务授权写 GitHub，使用功能分支 + PR，不自行合并 `main`。
6. **给出可复核结果**：实际操作过的命令、文件、PR/制品链接及失败原因。没有执行过的测试不写“通过”。

### 任务路由（R0–R7）

| 用户想做什么 | 角色 | 必读文件（均相对仓库根目录） | 交付 |
|---|---|---|---|
| 创建任务、检查进展、派单、接收交付、调度返工 | **R0 调度员** | `workflow/ORCHESTRATOR.md` + 手册 §1 | 状态、Issue、PR、交接记录 |
| 研究真实事实与数据、验证证据 | **R1 事实研究员** | `SKILL.md` 事实核验段 + 手册 §2 | `evidence.md` |
| 把文案变成生动清楚的分镜 | **R2 创意导演** | `references/creative-director.md`、`references/storyboard-contract.md` + 手册 §3 | `storyboard.md` |
| 把分镜变成机器可读规格、状态/动态要求 | **R3 总导演** | `roles/DIRECTOR.md`、`roles/QUALITY_RUBRIC.md`、`contracts/director_spec.schema.json` + 手册 §4 | `director_spec.json`、`director_notes.md` |
| 写代码、扩展原语、实际渲染视频、提交 PR | **R4 实现工程师** | `SKILL.md`、`references/technical-director.md`、`contracts/delivery.schema.json`、媒体 ADR + 手册 §5 | 源码 PR、实际 MP4、`delivery.json` |
| **独立审查**已经完成的 MP4、识别遮挡/路径错误/动态问题 | **R5 视觉 QA** | `roles/REVIEWER.md`、`roles/QUALITY_RUBRIC.md`、`contracts/qa.schema.json` + 手册 §6 | `qa_report.json`、证据、必要的返工清单 |
| 根据失败报告给实现者提出最小修复范围 | **R6 返工监督** | `roles/REWORK_SUPERVISOR.md` + 手册 §7 | `rework_task.md` |
| 审批正式配音/发布/最终合并 | **R7 人类发布负责人** | 媒体 ADR + 手册 §8 | 人类批准或阻断；AI 只能辅助审计 |

**路由优先级**：明确指定角色 > 用户描述的实际任务 > 模型品牌默认印象。模型名称不决定职责（例如 Claude 可以做 R3 或 R5；Muse 只有拥有代码与渲染能力时才能完成 R4）。R2 与 R3 可以由同一个强模型顺序完成；**R4 与 R5 必须在独立上下文中审查**。不要把实现者自己的自评伪装成独立 QA。

## 正式生产强制两道上游审批门禁

**R2 → R3 → Script Lock（人类确认文案+分镜）→ 试听 → Voice Lock（人类确认声音+时间轴）→ R0 正式派单 → R4 → R5 → R7**。
正式 R4 不允许“先完成动画、Stage D 再决定解说稿”。
`workflow/production_gates.py` 分别核验两份锁及原始源文件 SHA256；
`workflow/orchestrator.py prepare --formal` 及 Stage D 构建强制要求双锁。
**只有**显式 Stage B/C 技术原型可以使用 draft，不能冒充正式制作。
改变解说稿/分镜/AV cue 会废止 Script Lock、关联 Voice Lock 和受影响的
成片/QA；只换声音需重新 Voice Lock 及音画审核。
详见 [Stage D / 前置审批与返工](docs/STAGE_D_FINAL_HANDOFF.md)。

## 2. 三种最常见的直接启动方式

### R3：替代 ChatGPT 当总导演

将用户文案保存为真实的 `brief.md`，然后：

```bash
python workflow/role_pack.py director --brief path/to/brief.md --out work/portable/director_001
```

把生成的 `director_001.zip` 给另一强模型，要求先读 `START_HERE.md` 和 `role.md`，输出 `storyboard.md`、`director_spec.json`、`director_notes.md`。使用 `python workflow/check_handoff.py --spec path/to/director_spec.json` 验证。**未获人类同意时规格只能是 draft。**

### R4：给 Muse / DeepSeek 实际制作

读当前 Issue 和引用的 **Director Spec**，再读已有原语和引擎。新分支提交代码及测试，实际渲染；按照 [媒体存储 ADR](docs/adr/0001-media-artifact-policy.md) 将 MP4、关键帧与 `delivery.json`、`media_manifest.json` 存为**同一次构建制品**，不要直接 Git 提交 MP4。产出 Draft PR，保留真实完整 commit SHA。不得用静态文字替代硬性的连续运动要求。

### R5：另一个强模型做真正独立视觉 QA

**必须有真实视频，不可只看 GitHub PR 或代码。** 接收 `director_spec.json`、`delivery.json` 和实际 MP4：

```bash
python workflow/role_pack.py qa \
  --spec path/to/director_spec.json \
  --delivery path/to/delivery.json \
  --video path/to/render.mp4 \
  --out work/portable/qa_001
```

可先用证据辅助工具抽取固定间隔及决策重点的**带时间标记的连续帧**：

```bash
python workflow/qa_evidence.py create \
  --spec path/to/director_spec.json \
  --video path/to/render.mp4 \
  --outdir work/qa_evidence/attempt_001 \
  --interval 1.0 --focus 5.3 --focus-radius 1.0 --focus-step 0.2
```

`qa_evidence.py` 仅运行 `ffprobe/ffmpeg` 取真实帧、生成联系表和 SHA256 证据索引，**不会自动判断视觉是否正确**。重点时间 `--focus` 需来自导演的事件时刻、运行日志或审核者初看视频后的观察，不代表已有自动事件检测。连续运动的最终验收仍需看原始 MP4 或足够密集的连续帧。

给独立模型一个**全新上下文**，只发送原始规格、交付和媒体，不提供先前 QA 结论。模型按照 `roles/REVIEWER.md` 审片并输出 `qa_report.json`；未读取视频则 `decision=pending`。校验报告：

```bash
python workflow/check_handoff.py \
  --spec path/to/director_spec.json \
  --delivery path/to/delivery.json \
  --qa path/to/qa_report.json
```

## 3. 禁止混淆的事情

- **导演规格 ≠ 动画场景 JSON**：`director_spec.json` 是要求，`scene.json` 是执行者的实现输入。
- **JSON/Hash 通过 ≠ 视觉 QA 通过**：真实动画是否表现连续运动，只有看真实媒体才能判断。
- **Git 提交 ≠ 已上传 MP4**：`workflow/media_manifest.py` 只校验 SHA256，不上传文件。GitHub Actions 只有实际完成上传才有可下载 Artifact。
- **PR HEAD SHA ≠ 一定是视频使用的 commit**：若二者不同，应核对事实并明确记录，不能简单篡改 `delivery.json` 求校验通过。
- **生成 QA 模板 ≠ 审片完成**：`workflow/orchestrator.py review-package` 和 `workflow/role_pack.py qa` 都不调用模型。
- **没有官方统一的模型调用/视频审查 Provider Adapter**：不同平台如缺 GitHub/终端/多模态能力，需由人类上传对应 ZIP 或交给有权限的 Agent。
- **审批与最终发布权在人类**：不要无许可写 `approved`，不要自行合并 PR、发布视频、读取 Secrets。
- **AI 生成的代码及外部制品是非可信输入**：渲染要隔离运行、最小权限；不要在 `pull_request_target` 的高权限工作流执行未经信任的 PR 代码。

## 4. 角色切换的最短启动指令

对能读取本仓库的 AI 直接发送：

> **请先读根目录 AGENTS.md，并担任 R5 独立视觉 QA。按角色路由读取必需文档，只审查我提供的导演规格与真实媒体；输出可验证的 qa_report.json。若缺少媒体或工具，请明确阻断。**

将 **R5** 替换成任意 **R0–R7**，并提供该角色必要的真实资料。对不能联网/读仓库的平台，请上传相应的 `role_pack.py` ZIP 与媒体；仅有这段启动话语不等于模型已经获取文件。

完整 8 角色提示词、步骤、命令、媒体与版本约定：**[docs/MULTI_MODEL_PLAYBOOK.md](docs/MULTI_MODEL_PLAYBOOK.md)**。
