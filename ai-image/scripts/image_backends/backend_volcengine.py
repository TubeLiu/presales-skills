#!/usr/bin/env python3
"""
Volcengine Seedream image generation backend.

Configuration keys:
  VOLCENGINE_API_KEY / ARK_API_KEY   (required)
  VOLCENGINE_BASE_URL                (optional)
  VOLCENGINE_MODEL                   (optional)
"""

import os
import time

import requests

from image_backends.backend_common import (
    MAX_RETRIES,
    download_image,
    http_error,
    is_rate_limit_error,
    normalize_image_size,
    require_api_key,
    resolve_output_path,
    retry_delay,
    sanitize_error,
)


DEFAULT_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DEFAULT_MODEL = "doubao-seedream-4-5-251128"

# Seedream 4.5 要求 width*height >= 3,686,400 像素且 1024 <= 单边 <= 4096。
# 每档按 "像素总量不小于官方阈值" 的档位递增（1K ≈ 阈值、2K ≈ 2x、4K ≈ 上限）。
ASPECT_RATIO_SIZE_MAP = {
    "512px": {
        "1:1": "2048x2048",
        "2:3": "1600x2400",
        "3:2": "2400x1600",
        "3:4": "1728x2304",
        "4:3": "2304x1728",
        "4:5": "1792x2240",
        "5:4": "2240x1792",
        "9:16": "1440x2560",
        "16:9": "2560x1440",
        "21:9": "3024x1296",
    },
    "1K": {
        "1:1": "2048x2048",
        "2:3": "1600x2400",
        "3:2": "2400x1600",
        "3:4": "1728x2304",
        "4:3": "2304x1728",
        "4:5": "1792x2240",
        "5:4": "2240x1792",
        "9:16": "1440x2560",
        "16:9": "2560x1440",
        "21:9": "3024x1296",
    },
    "2K": {
        "1:1": "2560x2560",
        "2:3": "2112x3168",
        "3:2": "3168x2112",
        "3:4": "2304x3072",
        "4:3": "3072x2304",
        "4:5": "2304x2880",
        "5:4": "2880x2304",
        "9:16": "1728x3072",
        "16:9": "3072x1728",
        "21:9": "3528x1512",
    },
    "4K": {
        "1:1": "4096x4096",
        "2:3": "2730x4096",
        "3:2": "4096x2730",
        "3:4": "3072x4096",
        "4:3": "4096x3072",
        "4:5": "3276x4096",
        "5:4": "4096x3276",
        "9:16": "2304x4096",
        "16:9": "4096x2304",
        "21:9": "4096x1756",
    },
}


def _resolve_url(base_url: str) -> str:
    """Resolve the Volcengine generation endpoint."""
    base = base_url.rstrip("/")
    if base.endswith("/images/generations"):
        return base
    return base + "/api/v3/images/generations"


def _resolve_size(aspect_ratio: str, image_size: str) -> str:
    """Resolve the target resolution for a ratio and logical size preset."""
    normalized = normalize_image_size(image_size)
    size = (ASPECT_RATIO_SIZE_MAP.get(normalized) or {}).get(aspect_ratio)
    if not size:
        supported = sorted(ASPECT_RATIO_SIZE_MAP["1K"])
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for Volcengine backend. "
            f"Supported: {supported}"
        )
    return size


def _generate_image(api_key: str, prompt: str, negative_prompt: str = None,
                    aspect_ratio: str = "1:1", image_size: str = "1K",
                    output_dir: str = None, filename: str = None,
                    model: str = DEFAULT_MODEL, base_url: str = DEFAULT_ENDPOINT) -> str:
    """Generate one image with the Volcengine backend."""
    size = _resolve_size(aspect_ratio, image_size)
    url = _resolve_url(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    final_prompt = prompt
    if negative_prompt:
        final_prompt += f"\n\nAvoid the following: {negative_prompt}"
    payload = {
        "model": model,
        "prompt": final_prompt,
        "size": size,
        "response_format": "url",
        "watermark": False,
    }

    print("[Volcengine Seedream]")
    print(f"  Model:        {model}")
    print(f"  Prompt:       {prompt[:120]}{'...' if len(prompt) > 120 else ''}")
    print(f"  Aspect Ratio: {aspect_ratio}")
    print(f"  Resolution:   {size}")
    print()
    print("  [..] Generating...", end="", flush=True)
    start = time.time()
    response = requests.post(url, headers=headers, json=payload, timeout=300)
    elapsed = time.time() - start
    print(f"\n  [DONE] Response received ({elapsed:.1f}s)")

    if response.status_code != 200:
        raise http_error(response, "Volcengine image generation")

    data = response.json()
    items = data.get("data") or []
    image_url = items[0].get("url") if items else None
    if not image_url:
        raise RuntimeError(f"Volcengine response missing image URL: {data}")

    path = resolve_output_path(prompt, output_dir, filename, ".jpeg")
    return download_image(image_url, path)


def generate(prompt: str, negative_prompt: str = None,
             aspect_ratio: str = "1:1", image_size: str = "1K",
             output_dir: str = None, filename: str = None,
             model: str = None, max_retries: int = MAX_RETRIES) -> str:
    """Generate an image with retries using the Volcengine backend."""
    api_key = require_api_key(
        "VOLCENGINE_API_KEY",
        "ARK_API_KEY",
        message="No API key found. Set VOLCENGINE_API_KEY or ARK_API_KEY in the current environment or the project-root .env.",
    )
    base_url = os.environ.get("VOLCENGINE_BASE_URL") or DEFAULT_ENDPOINT
    resolved_model = model or os.environ.get("VOLCENGINE_MODEL") or DEFAULT_MODEL

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return _generate_image(
                api_key=api_key,
                prompt=prompt,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                output_dir=output_dir,
                filename=filename,
                model=resolved_model,
                base_url=base_url,
            )
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            limited = is_rate_limit_error(exc)
            delay = retry_delay(attempt, rate_limited=limited)
            label = "Rate limit hit" if limited else f"Error: {sanitize_error(exc)}"
            print(f"\n  [WARN] {label}. Retrying in {delay}s...")
            time.sleep(delay)

    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {sanitize_error(last_error)}")
