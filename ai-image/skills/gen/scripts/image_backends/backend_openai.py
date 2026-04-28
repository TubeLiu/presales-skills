#!/usr/bin/env python3
"""
OpenAI Compatible Image Generation Backend

Generates images via OpenAI-compatible APIs (OpenAI, local models like Qwen-Image, etc.).
Used by image_gen.py as a backend module.

Configuration keys:
  OPENAI_API_KEY   (required) API key
  OPENAI_BASE_URL  (optional) Custom API endpoint (e.g. http://127.0.0.1:3000/v1)
  OPENAI_MODEL     (optional) Model name (default: gpt-image-1)

Dependencies:
  pip install openai Pillow
"""

import base64
import os
import time
import threading

from openai import OpenAI
from image_backends.backend_common import (
    MAX_RETRIES,
    is_rate_limit_error,
    normalize_image_size,
    resolve_output_path,
    retry_delay,
    sanitize_error,
    save_image_bytes,
)

# TODO(F-030): apply get_timeout() and retry_delay_from_header() in 429/timeout paths


# ╔══════════════════════════════════════════════════════════════════╗
# ║  Constants                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# Aspect ratio -> OpenAI size mapping
# Covers common PPT/social media ratios
ASPECT_RATIO_TO_SIZE = {
    "1:1":  "1024x1024",
    "16:9": "1536x1024",   # closest landscape (gpt-image-1 has no 16:9 native)
    "9:16": "1024x1536",   # closest portrait
    "3:2":  "1536x1024",
    "2:3":  "1024x1536",
    "4:3":  "1536x1024",   # closest available
    "3:4":  "1024x1536",   # closest available
    "4:5":  "1024x1024",   # fallback to square
    "5:4":  "1024x1024",   # fallback to square
    "21:9": "1536x1024",   # closest wide format
}

VALID_ASPECT_RATIOS = list(ASPECT_RATIO_TO_SIZE.keys())

# image_size -> quality mapping
IMAGE_SIZE_TO_QUALITY = {
    "512px": "low",
    "1K":    "auto",
    "2K":    "high",
    "4K":    "high",
}

DEFAULT_MODEL = "gpt-image-1"


# ╔══════════════════════════════════════════════════════════════════╗
# ║  Image Generation                                               ║
# ╚══════════════════════════════════════════════════════════════════╝

def _generate_image(api_key: str, prompt: str, negative_prompt: str = None,
                    aspect_ratio: str = "1:1", image_size: str = "1K",
                    output_dir: str = None, filename: str = None,
                    model: str = DEFAULT_MODEL, base_url: str = None,
                    background: str = "auto",
                    output_format: str = "png",
                    output_compression: int = None) -> str:
    """
    Image generation via OpenAI-compatible API.

    Maps aspect_ratio to OpenAI's size parameter, and image_size to quality.

    Returns:
        Path of the saved image file

    Raises:
        RuntimeError: When generation fails
    """
    client = OpenAI(api_key=api_key, base_url=base_url)

    # Build prompt (OpenAI has no native negative_prompt, append to prompt)
    final_prompt = prompt
    if negative_prompt:
        final_prompt += f"\n\nAvoid the following: {negative_prompt}"

    # Map parameters
    size = ASPECT_RATIO_TO_SIZE.get(aspect_ratio, "1024x1024")
    quality = IMAGE_SIZE_TO_QUALITY.get(image_size, "auto")

    # 透明背景需要 PNG（jpeg/webp 不支持 alpha 通道）
    if background == "transparent" and output_format != "png":
        print(f"  [WARN] background=transparent 需要 png 格式；已忽略 output_format={output_format} 强制使用 png")
        output_format = "png"

    extras = {}
    if background != "auto":
        extras["background"] = background
    if output_format != "png":
        extras["output_format"] = output_format
    if output_compression is not None and output_format in ("jpeg", "webp"):
        extras["output_compression"] = output_compression

    mode_label = f"Proxy: {base_url}" if base_url else "OpenAI API"
    print(f"[OpenAI - {mode_label}]")
    print(f"  Model:        {model}")
    print(f"  Prompt:       {final_prompt[:120]}{'...' if len(final_prompt) > 120 else ''}")
    print(f"  Size:         {size} (from aspect_ratio={aspect_ratio})")
    print(f"  Quality:      {quality} (from image_size={image_size})")
    if extras:
        print(f"  Extras:       {extras}")
    print()

    start_time = time.time()
    print(f"  [..] Generating...", end="", flush=True)

    # Heartbeat thread
    heartbeat_stop = threading.Event()

    def _heartbeat():
        while not heartbeat_stop.is_set():
            heartbeat_stop.wait(5)
            if not heartbeat_stop.is_set():
                elapsed = time.time() - start_time
                print(f" {elapsed:.0f}s...", end="", flush=True)

    hb_thread = threading.Thread(target=_heartbeat, daemon=True)
    hb_thread.start()

    try:
        resp = client.images.generate(
            prompt=final_prompt,
            model=model,
            size=size,
            quality=quality,
            n=1,
            **extras,
        )
    finally:
        heartbeat_stop.set()
        hb_thread.join(timeout=1)

    elapsed = time.time() - start_time
    print(f"\n  [DONE] Image generated ({elapsed:.1f}s)")

    if resp is not None and resp.data:
        ext = "." + output_format.replace("jpeg", "jpg") if output_format != "png" else ".png"
        path = resolve_output_path(prompt, output_dir, filename, ext)
        image_data = base64.b64decode(resp.data[0].b64_json)
        return save_image_bytes(image_data, path)

    raise RuntimeError("No image was generated. The server may have refused the request.")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  Public Entry Point                                             ║
# ╚══════════════════════════════════════════════════════════════════╝

def generate(prompt: str, negative_prompt: str = None,
             aspect_ratio: str = "1:1", image_size: str = "1K",
             output_dir: str = None, filename: str = None,
             model: str = None,
             background: str = "auto",
             output_format: str = "png",
             output_compression: int = None,
             max_retries: int = MAX_RETRIES) -> str:
    """
    OpenAI-compatible image generation with automatic retry.

    Reads credentials from the current process environment or the project-root `.env`:
      OPENAI_API_KEY
      OPENAI_BASE_URL
      OPENAI_MODEL (optional override)

    Args:
        prompt: Positive prompt text
        negative_prompt: Negative prompt text (appended to prompt as "Avoid...")
        aspect_ratio: Aspect ratio, mapped to OpenAI size
        image_size: Image size, mapped to OpenAI quality
        output_dir: Output directory
        filename: Output filename (without extension)
        model: Model name (default: gpt-image-1)
        background: auto / transparent / opaque（透明背景仅 png 支持）
        output_format: png / jpeg / webp
        output_compression: 0-100，仅 jpeg/webp 生效
        max_retries: Maximum number of retries

    Returns:
        Path of the saved image file
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")

    if not api_key:
        raise ValueError(
            "No API key found. Set OPENAI_API_KEY in the current environment or the project-root .env."
        )

    if model is None:
        model = os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL

    image_size = normalize_image_size(image_size)

    if aspect_ratio not in ASPECT_RATIO_TO_SIZE:
        supported = list(ASPECT_RATIO_TO_SIZE.keys())
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for OpenAI backend. "
            f"Supported: {supported}"
        )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return _generate_image(api_key, prompt, negative_prompt,
                                   aspect_ratio, image_size, output_dir,
                                   filename, model, base_url,
                                   background=background,
                                   output_format=output_format,
                                   output_compression=output_compression)
        except Exception as e:
            last_error = e
            if attempt < max_retries and is_rate_limit_error(e):
                delay = retry_delay(attempt, rate_limited=True)
                print(f"\n  [WARN] Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                      f"Waiting {delay}s before retry...")
                time.sleep(delay)
            elif attempt < max_retries:
                delay = retry_delay(attempt, rate_limited=False)
                print(f"\n  [WARN] Error (attempt {attempt + 1}/{max_retries + 1}): {sanitize_error(e)}. "
                      f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                break

    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {sanitize_error(last_error)}")


# ╔══════════════════════════════════════════════════════════════════╗
# ║  Image Editing (Inpainting)                                     ║
# ╚══════════════════════════════════════════════════════════════════╝

def _edit_image(api_key: str, prompt: str, input_image: str,
                mask: str = None, negative_prompt: str = None,
                aspect_ratio: str = "1:1", image_size: str = "1K",
                output_dir: str = None, filename: str = None,
                model: str = DEFAULT_MODEL, base_url: str = None,
                input_fidelity: str = "high",
                background: str = "auto",
                output_format: str = "png",
                output_compression: int = None) -> str:
    """调用 OpenAI /images/edits 端点（inpainting）"""
    client = OpenAI(api_key=api_key, base_url=base_url)

    final_prompt = prompt
    if negative_prompt:
        final_prompt += f"\n\nAvoid the following: {negative_prompt}"

    size = ASPECT_RATIO_TO_SIZE.get(aspect_ratio, "1024x1024")
    quality = IMAGE_SIZE_TO_QUALITY.get(image_size, "auto")

    if background == "transparent" and output_format != "png":
        print(f"  [WARN] background=transparent 需要 png 格式；已忽略 output_format={output_format} 强制使用 png")
        output_format = "png"

    extras = {"input_fidelity": input_fidelity}
    if background != "auto":
        extras["background"] = background
    if output_format != "png":
        extras["output_format"] = output_format
    if output_compression is not None and output_format in ("jpeg", "webp"):
        extras["output_compression"] = output_compression

    mode_label = f"Proxy: {base_url}" if base_url else "OpenAI API"
    print(f"[OpenAI Edit - {mode_label}]")
    print(f"  Model:        {model}")
    print(f"  Input image:  {input_image}")
    print(f"  Mask:         {mask if mask else '(none — 全图编辑)'}")
    print(f"  Prompt:       {final_prompt[:120]}{'...' if len(final_prompt) > 120 else ''}")
    print(f"  Size:         {size}")
    print(f"  Quality:      {quality}")
    print(f"  Extras:       {extras}")
    print()

    start_time = time.time()
    print(f"  [..] Editing...", end="", flush=True)

    heartbeat_stop = threading.Event()

    def _heartbeat():
        while not heartbeat_stop.is_set():
            heartbeat_stop.wait(5)
            if not heartbeat_stop.is_set():
                elapsed = time.time() - start_time
                print(f" {elapsed:.0f}s...", end="", flush=True)

    hb_thread = threading.Thread(target=_heartbeat, daemon=True)
    hb_thread.start()

    try:
        with open(input_image, "rb") as image_fh:
            mask_fh = open(mask, "rb") if mask else None
            try:
                kwargs = dict(
                    image=image_fh,
                    prompt=final_prompt,
                    model=model,
                    size=size,
                    quality=quality,
                    n=1,
                    **extras,
                )
                if mask_fh is not None:
                    kwargs["mask"] = mask_fh
                resp = client.images.edit(**kwargs)
            finally:
                if mask_fh is not None:
                    mask_fh.close()
    finally:
        heartbeat_stop.set()
        hb_thread.join(timeout=1)

    elapsed = time.time() - start_time
    print(f"\n  [DONE] Image edited ({elapsed:.1f}s)")

    if resp is not None and resp.data:
        ext = "." + output_format.replace("jpeg", "jpg") if output_format != "png" else ".png"
        path = resolve_output_path(prompt, output_dir, filename, ext)
        image_data = base64.b64decode(resp.data[0].b64_json)
        return save_image_bytes(image_data, path)

    raise RuntimeError("No edited image was returned. The server may have refused the request.")


def edit(prompt: str, input_image: str, mask: str = None,
         negative_prompt: str = None,
         aspect_ratio: str = "1:1", image_size: str = "1K",
         output_dir: str = None, filename: str = None,
         model: str = None,
         input_fidelity: str = "high",
         background: str = "auto",
         output_format: str = "png",
         output_compression: int = None,
         max_retries: int = MAX_RETRIES) -> str:
    """
    OpenAI 图像编辑（inpainting），支持可选 mask。

    Args:
        prompt: 编辑指令
        input_image: 原始图像路径（PNG）
        mask: 可选 mask PNG 路径（透明=待编辑区域，不透明=保留）；省略则全图编辑
        input_fidelity: low / high，控制原图保留强度
        background / output_format / output_compression: 与 generate() 一致

    Returns:
        Path of the saved edited image file
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")

    if not api_key:
        raise ValueError(
            "No API key found. Set OPENAI_API_KEY in the current environment or the project-root .env."
        )

    if not input_image:
        raise ValueError("--input-image 必填：edit 模式需要提供原始图像 PNG 路径。")

    if not os.path.isfile(input_image):
        raise FileNotFoundError(f"Input image not found: {input_image}")

    if mask and not os.path.isfile(mask):
        raise FileNotFoundError(f"Mask not found: {mask}")

    if model is None:
        model = os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL

    image_size = normalize_image_size(image_size)

    if aspect_ratio not in ASPECT_RATIO_TO_SIZE:
        supported = list(ASPECT_RATIO_TO_SIZE.keys())
        raise ValueError(
            f"Unsupported aspect ratio '{aspect_ratio}' for OpenAI backend. "
            f"Supported: {supported}"
        )

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return _edit_image(api_key, prompt, input_image, mask,
                               negative_prompt, aspect_ratio, image_size,
                               output_dir, filename, model, base_url,
                               input_fidelity=input_fidelity,
                               background=background,
                               output_format=output_format,
                               output_compression=output_compression)
        except Exception as e:
            last_error = e
            if attempt < max_retries and is_rate_limit_error(e):
                delay = retry_delay(attempt, rate_limited=True)
                print(f"\n  [WARN] Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                      f"Waiting {delay}s before retry...")
                time.sleep(delay)
            elif attempt < max_retries:
                delay = retry_delay(attempt, rate_limited=False)
                print(f"\n  [WARN] Error (attempt {attempt + 1}/{max_retries + 1}): {sanitize_error(e)}. "
                      f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                break

    raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last error: {sanitize_error(last_error)}")
