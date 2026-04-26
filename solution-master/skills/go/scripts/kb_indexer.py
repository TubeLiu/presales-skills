#!/usr/bin/env python3
"""
知识库目录索引生成器

扫描知识库目录，为每个子目录生成轻量索引条目。
索引仅做路由用途，不存储段落信息或图片引用。

用法：
  python3 kb_indexer.py --scan
  python3 kb_indexer.py --scan --kb-path /path/to/Local-KnowledgeBase
  python3 kb_indexer.py --scan --output /path/to/output.yaml

输出：Local-KnowledgeBase/.index/kb_catalog.yaml（默认）
"""

import argparse
import datetime
import logging
import re
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    import subprocess
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyyaml", "-q"],
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print("错误：缺少 pyyaml 依赖且自动安装失败，请手动执行：", file=sys.stderr)
        print(f"  {sys.executable} -m pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    import yaml


# 目录名前缀 -> category 映射（扩展版，适用于通用方案）
CATEGORY_MAP = {
    "技术方案": "technical",
    "交付方案": "delivery",
    "商务方案": "commercial",
    "服务方案": "service",
    "项目方案": "project",
    "运维方案": "operations",
    "安全方案": "security",
    "业务方案": "business",
    "咨询报告": "consulting",
    "行业研究": "research",
    "产品文档": "product",
    "培训资料": "training",
}


def infer_category(dir_name: str) -> str:
    """从目录名前缀推断分类"""
    for prefix, category in CATEGORY_MAP.items():
        if dir_name.startswith(prefix):
            return category
    return "other"


def extract_metadata(md_path: Path, max_headings: int = 5, max_summary_chars: int = 100) -> dict:
    """单次读取主文档，提取 title、headings、summary"""
    title = ""
    h1_headings = []
    h2_headings = []
    summary_parts = []
    summary_chars = 0
    summary_done = False

    try:
        with open(md_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                if stripped.startswith("#"):
                    heading_text = re.sub(r'^#+\s*', '', stripped).strip()
                    if not heading_text:
                        continue
                    if stripped.startswith("## ") and not stripped.startswith("### "):
                        h2_headings.append(heading_text)
                    elif stripped.startswith("# ") and not stripped.startswith("## "):
                        if not title:
                            title = heading_text
                        h1_headings.append(heading_text)
                    # 早期退出：已收集足够标题且摘要已满
                    if summary_done and len(h2_headings) >= max_headings:
                        break
                    continue

                if stripped.startswith("!["):
                    continue

                if not summary_done:
                    summary_parts.append(stripped)
                    summary_chars += len(stripped)
                    if summary_chars >= max_summary_chars:
                        summary_done = True
                        if len(h2_headings) >= max_headings:
                            break
    except Exception as e:
        logger.warning(f"提取元数据失败 {md_path}: {e}")

    # headings: 优先用 H2；若无 H2 则用 H1（跳过首个，已作为 title）
    if h2_headings:
        headings = h2_headings[:max_headings]
    elif len(h1_headings) > 1:
        headings = h1_headings[1:max_headings + 1]
    else:
        headings = []

    summary = "".join(summary_parts)
    if len(summary) > max_summary_chars:
        summary = summary[:max_summary_chars] + "..."

    return {"title": title, "headings": headings, "summary": summary}


def scan_kb_directory(kb_path: Path) -> list:
    """扫描知识库目录，生成索引条目列表"""
    entries = []
    if not kb_path.exists():
        print(f"错误：目录不存在: {kb_path}", file=sys.stderr)
        return entries

    subdirs = sorted([
        d for d in kb_path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])

    for subdir in subdirs:
        md_files = sorted(subdir.glob("*.md"))
        if not md_files:
            print(f"跳过（无 .md 文件）: {subdir.name}")
            continue
        main_md = next((f for f in md_files if f.name == "full.md"), md_files[0])

        dir_name = subdir.name
        meta = extract_metadata(main_md)
        entry = {
            "dir": dir_name,
            "file": main_md.name,
            "title": meta["title"] or dir_name,
            "category": infer_category(dir_name),
            "headings": meta["headings"],
            "summary": meta["summary"],
        }
        entries.append(entry)
        print(f"已索引: {dir_name} ({entry['category']}, {len(entry['headings'])} headings)")

    return entries


def get_default_kb_path() -> Optional[Path]:
    """获取默认 KB 路径（通过 sm_config 读取）。

    v1.0.0 fix：原路径 `parent.parent.parent / 'solution-config' / 'scripts'` 是
    0.1.x 残留的死引用（`solution-config` skill 已合并到 mega，且实际解析到不存在的
    `skills/skills/solution-config/scripts/`，import 永远静默失败 → 本函数永远返回
    None）。修复为 `parent`：sm_config.py 与 kb_indexer.py 同处 scripts/ 目录。
    """
    try:
        import sys as _sys
        _sm_config_dir = str(Path(__file__).resolve().parent)
        if _sm_config_dir not in _sys.path:
            _sys.path.insert(0, _sm_config_dir)
        from sm_config import get
        lib_path = get("localkb.path")
        if lib_path:
            return Path(lib_path)
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="知识库目录索引生成器")
    parser.add_argument("--scan", action="store_true", help="扫描并生成索引")
    parser.add_argument("--kb-path", type=str, help="Local-KnowledgeBase 目录路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()

    if not args.scan:
        parser.print_help()
        return

    if args.kb_path:
        kb_path = Path(args.kb_path)
    else:
        kb_path = get_default_kb_path()
        if not kb_path:
            print("错误：未指定 --kb-path，且配置文件中无 localkb.path", file=sys.stderr)
            sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = kb_path / ".index" / "kb_catalog.yaml"

    print(f"扫描目录: {kb_path}")
    print(f"输出文件: {output_path}")

    entries = scan_kb_directory(kb_path)
    if not entries:
        print("未找到任何有效文档目录")
        sys.exit(1)

    catalog = {
        "generated_at": datetime.datetime.now().isoformat(),
        "source_dir": str(kb_path),
        "total_docs": len(entries),
        "entries": entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"\n索引生成完成: {len(entries)} 个文档 -> {output_path}")


if __name__ == "__main__":
    main()
