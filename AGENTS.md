# 本工作区约定（AGENTS.md）

本工作区是一个「软件开发子代理团队」的定义包，入口文档是
[`subagents/README.md`](subagents/README.md)。任何在本工作区做开发类任务的代理，请先读它。

## 新会话启动（lead 必读）

队友是**会话级**的，新会话不会继承上一会话的成员；但角色定义是持久的。
新会话中你是 leader，请按以下顺序启动：

1. 读 `subagents/protocol.toml` 与 `subagents/README.md`，确认协议版本与流水线；
2. 运行 `python subagents/scripts/validate_agents.py` 确认文件完好；
3. 用 `subagents/scripts/render_prompt.py` 渲染角色卡，按需为 router / planner / worker /
   reviewer 创建子代理（`subagent` 或 `spawn_teammate`），**不要自行编造角色设定**；
4. 先向用户确认任务四要素（目标、项目目录、验收标准、约束），再按流水线启动 run；
5. 没有用户任务时不要空转，只做准备并等待。

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
