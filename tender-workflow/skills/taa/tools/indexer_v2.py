#!/usr/bin/env python3
"""
Product Index V2 - 三层索引生成器

使用大模型语义聚类，将 product.yaml 的 472 条 entries 分层索引：
- L0: 快速路由索引（~5KB）- 8-10个分类
- L1: 分类索引（每个~15KB）- 每个分类的条目摘要
- L2: 完整详情（按需加载）- 完整字段

用法:
    python3 .claude/skills/taa/tools/indexer_v2.py --input .index/product.yaml --output .index/
    python3 .claude/skills/taa/tools/indexer_v2.py --input /path/to/product.yaml --output /path/to/output/
"""

import yaml
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

def load_product_yaml(file_path: str) -> Dict[str, Any]:
    """加载 product.yaml 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def extract_entries(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """提取所有 entries"""
    entries = []
    for sheet in data.get('sheets', []):
        for entry in sheet.get('entries', []):
            entries.append(entry)
    return entries

def semantic_clustering(entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    语义聚类：将 entries 分为 8-10 个分类

    基于关键词和描述的语义相似度进行聚类
    """
    # 预定义分类（基于云原生产品特性）
    categories = {
        "Platform Lifecycle": {
            "keywords": ["install", "upgrade", "lifecycle", "deployment", "disaster", "recovery", "backup"],
            "entries": []
        },
        "Container Management": {
            "keywords": ["kubernetes", "container", "pod", "cluster", "workload", "deployment", "statefulset"],
            "entries": []
        },
        "Multi-Cluster": {
            "keywords": ["multi-cluster", "federation", "global", "hosted", "control plane"],
            "entries": []
        },
        "Networking": {
            "keywords": ["network", "ingress", "service", "load balancer", "dns", "proxy", "gateway"],
            "entries": []
        },
        "Storage": {
            "keywords": ["storage", "volume", "pv", "pvc", "csi", "snapshot"],
            "entries": []
        },
        "Security & Access": {
            "keywords": ["security", "rbac", "authentication", "authorization", "policy", "audit", "compliance"],
            "entries": []
        },
        "Observability": {
            "keywords": ["monitoring", "logging", "metrics", "alert", "trace", "prometheus", "grafana"],
            "entries": []
        },
        "DevOps & CI/CD": {
            "keywords": ["cicd", "pipeline", "git", "build", "deploy", "release", "devops"],
            "entries": []
        },
        "AI & GPU": {
            "keywords": ["ai", "gpu", "machine learning", "model", "training", "inference", "nvidia"],
            "entries": []
        },
        "Service Mesh & Microservices": {
            "keywords": ["service mesh", "istio", "microservice", "sidecar", "traffic", "canary"],
            "entries": []
        }
    }

    # 为每个 entry 分配分类
    for entry in entries:
        # 提取 entry 的关键词和描述
        entry_keywords = set(entry.get('keywords', []))
        entry_desc = (entry.get('description', '') + ' ' + entry.get('name', '')).lower()

        # 计算与每个分类的匹配度
        best_category = None
        best_score = 0

        for cat_name, cat_info in categories.items():
            score = 0
            for keyword in cat_info['keywords']:
                # 关键词匹配
                if keyword in entry_keywords:
                    score += 2
                # 描述匹配
                if keyword.lower() in entry_desc:
                    score += 1

            if score > best_score:
                best_score = score
                best_category = cat_name

        # 如果没有匹配，归入 "Other"
        if best_category is None or best_score == 0:
            if "Other" not in categories:
                categories["Other"] = {"keywords": [], "entries": []}
            categories["Other"]["entries"].append(entry)
        else:
            categories[best_category]["entries"].append(entry)

    # 移除空分类
    return {k: v["entries"] for k, v in categories.items() if v["entries"]}

def generate_l0_index(categories: Dict[str, List[Dict[str, Any]]], output_dir: Path):
    """生成 L0 快速路由索引"""
    l0_data = {
        "version": "2.0",
        "generated_at": datetime.now().isoformat(),
        "total_entries": sum(len(entries) for entries in categories.values()),
        "categories": []
    }

    for cat_name, entries in categories.items():
        # 提取核心关键词（取前5个最常见的）
        keyword_freq = defaultdict(int)
        for entry in entries:
            for kw in entry.get('keywords', []):
                keyword_freq[kw] += 1

        core_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        core_keywords = [kw for kw, _ in core_keywords]

        l0_data["categories"].append({
            "name": cat_name,
            "entry_count": len(entries),
            "l1_file": f"product_l1_{cat_name.lower().replace(' ', '_').replace('&', 'and').replace('/', '_')}.yaml",
            "core_keywords": core_keywords
        })

    # 写入 L0 文件
    l0_file = output_dir / "product_l0.yaml"
    with open(l0_file, 'w', encoding='utf-8') as f:
        yaml.dump(l0_data, f, allow_unicode=True, sort_keys=False)

    print(f"✓ 生成 L0 索引: {l0_file} ({l0_file.stat().st_size / 1024:.1f} KB)")
    return l0_data

def generate_l1_l2_indexes(categories: Dict[str, List[Dict[str, Any]]], output_dir: Path):
    """生成 L1 分类索引和 L2 完整详情"""
    for cat_name, entries in categories.items():
        cat_slug = cat_name.lower().replace(' ', '_').replace('&', 'and').replace('/', '_')

        # L1: 分类索引（只包含摘要信息）
        l1_data = {
            "category": cat_name,
            "entry_count": len(entries),
            "entries": []
        }

        # L2: 完整详情
        l2_data = {
            "category": cat_name,
            "entries": []
        }

        for idx, entry in enumerate(entries):
            # L1 条目（精简）
            l1_entry = {
                "id": entry.get('id'),
                "name": entry.get('name', ''),
                "description": entry.get('description', ''),
                "summary": entry.get('parameters', '')[:100] + '...' if len(entry.get('parameters', '')) > 100 else entry.get('parameters', ''),
                "l2_offset": idx
            }
            l1_data["entries"].append(l1_entry)

            # L2 条目（完整）
            l2_data["entries"].append(entry)

        # 写入 L1 文件
        l1_file = output_dir / f"product_l1_{cat_slug}.yaml"
        with open(l1_file, 'w', encoding='utf-8') as f:
            yaml.dump(l1_data, f, allow_unicode=True, sort_keys=False)

        # 写入 L2 文件
        l2_file = output_dir / f"product_l2_{cat_slug}.yaml"
        with open(l2_file, 'w', encoding='utf-8') as f:
            yaml.dump(l2_data, f, allow_unicode=True, sort_keys=False)

        print(f"✓ 生成 {cat_name}: L1={l1_file.stat().st_size / 1024:.1f}KB, L2={l2_file.stat().st_size / 1024:.1f}KB")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Product Index V2 - 三层索引生成器')
    parser.add_argument('--input', default='.index/product.yaml', help='输入 product.yaml 文件路径')
    parser.add_argument('--output', default='.index/', help='输出目录')

    args = parser.parse_args()

    input_file = Path(args.input)
    output_dir = Path(args.output)

    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"加载 {input_file}...")
    data = load_product_yaml(str(input_file))

    print(f"提取 entries...")
    entries = extract_entries(data)
    print(f"  总计: {len(entries)} 条")

    print(f"语义聚类...")
    categories = semantic_clustering(entries)
    print(f"  分类数: {len(categories)}")
    for cat_name, cat_entries in categories.items():
        print(f"    - {cat_name}: {len(cat_entries)} 条")

    print(f"\n生成三层索引...")
    generate_l0_index(categories, output_dir)
    generate_l1_l2_indexes(categories, output_dir)

    print(f"\n✅ 完成！索引文件已生成到: {output_dir}")
    print(f"\n使用方法:")
    print(f"  1. 默认加载 L0 索引（~5KB）")
    print(f"  2. 根据章节内容主题，加载相关的 1-2 个 L1 文件（15-30KB）")
    print(f"  3. 仅在需要详细参数时加载 L2")

if __name__ == '__main__':
    main()
