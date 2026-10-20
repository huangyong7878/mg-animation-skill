# 多模型动画协作调度器 — CLI v0.1

**本阶段已经实现本地状态机 + GitHub Issue/PR 人工触发的交接，不是自动模型调用平台。** 强模型、Muse 和 DeepSeek 暂时通过共享文件/仓库协作。后续可以把这些确定性步骤接进 API 或受控 GitHub Actions 工作流。

## 正式生产的 R0 派单门禁（先锁内容，后做动画）

`prepare` 原有参数仍用于技术验证/原型，允许 `draft`；
正式业务必须加 `--formal`，同时提供 R2/R3 审定的
script、storyboard、plan、approved AV cues、`script_lock.json`，
以及人类试听批准的原始 WAV、measured timings、`voice_lock.json`。
如果缺了任一文件或内容哈希/导演分镜发生变化，**拒绝派给 R4**。

正式 `receive` 还会复核 R0 最初批准的 Script/Voice Lock 是否等于
R4 交付包中的原始记录，验证 Media Manifest 的所有 SHA256；
正式 `release-check` 会再核实它们。因此模型不能只在最后偷偷修改台词
或更换配音。R5/R7 仍独立决策，元数据检查不验证真实批准人身份。
使用命令和返工范围参见 [Stage D 手册](../docs/STAGE_D_FINAL_HANDOFF.md)。

## 流转状态

prepared → published（可跳过）→ implementation_received → review_pending
- QA pass → qa_passed（草稿配音仍**不得发布**）
- QA rework → rework_requested → 下一轮 implementation_received
- QA blocked 或达到返工上限 → escalation_required（交给强模型/人工重新定位问题）

创建 Issue 和在 PR 写反馈**不会自动发生**，需要显式执行 publish / feedback 命令；所有 GitHub CLI 调用均使用参数数组，不运行拼接的 Shell 命令。不会合并 PR、重写 main、发布成片或调用付费模型。

## 先跑一个安全的示例

在仓库根目录运行：

~~~bash
python -m pip install -r requirements.txt

python workflow/orchestrator.py prepare \
  --spec examples/workflow_orders_spec.json \
  --workdir work/orders_test \
  --executor muse

# 只预览将要执行的 gh 命令，不写入 GitHub
python workflow/orchestrator.py publish \
  --workdir work/orders_test \
  --repo huangyong7878/mg-animation-skill --dry-run

python workflow/orchestrator.py status --workdir work/orders_test
~~~

`prepare` 会在 workdir 生成当前版本的 `director_spec.json`、`executor_task.md` 和 `state.json`。拒绝覆盖一个已有非空工作目录；规格指纹使用 `canonical_digest`，保证其他模型不能无声更换要求。

## 开始实际合作

1. **强模型设计**：修改/生成导演规格，运行 `workflow/check_handoff.py --spec ...`，用户确认规格（草稿可以制作无声原型）。
2. **GitHub 建 Issue**：安装并登录 GitHub CLI gh（`gh auth login`），去掉 `--dry-run` 执行 `publish`。此步骤会在指定仓库创建真实 Issue。
3. **执行模型实现**：Muse / DeepSeek 阅读 Issue 中的任务及 `director_spec.json`；在功能分支创建 Python/SVG/Canvas 等动画，渲染 MP4、关键帧，提交源码并开 PR。填写符合 Schema 的 `delivery.json`，`implementation_commit` 必须是其**完整 40 位 SHA**。
4. **接收实现**：可选用 `--repo` 和 `--pr` 验证 delivery commit 是否等于线上 PR HEAD；实现文件要位于 `--artifact-root` 下，且能由本地程序读取。无需把大视频直接提交 Git；可以从 CI Artifacts 下载到工作目录，具体存储链路尚未自动化。
5. **独立强模型 QA**：运行 `review-package` 生成 QA Prompt 和 `qa_template.json`，在独立模型上下文里观看真实视频，输出 `qa_report.json`。
6. **记录并反馈**：运行 `record-qa` 更新状态。若需返工，生成 `rework_task.md`；可用 `feedback --dry-run` 检查，再正式向 PR 发表评论。原版 QA 不能用于新 commit。
7. **最终门禁**：须使用已批准规格、正式音频及时间轴 SHA、Stage D 交付、独立 QA 全通过，再运行 `release-check`。门禁检查的是**结构与字节一致性**，不会判断视频美术/事实是否真实正确。

~~~bash
# 以下路径示意真实交付产生后如何操作
python workflow/orchestrator.py publish \
  --workdir work/orders_test \
  --repo huangyong7878/mg-animation-skill

python workflow/orchestrator.py receive \
  --workdir work/orders_test \
  --delivery work/executor/delivery.json \
  --artifact-root work/executor \
  --repo huangyong7878/mg-animation-skill \
  --pr 4

python workflow/orchestrator.py review-package --workdir work/orders_test

# 独立 QA 人工/外部模型审查实际视频后，写好完整 qa_report.json
python workflow/orchestrator.py record-qa \
  --workdir work/orders_test \
  --qa work/reviewer/qa_report.json --max-attempts 2

python workflow/orchestrator.py feedback \
  --workdir work/orders_test \
  --repo huangyong7878/mg-animation-skill --pr 4 --dry-run

# 需要明确执行才能真正向 PR 写评论
python workflow/orchestrator.py feedback \
  --workdir work/orders_test \
  --repo huangyong7878/mg-animation-skill --pr 4

python workflow/orchestrator.py release-check \
  --workdir work/orders_test --artifact-root work/executor
~~~

示例里的 PR 编号是**占位**，不表示已创建该 PR。示例导演规格仍是 `draft`，只能测试原型阶段。

## 注意事项

- 本地 `state.json` 是工作状态日志，不是加密审计/权限系统。多进程同时执行、断点恢复与线上状态双向同步暂未实现；同一个工作区不要并发操作。
- GitHub 远程核对使用 `gh pr view --json headRefOid,url,state`。本地纯离线模式无法验证 SHA 真实性；启用 `--repo`、`--pr` 可进行真实远程核对。
- QA 包只生成空白待审核模板；**不等于已调用强模型，也不代表已看过视频**。
- 原始素材、无信任 AI 生成代码须在隔离容器中运行；本调度器不会执行交付的源码，只检查文件存在性。
- GitHub CLI 权限应按最小权限原则管理；没有配置凭证时，保留 `--dry-run`。
- 如果 PR #2 尚未合并，这个阶段的 PR 应基于 PR #2 分支，合并时先合并 PR #2 再调整本 PR 的目标分支，避免混杂历史。
