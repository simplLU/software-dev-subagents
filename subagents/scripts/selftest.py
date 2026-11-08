#!/usr/bin/env python3
"""对 validation 规则做自测：故意制造违规，确认脚本能拦住。

用法:
    python subagents/scripts/selftest.py

每次用例都会把 subagents/ 复制到临时目录、制造一处违规、运行校验脚本，
并断言输出中出现了预期的错误码。这样可证明"权限边界"不是纸面约定。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 临时目录放在工作区内（沙箱通常不允许写系统临时目录）
WORKSPACE_ROOT = ROOT.parent
BASE = WORKSPACE_ROOT / ".subagents-selftest"


def copy_pack(dest: Path) -> Path:
    shutil.copytree(
        ROOT,
        dest / "subagents",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return dest / "subagents"


def mutate(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"自测用例失效：在 {path.name} 中找不到待替换文本：{old[:60]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def run_validate(pack: Path) -> tuple[int, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, str(pack / "scripts" / "validate_agents.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return proc.returncode, proc.stdout + proc.stderr


def case_baseline(pack: Path) -> None:
    """原样必须通过。"""
    pass


def case_write_drift(pack: Path) -> None:
    """角色写域与 protocol.ownership 不一致。"""
    mutate(
        pack / "planner.toml",
        'write = ["runs/{run_id}/plan.md", "runs/{run_id}/tasks.json", "docs/specs/**"]',
        'write = ["runs/{run_id}/plan.md", "runs/{run_id}/tasks.json", "docs/specs/**", "src/**"]',
    )


def case_write_overlap(pack: Path) -> None:
    """worker 与 reviewer 写域重叠（两侧同时改，保证先过一致性检查）。"""
    mutate(
        pack / "protocol.toml",
        'worker   = ["src/**", "tests/**", "scripts/**", "runs/{run_id}/impl/**"]',
        'worker   = ["src/**", "tests/**", "scripts/**", "runs/{run_id}/impl/**", "runs/{run_id}/review.md"]',
    )
    mutate(
        pack / "worker.toml",
        'write = ["src/**", "tests/**", "scripts/**", "runs/{run_id}/impl/**"]',
        'write = ["src/**", "tests/**", "scripts/**", "runs/{run_id}/impl/**", "runs/{run_id}/review.md"]',
    )


def case_approve_power(pack: Path) -> None:
    """reviewer 失去实现放行权。"""
    mutate(
        pack / "reviewer.toml",
        'approve = ["implementation_approved", "merge_gate"]',
        'approve = ["merge_gate"]',
    )


def case_spawn_illegal(pack: Path) -> None:
    """leader 被禁止派出子代理。"""
    mutate(pack / "leader.toml", "allowed = true", "allowed = false")


def case_protected(pack: Path) -> None:
    """受保护路径落进 worker 写域。"""
    mutate(
        pack / "protocol.toml",
        '  "migrations/**",',
        '  "migrations/**",\n  "src/secret.pem",',
    )


def case_pipeline(pack: Path) -> None:
    """feature 流水线被删掉 reviewer。"""
    mutate(
        pack / "protocol.toml",
        '"worker:implement", "reviewer:review", "leader:deliver",',
        '"worker:implement", "leader:deliver",',
    )


CASES = [
    ("基线：原样应通过", case_baseline, None),
    ("角色写域漂移", case_write_drift, "WRITE_DRIFT"),
    ("写域重叠", case_write_overlap, "WRITE_OVERLAP"),
    ("放行权被篡改", case_approve_power, "APPROVE_POWER"),
    ("派出权被篡改", case_spawn_illegal, "SPAWN_LEADER"),
    ("受保护路径被写入", case_protected, "PROTECTED_OVERLAP"),
    ("流水线缺少 reviewer", case_pipeline, "PIPELINE_NO_REVIEW"),
]


def main() -> int:
    failures = 0
    BASE.mkdir(exist_ok=True)
    try:
        for index, (name, mutator, expected) in enumerate(CASES):
            case_dir = BASE / f"case-{index:02d}"
            if case_dir.exists():
                shutil.rmtree(case_dir, ignore_errors=True)
            case_dir.mkdir(parents=True)
            pack = copy_pack(case_dir)
            mutator(pack)
            code, output = run_validate(pack)
            if expected is None:
                passed = code == 0
            else:
                passed = code != 0 and expected in output
            mark = "PASS" if passed else "FAIL"
            print(f"[{mark}] {name}" + (f"（期望 {expected}）" if expected else ""))
            if not passed:
                failures += 1
                print("  ---- 校验输出 ----")
                print("  " + output.replace("\n", "\n  ").strip())
            shutil.rmtree(case_dir, ignore_errors=True)
    finally:
        if BASE.exists() and not any(BASE.iterdir()):
            BASE.rmdir()
    print()
    print(f"自测结果：{len(CASES) - failures}/{len(CASES)} 通过")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
