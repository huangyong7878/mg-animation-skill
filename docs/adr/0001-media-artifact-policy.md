# ADR 0001: 动画媒体的 Git / Artifacts 交付约定

- **状态：提案，待合并**
- 适用范围：所有使用 MG Director → Muse/DeepSeek Executor → Independent QA 的项目
- 背景：Git 应保存可复现的源代码与规范；MP4、关键帧序列是反复重新生成的大型二进制，不应令历史仓库持续膨胀

## 决议（v1）

**不要把渲染生成的 MP4、成组关键帧、连续帧、完整音轨提交到 Git。**
二进制渲染输出暂存于 **GitHub Actions Artifacts**；如不是由 GitHub Actions 生成，则先存于执行者本地或明确的对象存储中，不能冒称已上传 Actions。长期存档可迁往对象存储（S3/OSS/R2 等，需另行配置权限与成本预算）。

### 归属

| 内容 | 权威位置 | 说明 |
|---|---|---|
| Python/SVG/Canvas/场景 JSON/测试 | Git，镜头开发分支 → PR | 可复现和审查 |
| 正式导演规格/锁定语音的哈希记录 | Git | 规格审查与批准依既有 workflow 进行 |
| MP4/MOV/音频/连续帧/大量关键帧 | Actions Artifact / 对象存储 | 按一次**源代码 commit** 归档 |
| 展示缩略图或 contact sheet | 可选 Git | 最多 1 MB/张；所有其他渲染帧仍放制品包 |
| delivery.json / media_manifest.json | **同一次制品包** | 使用实际构建的源代码 commit SHA；不要写入同一个正在被追踪的实现 PR，以免自引用 |
| QA 报告/修复清单 | PR 评论 + 审查存档（文件或单独记录） | 必须引用**实际审查过的 commit + artifact/run**；不得复用旧 QA |

此约定优先于早期“delivery.json 一定进入同一 PR”的泛化说法。JSON Schema 仍保留，改变的是**存放位置**，不是字段含义。

## 统一文件和命名

在执行者的工作目录（已被 .gitignore 忽略）：

~~~text
work/<project_id>/attempt-001/
  media/
    shot_01_silent.mp4
    keyframes/shot_01_000000.png
    keyframes/shot_01_005000.png
    contact_sheet.jpg
    frame_sequences/shot_01/...
  delivery.json
  media_manifest.json
  build_log.txt
~~~

- 一次制品建议命名：`mg-<project_id>-r<spec_revision>-a<attempt>-<source_sha12>`（同一完整 SHA 绑定在 manifest）
- 帧文件名称时间以毫秒为单位，例如 `shot_01_005000.png` 表示 5.000 秒。必须记录实际抽样位置，不凭文件名猜测连续性。
- 优先只留用于审片的**重点关键帧和关键时间段的连续帧**，不要无目的地导出全部 24 FPS 帧；必要的连续帧范围应作为有组织的短片或 ZIP 附加。
- 初始方案采用 960×540、24 FPS 的无声 H.264 MP4；这是当前 Pilot 001 的实际规格，其他项目应以其 director_spec.json 为准。

## GitHub Actions Artifact：临时交接

1. Muse 在 PR 分支提交**可复现的源代码**，CI 可按项目确定性命令渲染视频时，由无特权的 Actions 作业构建媒体。
2. **在同一个作业中**从构建实际采用的源代码 SHA 生成 `delivery.json` 与 `media_manifest.json`，与 `media/` 一起执行 `actions/upload-artifact@v4`。
3. 建议预览保留期 `retention-days: 30`。正式需要长期保留的成片**另行归档**。公开仓库 Actions 制品默认 90 天，可配置 1–90 天，不是永久存储。
4. PR 的说明/评论写入：构建运行 URL、artifact name、源码 commit SHA、规格 revision/SHA256；审查者下载该次精确制品，而不是“最新文件”的模糊链接。
5. QA 必须看到实际 MP4 和相应连续帧；拿不到视频时结论为 pending。QA 中出现的每个媒体引用必须能追溯具体 artifact。

**目前仓库没有通用的“为任意 Muse 生成镜头自动运行渲染代码 + 上传 Actions Artifact”流水线。** 项目需要先提供可执行的渲染命令与依赖，才能接通此步骤。不能将从 Muse 本地生成的视频**直接**看作已经存入 Actions；如果尚无 CI 渲染环境，先用可信对象存储或由操作者手工传送 ZIP，且报告所在位置。

### 下载范例

~~~bash
gh run download <run_id> --repo huangyong7878/mg-animation-skill \
  --name "mg-<project_id>-r<revision>-a<attempt>-<sha12>" \
  --dir work/downloaded/<project_id>/attempt-001

python workflow/media_manifest.py verify \
  --manifest work/downloaded/<project_id>/attempt-001/media_manifest.json \
  --artifact-root work/downloaded/<project_id>/attempt-001
~~~

请将 <...> 占位值替换为真实编号；下载需要 GitHub 仓库读取权限并在制品过期前完成。若模型平台没有 Actions 访问能力，由操作员**下载后上传 ZIP 给模型**，不得要求它仅凭 PR 链接就宣布审片通过。

### GitHub Actions 安全边界

- 不使用 `pull_request_target` 去 checkout 并执行外部 PR 的未经信任代码，同时授予写入 Token/Secrets。
- 预览任务的 `GITHUB_TOKEN` 只需 `contents: read`；尽量不要向渲染任务提供交易/云服务等 Secrets。
- 来自未经信任分支的代码应在隔离/无秘密环境里渲染，禁止默认联网读取敏感系统。渲染产物本身也按不可信输入处理。

## 构建时的清单

本仓库的 `workflow/media_manifest.py` 生成/校验媒体文件的 SHA256 清单：

~~~bash
python workflow/media_manifest.py create \
  --spec path/to/director_spec.json \
  --delivery work/<project_id>/attempt-001/delivery.json \
  --artifact-root work/<project_id>/attempt-001 \
  --backend actions \
  --artifact-name mg-<project_id>-r1-a1-<sha12> \
  --out work/<project_id>/attempt-001/media_manifest.json

python workflow/media_manifest.py verify \
  --manifest work/<project_id>/attempt-001/media_manifest.json \
  --artifact-root work/<project_id>/attempt-001
~~~

该工具只检查元数据/文件 SHA/规格匹配与路径，不验证视频真实能播放，更不验证艺术质量或物理运动。生成记录应该与媒体文件一起打包。

## 审查版本有效性

交付和审查一律以**参与渲染的准确源代码 SHA** 为身份；PR 再次提交代码，则以前 artifact/QA 仍保留历史记录，但**不能自动作为当前代码验收结果**，需要重新渲染和独立审核。

如果要把 QA 报告提交到 Git：应在独立的审查/存档提交里记录“被审源码 SHA + artifact/run ID”，不要将元数据提交造成的 PR HEAD 更新理解为“渲染本身更新”。当前 `orchestrator.receive --pr` 严格比对 PR HEAD 与 delivery commit，因此应在 **代码提交完成且未再推送新代码时** 接收该轮媒体；元数据放制品中可避免自引用。

## 当前 Pilot 001

《两张订单，两条路径》对应 Issue #4：让 Muse 提交**渲染脚本和源码**，真实无声 MP4 / 审片连续帧保存到制品。未配置自动上传时，可先由 Muse 输出到 `work/orders_two_routes/attempt-001/`，人工提供视频与 ZIP 给独立 QA。不要为演示而往仓库塞测试视频。