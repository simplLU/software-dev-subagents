# 软件开发子代理团队（Subagent Team Kit）

> 5 个角色 · TOML 角色卡 · 权限边界可机检 · 适用于 AI 编码代理的团队化协作

把「路由 → 调度 → 规划 → 执行 → 审核」沉淀成一套**可复用的角色定义**：
每个角色都有明确的职责、**权力边界**（能写哪些路径、能否派出子代理、能否批准）
和**项目边界**（做什么 / 不做什么 / 何时必须升级），并配一份全局协议和三个工具脚本。

不绑定具体模型：TOML 是角色定义，脚本把它渲染成提示词，交给任意支持子代理 /
系统提示词的运行环境（DeepSeek Harness、其他 Agent 框架、甚至手工复制到聊天窗口）。

## 特性

- **可机检**：`validate_agents.py` 检查写域一致性、单写者冲突、批准权归属、流水线合法性；
- **可自证**：`selftest.py` 故意制造 7 类违规，证明校验规则真的拦得住；
- **可移植**：纯 TOML + Markdown + Python 标准库，零第三方依赖；
- **可扩展**：加角色 / 加流水线只改配置，脚本自动发现（见 `subagents/README.md`）；
- **有安全边界**：`protected_paths`、升级规则、独立评审、完成定义（DoD）。

## 目录结构

```text
.
├── AGENTS.md                      # 工作区约定：任何代理进入后先读它
├── README.md                      # 本文件（仓库首页）
├── .gitignore
├── subagents/
│   ├── protocol.toml              # 全局协议（宪法）
│   ├── router.toml                # 路由
│   ├── leader.toml                # 调度
│   ├── planner.toml               # 规划师
│   ├── worker.toml                # 执行者
│   ├── reviewer.toml              # 审核
│   ├── README.md                  # 详细使用说明
│   ├── templates/
│   │   └── session_start.md       # 新会话开场白模板（复制到新对话）
│   ├── examples/                  # 任务信封示例 / 模板 / 路由结果示例
│   └── scripts/
│       ├── validate_agents.py     # 一致性 / 权限边界校验
│       ├── render_prompt.py       # 角色 TOML → 子代理提示词
│       ├── selftest.py            # 校验规则自测（7 个用例）
│       └── install_into_project.py# 把团队安装到任意项目根目录
└── runs/                          # 一次任务一个目录（示例 run 已提交）
```

## 快速开始

```bash
# 1) 校验角色定义与权限边界
python subagents/scripts/validate_agents.py

# 2) 校验规则自测（可选，证明规则有效）
python subagents/scripts/selftest.py

# 3) 看看有哪些角色
python subagents/scripts/render_prompt.py --list

# 4) 渲染某个角色，作为子代理提示词
python subagents/scripts/render_prompt.py planner \
  --run-id 20260101-120000-demo \
  --task-file subagents/examples/feature_request.md
```

> 没有 `python` 命令时，用你环境里的 Python 3.11+（脚本只用标准库 `tomllib`）。

## 在真实项目里使用（新会话也能复用）

```bash
# 把团队安装到你的项目根目录（自动创建 AGENTS.md 标记块、runs/、.gitignore）
python subagents/scripts/install_into_project.py --target "D:\code\myapp"

# 已安装过、需要更新角色定义时
python subagents/scripts/install_into_project.py --target "D:\code\myapp" --force
```

安装后，**在该项目目录新开任何会话，AGENTS.md 都会被自动加载**，代理会按协议
找到 `subagents/`、重建角色队友，无需你手动重读配置。新会话开场白模板见
[`subagents/templates/session_start.md`](subagents/templates/session_start.md)。

## 五个角色

| 角色 | 一句话 | 可写路径 | 可派子代理 | 可批准 |
|---|---|---|---|---|
| router 路由 | 分诊、选流水线、标风险 | `runs/{run_id}/route.json` | 否 | 无 |
| leader 调度 | 编排 run、分派、守闸门、收口 | 看板 / 报告 / 交接记录 | **是**（≤4） | 计划、交付 |
| planner 规划师 | 需求 → 方案 → 任务 → 验收 | 计划 / 任务 / 规格文档 | 否 | 计划自洽性 |
| worker 执行者 | 单任务实现 + 测试 + 报告 | `src/**`、`tests/**`、`scripts/**`、`impl/**` | 否 | 无 |
| reviewer 审核 | 独立复核、放行判断 | 评审报告 / JSON | 否 | 实现放行 |

完整职责、权力边界、项目边界见各角色 TOML 与 [`subagents/README.md`](subagents/README.md)。

## 一次任务长什么样

```text
用户请求
   │
   ▼
router（分诊）──route.json──▶ leader（调度）
                               ├─ planner（计划）──▶ leader 审批
                               ├─ worker（实现）──▶ reviewer（独立复核）
                               └─ 闸门全部通过 ──▶ leader 收口
                                                    │
                                                    ▼
                                     runs/<run_id>/report.md（交付结论 + 证据）
```

一次请求 = 一个 `runs/<run_id>/` 目录；未通过闸门不进入下一阶段；完成必须附证据。

## 设计原则

1. **单写者**：同一路径同一时刻只有一个角色能写，写域冲突会被脚本拦下；
2. **分权制衡**：写代码的人不评审，评审的人不改代码，调度的人不写实现；
3. **留痕闸门**：产物落盘、闸门硬约束、完成定义（DoD）逐条对证据；
4. **不猜需求**：缺信息就写进 `missing_info` / `open_questions` 并升级。

## 自测与维护

```bash
python subagents/scripts/validate_agents.py   # 改完任何 TOML 后必须通过
python subagents/scripts/selftest.py          # 校验规则回归测试
```

## 许可证

本仓库暂未附带开源许可证；如需开源发布，请自行添加 `LICENSE`（例如 MIT）。
