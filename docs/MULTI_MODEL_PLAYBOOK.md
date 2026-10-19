# MG 动画多模型协作：完整操作手册与角色提示词

> **版本**：v1.0（2026-10-19）
> **对象**：项目负责人，以及使用 ChatGPT、Claude、Gemini、Muse、DeepSeek、Codex 或其他模型的操作者
> **仓库**：https://github.com/huangyong7878/mg-animation-skill
> **状态**：此文档是可执行的人工/半自动协作 SOP，**不是**已经接好所有模型 API 的全自动平台。

## 0. 五分钟总览

不绑定任何模型厂商。只要求角色输出满足同一套协议、拥有实际执行需要的工具，并对真实媒体留下可追溯证据。

~~~text
人类项目负责人 / 流程调度员
  ├─ [可选] 事实研究模型 → evidence.md / sources
  ├─ 强模型·创意导演 → storyboard.md
  ├─ 强模型·总导演/技术规格负责人 → director_spec.json (draft)
  │      ↓ 人类审分镜；正式配音与发布需另行批准
  ├─ 低成本代码模型·执行工程师 → 代码 PR + 实际 MP4 + delivery.json
  ├─ 独立强模型·视觉 QA → qa_report.json
  │      ├─ pass → 受审批与发布门禁约束
  │      └─ rework → 返工监督 → 执行工程师新 commit / 新 MP4 → 新 QA
  └─ 人类发布负责人 → 确认成片后决定是否合并/归档/发布
~~~

| 角色 | 默认模型建议（举例，不代表内置集成） | 输入 | 输出 |
|---|---|---|---|
| R0 项目负责人/调度 | 人类 + 任一具备 CLI/GitHub 访问能力的 Agent | 项目需求、规格/交付/QA | GitHub Issue、状态、审批与收发文件 |
| R1 事实研究员（可选） | 有可信网络检索能力的模型 | 文案、事实诉求 | sources.md / evidence.md（带出处） |
| R2 创意导演 | ChatGPT/Claude/Gemini 等强推理模型 | 文案、受众、事实 | storyboard.md |
| R3 总导演 / 技术规格负责人 | 任一强模型 | 分镜、风格、已有组件能力 | director_spec.json + director_notes.md |
| R4 动画实现工程师 | Muse/DeepSeek/Codex 等能执行代码的模型 | 锁定版本规格 + 项目仓库 | 源码 PR、渲染 MP4、delivery.json、媒体清单 |
| R5 独立视觉 QA | **能真实看视频**的强多模态模型 | 规格、delivery、真实视频/连续帧 | qa_report.json |
| R6 返工监督 | 强模型或受控 Agent | 不合格 QA、规格、交付 | rework_task.md / PR 反馈 |
| R7 发布负责人 | 人类；可用模型辅助检查 | 正式音频、全部门禁与 QA | 发布批准/拒绝与归档记录 |

**可以合并角色**：一个强模型可先做 R2 再做 R3。但 **R4 制作和 R5 独立 QA 不得共用同一执行上下文**；仅改一个聊天角色名不等于独立审核。人类 R0/R7 的批准永远不能由模型代签。

### 0.1 真正已经实现 vs 尚未实现

已实现：`workflow/role_pack.py` 打包三个角色任务；`workflow/check_handoff.py` 做 JSON/版本检查；`workflow/orchestrator.py` 用本地状态与显式的 `gh` Issue/PR 命令交接；`workflow/media_manifest.py` 做媒体文件字节清单；`scripts/validate.py`、`scripts/contract_check.py`、`scripts/render.py` 提供现有场景引擎与校验。

**尚未实现**：平台无关的一键调用 ChatGPT/Claude/Muse/DeepSeek API、自动让 Muse 领取 Issue、为任意自定义镜头自动在 Actions 中渲染上传、自动观看 MP4、自动合并与正式发布。模型收到提示词后，仍需它自身具备仓库、终端、视频等权限。

### 0.2 环境准备（一次性）

~~~bash
git clone https://github.com/huangyong7878/mg-animation-skill.git
cd mg-animation-skill
git checkout main
git pull --ff-only

python -m pip install -r requirements.txt
python -m unittest discover -s tests -v

# 这些命令用于检查环境，非每个角色都需要运行
python workflow/orchestrator.py --help
python workflow/role_pack.py --help
python workflow/media_manifest.py --help
~~~

需要真正渲染时还须正确安装 FFmpeg、字体、Pillow 等环境，参考仓库 `README.md` 和 `SKILL.md`。做 GitHub Issue/PR 操作需安装 GitHub CLI、`gh auth login` 且具有相应仓库权限。不要把 Token 放进 Prompt 或仓库。

## 1. R0 — 项目负责人 / 流程调度员

**适用模型**：人类直接操作最稳妥；有终端和 GitHub 权限的受控 Agent 也可扮演。主要负责**状态和版本**，不是替执行模型写动画。

**给模型的完整提示词（复制以下内容）**

~~~text
你是 MG 动画项目的流程调度员（Orchestrator），不是创意导演或影片 QA。
仓库：https://github.com/huangyong7878/mg-animation-skill
先读 workflow/ORCHESTRATOR.md、workflow/README.md、
docs/adr/0001-media-artifact-policy.md、contracts/ 下的 Schema。
你的任务：固定导演规格 SHA/Revision；通过 GitHub Issue 派单；接收实施 PR、
delivery.json 与实际媒体制品；核对 commit、spec_sha256、attempt；
在独立审查结束后记录 QA 结果；必要时派定点返工。
只执行确实已经实现的 CLI，记录实际 stdout 和链接。
凡创建 Issue、发表 PR 评论或合并/发布等外部写入动作，先确认明确授权；
绝不擅自合并 main、修改导演审批状态或宣称 QA 已通过。
缺视频、缺 Git SHA、缺人工确认时明确阻断，不得填占位值伪造结果。
输出：当前项目状态、源代码 PR、媒体制品 URL、下一责任人及所需动作。
~~~

**实际命令**

~~~bash
# 首次准备：复制冻结当前设计规格，生成执行模型任务单。
# --outdir 不存在：prepare 需要全新的空目录；不能覆盖已有任务。
python workflow/orchestrator.py prepare \
  --spec examples/workflow_orders_spec.json \
  --workdir work/orders_two_routes_run01 \
  --executor muse

python workflow/orchestrator.py status --workdir work/orders_two_routes_run01

# 仅预览真实 GitHub Issue 创建命令；不会写入 GitHub
python workflow/orchestrator.py publish \
  --workdir work/orders_two_routes_run01 \
  --repo huangyong7878/mg-animation-skill --dry-run

# 当确实需要新 Issue 且已授权，去掉 --dry-run 才会真实创建：
# python workflow/orchestrator.py publish --workdir work/orders_two_routes_run01 \
#   --repo huangyong7878/mg-animation-skill
~~~

**Issue #4 已存在**：`https://github.com/huangyong7878/mg-animation-skill/issues/4`。该试点**无需再次 publish**；`prepare` 后可直接把现有 Issue #4 给执行模型，并在它交付时执行 `receive`。现有 CLI 并不会自动把 Issue #4 登记回本地 state，也不会监视 Issue 动态。

## 2. R1 — 事实研究员（可选但真实知识类影片建议有）

**适用模型**：能真正联网检索和读取来源的模型。若仅制作无事实主张的示意短片（如 Issue #4），可以明确标记为“教学虚构案例”，不需要发明真实运营数据。

**提示词**

~~~text
你是 MG 教育视频的事实研究员。请核验我提供的解说文案与画面数据，
逐条列出 claim_id、精确主张、数据口径、时间范围、原始权威出处 URL、
相关证据、相反证据/争议、核验状态及是否适合上画面。
区分“真实统计”“合理推断”“纯演示数字”。没有核对过来源就写未核实；
不要编造来源、网页原文或把相关性写成因果。
数值与图表必须可重算；对于关键结论，要求人类或可信独立研究复核。
交付 evidence.md 或 sources.md，列出允许呈现与不能呈现的内容。
若没有联网工具，应直说无法核验，不要标为 verified。
~~~

**相关命令（注意检查范围）**

~~~bash
# 下列命令只适用于已含 claims、factual 标记的引擎 scene JSON。
python scripts/factcheck.py PATH_TO_SCENE.json --report work/factcheck.json

# 如需请求网页内容核对（有网络时）；这不是“自动判定事实真假”。
python scripts/factcheck.py PATH_TO_SCENE.json --fetch-sources \
  --report work/factcheck_online.json
~~~

交接给 R2/R3：`evidence.md`、能用到的经过核对的数字、所有禁止被当作真实统计的数据。**没有固定的 R1 机器 Schema**，此处是工作约定，不要声称 `factcheck.py` 已经提供外部模型事实研究服务。

## 3. R2 — 创意导演（强模型）

**适用模型**：ChatGPT、Claude、Gemini 等；要求长文本和创作能力。这个阶段不直接写代码，也不应让既有原语限制画面想象。

**提示词**

~~~text
你是本项目的“创意导演”，负责用清楚、生动的画面讲好教育叙事，
不是动画程序员。请先阅读 references/creative-director.md、
references/storyboard-contract.md、roles/DIRECTOR.md（整体目标）、
roles/QUALITY_RUBRIC.md。
输入：我给出的文字 Brief、事实研究和受众/风格偏好。
请先按意义拆分 Beats，再决定 Shots；不要强制一段文字一个镜头。
分镜每镜写明：主题/关联 Beats、观众实际看见的对象与变化、
进入/退出镜头方式、阅读停顿、因果表达、情绪、转场意图与时间估计。
过程动画要在画面里表现“事情如何发生”，不能只有静态图标与数字。
分镜用自然视觉语言，不写程序坐标、animation 参数、引擎 JSON。
无真实音频时只写估计时间，不宣称已经达到词级/句级配音同步。
最终交付 storyboard.md；列出缺失事实、尚未确定的设计决策。
不要在没有用户确认时自称分镜已获批准。
~~~

**准备并分发角色任务包**

~~~bash
# 先创建真实 Brief：以下命令只复制文件，不会自动编文案
mkdir -p work/briefs
# 使用编辑器将项目需求/文案保存为 work/briefs/episode_001.md

python workflow/role_pack.py director \
  --brief work/briefs/episode_001.md \
  --out work/role_packages/episode_001_director

# 产出 work/role_packages/episode_001_director.zip
# 上传 ZIP 到模型；首先阅读 START_HERE.md、role.md
~~~

R2 可以只生成 `storyboard.md`；给 R3 的交接包括文案、分镜、事实材料和人类意见。`role_pack.py director` 实际包装的是**完整总导演角色**，不是专门的创意导演转换器；如果只采用 R2 单阶段，应在提示词中明确“先输出 storyboard”。

## 4. R3 — 总导演 / 技术规格负责人（强模型）

**职责**：将 R2 的创意分镜转换为**唯一、可机器校验**的合同，不负责替 Muse 写代码。也可以由一个强模型同时担任 R2+R3。当前角色主文件为 `roles/DIRECTOR.md`。

**提示词**

~~~text
你现在是 MG 动画总导演兼技术规格负责人。请读取：
roles/DIRECTOR.md、roles/QUALITY_RUBRIC.md、
references/technical-director.md、references/visual-contract.md、
contracts/director_spec.schema.json、SKILL.md。
输入：已讨论的 storyboard.md、Brief、事实证据、时间轴（如有）。
请把每个 Shot 的目的、必需可见实体、物体恒定身份、状态转换条件、
连续运动路径、数量/图形之间的计算关系和观众验收标准写具体。
对每个 shot 生成唯一的 must_show.id 与 continuous_motion.id；
render_mode 在 standard/custom 中选择，并说明能力缺口。
不要因为引擎支持简单卡片就将复杂流动暗中降级为箭头图。
输出完整导演规格 director_spec.json，严格符合 Schema；
同时给出 storyboard.md 和 director_notes.md，注明未验证事实和能力假设。
没有人类批准：approval.status=draft。
没有真实且锁定的配音/时间轴：narration.status=draft；
不得凭估计数字假造音频 sha256 或 approved_by。
如规格变更，revision 增加并重新生成规格指纹。
请实际执行校验命令并报告结果；无法运行请坦言未测试。
~~~

**实际命令**

~~~bash
# 模型将 director_spec.json 保存到真实工作目录后检查
python workflow/check_handoff.py \
  --spec work/episode_001/director_spec.json

# 获得 JSON 规范化指纹：交给执行模型绑定版本
python -c 'import json; from workflow.check_handoff import canonical_digest; p="work/episode_001/director_spec.json"; print(canonical_digest(json.load(open(p,encoding="utf-8"))))'

# 如果已有正式的 TTS timings，可一并打包给总导演
python workflow/role_pack.py director \
  --brief work/briefs/episode_001.md \
  --timings work/episode_001/timings.json \
  --out work/role_packages/episode_001_director_with_timings
~~~

**交接约束**：`director_spec.json` 的 `approval` 初始应为 `draft`；审查不等于擅自审批。不能把 Director Spec 与引擎使用的 `scene.json` 混为一谈：前者描述“必须表现什么”，后者是实现者的具体渲染输入。

## 5. R4 — 动画实现工程师（Muse / DeepSeek / Codex）

**适用模型**：具备 Git 仓库读写、Python、终端、FFmpeg 和渲染能力的代码模型。即使便宜但无法运行真实渲染器，也不符合这一职位要求。

**提示词：直接复制给 Muse/DeepSeek**

~~~text
你是 MG 动画实现工程师，只承担准确落地已确定的导演规格。
仓库：https://github.com/huangyong7878/mg-animation-skill
当前开发任务：https://github.com/huangyong7878/mg-animation-skill/issues/4
请从 main 拉取最新代码，再读 SKILL.md、scripts/engine.py、
scripts/primitives/、references/technical-director.md、
workflow/README.md、docs/adr/0001-media-artifact-policy.md、
contracts/delivery.schema.json 和 Issue 引用的 Director Spec。
首先运行现有测试，再用极简文字说明准备复用的原语和需要新增的能力。
随后直接动手编写、实际运行代码并渲染；不要重复输出冗长架构方案。
实现全部 must_show / continuous_motion，维持实体身份、时序和数学状态，
遇到引擎能力不足就申请/实现新原语，而不是悄悄删掉核心要求。
如果当前渲染引擎不支持文档中的通用 custom 动态模块加载，不得假称支持；
必须用注册原语或另写可复现的镜头渲染脚本，并报告具体实现途径。
本轮 Issue #4 的 director_spec 仍是 draft：只做无声原型，不能宣称成片获批。
完成后在新分支提交源代码和测试，创建 Draft PR；不要合并 main。
真正渲染 MP4、关键帧/必要连续帧；媒体不提交 Git，按 ADR 0001 提供
可访问的制品 ZIP、Actions Artifact 或独立存储链接。
delivery.json、media_manifest.json 与渲染的源码 HEAD SHA 绑定，并放入同一制品包，
列出真实已运行的测试、任何偏离和媒体路径。不编造测试、视频或链接。
输出：实现 PR URL、完整 commit SHA、实测构建命令、媒体制品访问方式。
~~~

**实现模型可运行的命令（在自己的工作环境里）**

~~~bash
git clone https://github.com/huangyong7878/mg-animation-skill.git
cd mg-animation-skill
git switch main
git pull --ff-only
git switch -c feat/pilot-orders-animation

python -m pip install -r requirements.txt
python -m unittest discover -s tests -v

# 仅在使用仓库的 JSON 场景引擎时执行以下步骤。
# 具体 scene 文件是实现模型产出的，不会由导演角色包自动生成。
python scripts/validate.py work/orders_two_routes/scene.json

# Visual Contract 从 director_spec.shots[*].visual_contract 提取成单独 JSON：
python -c 'import json; from pathlib import Path; s=json.load(open("examples/workflow_orders_spec.json",encoding="utf-8")); p=Path("work/orders_two_routes/shot_01_contract.json"); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(s["shots"][0]["visual_contract"],ensure_ascii=False,indent=2),encoding="utf-8")'

python scripts/contract_check.py \
  work/orders_two_routes/shot_01_contract.json \
  work/orders_two_routes/scene.json --strict \
  --report work/orders_two_routes/contract_report.json

# 使用 JSON 场景引擎渲染真实无声 MP4
python scripts/render.py work/orders_two_routes/scene.json \
  --out work/orders_two_routes/attempt-001/media/shot_01_silent.mp4

# 若采用独立 custom renderer，则运行其自己的可复现命令，
# 不要强行假装它符合 scripts/render.py 的输入格式。
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate \
  -of json work/orders_two_routes/attempt-001/media/shot_01_silent.mp4

# 视频真实生成后，从同一 MP4 抽取带实际时间戳的审查关键帧
mkdir -p work/orders_two_routes/attempt-001/media/keyframes
ffmpeg -hide_banner -y -ss 5 -i \
  work/orders_two_routes/attempt-001/media/shot_01_silent.mp4 \
  -frames:v 1 work/orders_two_routes/attempt-001/media/keyframes/shot_01_005000.png

# 确认代码和测试完整，再提交源文件；不要 git add work/ 或 MP4
git add scripts/ tests/   # 按实际修改范围选择，不要把不相关文件纳入
git commit -m "feat: implement two-order motion prototype"
git push -u origin feat/pilot-orders-animation
gh pr create --draft --base main --head feat/pilot-orders-animation \
  --title "Pilot 001: two order paths silent render" \
  --body "Implements Issue #4; media artifact supplied separately, QA pending."
git rev-parse HEAD
~~~

**重要顺序**：媒体实际渲染应该明确关联最终提交的源码 commit。上面仅给出开发命令顺序；最终交付前若再修改了任何影响渲染的代码，必须在**最终 commit** 上重新渲染并更新 deliverable。不要用旧 MP4 与新 HEAD 组成交付包。

**媒体和 delivery 的命令（执行者真实生成交付 JSON 后）**

~~~bash
# delivery.json 必须根据 contracts/delivery.schema.json 真实填写；
# implementation_commit = 最终 git rev-parse HEAD 的完整 40 位 SHA。
# 路径相对于下面的 artifact-root。
python workflow/check_handoff.py \
  --spec examples/workflow_orders_spec.json \
  --delivery work/orders_two_routes/attempt-001/delivery.json

python workflow/media_manifest.py create \
  --spec examples/workflow_orders_spec.json \
  --delivery work/orders_two_routes/attempt-001/delivery.json \
  --artifact-root work/orders_two_routes/attempt-001 \
  --backend local \
  --out work/orders_two_routes/attempt-001/media_manifest.json

python workflow/media_manifest.py verify \
  --manifest work/orders_two_routes/attempt-001/media_manifest.json \
  --artifact-root work/orders_two_routes/attempt-001 \
  --spec examples/workflow_orders_spec.json \
  --delivery work/orders_two_routes/attempt-001/delivery.json
~~~

`--backend local` 只是标记制品还在执行者本地，**不代表上传到 GitHub**。只有真实的 GitHub Actions 构建/上传作业才能正确使用 `--backend actions --artifact-name ...`。当前仓库还没有对任何自定义镜头通用的 CI 自动渲染上传功能。

## 6. R5 — 独立视觉 QA（另一强多模态模型）

**角色分配**：可以用 ChatGPT、Claude、Gemini 或其他真正具有可用视频/连续帧读取能力的模型。审查环境必须能取得**实际媒体字节**；只收到 GitHub PR 链接或者截图摘要的模型不能声称审查了完整动画。

**提示词**

~~~text
你是独立 MG 动画视觉 QA 审查官，不是导演，也不是实现工程师。
请先阅读 roles/REVIEWER.md、roles/QUALITY_RUBRIC.md、
contracts/qa.schema.json、当前 director_spec.json 与 delivery.json。
你必须实际查看本次构建的 MP4/连续帧与真实时间戳，先静音看全片，
复述观众真正会看到的因果过程；不要先用代码推断视觉表现。
逐个 shot 检查所有 must_show 与 continuous_motion，逐条产生 checks，
按实际媒体和时间点写 evidence。
重点关注：对象身份连续、路径不中断、库存分支与结果一致，
物理/数学状态一致、画面可读性、节奏与字幕（如有）。
发现问题生成 P0/P1/P2 findings，每项包含观察、预期、证据和定点修复要求。
不接受“代码含 contract 标签所以一定显示正确”的说法。
如果无法打开真实视频/足够连续帧，返回 pending 和 needs_review；
不编造所看内容、不填假的 reviewer 状态、不宣布 pass。
输出严格符合 contracts/qa.schema.json 的完整 qa_report.json，
绑定本次 spec_sha256、revision 和 implementation_commit。
~~~

**准备审片包、接收版本、记录 QA**

~~~bash
# 用实际 PR 编号替换 IMPLEMENTATION_PR_NUMBER，不要将 Issue #4 当作 PR。
# 从执行者制品下载/拷贝 delivery 和视频到 work/executor/attempt-001。
python workflow/orchestrator.py receive \
  --workdir work/orders_two_routes_run01 \
  --delivery work/executor/attempt-001/delivery.json \
  --artifact-root work/executor/attempt-001 \
  --repo huangyong7878/mg-animation-skill \
  --pr IMPLEMENTATION_PR_NUMBER

# 生成一份 pending 的审片提示/模板；本命令本身不调用审片模型
python workflow/orchestrator.py review-package \
  --workdir work/orders_two_routes_run01

# 用实际媒体打包给另一模型；可以添加多个 --frame
python workflow/role_pack.py qa \
  --spec work/orders_two_routes_run01/director_spec.json \
  --delivery work/executor/attempt-001/delivery.json \
  --video work/executor/attempt-001/media/shot_01_silent.mp4 \
  --frame work/executor/attempt-001/media/keyframes/shot_01_005000.png \
  --out work/role_packages/pilot_001_qa

# 将 pilot_001_qa.zip 上传到独立多模态模型。
# 审查模型完成真实检查并返回 work/reviewer/qa_report.json 后：
python workflow/orchestrator.py record-qa \
  --workdir work/orders_two_routes_run01 \
  --qa work/reviewer/qa_report.json --max-attempts 2
~~~

`role_pack.py qa` 目前只核对媒体**存在、非空、文件扩展名**；它不证明媒体可解码。建议另用 `ffprobe` 验证视频元数据并让审查模型实际读取。`record-qa` 只验证结构、版本和状态，**不能证明**声明的独立上下文或所写证据真实发生。

## 7. R6 — 定点返工监督（强模型或规则 Agent）

**提示词**

~~~text
你是 MG 动画返工监督。读取 roles/REWORK_SUPERVISOR.md、
当前 director_spec.json、delivery.json、qa_report.json。
只针对独立 QA 已发现、有具体时间戳/证据的问题生成返工任务。
每条任务必须引用 finding ID、严重程度、镜头、观察到的错误、
应实现的状态、最小修复动作和真实视频复测方法。
优先 P0 → P1 → P2。保留所有已通过的元素，不重写导演规格。
若是导演规格矛盾，停止给工程师盲派单，升级总导演并提高 revision。
每轮返工生成新的代码 commit、新视频、新 delivery 和独立新 QA；
原有 QA 不再适用于新 commit。最多正常返工两轮，仍失败则升级。
输出 rework_task.md；如证据不足，写明需要什么媒体/信息才能执行。
~~~

**打包与发表 PR 反馈**

~~~bash
# 只有 qa_report.json 的 decision 为 rework/blocked 才能打包
python workflow/role_pack.py rework \
  --spec work/orders_two_routes_run01/director_spec.json \
  --delivery work/executor/attempt-001/delivery.json \
  --qa work/reviewer/qa_report.json \
  --out work/role_packages/pilot_001_rework

# orchestrator 在 record-qa 失败后自动生成 rework_task.md
# 下面先预览、不发表 GitHub 评论
python workflow/orchestrator.py feedback \
  --workdir work/orders_two_routes_run01 \
  --repo huangyong7878/mg-animation-skill \
  --pr IMPLEMENTATION_PR_NUMBER --dry-run

# 得到明确授权，且 PR HEAD 仍与待修复提交一致后，才真正评论：
python workflow/orchestrator.py feedback \
  --workdir work/orders_two_routes_run01 \
  --repo huangyong7878/mg-animation-skill \
  --pr IMPLEMENTATION_PR_NUMBER

python workflow/orchestrator.py status \
  --workdir work/orders_two_routes_run01
~~~

返工后的第二轮须让 Muse 新提交、新渲染、新交付，重新执行 `receive → review-package → record-qa`。不能只更改 `qa_report.json` 来“通过”测试。

## 8. R7 — 人类发布负责人（模型只能辅助）

**提示词：可给技术审计模型，但其意见不是批准本身**

~~~text
你是 MG 成片发布前技术审计助手，不拥有人工发布审批权。
读取正式批准的 director_spec.json、锁定配音音频及 timings、
最终实施 delivery.json、media_manifest.json、qa_report.json、
真实成片以及 GitHub PR 状态。
检查：导演规格是否已由人类批准、音频与时间轴 SHA 匹配、
实施是否对应当前 commit、Stage D 是否完成、
QA 每条 requirement 是否已实际审查、是否存在 P0/P1、
制品是否能访问并长期归档，以及内容/版权/事实/音画是否有未解决问题。
标注你亲自验证过的项目和只来自声明的项目。
输出 release_checklist.md：可发布/阻断/待人工决定，
每个阻断项带事实依据。不要替人类批准、合并或发布。
~~~

**正式发布前的门禁命令**

~~~bash
python workflow/check_handoff.py \
  --spec work/orders_two_routes_run01/director_spec.json \
  --delivery work/executor/final/delivery.json \
  --qa work/reviewer/final_qa_report.json \
  --release \
  --artifact-root work/executor/final

python workflow/orchestrator.py release-check \
  --workdir work/orders_two_routes_run01 \
  --artifact-root work/executor/final

python workflow/media_manifest.py verify \
  --manifest work/executor/final/media_manifest.json \
  --artifact-root work/executor/final \
  --spec work/orders_two_routes_run01/director_spec.json \
  --delivery work/executor/final/delivery.json
~~~

当前 Issue #4 的 director_spec 是 **draft** 且配音 **draft**，所以 `--release` **应当失败**；这不是系统故障。只有用户真正审批分镜、正式音频和 timings 已锁定、完成 Stage D 与独立 QA 后才能尝试放行。即便门禁通过，最后仍需人工认可作品。

## 9. MP4 与关键帧约定（所有角色必须遵守）

详细规则见 [ADR 0001](../docs/adr/0001-media-artifact-policy.md)。

~~~text
Git PR：源代码 / 测试 / 场景 JSON / 版本化导演规格
媒体制品（不进 Git）：
  media/shot_01_silent.mp4
  media/keyframes/shot_01_005000.png
  media/frame_sequences/...（需要证明连续运动时）
  delivery.json
  media_manifest.json
  build_log.txt
PR / Issue：真实制品链接 + 完整 source commit SHA + spec revision/SHA
~~~

- 预览件优先 GitHub Actions Artifact（建议 30 天）；若 Muse 在本地渲染、没有 Actions 上传工作流，则**先手工传 ZIP 或使用外部对象存储**，不可谎称已经上传。
- 关键帧适合检查构图，**不能替代连续视频的动态验收**。
- `delivery.json` 和 `media_manifest.json` 放在对应构建制品中：不在实现 PR 上单独提交一个“更新 delivery SHA”的 commit，否则 PR HEAD 会改变，反而形成版本自引用。
- `media_manifest.py` 只做文件大小、SHA256、路径与规格/交付绑定校验；**不会**调用模型、上传媒体或解码视频。
- 如果模型不能读 GitHub Actions Artifacts，请由操作员用真实 `gh run download` 下载后给模型上传 ZIP。不要仅让模型访问 PR 便要求其声称审片完成。

**从实际存在的 Actions 运行下载制品的命令（示意）**

~~~bash
gh run download ACTUAL_RUN_ID \
  --repo huangyong7878/mg-animation-skill \
  --name ACTUAL_ARTIFACT_NAME \
  --dir work/executor/attempt-001

python workflow/media_manifest.py verify \
  --manifest work/executor/attempt-001/media_manifest.json \
  --artifact-root work/executor/attempt-001
~~~

`ACTUAL_RUN_ID`、`ACTUAL_ARTIFACT_NAME` 必须来自真实构建记录，不存在就不能执行。

## 10. 不用 GitHub 连接器的模型如何工作

### A. 只有聊天和文件上传

1. 人类提供 repo 文件或打好的 Director ZIP（`role_pack.py director`）。
2. 模型返回完整的 `storyboard.md`、`director_spec.json`、`director_notes.md`。
3. 人类把这些文件交给有终端/GitHub 的执行 Agent。审片时再提供带媒体的 QA ZIP。
4. 人类运行 JSON 校验和 GitHub CLI；模型不要自称它能够直接提交 Git。

### B. 有 GitHub 读写 + 终端，但不支持视频

可以做 R0、R3、R4（如果能够渲染），但**不能担任独立 R5 视频 QA**。从视频采样连续帧交给另一具备视觉能力的模型；如仍不足以核实运动则保持 pending。

### C. 有原生视频阅读，但不能运行代码

优先做 R2 或 R5。由有终端的角色打包真实媒体与规格，模型返回 JSON；再由 R0 运行 `check_handoff.py` 验证。无需让 QA 模型接触源码。

### D. 模型 API 自动化

本仓库当前没有通用 Provider Adapter。若以后接 API，必须显式保留输入来源、模型版本、Token 成本、超时/重试、媒体可访问性、隔离上下文、审批与真实证据。**没有接上的接口不得写成已实现命令。**

## 11. 用 Issue #4 做一次完整演练（当前最短路径）

真实 Issue：[Pilot 001](https://github.com/huangyong7878/mg-animation-skill/issues/4)。**这是一份已经存在的开发任务，不要重复创建。**

1. R0 运行 `orchestrator prepare`（`--spec examples/workflow_orders_spec.json`，新 `--workdir work/orders_two_routes_run01`）；若已经准备过，用 `status` 查，不要覆盖。
2. 把 Issue #4 和第 5 节的 R4 提示词交给 Muse，明确要求从最新 `main` 实现**无声原型**。
3. Muse 提交独立实现 PR 与可访问媒体制品，提供完整最终源码 commit SHA。**Issue 编号 4 不是 PR 编号**；以实际新 PR 编号为准。
4. R0 下载真实交付文件/MP4 到本地，运行 `orchestrator receive --repo ... --pr 实际PR编号`；如果没有媒体不可进行 QA。
5. R5 使用 `role_pack.py qa` 的独立上下文审实际 MP4；`record-qa` 写入真实结果。
6. 不合格时 R6 反馈到正确的实现 PR，限两轮；下一轮以新 commit 重新生成媒体和独立 QA。
7. 这轮的成功标准是**无声动画质量与分工闭环**，不是正式有声版发布。`--release` 在当前 Draft Spec 下应当阻断。

## 12. 故障与快速判断

| 表现 | 正确处理 |
|---|---|
| 模型说“已完成”但没有 MP4 | 视为未交付；要求真实文件及渲染命令 |
| 只有 3 张截图、声称连续水流完全正确 | QA = pending / needs_review，索取连续片段 |
| 源码已更新、只有旧 MP4 | 重新渲染；不能拿旧视频对应新 SHA |
| `spec_sha256` 与当前规格不符 | 阻断交付，核对版本；不得修改 hash 欺骗检查 |
| QA 将代码/标签当成视觉证据 | 退回 R5 实际观看视频 |
| 模型想在一次 PR 提交 MP4 与关键帧序列 | 按 ADR 0001 放到独立媒体制品 |
| QA 提示词里要求调用不存在的“自动 Muse API” | 改为实际人工交接或实现/审查 Provider Adapter |
| Director Spec 未审批、无正式配音，却要求正式发布 | `--release` 阻断；先做人类审核与锁定 |
| 同一执行模型自己评出“满分” | 不是独立 QA，换隔离上下文或不同模型 |
| 两轮返工仍然不能通过 | 升级总导演，检查设计歧义/原语能力缺口 |

## 13. 规范和事实来源（仓库内）

- [模型无关角色包](../roles/README.md) 与 [总导演](../roles/DIRECTOR.md)、[视觉审查](../roles/REVIEWER.md)、[返工监督](../roles/REWORK_SUPERVISOR.md)、[质量标尺](../roles/QUALITY_RUBRIC.md)
- [创意导演](../references/creative-director.md)、[技术导演](../references/technical-director.md)、[分镜规范](../references/storyboard-contract.md)、[视觉契约](../references/visual-contract.md)
- [总导演规格 Schema](../contracts/director_spec.schema.json)、[交付 Schema](../contracts/delivery.schema.json)、[QA Schema](../contracts/qa.schema.json)、[媒体清单 Schema](../contracts/media_manifest.schema.json)
- [交接协议](../workflow/README.md)、[调度器操作说明](../workflow/ORCHESTRATOR.md)、[媒体存储 ADR](../docs/adr/0001-media-artifact-policy.md)
- [试点导演规格示例](../examples/workflow_orders_spec.json)

> 本手册描述的每项命令都以此仓库现有 CLI 入口为依据；路径以仓库根目录为工作目录。大写占位符、`PATH_TO_SCENE.json`、`episode_001`、`IMPLEMENTATION_PR_NUMBER` 需要替换成真实值，不是已经生成的资源或可以直接运行的真实项目。
