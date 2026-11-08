# 示例任务信封：新功能（feature）

> 把本文件作为 `--task-file` 传给 router / planner / worker。
> 实际使用时替换 `<...>` 中的占位内容。

## 基本信息

- run_id：`20260101-120000-add-dry-run`
- 分支：`agent/20260101-120000-add-dry-run`
- 仓库：`<待填写>`（示例假设：Python 3.11+，`src/` 布局，pytest，CLI 入口 `src/app/cli.py`）
- 请求人：`<用户>`
- 期望交付：代码改动 + 测试 + 实现报告 + 评审结论

## 需求

为 CLI 增加 `--dry-run` 参数：

- 带 `--dry-run` 时，CLI 只打印"将要执行的操作"，**不写入任何文件、不修改外部状态**；
- 不带该参数时，行为与现在完全一致；
- `--help` 中能看到该参数的说明。

## 验收期望

1. 运行 `python -m app --dry-run <任意合法参数>`：退出码为 0，输出包含将执行的操作清单，
   且运行前后工作区文件无变化（可用 `git status --porcelain` 证明）；
2. 运行 `python -m app <任意合法参数>`：行为与改动前一致，现有测试全绿；
3. 新增测试至少覆盖：`--dry-run` 不产生副作用、正常模式不受影响；
4. `pytest tests/test_cli.py -q` 全绿。

## 约束

- 不引入新依赖；
- 预期改动范围：`src/app/cli.py`、`tests/test_cli.py`（如需新文件，先在计划中说明）；
- 一次性改动控制在 200 行以内；
- 不改 `protected_paths`（依赖清单、CI、部署配置等）。

## 已知不确定点（供 planner 转化为 open_questions / 假设）

- `--dry-run` 的输出格式：纯文本还是结构化（JSON）？示例按纯文本处理；
- 是否需要为 `--dry-run` 增加 `--quiet` 兼容行为？示例按"不需要"处理。
