# Demo: 十二金刚 (12jingang)

15.5 秒 MG 动画：12 个金刚剪影站成一排 → 正向计数 1→12 → 逆向计数 12→1 → 流动成圆圈 → 圆心升起"12金刚"大字。

这是 v2.0 通用引擎的非表格实战：没有用 `table`，全靠 `absolute` 布局 + `image` + `text` + `card` 节点，以及新增的 `move` 动画原语。

## 文件

- `12jingang.json` — 场景文件（version 2.0，2 个 scene）
- `assets/warrior.png` — 金刚剪影素材（自制，无版权问题）
- `gen_scene.py` — 生成 JSON 的 Python 脚本（几何计算：直线排布→圆周排布）
- `12jingang.mp4` — 成片（960×540，24fps）

## 重新生成

```bash
# 从仓库根目录
python demos/12jingang/gen_scene.py          # 重新生成 12jingang.json
python scripts/validate.py demos/12jingang/12jingang.json
python scripts/render.py demos/12jingang/12jingang.json --out demos/12jingang/12jingang.mp4
```

注意：`gen_scene.py` 里写死了输出路径，如需改位置请自行调整。

## 用到的新能力

- `move` 动画：`from_x/from_y` → `to_x/to_y` 位置插值，直线→圆圈的流动就靠它
- `hide_before: False`：计数脉冲动画，已显示的元素不再被后续动画藏起来
- 多 scene 硬切：Scene 1（计数）→ Scene 2（变形），切点处人物位置连续，视觉上无缝
