"""检查所有 SKILL.md 中引用的文件路径和 YAML key 是否实际存在。

扫描 .claude/skills/*/SKILL.md 中的：
  - Read `.claude/skills/...` 或 Read `prompts/...` 引用 → 检查文件存在
  - python3 .claude/skills/... 脚本调用 → 检查文件存在
  - YAML 文件中的 key 引用（如 `phase_2a_execution`）→ 检查 key 存在
"""

import os
import re
import glob
import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, ".claude", "skills")

# 匹配模式：
#   Read `.claude/skills/...`
#   Read `prompts/...`（相对路径）
#   python3 .claude/skills/...
#   python .claude/skills/...
PATTERNS = [
    # Read 引用（反引号包裹的路径）
    re.compile(r'Read\s+`(\.claude/skills/[^`]+?)`'),
    re.compile(r'Read\s+`(prompts/[^`]+?)`'),
    re.compile(r'Read\s+工具读取\s+`(prompts/[^`]+?)`'),
    # python3/python 脚本调用
    re.compile(r'python3?\s+(\.claude/skills/\S+\.py)'),
    re.compile(r'python3?\s+(tools/\S+\.py)'),
]


def collect_skill_refs():
    """收集所有 SKILL.md 中的文件引用。"""
    refs = []
    skill_mds = glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md"))

    for skill_md in skill_mds:
        skill_name = os.path.basename(os.path.dirname(skill_md))
        skill_dir = os.path.dirname(skill_md)

        with open(skill_md, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                for pattern in PATTERNS:
                    for match in pattern.finditer(line):
                        raw_path = match.group(1)
                        # 去掉路径后的非路径字符（如 ` 中 `、逗号等）
                        raw_path = raw_path.split("`")[0].split("，")[0].split(" ")[0].rstrip(",;。")

                        # 解析为绝对路径
                        if raw_path.startswith(".claude/skills/"):
                            abs_path = os.path.join(REPO_ROOT, raw_path)
                        elif raw_path.startswith("prompts/"):
                            # prompts/ 是 skill 内部目录
                            abs_path = os.path.join(skill_dir, raw_path)
                        elif raw_path.startswith("tools/"):
                            # tools/ 优先检查 skill 内部，否则仓库根目录
                            skill_local = os.path.join(skill_dir, raw_path)
                            repo_root_path = os.path.join(REPO_ROOT, raw_path)
                            abs_path = skill_local if os.path.exists(skill_local) else repo_root_path
                        else:
                            abs_path = os.path.join(REPO_ROOT, raw_path)

                        refs.append((skill_name, skill_md, line_no, raw_path, abs_path))

    return refs


ALL_REFS = collect_skill_refs()


@pytest.mark.parametrize(
    "skill,skill_md,line_no,raw_path,abs_path",
    ALL_REFS,
    ids=[f"{r[0]}:{r[3]}" for r in ALL_REFS],
)
def test_referenced_file_exists(skill, skill_md, line_no, raw_path, abs_path):
    """每个 SKILL.md 中引用的文件都必须实际存在。"""
    assert os.path.exists(abs_path), (
        f"{skill}/SKILL.md:{line_no} 引用了 `{raw_path}`，"
        f"但文件不存在：{abs_path}"
    )


# ── YAML key 引用检查 ──
# 匹配 SKILL.md 中对 YAML 文件内部 key 的引用，如：
#   按 `phase_2a_execution` 步骤
#   按 `phase_2b_execution.result_checking` 检查
#   中 `search_result_formats`～`annotation_rules` 部分
YAML_KEY_PATTERN = re.compile(
    r'Read\s+`([^`]+\.yaml)`[^`]*?`([a-z_][a-z0-9_.]+)`'
)
# 也匹配 ～ 范围引用中的第二个 key
YAML_KEY_RANGE_PATTERN = re.compile(
    r'`([a-z_][a-z0-9_.]+)`[～~]`([a-z_][a-z0-9_.]+)`'
)


def resolve_yaml_path(yaml_ref, skill_dir):
    """将 YAML 路径引用解析为绝对路径。"""
    if yaml_ref.startswith(".claude/skills/"):
        return os.path.join(REPO_ROOT, yaml_ref)
    elif yaml_ref.startswith("prompts/"):
        return os.path.join(skill_dir, yaml_ref)
    return os.path.join(REPO_ROOT, yaml_ref)


def get_top_level_key(key_ref):
    """从 `phase_2b_execution.result_checking` 提取顶层 key `phase_2b_execution`。"""
    return key_ref.split(".")[0]


def collect_yaml_key_refs():
    """收集所有 SKILL.md 中对 YAML key 的引用。"""
    refs = []
    skill_mds = glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md"))

    for skill_md in skill_mds:
        skill_name = os.path.basename(os.path.dirname(skill_md))
        skill_dir = os.path.dirname(skill_md)

        with open(skill_md, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                # 匹配 Read `xxx.yaml` ... `key_name`
                for m in YAML_KEY_PATTERN.finditer(line):
                    yaml_path = resolve_yaml_path(m.group(1), skill_dir)
                    key = get_top_level_key(m.group(2))
                    refs.append((skill_name, line_no, yaml_path, m.group(1), key))

                # 匹配 `key1`～`key2` 范围引用
                for m in YAML_KEY_RANGE_PATTERN.finditer(line):
                    # 需要找到同一行的 YAML 文件路径
                    yaml_match = re.search(r'`([^`]+\.yaml)`', line)
                    if yaml_match:
                        yaml_path = resolve_yaml_path(yaml_match.group(1), skill_dir)
                        for key_ref in [m.group(1), m.group(2)]:
                            key = get_top_level_key(key_ref)
                            refs.append((skill_name, line_no, yaml_path, yaml_match.group(1), key))

    # 去重
    seen = set()
    unique = []
    for r in refs:
        sig = (r[2], r[4])  # (yaml_abs_path, key)
        if sig not in seen:
            seen.add(sig)
            unique.append(r)
    return unique


YAML_KEY_REFS = collect_yaml_key_refs()


@pytest.mark.parametrize(
    "skill,line_no,yaml_path,yaml_ref,key",
    YAML_KEY_REFS,
    ids=[f"{r[0]}:{r[3]}::{r[4]}" for r in YAML_KEY_REFS],
)
def test_yaml_key_exists(skill, line_no, yaml_path, yaml_ref, key):
    """SKILL.md 中引用的 YAML 顶层 key 必须在文件中存在。"""
    assert os.path.exists(yaml_path), (
        f"{skill}/SKILL.md:{line_no} 引用了 `{yaml_ref}`，但文件不存在"
    )
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), (
        f"`{yaml_ref}` 不是有效的 YAML mapping"
    )
    assert key in data, (
        f"{skill}/SKILL.md:{line_no} 引用了 `{yaml_ref}` 中的 key `{key}`，"
        f"但该 key 不存在。现有 keys：{list(data.keys())}"
    )
