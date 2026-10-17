# CHANGELOG

## v2.1.1 (2026-10-17)

### 合并
- `move` 动画原语（from 十二金刚实战）：`from_x/from_y` → `to_x/to_y` 位置插值
- `hide_before` 参数：`pop`/`fade` 未开始时不再误隐藏已显示元素（修复多动画叠加 bug）
- 新增 2 项测试：`test_move_interpolates_position`、`test_future_pulse_does_not_hide`
- 新增 `demos/12jingang/` 实战 demo


