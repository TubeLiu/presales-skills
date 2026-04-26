"""检查所有 SKILL.md 中引用的文件路径和 YAML key 是否实际存在。

扫描 skills/*/SKILL.md 中的：
  - Read `${CLAUDE_SKILL_DIR}/...` 或 Read `${CLAUDE_SKILL_DIR}/../<other>/...` 或 Read `prompts/...` 引用
  - python3 ${CLAUDE_SKILL_DIR}/... / ${CLAUDE_PLUGIN_ROOT}/tools/... 脚本调用
  - YAML 文件中的 key 引用（如 `phase_2a_execution`）→ 检查 key 存在

注：本测试假设从 tender-workflow/ 根目录运行 pytest。${CLAUDE_SKILL_DIR} 和 ${CLAUDE_PLUGIN_ROOT}
是 SKILL.md 里由 Claude Code 文本替换的占位（仅带花括号形式被替换），测试里把它们映射回源码
仓库的相对位置。
"""

import os
import re
import glob
import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")

# 匹配模式（按照文本替换后的新占位——Claude Code 加载器只替换 ${...} 带花括号的形式）：
#   Read `${CLAUDE_SKILL_DIR}/...`
#   Read `${CLAUDE_SKILL_DIR}/../<other>/...`
#   Read `prompts/...`（相对路径）
#   python3 ${CLAUDE_SKILL_DIR}/...
#   python3 ${CLAUDE_PLUGIN_ROOT}/tools/...
#   python3 tools/...（源码模式）
PATTERNS = [
    # Read 引用（反引号包裹的路径）
    re.compile(r'Read\s+`(\$\{CLAUDE_SKILL_DIR\}/[^`]+?)`'),
    re.compile(r'Read\s+`(\$\{CLAUDE_PLUGIN_ROOT\}/[^`]+?)`'),
    re.compile(r'Read\s+`(\$SKILL_DIR/[^`]+?)`'),
    re.compile(r'Read\s+`(prompts/[^`]+?)`'),
    re.compile(r'Read\s+工具读取\s+`(prompts/[^`]+?)`'),
    # python3/python 脚本调用
    re.compile(r'python3?\s+(\$\{CLAUDE_SKILL_DIR\}/\S+\.py)'),
    re.compile(r'python3?\s+(\$\{CLAUDE_PLUGIN_ROOT\}/\S+\.py)'),
    re.compile(r'python3?\s+"?(\$SKILL_DIR/\S+?\.py)"?'),
    re.compile(r'python3?\s+(tools/\S+\.py)'),
]


def resolve_path(raw_path, skill_dir):
    """把 SKILL.md 里带占位的路径转成仓库内绝对路径，用于存在性校验。

    skill_dir: 当前 SKILL.md 所在目录（skills/<name>/）

    支持的占位形式：
      - ${CLAUDE_SKILL_DIR}/X / ${CLAUDE_SKILL_DIR}/../<other>/X — Claude Code runtime 替换
      - ${CLAUDE_PLUGIN_ROOT}/X — Claude Code runtime 替换
      - $SKILL_DIR/X / $SKILL_DIR/../<other>/X — taw/twc/etc. bootstrap bash 变量
        （runtime 由 SKILL.md 顶部的 §路径自定位 段解析；测试里等价于 ${CLAUDE_SKILL_DIR}）
      - prompts/X / tools/X — 相对路径
    """
    # ${CLAUDE_SKILL_DIR}/../<other>/X 或 $SKILL_DIR/../<other>/X → skills/<other>/X
    m = re.match(r'(?:\$\{CLAUDE_SKILL_DIR\}|\$SKILL_DIR)/\.\./([^/]+)/(.+)', raw_path)
    if m:
        return os.path.join(SKILLS_DIR, m.group(1), m.group(2))
    # ${CLAUDE_SKILL_DIR}/X 或 $SKILL_DIR/X → skills/<self>/X
    for prefix in ("${CLAUDE_SKILL_DIR}/", "$SKILL_DIR/"):
        if raw_path.startswith(prefix):
            return os.path.join(skill_dir, raw_path[len(prefix):])
    # ${CLAUDE_PLUGIN_ROOT}/X → tender-workflow/X
    if raw_path.startswith("${CLAUDE_PLUGIN_ROOT}/"):
        return os.path.join(REPO_ROOT, raw_path[len("${CLAUDE_PLUGIN_ROOT}/"):])
    # prompts/X → skills/<self>/prompts/X
    if raw_path.startswith("prompts/"):
        return os.path.join(skill_dir, raw_path)
    # tools/X → 源码模式：先查 skill 内部 tools/，否则 tender-workflow/tools/
    if raw_path.startswith("tools/"):
        skill_local = os.path.join(skill_dir, raw_path)
        return skill_local if os.path.exists(skill_local) else os.path.join(REPO_ROOT, raw_path)
    return os.path.join(REPO_ROOT, raw_path)


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

                        abs_path = resolve_path(raw_path, skill_dir)
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
    return resolve_path(yaml_ref, skill_dir)


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
            content = f.read()

        # 先按段落（空行）切开，避免跨段误匹配
        for segment in content.split("\n\n"):
            # 匹配 Read `xxx.yaml` + 后续最近的 `key_name`
            for match in YAML_KEY_PATTERN.finditer(segment):
                yaml_ref, key_ref = match.group(1), match.group(2)
                yaml_path = resolve_yaml_path(yaml_ref, skill_dir)
                top_key = get_top_level_key(key_ref)
                refs.append((skill_name, skill_md, yaml_ref, yaml_path, top_key))
            # 匹配 `key_a`～`key_b` 范围
            for match in YAML_KEY_RANGE_PATTERN.finditer(segment):
                # 只记录第二个 key（第一个通常也会被上面的模式抓到）
                pass

    return refs


ALL_YAML_REFS = collect_yaml_key_refs()


@pytest.mark.parametrize(
    "skill,skill_md,yaml_ref,yaml_path,top_key",
    ALL_YAML_REFS,
    ids=[f"{r[0]}:{os.path.basename(r[2])}:{r[4]}" for r in ALL_YAML_REFS],
)
def test_yaml_key_exists(skill, skill_md, yaml_ref, yaml_path, top_key):
    """SKILL.md 中引用的 YAML 顶层 key 必须在目标 YAML 文件中存在。"""
    assert os.path.exists(yaml_path), f"YAML 文件不存在: {yaml_path}"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"{yaml_path} 不是 dict"
    assert top_key in data, (
        f"{skill}/SKILL.md 引用的 YAML 文件 {yaml_ref} 中找不到顶层 key `{top_key}`。"
        f"已有 keys: {list(data.keys())}"
    )
