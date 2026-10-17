# 可直接复制给其他 AI 编程工具

你现在负责用 `mg-infographic-animation` Skill 2.1 将我提供的文案制作成复古纸张信息图 MG 动画。请先完整阅读 SKILL.md、references/scene-contract.md、references/fact-research-protocol.md，并运行 `python -m unittest discover -s tests -v` 及两镜头样例。

请执行以下步骤：

1. 将文案分解成适合可视化的多个镜头，每个镜头选用 table、timeline、flow、icon 或 card；不要假设固定 2×3 表格。
2. 对可验证的事实性陈述先联网寻找原始来源并交叉核对，填入 claims/claim_ids；无法验证的事实不得标记 verified 或制作成肯定性结论。
3. 输出合法的 `version: 2.1` 场景 JSON，为 `canvas.default_transition` 或镜头 `transition_in` 指定合适转场，避免多镜头交叉区间互相重叠。
4. 输出 narration.segments，每段关联到 scene_index/offset；调用 scripts/narrate.py 生成音频、准确的句段时间戳和 SRT。用于公开视频时优先使用质量更高的 Edge TTS；不可访问时使用 eSpeak 仅验证系统功能。
5. 核对每段音频不超出对应镜头时间。若有单字级动画卡点，则配置 WhisperX 强制对齐，并抽查缺失或错位部分。
6. 使用 scripts/validate.py 和 scripts/factcheck.py 验证，使用 scripts/render.py --audio ... --timings ... 导出视频，逐帧检查转场、字体、字幕和表格；发现重叠/越界则调整 JSON。
7. 最终交付 MP4、JSON、WAV、SRT、timings.json、事实来源与核验说明，清楚说明未完成的验证事项。不要冒称自动做到了真正的事实核查。
