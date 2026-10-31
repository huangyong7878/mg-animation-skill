# Agensi Free Edition — Agent B 执行规格与验收基线

> 状态：需求规格已提出，**尚未实现 / 测试 / 批准发布**。  
> 执行负责人：**Agent B**（AI 角色，不等同于已核实的 GitHub 账号）。  
> 任务：Issue #40。仓库：huangyong7878/mg-animation-skill（公开旧实现）。  
> 本文件日期：2026-10-31。  
> 审批人：项目所有者。任务 PR 始终保留 Draft，直到代码、测试、审核完成。

## 1. 目标与设计决策

交付一个 Agensi 可上架的 **免费、单一 Skill**。用户仅用 Agensi 连接的 AI Agent（不假设已经安装 Python、FFmpeg、TTS 或下载 GitHub 仓库）也能够完成：

1. 将用户文案或主题拆解为结构化分镜（Storyboard）。
2. 生成符合**旧版 MG Animation Skill v2.1** 已有契约的 Scene JSON 和时间轴、转场规划。
3. 输出 QA 说明，包括假设、引用核验状态、文字溢出风险、配音时长风险和缺失依赖。

**视频渲染是可选的第二路径**：仅在用户明确授权且本地已有旧版渲染引擎及必要依赖时，才能调用已有本地工具导出视频。没有真实执行时严禁声称已生成 MP4 / WAV / SRT 或通过审核。

该任务是旧仓库的 **发行适配**，不是重构视频引擎，更不是交付新的 MG Studio 交互画布。不得访问、复制或修改私有 mg-studio 的架构文件、配置或资产。

## 2. 为什么不能直接把整个旧仓库上传

Agensi 通过 MCP 的 get_skill 发送 SKILL.md，并在 Agent 要求时按文件路径提供其他**文本文件**。平台对上传脚本的执行机制是：Agent 将单个文件原样写入临时文件，独立执行，然后删除；不能默认它能读取上传 ZIP 中其他并列文件。

现有 scripts/pipeline.py 会 import engine、validate、factcheck、narrate；validate.py 需要 references/scene.schema.json；完整渲染还要求 FFmpeg、Python 依赖、字体以及可选 TTS。上传整个工程会导致“Skill 可被读取但脚本不能依原方式运行”的落差。

Agensi 官方文档（2026-10-31 核对）：
- https://www.agensi.io/docs/packaging
- https://www.agensi.io/docs/how-agents-load-skills
- https://www.agensi.io/docs/review-and-approval
- https://www.agensi.io/docs/submit-on-the-website
- https://www.agensi.io/docs/pricing-your-skill
- https://www.agensi.io/docs/creator-faq

## 3. 明确的范围和禁止事项

**必须做：** 专用 SKILL.md；可按需获取的文本参考文档；精简真实 Scene 规范；中英文示例；可复现打包脚本；自动化和隔离环境测试；英文上架说明；权限、安全、版权/许可证审计；逐项验收证据。

**禁止做：**
- 修改现有渲染核心 scripts/engine.py、pipeline.py、render.py、narrate.py、工作流 R0–R7 门禁或审批记录，仅为上架做重构。
- 修改私有 mg-studio 或使用未发布的画布/UI 功能进行营销。
- 在包内塞入整个 legacy repo、可执行二进制、图片音频/视频、依赖环境、私钥、API Key 或第三方无授权素材。
- 强制绑定 Claude、Codex、某个模型厂商或 Azure；不得创建新的私有服务或偷偷联网。
- 自动 clone、安装软件、运行远端脚本、调用付费 TTS/模型；需要用户明确授权。
- 擅自选择许可证、合并 PR、改动主分支、在 Agensi 上传发布、创建支付账户或绕过人工审核。

超出范围先在 Issue #40 留 BLOCKER / PROPOSAL，由项目所有者批准，不能擅自扩大。

## 4. 建议交付目录与文件

Agent B 可以在说明理由后调整文件名，但**产物能力与测试不可缩水**。

    distributions/agensi-free/
      SKILL.md                         # 独立 Skill 的主要指令；正确 YAML frontmatter
      README.md                        # 安装前提、用户流程、限制、故障处理
      references/
        scene-contract-lite.md        # 从实际 v2.1 schema 精简
        output-and-qa.md              # 分镜、JSON、QA 三种输出格式和检查表
        safety-and-limitations.md     # 安全、权限、引用/版权、真实能力边界
      examples/
        brief_en.md
        storyboard_en.md
        scene_en.json
        brief_zh.md
        storyboard_zh.md
        scene_zh.json
      LISTING.md                       # 提交表单素材，不必打入 ZIP
    scripts/package_agensi_free.py    # 打包/校验脚本，放在分发 ZIP 之外
    tests/test_agensi_free.py         # 构建+结构+内容/安全等离线检查
    dist/agensi-free-<version>.zip     # 本地或 CI 生成；本任务不上传平台、不提交二进制

使用 allowlist 打包，压缩包根部必须有 SKILL.md，单一 Skill，不产生嵌套 ZIP 或无意的第二个 SKILL.md。ZIP 输出内容优先只有 SKILL.md、README.md、references 和 examples 中的**文本**。LISTING.md、测试代码和打包代码可以保留在仓库，但不得混入最终包而误导消费者。

约束：网站上传 ZIP 上限 50 MB、最多 1000 文件；实际交付要远低于这些上限，尤其要避免 Agensi 每次加载最多 200 个附加文本文件 / 600 万字符的截断情形。不要依赖平台传输图片、PDF 或二进制资源，也不要附带 node_modules / Python venv / site-packages。

## 5. SKILL.md 行为契约

### 5.1 触发与输入

描述用户何时应调用该 Skill，例：把文章、课程讲稿、科普文本或结构化数据制作成信息图动画分镜。

支持输入：主题/文字脚本、资料、目标受众、语言（至少中文/英文）、时长、画幅、风格偏好、旁白有无。缺少非阻塞项时应**声明默认值**；阻塞项询问用户，不要杜撰证据或时长。

### 5.2 无运行环境时也必须交付

- **Storyboard**：逐镜头 ID、叙事目标、可视元素、动画/转场、时间轴、旁白建议、事实性陈述及来源状态、潜在问题。
- **Scene JSON**：按 references/scene.schema.json 的真实 v2.1 字段生成，不可臆造字段。JSON 语法必须正确。未真实运行 validate.py 时明确写“按 Schema 编写；尚未由实际渲染器验证”。
- **QA Notes**：假设、缺失来源、需要人工核实之处、字幕与解说时间风险、文本溢出/遮挡风险、后续需要的工具和动作。

Agensi 只有文本/Agent 的情况下，这三种交付就是免费版的完整有效成果；绝不把“生成 JSON”宣传成“已生成视频”。

### 5.3 事实性内容和验证

保留旧 Skill 的 fail-closed 事实证据理念；区分“用户提供的事实”“已独立核验”“没有证据的待核实声明”。不得伪造 URL、来源摘录、人工批准或 verified 标记。旧 factcheck.py 的引文存在性检查**不是**事实真伪证明。无法核验时可以交付草案，但必须标记“不应发布为已核实视频”。

### 5.4 可选本地渲染

仅在用户授权且真实存在本地 checkout 时，检查 Python>=3.10、FFmpeg/ffprobe、依赖、适用字体及选定 TTS。使用现有 scripts/validate.py 与 scripts/pipeline.py 执行样例；报告真实命令、退出码与文件路径。离线 eSpeak 是功能验证声音，不能宣传为自然配音；Edge TTS 需要网络且可能失败；不得自动触发收费服务。

运行环境缺失时保持文本路径，并明确说没有生成/播放/审核 MP4。不得静默修改渲染引擎来让测试通过。

### 5.5 Agensi 按需读取与跨 Agent

SKILL.md 要清晰指示需要哪些 references、何时让 Agent 请求读取文件，不假定所有支持文件一开始就已被加载。不能依赖仓库 AGENTS.md、private Studio 文档、某个模型内置记忆或单一厂商 API。只使用已有真实功能，英文介绍配中英文例子。

## 6. 上架安全与许可规范

1. 正确 YAML frontmatter，至少 name / description；名称需通过平台唯一性校验。允许 version、tags、summary 等字段，但不得虚假宣传。
2. **v1 推荐不在 ZIP 中包含 Python 执行脚本**。若有充分理由引入脚本，则每个必须完全自包含、独立临时执行、不读取包内邻接文件、不读取隐私凭据；先取得所有者审查许可。
3. 禁止环境变量采集/外传、隐藏下载/执行、恶意提示注入、删除根路径、shell=True、curl|sh、混淆代码及不必要终端/网络权限。文案明确最低权限。
4. 核实所有第三方素材、配音服务、字体、图片及代码复制许可。旧仓库根目录在 2026-10-31 查询不到 LICENSE / LICENSE.md：**公开 GitHub 仓库不代表取得可再分发授权**。Agent B 只提出合适的许可证和素材处理建议，不擅自加上。
5. 上架发布必须等待项目所有者明确审定版权/许可证、隐私与安全、实际宣传能力。
6. LISTING.md 应含：英文名称、摘要/详细说明、受众、三个使用提示词、所需服务与权限、限制、FAQ、截图/示例建议、定价=FREE、源项目链接。不得包含站外付费升级/购买链接。免费版不要求支付账户。
7. Agensi 审核为 8 类安全扫描 + AI + 人工。提交前尽量本地模拟检测；不声称安全审查已通过，平台最终结果只有上传后才能确认。

## 7. A1–A11 客观验收条件

每项需在 PR 留下 PASS / FAIL / NOT RUN、执行环境、准确命令、真实输出、证据链接及对应提交 SHA。任何没有真实执行的检查都不能标 PASS。

**A1 — 隔离 Agent 运行：** 在无仓库上下文的新会话中，只输入 Agensi ZIP 能提供的 SKILL.md 和必要的按需读取 references，分别完成英文 brief 和中文 brief，输出三种交付成果。必须记录读取路径及过程，不靠私有文档或既有记忆。

**A2 — JSON 契约：** 英文、中文 example JSON 都通过实际旧版 scripts/validate.py；测试能检测 JSON 语法错误、缺失字段和非法场景。仅通过 json.loads 不等于 Schema PASS。不能运行时标 NOT RUN。

**A3 — 真正渲染：** 在有依赖的可执行环境，至少一个样例经过真实一键流程输出非零时长 MP4；用 ffprobe 证实视频/音频流，核对 SRT/timings、字幕/音频与影片范围；记录输出样片和实际运行数据。优先 eSpeak 离线测试，避免隐藏联网/收费。若缺环境标 NOT RUN，不能宣称完成此验收。

**A4 — 无运行环境回退：** 在没有终端、FFmpeg、TTS、本地 repo 的条件下，仍产生有效分镜/JSON/QA；明确承认没有生成 MP4，不擅自下载/安装工具。

**A5 — 事实来源：** 输入含未核实具体事实时，不伪造来源或 verified 标志；明确区分来源有无，避免把引用匹配当成实质核实。

**A6 — ZIP 完整性：** 自动构建、文件 allowlist、根 SKILL.md、只有一个 SKILL.md、文件个数/大小受控；ZIP 内文本可解码，不存在秘密、无关文件、可执行二进制、绝对路径、路径穿越、嵌套 ZIP；references/ 相对路径完整；产出文件清单和 SHA256。两次从相同输入构建得到可复现内容。

**A7 — 权限与安全：** 完成基础 secret/prompt-injection/网络/危险命令扫描并人工复核告警；纯文本输出无需用户本地 shell 权限，只有可选渲染才申请权限。

**A8 — 版权与许可：** 提交明确的第一方/第三方许可证核查表，列出不可分发项、需要所有者决定的许可证和引用要求；未获所有者批准前将发布标 BLOCKED。

**A9 — 商品页准确性：** 英文上架文案准确描述“结构化分镜与 Scene JSON”，不承诺默认生成 MP4、真实 TTS、交互画布、自动事实核实、独立 QA 或完全自动安装，披露本地渲染前提。

**A10 — 回归与工程边界：** 已有单元测试实际运行且结果记录；PR 不改核心渲染/生产门禁，不更改私有仓库、不上传钥匙或视频、不破坏已锁定内容。并发工作已确认：此公开旧仓库存在 PR #38（TTS）和 PR #39（可选制作检查），Agent B 不得覆盖其文件或自行合并。

**A11 — 双重审核与发布关口：** Agent B 实施完成后提交独立技术审核资料；只有所有者能决定许可证、合并、上架和发布。A1–A10 全部有证据仍不等于 A11 已通过。保持 PR Draft 直至明确批准。

## 8. Agent B 执行流程、所有权及交接

**起步：**
1. 阅读 Issue #40、此文档，以及 main 的 README.md、AGENTS.md、SKILL.md、references/scene.schema.json、scripts/pipeline.py 与当前所有相关 open PR。
2. 在 Issue #40 评论 **CLAIM — Agent B**，写出 AI/模型/工具、实际 GitHub actor、Session 标识、branch、改动文件范围、可能的文件冲突。GitHub 用户身份不能替代 AI 执行身份。
3. 认领后由 Agent B 单独向本 Draft PR 分支提交实现；如平台不允许推送原分支，建立单独分支并明确回报，未经协调不得另开竞争 PR 或覆盖其他代理提交。
4. 每达到 SKILL + 规范、双语示例、构建包 + 扫描、验证证据四个里程碑之一，在 Issue 评论实际提交 SHA、差异、测试、阻塞事项。
5. 结尾交付 HANDOFF，列明复现命令、示例输出、ZIP 文件清单和 SHA256、A1–A11 状态、未解决问题、请求所有者决策。

**不允许：** 自行 merge、上传 Agensi、创建收费配置、使用付费模型/服务、将用户授权推导为允许绕过其他发布审批。

### PR 最终交接模板

    Agent: Agent B — model/tool; GitHub actor; Session
    Issue: #40
    Draft PR: [URL]; Head commit: [SHA]
    Changed files:
    ZIP filename / SHA256 / content manifest:
    A1: PASS | FAIL | NOT RUN — evidence:
    A2: PASS | FAIL | NOT RUN — evidence:
    A3: PASS | FAIL | NOT RUN — evidence:
    A4: PASS | FAIL | NOT RUN — evidence:
    A5: PASS | FAIL | NOT RUN — evidence:
    A6: PASS | FAIL | NOT RUN — evidence:
    A7: PASS | FAIL | NOT RUN — evidence:
    A8: PASS | FAIL | NOT RUN — evidence:
    A9: PASS | FAIL | NOT RUN — evidence:
    A10: PASS | FAIL | NOT RUN — evidence:
    A11: PENDING REVIEW / OWNER APPROVAL
    Known limitations, blockers, suggested next step:
    Tested reproduction commands and real results:

## 9. 参考源代码（旧实现）

- https://github.com/huangyong7878/mg-animation-skill/blob/main/SKILL.md
- https://github.com/huangyong7878/mg-animation-skill/blob/main/scripts/pipeline.py
- https://github.com/huangyong7878/mg-animation-skill/blob/main/scripts/validate.py
- https://github.com/huangyong7878/mg-animation-skill/blob/main/references/scene.schema.json

**本 PR 目前只提交规范文档。所有测试和验收状态一律为未执行，不能把这份任务安排当成发布许可。**
