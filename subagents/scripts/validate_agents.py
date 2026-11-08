#!/usr/bin/env python3
"""校验 subagents/ 目录下的协议与角色文件。

用法:
    python subagents/scripts/validate_agents.py
    python subagents/scripts/validate_agents.py --quiet

校验内容:
    1. protocol.toml 与 5 个角色 TOML 均可解析, 必需字段齐全;
    2. 角色 authority.write 与 protocol.ownership 完全一致（单一事实来源）;
    3. 不同角色的写域互不重叠（单写者原则）;
    4. 任何角色的写域都不与 protected_paths 冲突;
    5. 路由表中的流水线合法、角色已定义、阶段顺序正确;
    6. 分权制衡: 只有 leader 能派出子代理, 只有 reviewer 能放行实现;
    7. 每个角色的闸门、升级条件、预算字段完整。

退出码: 0 通过; 1 存在错误。
"""

from __future__ import annotations

import fnmatch
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "protocol.toml"

REQUIRED_TOP = ["schema_version", "id", "name", "name_en", "phase", "summary"]
REQUIRED_SECTIONS = [
    "persona", "responsibilities", "authority", "project_boundary",
    "io_contract", "collaboration", "escalation",
]
REQUIRED_LISTS = {
    ("persona", "principles"),
    ("responsibilities", "owns"),
    ("responsibilities", "must"),
    ("responsibilities", "must_not"),
    ("authority", "read"),
    ("authority", "write"),
    ("authority", "forbidden"),
    ("project_boundary", "in_scope"),
    ("project_boundary", "out_of_scope"),
    ("project_boundary", "stop_and_escalate"),
    ("io_contract", "inputs"),
    ("io_contract", "outputs"),
    ("io_contract", "acceptance"),
    ("collaboration", "upstream"),
    ("collaboration", "downstream"),
    ("escalation", "triggers"),
}

findings: list[tuple[str, str, str]] = []  # (level, code, message)


def err(code: str, msg: str) -> None:
    findings.append(("ERROR", code, msg))


def warn(code: str, msg: str) -> None:
    findings.append(("WARN", code, msg))


def ok(msg: str) -> None:
    findings.append(("OK", "-", msg))


def load_toml(path: Path, label: str) -> dict | None:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError:
        err("FILE_MISSING", f"{label} 不存在: {path}")
    except tomllib.TOMLDecodeError as exc:
        err("TOML_INVALID", f"{label} 解析失败: {exc}")
    return None


def static_prefix(pattern: str) -> str:
    """返回 glob 模式中第一个通配符之前的静态前缀（按路径段）。"""
    p = pattern.replace("\\", "/").strip("/")
    out: list[str] = []
    for seg in p.split("/"):
        if any(ch in seg for ch in "*?["):
            break
        out.append(seg)
    return "/".join(out)


def overlap(a: str, b: str) -> bool | None:
    """保守判断两个路径模式是否可能重叠; None 表示静态无法判断。"""
    pa, pb = static_prefix(a), static_prefix(b)
    if not pa or not pb:
        return None
    if pa == pb:
        return True
    return pa.startswith(pb + "/") or pb.startswith(pa + "/")


def covered(child: str, parent: str) -> bool:
    """child 写域是否被 parent 写域覆盖。"""
    pc, pp = static_prefix(child), static_prefix(parent)
    if not pc or not pp:
        return False
    return pc == pp or pc.startswith(pp + "/")


def check_required_table(role_id: str, data: dict, table: str, keys: list[str]) -> None:
    node = data.get(table)
    if node is None:
        err("SECTION_MISSING", f"[{role_id}] 缺少 [{table}] 段")
        return
    for key in keys:
        if key not in node:
            err("FIELD_MISSING", f"[{role_id}] [{table}] 缺少 {key}")


def get_path(data: dict, path: str):
    node = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def check_string_list(role_id: str, data: dict, table: str, key: str) -> list[str]:
    node = get_path(data, table) or {}
    value = node.get(key)
    if value is None:
        err("FIELD_MISSING", f"[{role_id}] [{table}].{key} 缺失")
        return []
    if not isinstance(value, list) or not value:
        err("LIST_EMPTY", f"[{role_id}] [{table}].{key} 必须是非空数组")
        return []
    if not all(isinstance(item, str) and item.strip() for item in value):
        err("LIST_ITEM_INVALID", f"[{role_id}] [{table}].{key} 含空项或非字符串")
    return value


def validate_roles(protocol: dict, roles: dict[str, dict], role_order: list[str]) -> None:
    ownership = protocol.get("ownership", {})
    role_ids = set(roles)

    # 1) 角色列表与 ownership 键一致
    own_keys = {k for k in ownership if not k.startswith("protected_")}
    if own_keys != role_ids:
        err(
            "OWNERSHIP_KEYS",
            f"protocol.ownership 角色键 {sorted(own_keys)} 与角色文件 {sorted(role_ids)} 不一致",
        )

    for role_id in role_order:
        data = roles.get(role_id)
        if data is None:
            continue

        # 2) 基本信息
        if data.get("id") != role_id:
            err("ID_MISMATCH", f"[{role_id}] id 字段为 {data.get('id')!r}, 与文件名不一致")
        for key in REQUIRED_TOP:
            if key not in data:
                err("FIELD_MISSING", f"[{role_id}] 顶层缺少 {key}")
        for section in REQUIRED_SECTIONS:
            if section not in data:
                err("SECTION_MISSING", f"[{role_id}] 缺少 [{section}]")
        for table, key in REQUIRED_LISTS:
            check_string_list(role_id, data, table, key)

        # 3) authority.write 必须与 protocol.ownership 完全一致
        writes = data.get("authority", {}).get("write", [])
        own = ownership.get(role_id, [])
        if set(writes) != set(own):
            err(
                "WRITE_DRIFT",
                f"[{role_id}] authority.write {writes} 与 protocol.ownership.{role_id} {own} 不一致",
            )
        if not writes:
            err("WRITE_EMPTY", f"[{role_id}] 写域为空")

        # 4) 命令执行与子代理权限
        execute = data.get("authority", {}).get("execute", {})
        if not execute:
            err("EXEC_MISSING", f"[{role_id}] 缺少 [authority.execute]")
        else:
            for key in ("allowed", "forbidden"):
                check_string_list(role_id, data, "authority.execute", key)
        spawn = data.get("authority", {}).get("spawn", {})
        if "allowed" not in spawn:
            err("SPAWN_MISSING", f"[{role_id}] 缺少 [authority.spawn].allowed")
        if not isinstance(spawn.get("max", 0), int):
            err("SPAWN_MAX", f"[{role_id}] [authority.spawn].max 必须是整数")

        # 5) 闸门完整
        gates = data.get("gates", [])
        if not gates:
            err("GATES_EMPTY", f"[{role_id}] 至少需要一个 [[gates]]")
        for index, gate in enumerate(gates):
            for key in ("id", "check", "on_fail"):
                if not gate.get(key):
                    err("GATE_FIELD", f"[{role_id}] gates[{index}] 缺少 {key}")

        # 6) 升级与预算
        escalation = data.get("escalation", {})
        if escalation.get("to") not in {"leader", "human"}:
            err("ESCALATION_TO", f"[{role_id}] escalation.to 应为 leader 或 human")
        limits = data.get("limits", {})
        if not isinstance(limits.get("max_tool_steps"), int):
            err("LIMITS_STEPS", f"[{role_id}] limits.max_tool_steps 必须是整数")

        ok(f"角色 {role_id} 结构完整")

    # 7) 单写者: 任意两个角色的写域不得重叠
    for i, a in enumerate(role_order):
        for b in role_order[i + 1:]:
            for pa in ownership.get(a, []):
                for pb in ownership.get(b, []):
                    result = overlap(pa, pb)
                    if result:
                        err("WRITE_OVERLAP", f"写域冲突: {a}:{pa} 与 {b}:{pb}")

    # 8) 受保护路径不得落在任何写域内
    protected = protocol.get("protected_paths", [])
    if not protected:
        err("PROTECTED_EMPTY", "protocol.protected_paths 不能为空")
    for role_id in role_order:
        for pattern in ownership.get(role_id, []):
            last_seg = pattern.replace("\\", "/").rstrip("/").split("/")[-1]
            for prot in protected:
                result = overlap(pattern, prot)
                if result:
                    err("PROTECTED_OVERLAP", f"[{role_id}] 写域 {pattern} 与受保护路径 {prot} 冲突")
                    continue
                # "**/*.pem" 这类"任意目录 + 后缀"模式: 用文件名段做二次判断
                if prot.startswith("**/") and fnmatch.fnmatchcase(last_seg, prot[3:]):
                    err("PROTECTED_OVERLAP", f"[{role_id}] 写域 {pattern} 命中受保护路径 {prot}")
                    continue
                # 写域本身以通配符开头时静态无法判断, 提示人工确认
                if not static_prefix(pattern):
                    warn("PROTECTED_UNKNOWN", f"[{role_id}] 无法静态判断 {pattern} 是否触碰 {prot}")

    # 9) 分权制衡: approve 权限归属
    approve_map = {
        role: set(roles[role].get("authority", {}).get("approve", [])) for role in role_order
    }
    exclusive = {
        "implementation_approved": "reviewer",
        "merge_gate": "reviewer",
        "delivery_accepted": "leader",
        "plan_approved": "leader",
    }
    for perm, owner in exclusive.items():
        holders = [role for role, perms in approve_map.items() if perm in perms]
        if holders != [owner]:
            err("APPROVE_POWER", f"批准权 {perm} 应仅属于 {owner}, 实际: {holders}")

    # 10) 只有 leader 可派出子代理
    for role in role_order:
        spawn = roles[role].get("authority", {}).get("spawn", {})
        allowed = spawn.get("allowed")
        if role == "leader":
            if allowed is not True:
                err("SPAWN_LEADER", "leader 必须允许派出子代理")
            spawn_roles = spawn.get("roles", [])
            if set(spawn_roles) - role_ids:
                err("SPAWN_ROLE_UNKNOWN", f"leader.spawn.roles 含未定义角色: {set(spawn_roles) - role_ids}")
            if spawn.get("max", 0) <= 0:
                err("SPAWN_MAX_ZERO", "leader.spawn.max 必须为正")
            ok("分权: leader 拥有唯一派出权")
        elif allowed is not False:
            err("SPAWN_ILLEGAL", f"[{role}] 不应拥有子代理派出权")


def validate_router(protocol: dict, router: dict, roles: dict[str, dict]) -> None:
    routing = protocol.get("routing", {})
    pipelines = routing.get("pipeline", [])
    if not pipelines:
        err("ROUTING_EMPTY", "protocol 至少需要一条 [[routing.pipeline]]")
        return

    ids = [p.get("id") for p in pipelines]
    if len(ids) != len(set(ids)):
        err("PIPELINE_DUP", f"流水线 id 重复: {ids}")
    if routing.get("default_pipeline") not in ids:
        err("PIPELINE_DEFAULT", "routing.default_pipeline 未指向已定义的流水线")

    role_ids = set(roles)
    max_workers = protocol.get("quality", {}).get("max_parallel_workers", 0)
    used_roles: set[str] = set()

    for pipeline in pipelines:
        pid = pipeline.get("id", "<unknown>")
        stages = pipeline.get("stages", [])
        if not stages:
            err("PIPELINE_STAGES", f"流水线 {pid} 缺少 stages")
            continue
        stage_roles = []
        for stage in stages:
            role = str(stage).split(":", 1)[0]
            if role not in role_ids:
                err("PIPELINE_ROLE", f"流水线 {pid} 阶段 {stage!r} 引用了未定义角色 {role!r}")
            stage_roles.append(role)
            used_roles.add(role)
        if stage_roles[0] != "leader":
            err("PIPELINE_START", f"流水线 {pid} 必须以 leader 起始")
        if "leader" not in stage_roles:
            err("PIPELINE_NO_LEADER", f"流水线 {pid} 缺少 leader")
        if pipeline.get("requires_review", False) and "reviewer" not in stage_roles:
            err("PIPELINE_NO_REVIEW", f"流水线 {pid} 要求评审, 但阶段中没有 reviewer")
        if pipeline.get("requires_plan", False) and "planner" not in stage_roles:
            err("PIPELINE_NO_PLAN", f"流水线 {pid} 要求规划, 但阶段中没有 planner")
        if "router" in stage_roles:
            err("PIPELINE_ROUTER", f"流水线 {pid} 不应包含 router（router 是入口, 不在执行链内）")
        if pipeline.get("max_workers", 0) > max_workers:
            err("PIPELINE_PARALLEL", f"流水线 {pid} 的 max_workers 超过 quality.max_parallel_workers")
        if not pipeline.get("gates"):
            err("PIPELINE_GATES", f"流水线 {pid} 缺少 gates")

    missing = role_ids - used_roles - {"router"}
    if missing:
        err("ROLE_UNUSED", f"以下角色未出现在任何流水线中: {sorted(missing)}")
    ok(f"路由表合法: {len(pipelines)} 条流水线")

    # router 契约
    required = {"run_id", "pipeline", "confidence", "facts", "assumptions",
                "missing_info", "risk_flags", "budget_suggestion", "target_roles"}
    fields = set(router.get("io_contract", {}).get("required_fields", []))
    if not required <= fields:
        err("ROUTE_FIELDS", f"router.required_fields 缺少: {sorted(required - fields)}")


def main() -> int:
    protocol = load_toml(PROTOCOL_PATH, "protocol.toml")
    roles: dict[str, dict] = {}
    role_order: list[str] = []

    if protocol is not None:
        role_map = protocol.get("roles", {})
        if not role_map:
            err("ROLES_MISSING", "protocol 缺少 [roles] 角色清单")
        role_order = list(role_map)
        for role_id, filename in role_map.items():
            data = load_toml(ROOT / filename, filename)
            if data is not None:
                roles[role_id] = data

    if protocol is not None:
        for key in ("schema_version", "protocol_id", "protocol_version"):
            if key not in protocol:
                err("PROTOCOL_FIELD", f"protocol 缺少 {key}")
        for section in ("run", "handoff", "ownership", "quality", "escalation", "routing", "roles"):
            if section not in protocol:
                err("PROTOCOL_SECTION", f"protocol 缺少 [{section}]")
        handoff = protocol.get("handoff", {})
        if not handoff.get("required_fields"):
            err("HANDOFF_FIELDS", "protocol.handoff.required_fields 不能为空")
        if not protocol.get("quality", {}).get("definition_of_done"):
            err("DOD_EMPTY", "protocol.quality.definition_of_done 不能为空")

    if protocol is not None and role_order and len(roles) == len(role_order):
        validate_roles(protocol, roles, role_order)
        if "router" in roles:
            validate_router(protocol, roles["router"], roles)
        else:
            err("ROUTER_MISSING", "缺少 router 角色, 无法校验路由表")

    errors = [f for f in findings if f[0] == "ERROR"]
    warnings = [f for f in findings if f[0] == "WARN"]
    oks = [f for f in findings if f[0] == "OK"]

    for level, code, message in findings:
        if level == "OK":
            continue
        print(f"[{level}] {code}: {message}")

    print()
    print(f"通过: {len(oks)} 项 | 警告: {len(warnings)} 项 | 错误: {len(errors)} 项")
    if errors:
        print("校验失败，请修复上述错误。")
        return 1
    print(f"校验通过: 协议与 {len(role_order)} 个角色文件一致, 权限边界无冲突。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
