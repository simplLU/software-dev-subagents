# Run 看板：20260101-120000-add-dry-run

- 需求：给 CLI 增加 `--dry-run` 参数（演示用，示例需求见 `subagents/examples/feature_request.md`）
- 流水线：`feature`（router 已确认）
- 预算：任务数 ≤ 2、worker ≤ 1、评审 ≤ 3 轮、时间盒 40 分钟
- 状态：**awaiting_human** —— route 完成；目标仓库未落地，按协议在 plan 前升级人类

## 阶段与产物

| 阶段 | 负责 | 状态 | 产物 |
|---|---|---|---|
| route | router | **done** | `route.json` |
| plan | planner | blocked（缺目标仓库） | — |
| approve_plan | leader | pending | — |
| implement | worker | pending | — |
| review | reviewer | pending | — |
| deliver | leader | pending | `report.md` |

## route 结果摘要（来自 `route.json`）

- pipeline：`feature`；confidence：0.75
- target_roles：leader / planner / worker / reviewer
- 合规检查：router 只写入了 `route.json`，未触碰任何其他路径（符合单写者原则）

## 证据

- 路由结果：`runs/20260101-120000-add-dry-run/route.json`
- 交接信封：`runs/20260101-120000-add-dry-run/handoffs/route_envelope.json`

## 升级人类（leader 决策：暂停，不进入 plan）

1. **目标仓库路径**：当前工作区只有 `AGENTS.md`、`subagents/`、`runs/`，没有 `src/` 与 `tests/`；
   需求文件把「仓库」标为 `<待填写>`。需要确认真实仓库路径，或确认"先落地示例骨架"。
2. **验收证据替代方案**：验收标准 1 依赖 `git status --porcelain`，但当前工作区不是 git 仓库；
   是否接受"文件哈希快照前后对比"作为替代，或先 `git init`。
3. **dry-run 覆盖范围**：需要覆盖哪些"会写文件/改外部状态"的命令，决定测试边界。

> 按 `protocol.toml` 的升级规则：需求范围/验收方式需要变更、目标环境不明确时，leader 必须停止并
> 升级人类，不得擅自让 worker 从零创建源码。
