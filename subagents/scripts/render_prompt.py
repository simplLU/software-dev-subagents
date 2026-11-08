#!/usr/bin/env python3
"""把角色 TOML 渲染成可直接交给子代理（subagent / spawn_teammate）的提示词。

用法:
    # 列出全部角色
    python subagents/scripts/render_prompt.py --list

    # 渲染某个角色（自动带上全局协议摘要）
    python subagents/scripts/render_prompt.py planner

    # 渲染并附加本次任务
    python subagents/scripts/render_prompt.py worker --run-id 20260101-120000-add-cli \
        --task-file subagents/examples/feature_request.md

    # 保存到文件, 再粘贴 / 传给子代理
    python subagents/scripts/render_prompt.py reviewer --task "复核 task-1 的 diff" \
        --out runs/20260101-120000-add-cli/reviewer_prompt.md
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "protocol.toml"


def role_order_of(protocol: dict) -> list[str]:
    """从 protocol.roles 派生角色顺序; 缺失时回退到默认顺序。"""
    mapped = list(protocol.get("roles", {}))
    return mapped or ["router", "leader", "planner", "worker", "reviewer"]


def load_toml(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def bullet(items, indent: str = "") -> str:
    return "\n".join(f"{indent}- {item}" for item in items)


def render(
    role: dict,
    protocol: dict,
    *,
    task: str | None = None,
    run_id: str = "<run_id>",
    include_protocol: bool = True,
    role_order: list[str] | None = None,
) -> str:
    role_order = role_order or role_order_of(protocol)
    artifact_root = protocol.get("run", {}).get("artifact_root", "runs/{run_id}")
    run_dir = artifact_root.replace("{run_id}", run_id)
    a = role
    out: list[str] = []

    out.append(f"# 角色卡：{a['name']}（{a['id']}）")
    out.append("")
    out.append(
        f"> 团队协议：{protocol.get('protocol_id')} v{protocol.get('protocol_version')} · "
        f"阶段：{a.get('phase')} · 角色版本：{a.get('role_version')}"
    )
    out.append(f"> 本次 run：`{run_id}` · 产物目录：`{run_dir}`")
    out.append("> 你是团队中的子代理，不是用户的最终接口人；对用户的结论由 leader 汇总。")
    out.append("")

    persona = a.get("persona", {})
    out.append("## 1. 你是谁")
    out.append("")
    out.append(f"- 定位：{persona.get('role', '')}")
    out.append(f"- 工作姿态：{persona.get('stance', '')}")
    out.append("")
    out.append("工作原则：")
    out.append(bullet(persona.get("principles", [])))
    out.append("")

    resp = a.get("responsibilities", {})
    out.append("## 2. 职责")
    out.append("")
    out.append("你负责（owns）：")
    out.append(bullet(resp.get("owns", [])))
    out.append("")
    out.append("你必须（must）：")
    out.append(bullet(resp.get("must", [])))
    out.append("")
    out.append("你绝不（must_not）：")
    out.append(bullet(resp.get("must_not", [])))
    out.append("")

    auth = a.get("authority", {})
    out.append("## 3. 权限边界（硬约束，越界即停）")
    out.append("")
    out.append(f"- 可读：{', '.join(auth.get('read', []))}")
    out.append(f"- 可写（仅此范围）：{', '.join(auth.get('write', []))}")
    if auth.get("write_rule"):
        out.append(f"- 写域规则：{auth['write_rule']}")
    execute = auth.get("execute", {})
    out.append("")
    out.append("命令执行：")
    out.append(f"- 允许：{'; '.join(execute.get('allowed', []))}")
    out.append(f"- 需批准：{'; '.join(execute.get('needs_approval', [])) or '无'}")
    out.append(f"- 禁止：{'; '.join(execute.get('forbidden', []))}")
    out.append("")
    spawn = auth.get("spawn", {})
    if spawn.get("allowed"):
        out.append(
            f"- 调用子代理：允许，最多 {spawn.get('max')} 个，"
            f"可选角色 {', '.join(spawn.get('roles', []))}"
        )
    else:
        out.append("- 调用子代理：不允许（你没有派出权）")
    approve = auth.get("approve", [])
    out.append(f"- 批准权限：{', '.join(approve) if approve else '无'}")
    if auth.get("requires_approval"):
        out.append(f"- 需上层批准：{'；'.join(auth['requires_approval'])}")
    out.append("")
    out.append("明确禁止：")
    out.append(bullet(auth.get("forbidden", [])))
    out.append("")

    boundary = a.get("project_boundary", {})
    out.append("## 4. 项目边界")
    out.append("")
    out.append(f"- 工作区：{boundary.get('workspace', '')}")
    out.append(f"- 跨仓库：{boundary.get('cross_repo', '')}")
    out.append("")
    out.append("范围内（in scope）：")
    out.append(bullet(boundary.get("in_scope", [])))
    out.append("")
    out.append("范围外（out of scope，不得越界）：")
    out.append(bullet(boundary.get("out_of_scope", [])))
    out.append("")
    out.append("触发升级即停（stop & escalate）：")
    out.append(bullet(boundary.get("stop_and_escalate", [])))
    out.append("")

    io = a.get("io_contract", {})
    out.append("## 5. 输入 / 输出契约")
    out.append("")
    out.append("输入：")
    out.append(bullet(io.get("inputs", [])))
    out.append("")
    out.append(f"产物：{', '.join(io.get('outputs', []))}")
    if io.get("output_format"):
        out.append(f"格式：{io['output_format']}")
    if io.get("required_sections"):
        out.append(f"必需章节：{', '.join(io['required_sections'])}")
    if io.get("required_fields"):
        out.append(f"必需字段：{', '.join(io['required_fields'])}")
    if io.get("task_fields"):
        out.append(f"任务字段：{', '.join(io['task_fields'])}")
    if io.get("report_sections"):
        out.append(f"报告章节：{', '.join(io['report_sections'])}")
    if io.get("review_json_fields"):
        out.append(f"评审 JSON 字段：{', '.join(io['review_json_fields'])}")
    if io.get("route_json_fields"):
        out.append(f"路由 JSON 字段：{', '.join(io['route_json_fields'])}")
    out.append("")
    out.append("验收（你的产出必须满足）：")
    out.append(bullet(io.get("acceptance", [])))
    out.append("")

    out.append("## 6. 闸门（未通过不得进入下一阶段）")
    out.append("")
    for gate in a.get("gates", []):
        out.append(f"- [{gate.get('id')}] {gate.get('check')}")
        out.append(f"  - 失败处理：{gate.get('on_fail')}")
    out.append("")

    esc = a.get("escalation", {})
    out.append("## 7. 升级机制")
    out.append("")
    out.append(f"- 升级对象：{esc.get('to')}")
    out.append(f"- 升级阶梯：{' → '.join(esc.get('ladder', []))}")
    out.append("- 触发条件：")
    out.append(bullet(esc.get("triggers", []), indent="  "))
    out.append("")

    if include_protocol:
        out.append("## 8. 团队全局协议（所有角色共享，不可违反）")
        out.append("")
        out.append("### 单写者原则（路径所有权）")
        ownership = protocol.get("ownership", {})
        for role_id in role_order:
            patterns = ownership.get(role_id, [])
            if patterns:
                out.append(f"- {role_id}: {', '.join(patterns)}")
        out.append("")
        out.append("受保护路径（未经人类批准一律不可写）：")
        out.append(", ".join(protocol.get("protected_paths", [])))
        out.append("")
        handoff = protocol.get("handoff", {})
        out.append("### 交接信封")
        out.append(f"- 必填字段：{', '.join(handoff.get('required_fields', []))}")
        out.append(f"- 信任规则：{handoff.get('trust_rule', '')}")
        out.append("")
        quality = protocol.get("quality", {})
        out.append("### 完成定义（DoD）")
        out.append(bullet(quality.get("definition_of_done", [])))
        out.append("")
        routing = protocol.get("routing", {})
        out.append("### 可用流水线（不要发明新流水线）")
        for pipeline in routing.get("pipeline", []):
            out.append(
                f"- {pipeline.get('id')}（{pipeline.get('label')}）："
                f"{' → '.join(pipeline.get('stages', []))}"
            )
        out.append("")
        out.append("需要人类确认的信号：")
        out.append(bullet(routing.get("require_human_approval_for", [])))
        out.append("")

    out.append("## 9. 本次任务")
    out.append("")
    if task:
        out.append(task.strip())
    else:
        out.append("（尚未分配任务。等待 leader 下发任务信封；收到前只做准备与自检。）")
    out.append("")

    out.append("## 10. 交付格式（交接信封，JSON）")
    out.append("")
    out.append("```json")
    out.append("{")
    out.append(f'  "run_id": "{run_id}",')
    out.append('  "task_id": "<任务 id>",')
    out.append(f'  "from": "{a["id"]}",')
    out.append('  "to": "<下游角色>",')
    out.append(f'  "phase": "{a.get("phase")}",')
    out.append('  "summary": "<一句话结论>",')
    out.append('  "artifacts": ["<产物路径>"],')
    out.append('  "open_questions": ["<未决问题，最多 3 条>"]')
    out.append("}")
    out.append("```")
    out.append("")
    out.append("## 11. 开始前自检")
    out.append("")
    out.append(f"1. 确认 run_id 为 `{run_id}`，所有产物写入 `{run_dir}/`；")
    out.append("2. 确认任务信封中的输入齐全，缺失项进入 open_questions 并升级，不猜测；")
    out.append("3. 确认你的写域：只允许写上面列出的路径，越界即停；")
    out.append("4. 完成后输出交接信封，并把产物路径列全。")
    out.append("")

    return "\n".join(out)


def main() -> int:
    protocol = load_toml(PROTOCOL_PATH)
    role_order = role_order_of(protocol)
    role_files = protocol.get("roles", {})

    parser = argparse.ArgumentParser(description="把角色 TOML 渲染为子代理提示词")
    parser.add_argument("role", nargs="?", help=f"角色 id: {' / '.join(role_order)}")
    parser.add_argument("--list", action="store_true", help="列出全部角色")
    parser.add_argument("--task", help="本次任务描述文本")
    parser.add_argument("--task-file", help="从文件读取本次任务描述")
    parser.add_argument("--run-id", default="<run_id>", help="run id（默认占位符 <run_id>）")
    parser.add_argument("--no-protocol", action="store_true", help="不输出全局协议摘要")
    parser.add_argument("--out", help="输出到文件而不是标准输出")
    args = parser.parse_args()

    if args.list:
        print(f"{'id':<10}{'阶段':<10}{'名称':<10}说明")
        for role_id in role_order:
            filename = role_files.get(role_id, f"{role_id}.toml")
            data = load_toml(ROOT / filename)
            print(
                f"{role_id:<10}{data.get('phase', ''):<10}"
                f"{data.get('name', ''):<10}{data.get('summary', '')}"
            )
        return 0

    if not args.role:
        parser.print_help()
        return 2
    if args.role not in role_order:
        print(f"未知角色: {args.role}；可选: {', '.join(role_order)}", file=sys.stderr)
        return 2
    if args.task and args.task_file:
        print("--task 与 --task-file 只能二选一", file=sys.stderr)
        return 2

    task = args.task
    if args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8")

    filename = role_files.get(args.role, f"{args.role}.toml")
    role = load_toml(ROOT / filename)
    prompt = render(
        role,
        protocol,
        task=task,
        run_id=args.run_id,
        include_protocol=not args.no_protocol,
        role_order=role_order,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(prompt, encoding="utf-8")
        print(f"已写入: {out_path}")
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
