#!/usr/bin/env python3
"""把「软件开发子代理团队」安装到任意项目根目录。

安装内容:
    <target>/subagents/          # 5 个角色 + 协议 + 脚本 + 文档
    <target>/AGENTS.md           # 项目约定（已有则追加带标记的块，不覆盖原文）
    <target>/runs/               # run 产物目录（含 .gitkeep）
    <target>/.gitignore          # 追加 Python / 自测临时目录忽略项

用法:
    python subagents/scripts/install_into_project.py --target "D:\\code\\myapp"
    python subagents/scripts/install_into_project.py --target . --force
    python subagents/scripts/install_into_project.py --target . --dry-run

安装完成后，在该项目目录新开会话时 AGENTS.md 会被自动加载，
新会话开场白模板见 <target>/subagents/templates/session_start.md。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parent.parent          # .../<project>/subagents
WORKSPACE_ROOT = PACK_ROOT.parent                            # 团队仓库根（含 AGENTS.md）
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".subagents-selftest")
MARKER_START = "<!-- subagents-team:start -->"
MARKER_END = "<!-- subagents-team:end -->"

GITIGNORE_LINES = [
    "# subagents-team",
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".subagents-selftest/",
]

DEFAULT_AGENTS = """# 本工作区约定（AGENTS.md）

本工作区使用「软件开发子代理团队」协议，入口文档是
[`subagents/README.md`](subagents/README.md)。任何在本工作区做开发类任务的代理，请先读它。

## 快速规则

1. 先校验：`python subagents/scripts/validate_agents.py`
2. 一次请求 = 一个 `runs/<run_id>/` 目录，按 `subagents/protocol.toml` 的流水线执行。
3. 单写者：只写 `protocol.toml` `[ownership]` 中声明的路径；`protected_paths` 未经批准不碰。
4. 不跳 review：实现完成后必须由独立上下文的 reviewer 给出 `approve` 才能交付。
5. 产物落盘：完成声明必须附证据。
6. 改完 TOML 必须重新校验。
"""


def read_agents_block() -> str:
    source = WORKSPACE_ROOT / "AGENTS.md"
    text = source.read_text(encoding="utf-8") if source.exists() else DEFAULT_AGENTS
    return f"{MARKER_START}\n{text.strip()}\n{MARKER_END}\n"


def write_agents(target: Path, dry_run: bool) -> str:
    dest = target / "AGENTS.md"
    block = read_agents_block()
    if not dest.exists():
        if not dry_run:
            dest.write_text(block, encoding="utf-8")
        return "已创建 AGENTS.md"

    text = dest.read_text(encoding="utf-8")
    if MARKER_START in text:
        before = text.split(MARKER_START)[0]
        after = text.split(MARKER_END, 1)[1] if MARKER_END in text else ""
        new_text = before + block + after
        if not dry_run:
            dest.write_text(new_text, encoding="utf-8")
        return "已更新 AGENTS.md 中的团队约定块"
    if not dry_run:
        dest.write_text(text.rstrip() + "\n\n" + block, encoding="utf-8")
    return "已在 AGENTS.md 末尾追加团队约定块（保留原有内容）"


def update_gitignore(target: Path, dry_run: bool) -> str:
    dest = target / ".gitignore"
    text = dest.read_text(encoding="utf-8") if dest.exists() else ""
    missing = [line for line in GITIGNORE_LINES if line not in text.splitlines()]
    if not missing:
        return ".gitignore 已包含所需规则"
    addition = "\n".join(missing) + "\n"
    if not dry_run:
        dest.write_text((text.rstrip() + "\n\n" + addition) if text else addition, encoding="utf-8")
    return f".gitignore 追加 {len(missing)} 条规则"


def ensure_runs(target: Path, dry_run: bool) -> str:
    runs = target / "runs"
    if not dry_run:
        runs.mkdir(exist_ok=True)
        keep = runs / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
    return "已创建 runs/（含 .gitkeep）"


def install_pack(target: Path, force: bool, dry_run: bool) -> None:
    dest = target / "subagents"
    if dest.exists() and not force:
        raise SystemExit(
            f"目标已存在 {dest}，未做任何修改。\n"
            "如需更新角色定义，请加 --force；只想预览请加 --dry-run。"
        )
    print(f"[install] {PACK_ROOT}  ->  {dest}")
    if dry_run:
        return
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(PACK_ROOT, dest, ignore=IGNORE)


def validate(target: Path) -> bool:
    script = target / "subagents" / "scripts" / "validate_agents.py"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    print("\n".join(tail[-6:]))
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="把子代理团队安装到项目根目录")
    parser.add_argument("--target", default=".", help="目标项目根目录（默认当前目录）")
    parser.add_argument("--force", action="store_true", help="目标已存在 subagents/ 时覆盖更新")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要执行的动作，不写文件")
    parser.add_argument("--skip-validate", action="store_true", help="安装后不运行校验")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if target.exists() and not target.is_dir():
        raise SystemExit(f"目标路径已存在但不是目录: {target}")
    if not target.exists():
        if args.dry_run:
            print(f"[dry-run] 将创建目标目录: {target}")
        else:
            target.mkdir(parents=True, exist_ok=True)
            print(f"[ok] 已创建目标目录: {target}")

    target_res = target.resolve()
    if target_res == PACK_ROOT or target_res == WORKSPACE_ROOT or PACK_ROOT in target_res.parents:
        raise SystemExit("不能安装到团队仓库自身或 subagents/ 内部，请指定其他项目目录。")

    install_pack(target, args.force, args.dry_run)
    messages = [
        write_agents(target, args.dry_run),
        ensure_runs(target, args.dry_run),
        update_gitignore(target, args.dry_run),
    ]
    print(f"[ok] {messages[0]}")
    print(f"[ok] {messages[1]}")
    print(f"[ok] {messages[2]}")

    if args.dry_run:
        print("\n[dry-run] 未写入任何文件。")
        return 0
    if not args.skip_validate:
        print("\n[validate] 运行安装后的校验脚本：")
        if not validate(target):
            print("[error] 安装后校验失败，请检查。")
            return 1

    print(
        "\n安装完成。下一步：\n"
        f"  1) 在 {target} 下新开会话，AGENTS.md 会被自动加载；\n"
        f"  2) 开场白模板: {target / 'subagents' / 'templates' / 'session_start.md'}\n"
        f"  3) 渲染角色: python subagents/scripts/render_prompt.py router --run-id <id>\n"
        f"  4) 更新角色定义: 重新运行本脚本并加 --force"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
