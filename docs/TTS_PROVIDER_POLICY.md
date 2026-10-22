# Story #37 — 配音引擎切换与跨 Agent 协作（2026-10-22）

> **当前策略**：MG Studio 正式配音候选默认使用 Edge TTS，音色 `zh-CN-XiaoxiaoNeural`；**不再以 Azure Speech 作为默认前提**。语音提供者必须可插拔，不把任何一款 TTS SDK 绑定进 Stage D。
>
> **实现状态**：Story #37 正在开发；`studio/tts_providers.py` 与 `studio/tts_preview_cli.py` 为早期预览入口。不要把它描述为已通过联网合成、已集成网页或已正式交付。

## Agent 职责

- **ChatGPT（Story #37 实现/集成 Owner）**：Provider 协议、Edge 适配器、预览文件生成、离线测试和文档；在独立 PR 交付，由人类决定合并。
- **Agent C（动画/媒体）**：维持现有 R4/Stage D 源码、音画渲染及锁定媒体验证；**由于其环境无法访问 Edge，不能交给 C 执行 Edge 在线合成验收**。不必为换 TTS 引擎重写动画。
- **R0/R3**：确认 Script Lock 与 AV cue 契约，检查新生成候选时长是否符合视觉事件；不能代替人类批准。
- **用户（人类）**：本地 Mac 可联网时亲自试听、批准 Voice Lock；仍独占合并与发布权限。R5 需重新审查新音轨的视听同步。

## Provider 适配规则

- `edge` 是默认 Provider，`zh-CN-XiaoxiaoNeural` 是默认 Voice；保留未来 `fish`、`gemini` 扩展点，但这些适配器尚未实现，**不允许暗中调用付费 API，也不允许无声降级或悄悄切换 Azure**。
- Provider 输出先保存为独立的预览（原始音频 + 统一单声道 22050 Hz PCM16 WAV + SHA256/实际时长）；不得直接覆盖 `media/voice.wav`、`media/timings.json` 或审批文件。
- 如果需字/句级时间轴，应由实际音频测量/对齐校验；不能假装所有 TTS 都返回词级时间戳，也不能凭文本长度伪造同步。
- Edge TTS 是第三方非官方接入微软在线朗读的方式，可能被限流或接口变更；没有可证明的商用保障。联网失败直接报告，不可虚构测试通过。
- 更换 Provider/音色/语速或重新合成使音频哈希改变时，即使 Script Lock 不变，**原 Voice Lock 也失效，必须重新试听和人工批准**。

## 开发/验证

```bash
python -m unittest tests.test_tts_providers -v
# 在有网络、已经安装 edge-tts / ffmpeg 的 Mac 上，由操作者显式启动：
python -m studio.tts_preview_cli --text-file PATH_TO_APPROVED_SCRIPT.txt \
  --output work/tts_previews/edge_pilot_001 --provider edge \
  --voice zh-CN-XiaoxiaoNeural --confirm-network-call
```

以上联网命令只是预览，`work/tts_previews/edge_pilot_001` 必须尚不存在。请人工试听，并检查音质、音频长度、镜头对应句段时刻以及适用的使用条款。未实际运行时，报告为「未验证」；不用测试音频签发正式锁。

## 验收交接

Story #37 完成需要：离线测试运行结果；本地 Mac 真实 Edge 连接与中文音色试听结果；可审计的音频 SHA/格式/时长；不修改正式双锁的预览操作；单独 Draft PR。Stage D 和 R5/R7 的合格状态由其各自流程判断。

[Issue #37](https://github.com/huangyong7878/mg-animation-skill/issues/37)
