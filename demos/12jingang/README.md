# Demo: 十二金刚 (12jingang)

15.5 秒 MG 动画：12 个金刚剪影站成一排 → 正向计数 1→12 → 逆向计数 12→1 → 流动成圆圈 → 圆心升起"12金刚"大字。

非表格实战：`absolute` 布局 + `image` + `text` + `card`，演示 `move` 原语和多 scene 衔接。

## 重新生成
```bash
python demos/12jingang/gen_scene.py
python scripts/validate.py demos/12jingang/12jingang.json
python scripts/render.py demos/12jingang/12jingang.json --out demos/12jingang/12jingang.mp4
```
