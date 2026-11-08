# 新会话开场白模板

> 在新对话（工作目录已安装本团队的项目根目录）里粘贴下面的内容，把 `<...>` 换成实际信息。
> 作用：让新会话的 lead 立刻进入角色，不需要你手动解释一遍协议。

---

按本项目的「软件开发子代理团队」协议工作。

1. 先读 `AGENTS.md`、`subagents/README.md`、`subagents/protocol.toml`，确认你是 leader（调度）。
2. 按 `protocol.toml` 的流水线判断任务类型；需要时创建 router / planner / worker / reviewer 子代理，
   每次创建都用 `subagents/scripts/render_prompt.py` 渲染对应角色卡，不要自己编角色设定。
3. 严格执行权限边界：单写者、`protected_paths` 未经我批准不动、评审必须独立上下文。
4. 先输出：选定的流水线 + 计划摘要 + 需要我确认的问题（≤3 个），等我确认后再执行。
5. 完成后按完成定义（DoD）给我结论和证据路径（`runs/<run_id>/report.md`）。

本次任务：`<一句话描述要做什么>`

项目目录：`<项目路径>`

验收标准：`<怎么算完成，例如 pytest 全绿 / 某命令输出符合预期>`

约束：`<技术栈、不能改的目录、是否用 git、依赖限制>`
