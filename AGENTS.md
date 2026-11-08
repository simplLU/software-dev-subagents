# 本工作区约定（AGENTS.md）

本工作区是一个「软件开发子代理团队」的定义包，入口文档是
[`subagents/README.md`](subagents/README.md)。任何在本工作区做开发类任务的代理，请先读它。

## 快速规则

1. **先校验，再使用**
   ```bash
   python subagents/scripts/validate_agents.py
   ```
2. **任务按协议走**：一次请求 = 一个 `runs/<run_id>/` 目录，按
   `subagents/protocol.toml` 的流水线执行（router → leader → planner → worker → reviewer）。
3. **单写者**：只允许写自己在 `protocol.toml` `[ownership]` 中声明的路径；`protected_paths`
   未经人类批准一律不碰。
4. **不跳 review**：实现完成后必须由独立上下文的 reviewer 给出 `approve` 才能交付。
5. **产物落盘**：计划、任务、实现报告、评审结论都写入 `runs/<run_id>/`，完成声明必须附证据。
6. **改完 TOML 必须重新校验**：`python subagents/scripts/validate_agents.py` 必须通过。

## 渲染角色提示词

```bash
python subagents/scripts/render_prompt.py <role> --run-id <id> --task "<任务>"
# role ∈ router / leader / planner / worker / reviewer
```

## 安装到其他项目

```bash
python subagents/scripts/install_into_project.py --target <项目根目录>
```
