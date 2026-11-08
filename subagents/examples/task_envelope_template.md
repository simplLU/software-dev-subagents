# 任务信封模板（复制后填写）

> 用法：填好后作为 `--task-file` 传给 router / planner / worker。
> 字段可多不可少；不确定的内容写进「不确定点」，不要脑补。

## 基本信息

- run_id：`YYYYMMDD-HHMMSS-<slug>`
- 流水线：`<feature | bugfix | refactor | review_only | spike>`（不确定就留空，由 router 判断）
- 仓库 / 工作目录：`<路径>`
- 分支：`agent/YYYYMMDD-HHMMSS-<slug>`
- 请求人：`<用户>`
- 期望交付：`<代码 + 测试 + 报告 / 仅评审意见 / 调研笔记>`

## 需求（原文优先）

<把用户的原始描述贴在这里；不要在这一步就替用户"优化"需求>

## 验收期望（尽量可执行）

1. `<命令>`：期望 `<输出 / 退出码 / 行为>`
2. `<命令>`：期望 `<...>`
3. `<人工检查步骤>`：期望 `<...>`

## 约束

- 允许改动的路径：`<例如 src/app/cli.py、tests/test_cli.py>`
- 禁止改动的路径：`<例如 protected_paths 全部>`
- 不引入新依赖：`是 / 否（若否，列出依赖与理由）`
- 规模上限：`<例如 ≤ 200 行、≤ 2 个任务>`
- 其他约束：`<编码规范、兼容性、性能要求>`

## 不确定点（供 planner 转成 open_questions / 假设）

- `<问题 1>`
- `<问题 2>`

## 预算建议

- max_tasks：`<2>`
- max_workers：`<1>`
- max_review_rounds：`<3>`
- timebox_minutes：`<40>`
