#!/usr/bin/env python3
"""
知识库目录索引生成器

扫描知识库目录，为每个子目录生成轻量索引条目。
索引仅做路由用途，不存储段落信息或图片引用。

每个子目录需包含至少一个 .md 文件作为主文档。
优先识别 full.md（向后兼容），否则使用第一个 .md 文件。

每条索引包含：
  - dir: 目录名
  - file: 主文档文件名（如 full.md、README.md 等）
  - title: 从主文档首个标题提取
  - category: 从目录名前缀推断（technical/delivery/other）
  - headings: 前 5 个 H2 标题（用于消歧相似文档）
  - summary: 正文前 100 字（用于消歧相似内容）

用法：
  python ${CLAUDE_SKILL_DIR}/tools/kb_indexer.py --scan
  python ${CLAUDE_SKILL_DIR}/tools/kb_indexer.py --scan --kb-path /path/to/Local-KnowledgeBase
  python ${CLAUDE_SKILL_DIR}/tools/kb_indexer.py --scan --output /path/to/output.yaml

输出：Local-KnowledgeBase/.index/kb_catalog.yaml（默认）
"""

import argparse
import datetime
import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    import subprocess
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "pyyaml", "-q"],
        stderr=subprocess.DEVNULL
    )
    import yaml


# 目录名前缀 → category 映射
CATEGORY_MAP = {
    "技术方案": "technical",
    "交付方案": "delivery",
    "商务方案": "commercial",
    "服务方案": "service",
}


def infer_category(dir_name: str) -> str:
    """从目录名前缀推断分类"""
    for prefix, category in CATEGORY_MAP.items():
        if dir_name.startswith(prefix):
            return category
    return "other"


def extract_title(md_path: Path) -> str:
    """从主文档提取首个标题（H1 或 H2）"""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    # 去掉 # 前缀
                    return re.sub(r'^#+\s*', '', line).strip()
    except Exception as e:
        logger.warning(f"提取标题失败 {md_path}: {e}")
    return ""


def extract_headings(md_path: Path, max_count: int = 5) -> list:
    """从主文档提取前 N 个次级标题（跳过首个标题，作为 title 已单独提取）

    自动检测文档的标题层级：
    - 若存在 H2（## ），提取 H2 标题
    - 若全部为 H1（# ），跳过首个 H1 后提取剩余 H1 标题
    """
    headings = []
    h1_headings = []
    h2_headings = []
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("## ") and not line.startswith("### "):
                    heading = re.sub(r'^##\s*', '', line).strip()
                    if heading:
                        h2_headings.append(heading)
                elif line.startswith("# ") and not line.startswith("## "):
                    heading = re.sub(r'^#\s*', '', line).strip()
                    if heading:
                        h1_headings.append(heading)
    except Exception as e:
        logger.warning(f"提取标题失败 {md_path}: {e}")

    # 优先用 H2；若无 H2 则用 H1（跳过首个，已作为 title）
    if h2_headings:
        headings = h2_headings[:max_count]
    elif len(h1_headings) > 1:
        headings = h1_headings[1:max_count + 1]

    return headings


def extract_summary(md_path: Path, max_chars: int = 100) -> str:
    """从主文档提取正文前 N 字（跳过标题行和图片引用）"""
    text_parts = []
    chars_collected = 0
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                # 跳过空行、标题行、图片引用
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                if stripped.startswith("!["):
                    continue
                # 收集正文
                text_parts.append(stripped)
                chars_collected += len(stripped)
                if chars_collected >= max_chars:
                    break
    except Exception as e:
        logger.warning(f"提取摘要失败 {md_path}: {e}")

    summary = "".join(text_parts)
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "..."
    return summary


def scan_kb_directory(kb_path: Path) -> list:
    """扫描知识库目录，生成索引条目列表"""
    entries = []

    if not kb_path.exists():
        print(f"错误：目录不存在: {kb_path}", file=sys.stderr)
        return entries

    # 遍历子目录
    subdirs = sorted([
        d for d in kb_path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])

    for subdir in subdirs:
        # 自动发现子目录中的 .md 文件，优先 full.md（向后兼容）
        md_files = sorted(subdir.glob("*.md"))
        if not md_files:
            print(f"跳过（无 .md 文件）: {subdir.name}")
            continue
        main_md = next((f for f in md_files if f.name == "full.md"), md_files[0])

        dir_name = subdir.name
        title = extract_title(main_md)
        category = infer_category(dir_name)
        headings = extract_headings(main_md)
        summary = extract_summary(main_md)

        entry = {
            "dir": dir_name,
            "file": main_md.name,
            "title": title or dir_name,
            "category": category,
            "headings": headings,
            "summary": summary,
        }
        entries.append(entry)
        print(f"已索引: {dir_name} ({category}, {len(headings)} headings)")

    return entries


def get_default_kb_path() -> Path:
    """获取默认 KB 路径（从配置文件读取）"""
    config_path = Path.home() / ".config" / "tender-workflow" / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            lib_path = config.get("localkb", {}).get("path")
            if lib_path:
                return Path(lib_path)
        except Exception:
            pass
    return None


def get_default_output_path() -> Path:
    """获取默认输出路径"""
    # 尝试从配置获取 localkb 路径
    kb_path = get_default_kb_path()
    if kb_path:
        index_dir = kb_path / ".index"
        index_dir.mkdir(parents=True, exist_ok=True)
        return index_dir / "kb_catalog.yaml"

    # 回退到 tender-workflow 项目目录。
    # 文件位于 skills/taw/tools/kb_indexer.py，4 个 .parent 解析到 tender-workflow/
    # 迁移前在 .claude/skills/taw/tools/ 下需要 5 个 .parent，.claude/ 层移除后相应减 1。
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    index_dir = project_root / "Local-KnowledgeBase" / ".index"
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir / "kb_catalog.yaml"


def main():
    parser = argparse.ArgumentParser(description="知识库目录索引生成器")
    parser.add_argument("--scan", action="store_true", help="扫描并生成索引")
    parser.add_argument("--kb-path", type=str, help="Local-KnowledgeBase 目录路径")
    parser.add_argument("--output", type=str, help="输出文件路径（默认自动检测）")
    parser.add_argument("--max-headings", type=int, default=5, help="每个文档最多提取的 H2 标题数")
    parser.add_argument("--max-summary", type=int, default=100, help="摘要最大字符数")
    args = parser.parse_args()

    if not args.scan:
        parser.print_help()
        return

    # 确定 KB 路径
    if args.kb_path:
        kb_path = Path(args.kb_path)
    else:
        kb_path = get_default_kb_path()
        if not kb_path:
            print("错误：未指定 --kb-path，且配置文件中无 localkb.path", file=sys.stderr)
            sys.exit(1)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = get_default_output_path()

    print(f"扫描目录: {kb_path}")
    print(f"输出文件: {output_path}")
    print()

    # 扫描
    entries = scan_kb_directory(kb_path)

    if not entries:
        print("未找到任何有效文档目录")
        sys.exit(1)

    # 生成索引
    catalog = {
        "generated_at": datetime.datetime.now().isoformat(),
        "source_dir": str(kb_path),
        "total_docs": len(entries),
        "entries": entries,
    }

    # 写入
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            catalog, f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    print(f"\n索引生成完成: {len(entries)} 个文档 → {output_path}")
    print(f"索引大小: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
