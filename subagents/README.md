# 软件开发子代理团队（subagents/）

> 5 个角色 · TOML 定义 · 权限边界可机检 · 适用于"软件开发 / 代码编写"场景
> 版本：0.1.0　｜　入口文档：本文件

这套文件把「规划师（planner）、执行者（worker）、调度（leader）、审核（reviewer）、路由（router）」
定义成 5 份可复用的角色卡，并用一份全局协议（`protocol.toml`）约束它们之间的
**谁可以写哪里、谁可以批准什么、谁可以向谁交接**。配套四个脚本：

- `scripts/render_prompt.py`：把角色 TOML 渲染成可直接交给任意模型 / 子代理的提示词；
- `scripts/validate_agents.py`：校验协议与角色文件是否一致、权限边界是否冲突；
- `scripts/selftest.py`：故意制造违规，证明上面的校验真的拦得住（7 个用例）；
- `scripts/install_into_project.py`：把整套团队安装到任意项目根目录（新会话可复用）。

适用场景：新功能开发、缺陷修复、重构、代码评审、技术调研；也适合单人开发者
"一个人扮演多个角色"时用来强制自己按流程走。

---

## 1. 目录结构

```text
subagents/
├── protocol.toml              # 全局协议（宪法）：run 模型、路径所有权、交接、闸门、路由表
├── router.toml                # 路由：分诊 → 选流水线 → 结构化路由结果
├── leader.toml                # 调度：编排、分派、守闸门、收口交付
├── planner.toml               # 规划师：需求 → 方案 → 任务 → 验收标准
├── worker.toml                # 执行者：单任务实现 + 测试 + 实现报告
├── reviewer.toml              # 审核：独立复核 diff 与验收项，只给结论不改代码
├── scripts/
│   ├── validate_agents.py     # 校验：一致性 / 写域冲突 / 权限归属 / 流水线合法性
│   ├── render_prompt.py       # 渲染：角色 TOML → 子代理提示词
│   ├── selftest.py            # 自测：制造 7 类违规，证明校验规则有效
│   └── install_into_project.py# 安装：把团队装进任意项目根目录
├── templates/
│   └── session_start.md       # 新会话开场白模板（复制到新对话）
├── examples/
│   ├── feature_request.md     # 示例任务信封（新功能）
│   ├── task_envelope_template.md  # 空白任务信封模板（复制后填写）
│   └── route.example.json     # 示例路由结果
└── README.md                  # 本文件
```

工作区根目录还应有 `runs/`（运行时自动创建），一次任务一个子目录，互不污染。

---

## 2. 5 个角色一览

| 角色 | 阶段 | 一句话 | 可写路径 | 可派子代理 | 可批准 |
|---|---|---|---|---|---|
| `router` 路由 | route | 分诊：判类型、选流水线、标风险 | `runs/{run_id}/route.json` | 否 | 无 |
| `leader` 调度 | orchestrate | 编排 run、分派任务、守闸门、汇总交付 | `runs/{run_id}/board.md`、`report.md`、`handoffs/**` | **是**（≤4 个） | 计划、交付 |
| `planner` 规划师 | plan | 需求 → 方案 → 任务 → 验收标准 | `runs/{run_id}/plan.md`、`tasks.json`、`docs/specs/**` | 否 | 计划自洽性 |
| `worker` 执行者 | implement | 在写域内实现单任务 + 测试 + 报告 | `src/**`、`tests/**`、`scripts/**`、`runs/{run_id}/impl/**` | 否 | 无 |
| `reviewer` 审核 | review | 独立复核，给 approve / request_changes / block | `runs/{run_id}/review.md`、`review_<task_id>.json` | 否 | 实现放行 |

角色之间的关系：

```text
用户请求
   │
   ▼
router（分诊）──route.json──▶ leader（调度）
                               │  ├─ planner（出计划）──plan.md/tasks.json──▶ leader 审批
                               │  ├─ worker（按任务实现）──diff + impl 报告──▶ reviewer 独立复核
                               │  └─ reviewer（结论）──approve / 退回──▶ leader 收口
                               ▼
                          report.md（交付结论 + 证据 + 未决问题）
```

---

## 3. 四条设计原则（为什么这么写）

1. **单写者原则**：同一路径同一时刻只有一个角色能写（见 `protocol.toml` 的 `[ownership]`）。
   脚本会自动检查 5 个角色的写域互不重叠 —— 改坏会直接报错。
2. **分权制衡**：写代码的人不评审代码；评审的人不改代码；调度的人不写实现。
   批准权也是独占的：只有 `reviewer` 能 `implementation_approved`，只有 `leader` 能 `delivery_accepted`。
3. **留痕 + 闸门**：每次请求 = 一个独立 `run`，所有产物落盘；不通过闸门不得进入下一阶段，
   完成声明必须附证据（测试输出、代码位置、评审结论）。
4. **不猜需求**：信息不足时写进 `missing_info` / `open_questions` 并升级，禁止脑补；
   这也是 `router` 存在的意义 —— 把"需求不清"挡在执行之前。

---

## 4. 权限边界（硬约束）

### 4.1 写域（谁能改什么）

| 角色 | 允许写入 | 明确禁止 |
|---|---|---|
| router | 仅 `route.json` | 一切代码、配置、他人产物 |
| leader | 看板 / 报告 / 交接记录 | `src/**`、`tests/**`、依赖与 CI |
| planner | 计划 / 任务清单 / 规格文档 | `src/**`、`tests/**`、依赖与 CI |
| worker | `src/**`、`tests/**`、`scripts/**`、`impl/**` | 他人产物、`protected_paths`、跨任务写域 |
| reviewer | 评审报告 / 评审 JSON | 任何代码、任何提交 |

### 4.2 受保护路径（`protected_paths`）

`.git/**`、`.env*`、`**/*.pem`、`**/*.key`、`.github/workflows/**`、`deploy/**`、`infra/**`、
`secrets/**`、`migrations/**`、`package.json`、`pnpm-lock.yaml`、`pyproject.toml`、`requirements*.txt`。

规则：**任何角色默认不可写**；只有任务信封显式声明 `allow_protected = true` 且 `leader` 批准、
并由人类确认后才能修改。校验脚本会检查写域是否覆盖受保护路径。

### 4.3 命令执行分级

每个角色都分三档：`allowed`（直接执行）/ `needs_approval`（需 leader 或人类批准）/
`forbidden`（禁止）。原则：

- 只读检索、测试、构建、lint 默认允许；
- 安装/升级依赖、联网、超时命令需要批准；
- 修改代码、`git commit`、破坏性操作按角色严格禁止。

### 4.4 升级（任何角色触发即停）

统一升级到 `leader`，再由 `leader` 决定是否上报人类。触发条件包括：需要改受保护路径、
需要改需求/验收标准、需要新依赖、连续 2 轮同一问题未解决、预算超限、发现安全/合规风险。

---

## 5. 项目边界：一次任务怎么切

- **一次用户请求 = 一个 run**：产物写入 `runs/<run_id>/`，run_id 建议 `YYYYMMDD-HHMMSS-<slug>`。
- **按流水线走**（见 `protocol.toml` 的 `[[routing.pipeline]]`）：

| 流水线 | 适用 | 阶段 |
|---|---|---|
| `feature` | 新功能 / 小特性 | leader → planner → leader 审批 → worker → reviewer → leader 交付 |
| `bugfix` | 缺陷修复 | leader → planner(诊断) → leader 审批 → worker → reviewer → leader |
| `refactor` | 重构 / 技术债 | leader → planner → leader 审批 → worker → reviewer → leader |
| `review_only` | 只评审 | leader → reviewer → leader |
| `spike` | 调研 / 可行性 | leader → planner(调研) → leader |

- **完成定义（DoD）**：验收项全部有证据、测试通过（或记录客观原因）、reviewer 结论为 approve、
  变更全部在写域内、leader 在 `report.md` 汇总证据。

---

## 6. 使用方法

### 6.0 前置：先校验，再渲染

在本工作区根目录执行（Windows 下可用 DSH 自带 Python，见文末）：

```bash
python subagents/scripts/validate_agents.py      # 应输出 "校验通过"
python subagents/scripts/selftest.py             # 应输出 "7/7 通过"（可选，验证规则有效）
python subagents/scripts/render_prompt.py --list # 列出 5 个角色
```

### 6.1 方式 A：手工复制提示词（最通用，任何模型 / 聊天工具都行）

每个阶段单独开一个对话（或至少清空上下文），把渲染结果整段粘贴为 system prompt，
再附上任务信封：

```bash
# 1) 分诊
python subagents/scripts/render_prompt.py router \
  --run-id 20260101-120000-add-dry-run \
  --task-file subagents/examples/feature_request.md

# 2) 调度（把 router 的 route.json 一起给 leader）
python subagents/scripts/render_prompt.py leader \
  --run-id 20260101-120000-add-dry-run \
  --task "按 route.json 启动 feature 流水线"

# 3) 规划
python subagents/scripts/render_prompt.py planner \
  --run-id 20260101-120000-add-dry-run \
  --task-file subagents/examples/feature_request.md

# 4) 实现（一次只给一个任务）
python subagents/scripts/render_prompt.py worker \
  --run-id 20260101-120000-add-dry-run \
  --task "task-1：在 src/app/cli.py 增加 --dry-run 参数；验收：pytest tests/test_cli.py 全绿"

# 5) 审核（独立上下文，不复用 worker 对话）
python subagents/scripts/render_prompt.py reviewer \
  --run-id 20260101-120000-add-dry-run \
  --task "复核 task-1 的 diff 与 runs/.../impl/task-1.md"
```

> 关键：**reviewer 必须用独立上下文**。如果和 worker 共用一个对话，评审独立性就没了。

### 6.2 方式 B：DSH 单次子代理（`subagent` 工具）

把 `render_prompt.py` 的输出作为 `prompt` 传给子代理；子代理在自己的上下文里执行，
只回传结果，不污染主对话：

```text
subagent(
  description = "router 分诊",
  prompt      = "<python subagents/scripts/render_prompt.py router ... 的完整输出>"
)
```

建议：路由、规划、评审各用一次单次子代理；worker 按任务逐个调用（并行任务注意写域不重叠）。

### 6.3 方式 C：DSH 持久队友（`spawn_teammate`）

主会话自己担任 `leader`（调度），把其余角色创建成常驻队友，之后用 `send_message`
下发任务信封、用共享任务板跟踪状态：

```text
spawn_teammate(
  name        = "planner",
  description = "规划师：需求 → 方案 → 任务 → 验收标准",
  prompt      = "<render_prompt.py planner 的输出>"
)
spawn_teammate(name = "worker",   description = "执行者：单任务实现", ...)
spawn_teammate(name = "reviewer", description = "审核：独立复核",   ...)
spawn_teammate(name = "router",   description = "路由：入口分诊",   ...)
```

注意：

- 持久队友是**会话级**的，会话结束后消失；真正可复用的是本目录的 TOML 文件（下次重新创建即可）。
- 别让 reviewer 和 worker 看到彼此的中间推理：给 reviewer 的任务信封只放 diff、计划与验收项。
- 队友空闲 ≠ 任务完成：状态以任务板 + 产物文件为准。

### 6.4 方式 D：workflow 编排（多任务 / 批量）

任务较多时，用 DSH 的 `workflow` 工具写脚本：先 router 分诊，再 planner 出任务表，
然后按任务 fan-out 给 worker，最后 reviewer 汇总复核。骨架：

```js
const role = await agent("<render_prompt.py router 输出>", { schema });
const plan = await agent("<render_prompt.py planner 输出>", { schema });
const results = await pipeline(plan.tasks,
  async (prev, t) => agent(`<worker 提示词>\n\n本次任务: ${JSON.stringify(t)}`),
  async (diff, t) => agent(`<reviewer 提示词>\n\n请复核: ${JSON.stringify(t)}`),
);
```

小规模（1–3 个任务）建议直接用 6.2 的手动串联，不必上 workflow。

### 6.5 方式 E：接到自己的框架 / CI

`render_prompt.py` 输出的是纯 Markdown，可直接作为 system prompt 或写进
`.github/copilot-instructions.md`、`AGENTS.md` 之类的项目说明文件；
`protocol.toml` 也可以当配置源，用脚本读取 `[ownership]`、`[[routing.pipeline]]`
驱动你自己的编排器。

### 6.6 一个 feature 请求的 8 步流程

| 步 | 执行者 | 动作 | 产物 / 闸门 |
|---|---|---|---|
| 1 | router | 分诊、选 `feature`、标风险 | `route.json`（confidence ≥ 0.6） |
| 2 | leader | 确认流水线/预算，建 run 目录与看板 | `board.md`，run_start 闸门 |
| 3 | planner | 出方案与任务表 | `plan.md`、`tasks.json` |
| 4 | leader | 审批计划 | plan_gate / task_limit / scope_gate |
| 5 | worker | 按 task-1 实现 | `src/**`、`tests/**`、`impl/task-1.md` |
| 6 | reviewer | 独立复核 | `review.md`、`review_task-1.json`（verdict=approve） |
| 7 | leader | 收口、对照 DoD | `report.md`，delivery_gate |
| 8 | leader | 向用户交付结论与证据 | 完成 |

### 6.7 安装到真实项目（新会话复用，推荐）

把整套团队装进你的项目根目录，之后在该目录新开任何会话，`AGENTS.md` 都会被自动加载，
代理会重新读取角色定义、按需重建队友：

```bash
python subagents/scripts/install_into_project.py --target "D:\code\myapp"

# 角色定义有更新时，重新安装（覆盖 subagents/，AGENTS.md 里保留你原有的内容）
python subagents/scripts/install_into_project.py --target "D:\code\myapp" --force

# 只看会改什么，不落盘
python subagents/scripts/install_into_project.py --target "D:\code\myapp" --dry-run
```

安装内容：`<项目>/subagents/`、`<项目>/AGENTS.md`（无则创建，有则追加带标记的约定块）、
`<项目>/runs/.gitkeep`、`.gitignore` 追加忽略规则。安装后自动运行一次校验脚本。

新会话开场白直接复制 [`templates/session_start.md`](templates/session_start.md)，填上任务即可。

---

## 7. 完整示例（照着跑一遍）

仓库里已带一个最小示例，假设需求为「给 CLI 增加 `--dry-run`」：

1. 用 `subagents/examples/feature_request.md` 作为任务信封；
2. 按第 6 节依次渲染 `router → leader → planner → worker → reviewer → leader`；
3. 预期产出的目录（`runs/20260101-120000-add-dry-run/`）：

```text
runs/20260101-120000-add-dry-run/
├── route.json
├── board.md
├── plan.md
├── tasks.json
├── impl/task-1.md
├── review.md
├── review_task-1.json
└── report.md
```

每个文件对应一个角色的交付物；`report.md` 是最终给用户的结论。

---

## 8. 自定义与扩展

改完任何 TOML，**务必再跑一次** `validate_agents.py`。

- **调预算**：改 `protocol.toml` 的 `[quality]`（任务数、并行数、评审轮次）与各角色 `[limits]`。
- **改写域 / 受保护路径**：先改 `protocol.toml` 的 `[ownership]` / `protected_paths`，
  再同步对应角色的 `authority.write`（两者必须完全一致，校验会拦）。
- **加一条流水线**：在 `[[routing.pipeline]]` 增加条目，写清 `requires_plan` / `requires_review`、
  `stages`、`max_workers`、`gates`。不用改脚本。
- **加一个角色**：
  1. 复制一个最接近的角色 TOML 改名，改 `id` / 阶段 / 职责；
  2. 在 `protocol.toml` 的 `[ownership]` 加写域、`[roles]` 登记（脚本据此自动发现）；
  3. 在相关流水线 `stages` 中引用它；
  4. 运行校验。
- **换模型**：`[model]` 只是建议；实际用 `subagent` / `spawn_teammate` 的 `provider` + `model` 指定。
- **分发到其他项目**：`python subagents/scripts/install_into_project.py --target <项目根目录>`；
  更新角色定义时加 `--force` 重新安装即可。

---

## 9. 常见问题（FAQ）

**Q：TOML 会被 DSH 自动加载成子代理吗？**
不会。这套 TOML 是**可移植的角色定义 + 权限契约**，由 `render_prompt.py` 转成提示词后
再交给 `subagent` / `spawn_teammate` / 其他框架。好处是不绑定具体运行时；如果以后 DSH
支持自定义 agent 注册，直接把 TOML 映射过去即可。

**Q：子代理之间共享上下文吗？**
不共享。它们只通过「交接信封 + 产物文件」协作，所以交接必须写全 `artifacts` 路径。

**Q：一个人开发也要 5 个角色吗？**
可以裁剪：主会话 = leader；小改动走 `review_only` 或只开 planner + worker；
router 在需求明确时可省。但**不要省 reviewer** —— 自审等于没审。

**Q：怎么防止 worker 越界写文件？**
三层：提示词写域约束 → worker 自己的 scope_check 闸门（`git diff --name-only` 对照 allowed_paths）
→ reviewer 的 scope_audit 一票否决。最后还有 leader 的 delivery_gate 对照 DoD。

**Q：reviewer 发现问题为什么不直接改？**
改代码是 worker 的写域；reviewer 直接改会破坏单写者与独立性，也让"谁改的、谁审的"无法追溯。
正确做法：reviewer 给 `required_changes`，leader 退回 worker。

**Q：评审意见和规划冲突怎么办？**
范围/方案争议由 leader 裁决，超出原需求则升级人类。reviewer 不要在执行层重开规划讨论。

**Q：没有 git 的仓库能用吗？**
能。把 `protocol.toml` 的 `[git].enabled` 设为 `false`，改用文件清单核对写域即可。

---

## 10. 维护

```bash
# 每次修改 TOML 后
python subagents/scripts/validate_agents.py

# 规则本身是否仍然有效（会故意制造 7 类违规并断言被拦截）
python subagents/scripts/selftest.py

# 需要时把某个角色的提示词固化成文件（便于评审/复用）
python subagents/scripts/render_prompt.py reviewer \
  --run-id <run_id> --task "<任务>" --out runs/<run_id>/reviewer_prompt.md
```

版本约定：`protocol.toml` 的 `schema_version` 与各角色 `schema_version` 保持一致；
`protocol_version` / `role_version` 各自独立递增。

> 本机 Python（DSH 自带）：
> `C:\Users\MR\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`
