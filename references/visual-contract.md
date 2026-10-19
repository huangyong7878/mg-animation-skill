# Visual Contract（视觉交接协议）v1.0

创意导演 → 技术导演的机器可读交接。每 shot 一份 JSON，技术导演必须逐项实现，
无法实现必须**报告阻断**，不许静默删减。也是 `contract_check.py` 和独立质检的依据。

## Schema

```json
{
  "shot_id": "shot_02",
  "visual_goal": "比较两种地面的雨水去向（观众一句话能说出的结论）",
  "core_takeaway": "草地吸水、马路排水——这就是积水差异的根源",
  "must_show": [
    {"id": "grass_cross_section", "desc": "草地剖面：草叶+土壤分层"},
    {"id": "soil_layers", "desc": "至少两层不同颜色/密度的土壤"},
    {"id": "asphalt_road", "desc": "沥青道路剖面：面层+基层+土基"},
    {"id": "rain_drops", "desc": "两侧持续降雨"},
    {"id": "surface_runoff", "desc": "草地少量地表径流，方向与道路不同"},
    {"id": "soil_infiltration", "desc": "雨水从地表进入土壤并下移"},
    {"id": "drain_inlet", "desc": "道路排水口，可见格栅"},
    {"id": "underground_pipe", "desc": "地下管道，水流有去处（非死胡同）"}
  ],
  "continuous_motion": [
    {
      "id": "infiltration_path",
      "from": "sky", "through": ["grass_surface"], "to": "deep_soil",
      "desc": "雨滴→草地表面→渗入土壤深处，路径连续无跳跃"
    },
    {
      "id": "drainage_path",
      "from": "road_surface", "through": ["drain_inlet"], "to": "underground_pipe",
      "desc": "雨水沿路面→排水口→地下管道，全程一条连续轨迹"
    }
  ],
  "editorial": {
    "title": "同一场雨，两种不同的去向",
    "legends": [["#7BA05B", "渗入地下"], ["#4A90D9", "少量径流"]],
    "layer_labels": ["松软土壤", "深层土壤", "基层/路基"],
    "status_states": [[14.26, "雨水进入土壤"], [999, "雨水汇向排水口"]]
  },
  "render_mode": "custom",
  "silent_downgrade": false
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `shot_id` | 是 | 与分镜表编号一致 |
| `visual_goal` | 是 | 纯视觉语言：观众应该"看到什么" |
| `core_takeaway` | 是 | 一句话结论：观众应该"带走什么"。直接决定标题和图例文案 |
| `must_show` | 是 | 核心视觉对象清单，每项有唯一 `id` + 一句话 `desc` |
| `continuous_motion` | 否 | 连续运动路径：`from` → `through` → `to`，粒子/水流不许断点 |
| `editorial` | 否 | 编辑层：标题、图例、图层标注、叙事状态。解释类 shot 默认要有 |
| `render_mode` | 是 | `standard`（纯原语拼装）或 `custom`（需自由编程） |
| `silent_downgrade` | 是 | `false` = 任何 must_show 缺失必须报告阻断，不许悄悄省略 |

## 技术导演的义务

1. `render_mode: standard` → 只用注册表原语拼装，不许写新代码。
2. `render_mode: custom` → 允许写新原语/自定义元素，但新代码必须遵守原语接口
   `(draw, box, t, node, style, col, fonts)` 且是时间的确定性函数。
3. 跑 `contract_check.py`：每个 `must_show.id` 必须在 scene JSON 中有对应元素
   （元素 `contract` 字段标注，如 `"contract": "soil_layers"`）。
4. 任何一项无法实现 → 在交付报告中写明阻断原因，**不许**用近似效果代替而不声明。
5. `silent_downgrade: false` 且有缺失 → 拒绝交付，进入修复循环。

## 版本

- v1.0 (2026-10-19)：初始版本。配合 technical-director 2.0。

## v1.1 结构校验与使用方式

本仓库的 `scripts/contract_check.py` 目前执行的是**结构覆盖检查**，不是实际视觉效果检查。校验规则：

- 只检查 `shot_id` 指定、`scenes[*].id` 完全匹配的**一个镜头**；找不到或发现重名镜头会阻断。
- 递归检查 `elements[*].children` 中的所有节点；其他镜头的 `contract` 标签不能冒充本镜头已完成。
- `must_show` 与 `continuous_motion` 的每个 `id` 必须有相应 `contract` 标签，重复的需求 ID 会阻断。
- `silent_downgrade: true` 在单独运行校验器且未开启严格模式时，只产生警告；`--strict` 始终阻断缺失。
- **校验通过不证明画面对象真的出现、路径真的连续、物理关系正确。** 必须另行提供渲染视频给独立 QA 审核。

```bash
# 按原 Contract 的降级设置执行；报告可供模型消费
python scripts/contract_check.py contracts/shot_02.json work/scene.json --report work/contract_report.json

# 严格模式：任意缺失都阻断
python scripts/contract_check.py contracts/shot_02.json work/scene.json --strict

# 现有两阶段流水线的 render 阶段，选择性强制契约门禁
# 严格校验通过才渲染；同一 timings.json 也会用于字幕烧录
python scripts/auto_pipeline.py render work/scene.json --outdir work/ep01 --contract contracts/shot_02.json
```

`--contract` 为可选参数，既有不传 Contract 的旧项目仍可按原流程渲染；新的多模型交接项目建议始终提供。注意，`scene.json` 中目标镜头的 `id` 必须等于 Contract 的 `shot_id`。
