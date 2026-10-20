# Pilot 001：GitHub Actions 自动渲染及 QA 制品交接

## 作用和边界

`.github/workflows/pilot-render-artifacts.yml` 在 **Pilot 001 的动画源码、场景 JSON 或构建脚本相关文件**发生 PR 变更时自动执行；也允许在 GitHub Actions 页面用 **Run workflow** 手工触发。合并到 main 且相关文件发生变更时也自动执行。

自动步骤：

1. 从精确的 PR 源码 commit checkout（不是 GitHub 自动生成的 PR merge commit）。
2. 安装 Pillow、jsonschema、FFmpeg 及 Noto CJK 字体，在无机密信息的 GitHub Runner 上执行场景校验和实际 H.264 渲染。
3. 用 `ffprobe` 验证 **960×540、24 FPS、312 帧、13 秒、无声轨**。
4. 从真实 MP4 提取关键帧，在 5.3 秒附近做密集抽样，生成联系表及证据索引。
5. 生成和该 commit 绑定的 `delivery.json`，`media_manifest.json`，以及一个包含真实视频/证据/审核角色的 `qa_review.zip`。
6. 上传名为 `mg-orders_two_routes-r1-ci-<run_id>-<source_sha12>` 的 GitHub Actions Artifact（保留 30 天）。

**此阶段不调用 Muse、ChatGPT、Claude 或 Gemini，不生成真实 `qa_report.json`，不做视频审查或自动返工。** 包内模板决策为 `pending`，必须由隔离的具备视觉能力的 R5 审核模型真实观看 MP4 后填写。也不会自动审批规格、修改 PR 评论、合并 main 或发布视频。

## 如何触发

- 修改 `scripts/primitives/orderflow.py` 后创建/更新 PR：自动触发。
- 在 GitHub 仓库打开 **Actions → Pilot 001 Render and QA Artifact → Run workflow**，选择包含此 workflow 的分支（合并后可选 main）。
- 打开本次 GitHub Actions run，找到 **Artifacts**，下载上述制品包。下载需要合适 GitHub 访问权限，且要在制品过期前完成。

## 如何交给第二个强模型审片

不需要再要求 Muse 自行打包：

1. 下载 Actions 的 Artifact ZIP，提取其中的 `qa_review.zip`。
2. 在另一个具有视频能力的模型开启全新对话，上传 `qa_review.zip`。
3. 给它指令：**“请先读 START_HERE.md 和 role.md，担任 R5 独立视觉 QA；真实观看 media/render.mp4，参考 media/evidence/，输出严格符合 contract.schema.json 的 qa_report.json。不能实际观看时保持 pending。”**
4. 让 R0 在获取真实 QA 后运行 `workflow/check_handoff.py --spec ... --delivery ... --qa ...`，由调度器接收判定；无声 Stage B 的通过不等于正式有声版发布。

媒体 ZIP 同时包含 `director_spec.json`、`delivery.json`、`media_manifest.json`、视频、关键帧、真实源码快照、`build_log.txt` 和 `qa_review.zip`。其中的源代码快照便于当前 `orchestrator.receive` 的相对路径检查，Git commit 仍然是源码权威版本。

## 为什么现在只支持 Pilot 001？

通用 MG 项目可能有多个镜头、不同 renderer 与自定义参数。当前方案直接使用已验证的 `work/orders_pilot/scene.json`，并显式核对对应导演规格、媒体尺寸和时长，**没有**在工作流里执行任意模型提供的字符串命令。

推广到新项目应添加受版本控制的项目 build recipe 和无秘密执行环境；再接收 Muse / DeepSeek 适配器输入，之后才能增加 R5 多模态 API 调用。

## 资源与安全

- 本工作流仅有 `contents: read` 权限，`checkout` 不持久化凭证，不读取模型 API Secrets。
- 渲染运行来自 PR 的实现代码，必须视为非可信输入；GitHub 托管 Runner 负责隔离。不要将本 Action 改成 `pull_request_target` 并授予 secrets 或写入权限。
- 每次源码修改可能触发一次真实视频渲染并消耗 Actions 分钟数。通过 `paths` 过滤减少无关触发；可以手动取消、禁用 workflow。
- 后续真正需要更多模型调用时，先另行定义配额、超时、重试和费用上限，避免失控。
