"""Unit tests for ai_image_config size/aspect_ratio schema + helpers (C9).

回归 user 报告的 bug：default_size 字面像素 '2048x2048' 是非法值（image_gen.py
--image_size 不接受），且 setup 不按 model max_resolution 过滤候选。

Standalone runner — no pytest dependency（与 test_sanitize_error.py 同 style）。
"""

import os
import sys

# 兼容 plugin install 模式 + 本地开发
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "gen", "scripts"))
import ai_image_config as ac  # noqa: E402


def test_default_config_size_is_legal_preset() -> None:
    """DEFAULT_CONFIG.default_size 必须是 ALL_IMAGE_SIZES 之一（修 v1.0.0 的 '2048x2048' 字面像素 bug）"""
    size = ac.DEFAULT_CONFIG["ai_image"]["default_size"]
    assert size in ac.ALL_IMAGE_SIZES, (
        f"default_size = {size!r} 不在 ALL_IMAGE_SIZES = {ac.ALL_IMAGE_SIZES}；"
        f"image_gen.py --image_size 会被 argparse 拒"
    )


def test_default_config_aspect_ratio_is_legal() -> None:
    """新增 default_aspect_ratio 字段必须存在且合法"""
    ratio = ac.DEFAULT_CONFIG["ai_image"].get("default_aspect_ratio")
    assert ratio is not None, "DEFAULT_CONFIG.ai_image 必须含 default_aspect_ratio 字段"
    assert ratio in ac.ALL_ASPECT_RATIOS, (
        f"default_aspect_ratio = {ratio!r} 不在 ALL_ASPECT_RATIOS"
    )


def test_constants_match_image_gen() -> None:
    """ALL_IMAGE_SIZES / ALL_ASPECT_RATIOS 必须与 image_gen.py 同源
    （ai_image_config 不直接 import image_gen 避免触发 ensure_deps，
    所以靠常量同步 + 这个 lint 防漂移）"""
    image_gen_path = os.path.join(
        os.path.dirname(__file__), "..", "skills", "gen", "scripts", "image_gen.py"
    )
    with open(image_gen_path, "r", encoding="utf-8") as f:
        text = f.read()
    # 抽出 ALL_IMAGE_SIZES = ["..."] 那行
    import ast
    tree = ast.parse(text)
    image_gen_sizes = None
    image_gen_ratios = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    if tgt.id == "ALL_IMAGE_SIZES":
                        image_gen_sizes = ast.literal_eval(node.value)
                    elif tgt.id == "ALL_ASPECT_RATIOS":
                        image_gen_ratios = ast.literal_eval(node.value)
    assert image_gen_sizes == ac.ALL_IMAGE_SIZES, (
        f"image_gen.py ALL_IMAGE_SIZES = {image_gen_sizes!r} 与 ai_image_config "
        f"{ac.ALL_IMAGE_SIZES!r} 不一致——必须保持同步"
    )
    assert image_gen_ratios == ac.ALL_ASPECT_RATIOS, (
        f"image_gen.py ALL_ASPECT_RATIOS = {image_gen_ratios!r} 与 ai_image_config "
        f"{ac.ALL_ASPECT_RATIOS!r} 不一致"
    )


def test_max_resolution_parser_handles_common_formats() -> None:
    """ai_image_models.yaml 各种 max_resolution 写法都要能 parse 出对的 preset"""
    cases = [
        ("2K (2048×2048)", "2K"),
        ("4K (4096×4096)", "4K"),
        ("原生2K, AI增强4K", "4K"),       # 取最大命中
        ("1K (1024×1024)", "1K"),
        ("1K-2K", "2K"),                    # 范围取上界
        ("~1.4K", "1K"),                    # 向下取整保守，不能误判 4K（回归 substring "4K" in "1.4K" bug）
        ("", None),
        ("512px", "512px"),
    ]
    for inp, want in cases:
        got = ac._max_resolution_to_preset(inp)
        assert got == want, f"_max_resolution_to_preset({inp!r}) = {got!r}, want {want!r}"


def test_supported_sizes_caps_at_model_max() -> None:
    """supported_sizes_for_model 返回的 preset 列表必须 ≤ model 的 max_resolution"""
    # gemini-2.0-flash-exp max = 1K → supported = [512px, 1K]
    sizes = ac.supported_sizes_for_model("gemini", "gemini-2.0-flash-exp")
    assert sizes == ["512px", "1K"], (
        f"gemini-2.0-flash-exp (max 1K) supported = {sizes!r}, want ['512px', '1K']"
    )
    # ark seedream-4.5 max = 4K → 全集
    sizes = ac.supported_sizes_for_model("ark", "doubao-seedream-4-5-251128")
    assert sizes == ["512px", "1K", "2K", "4K"], (
        f"seedream-4.5 (max 4K) supported = {sizes!r}, want full"
    )


def test_supported_sizes_unknown_model_returns_full() -> None:
    """未知 model（拼写错 / 用户自定义没注册）→ 返回 ALL_IMAGE_SIZES 兜底，不阻塞"""
    sizes = ac.supported_sizes_for_model("ark", "no-such-model-xyz")
    assert sizes == list(ac.ALL_IMAGE_SIZES), (
        f"unknown model 应该返回 ALL_IMAGE_SIZES 兜底，得到 {sizes!r}"
    )


def test_legacy_size_migration_to_preset() -> None:
    """老 config 的字面像素 (2048x2048 等) load 时透明迁移成 preset"""
    cases = [
        ("512x512", "512px"),
        ("1024x1024", "1K"),
        ("2048x2048", "2K"),
        ("4096x4096", "4K"),
    ]
    for legacy, want in cases:
        cfg = {"ai_image": {"default_size": legacy}}
        out = ac._normalize_default_size_legacy(cfg)
        assert out["ai_image"]["default_size"] == want, (
            f"legacy {legacy!r} 应该迁移到 {want!r}，得到 {out['ai_image']['default_size']!r}"
        )


def test_legacy_migration_leaves_valid_preset_alone() -> None:
    """已经是合法 preset 的 default_size 不动"""
    cfg = {"ai_image": {"default_size": "2K"}}
    out = ac._normalize_default_size_legacy(cfg)
    assert out["ai_image"]["default_size"] == "2K"


def test_legacy_migration_preserves_unknown_value() -> None:
    """陌生字符串既不是 preset 也不在 legacy_map → 原样保留（让 validate 报）"""
    cfg = {"ai_image": {"default_size": "weird-value"}}
    out = ac._normalize_default_size_legacy(cfg)
    assert out["ai_image"]["default_size"] == "weird-value"


def main() -> int:
    tests = [
        test_default_config_size_is_legal_preset,
        test_default_config_aspect_ratio_is_legal,
        test_constants_match_image_gen,
        test_max_resolution_parser_handles_common_formats,
        test_supported_sizes_caps_at_model_max,
        test_supported_sizes_unknown_model_returns_full,
        test_legacy_size_migration_to_preset,
        test_legacy_migration_leaves_valid_preset_alone,
        test_legacy_migration_preserves_unknown_value,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}", file=sys.stderr)
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
