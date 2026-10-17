# 可直接交给其他 AI 编程工具的启动提示词

请读取当前目录的 `SKILL.md`、`README.md`、`references/scene-contract.md` 和 `references/scene.schema.json`，然后使用 **mg-infographic-animation-v2** 技能完成下面任务。

**任务**：根据我提供的中文解说稿或视觉主题，生成复古纸张质感的二维信息图动画 MP4，同时交付可编辑的 v2 JSON。

**工作约束**：

1. 不允许继续使用固定 2 列 × 3 行表格的坐标实现。用户数据有多少列、多少行，就按 `columns` 和 `rows` 声明多少；画面溢出应分镜，不要强行压缩到不可读。
2. 动画须优先组合已实现的容器 `absolute / row / column / grid` 和节点 `text / card / icon / image / line / arrow / table / timeline`。
3. 按语义自动判断视觉形式：对比选表格，步骤选横向流程，时间顺序选时间轴。未经允许不要编造数据和地图归属信息。
4. 每个元素选择 `fade / slide / pop / draw` 等动画，并合理设置开始、时长、缓动；同一镜头最后保留稳定观看时间。
5. 使用本包 `scripts/validate.py` 校验 JSON，并使用 `scripts/render.py` 渲染样片。渲染中如果报错、文本越界或碰撞，请修改 JSON 重新输出。
6. 保留原视频的温暖纸张颗粒背景、砖红轮廓、清晰中文字体、适度的节奏，但不要复制未经授权的原视频资产。
7. 输出：最终 MP4、完整 JSON、关键帧 PNG。如果新增了渲染组件，还需给出对应源码及测试。
8. 首先运行附带的三个测试案例，确认 `table_2x3`、`table_4x5`、`flow_and_timeline` 均可以渲染；不要只输出一份实施建议。

如果没有提供具体文案，请先用三个示例验证环境，给我看图形样片，再询问我要转成动画的文字内容。

请不要声称本包已经内置语音合成、自动音频对齐、Remotion 实现或自动分页。这些功能需要独立开发。
