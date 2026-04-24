#!/usr/bin/env python3
"""
AI 图片生成器

支持火山方舟 Seedream、阿里云通义万相、Google Gemini Imagen 三 API。
使用中文提示词，生成专业技术图表。模型 ID 可通过配置切换。
"""

import os
import sys
import uuid
import logging
import tempfile
import requests
from typing import Optional, Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入 sm_config（从 solution-config skill 的 scripts 目录）
try:
    _sm_config_dir = str(Path(__file__).resolve().parent.parent.parent / "solution-config" / "scripts")
    if _sm_config_dir not in sys.path:
        sys.path.insert(0, _sm_config_dir)
    from sm_config import get as _sm_get
except ImportError:
    def _sm_get(key, default=None):
        return default

# 惰性初始化失败的哨兵值
_INIT_FAILED = object()


class AIImageGenerator:
    """AI 图片生成器（支持火山方舟、阿里云、Google Gemini 三 API）"""

    def __init__(self, ark_api_key=None, dashscope_api_key=None, gemini_api_key=None, provider=None):
        # API Key 优先级：参数 > sm_config（含环境变量 fallback）
        # 单次加载配置，避免多次文件读取 + YAML 解析
        try:
            from sm_config import load as _sm_load, _deep_get
            _cfg = _sm_load()
            _env_mapping = {
                "api_keys.ark": "ARK_API_KEY",
                "api_keys.dashscope": "DASHSCOPE_API_KEY",
                "api_keys.gemini": "GEMINI_API_KEY",
            }
            def _cfg_get(key, default=None):
                val = _deep_get(_cfg, key)
                if val is not None:
                    return val
                env_key = _env_mapping.get(key)
                if env_key:
                    env_val = os.environ.get(env_key)
                    if env_val:
                        return env_val
                return default
        except ImportError:
            def _cfg_get(key, default=None):
                return default

        self.ark_api_key = ark_api_key or _cfg_get("api_keys.ark")
        self.dashscope_api_key = dashscope_api_key or _cfg_get("api_keys.dashscope")
        self.gemini_api_key = gemini_api_key or _cfg_get("api_keys.gemini")

        self.provider = provider or _cfg_get("ai_image.default_provider", "ark")

        models_config = _cfg_get("ai_image.models", {}) or {}
        self.models = {
            'ark': models_config.get('ark', 'doubao-seedream-5-0-260128'),
            'dashscope': models_config.get('dashscope', 'qwen-image-2.0-pro'),
            'gemini': models_config.get('gemini', 'gemini-2.5-flash-image'),
        }

        # 延迟初始化：仅在实际调用时创建客户端，失败后不再重试
        self._ark_client = None
        self._gemini_client = None

    @property
    def ark_client(self):
        if self._ark_client is None and self.ark_api_key:
            try:
                from volcenginesdkarkruntime import Ark
                self._ark_client = Ark(base_url="https://ark.cn-beijing.volces.com/api/v3", api_key=self.ark_api_key)
            except Exception as e:
                logger.warning(f"火山方舟客户端初始化失败: {e}")
                self._ark_client = _INIT_FAILED
        return None if self._ark_client is _INIT_FAILED else self._ark_client

    @property
    def gemini_client(self):
        if self._gemini_client is None and self.gemini_api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                logger.warning(f"Google Gemini 客户端初始化失败: {e}")
                self._gemini_client = _INIT_FAILED
        return None if self._gemini_client is _INIT_FAILED else self._gemini_client

    def generate_diagram(self, diagram_type: str, topic: str, details: Dict, size: str = "2048x2048") -> Optional[str]:
        """生成图表，返回本地文件路径"""
        prompt = self._build_prompt(diagram_type, topic, details)
        logger.info(f"生成提示词: {prompt[:100]}...")

        try:
            if self.provider == 'ark':
                if not self.ark_client:
                    logger.error("火山方舟 API 未配置")
                    return None
                return self._generate_with_ark(prompt, size)
            elif self.provider == 'dashscope':
                if not self.dashscope_api_key:
                    logger.error("阿里云 DashScope API 未配置")
                    return None
                return self._generate_with_dashscope(prompt, size)
            elif self.provider == 'gemini':
                if not self.gemini_client:
                    logger.error("Google Gemini API 未配置")
                    return None
                return self._generate_with_gemini(prompt, size)
            else:
                logger.error(f"未知的 AI 生图供应商: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"AI 生图失败（供应商: {self.provider}）: {e}")
            return None

    def _build_prompt(self, diagram_type: str, topic: str, details: Dict) -> str:
        """构建中文提示词"""
        if diagram_type in ("architecture", "架构图"):
            components = details.get("components", [])
            components_str = "、".join(components) if isinstance(components, list) else str(components)
            return (
                f"专业技术架构图，展示{topic}，"
                f"主要组件：{components_str}，"
                f"要求：分层架构，使用标准IT图标，"
                f"配色：深蓝#1E3A8A、浅蓝#60A5FA、灰#6B7280，"
                f"白色背景，简洁专业，2048x2048高清"
            )
        elif diagram_type in ("flowchart", "流程图"):
            steps = details.get("steps", [])
            steps_str = "、".join(steps) if isinstance(steps, list) else str(steps)
            return (
                f"专业流程图，展示{topic}，"
                f"步骤：{steps_str}，"
                f"标准流程图符号，从上到下，逻辑清晰，"
                f"配色：深蓝#1E3A8A、浅蓝#60A5FA，"
                f"白色背景，简洁专业，2048x2048高清"
            )
        elif diagram_type in ("org_chart", "组织图"):
            structure = details.get("structure", "层级结构")
            return (
                f"专业组织架构图，展示{topic}，"
                f"结构：{structure}，树形布局，"
                f"配色：深蓝#1E3A8A、浅蓝#60A5FA，"
                f"白色背景，简洁专业，2048x2048高清"
            )
        else:
            return (
                f"专业技术示意图，展示{topic}，"
                f"标准IT图标和符号，"
                f"配色：深蓝#1E3A8A、浅蓝#60A5FA，"
                f"白色背景，简洁专业，2048x2048高清"
            )

    @staticmethod
    def _temp_image_path() -> str:
        return os.path.join(tempfile.gettempdir(), f"sm_ai_img_{uuid.uuid4().hex[:8]}.png")

    def _save_and_validate(self, local_path: str) -> Optional[str]:
        """验证已保存的图片，失败时清理临时文件"""
        if not self._validate_image(local_path):
            try:
                os.unlink(local_path)
            except OSError:
                pass
            return None
        return local_path

    def _download_and_validate(self, url: str) -> Optional[str]:
        """下载图片到临时文件并验证，失败时清理"""
        local_path = self._temp_image_path()
        try:
            self._download_image(url, local_path)
        except Exception:
            try:
                os.unlink(local_path)
            except OSError:
                pass
            raise
        return self._save_and_validate(local_path)

    def _save_bytes_and_validate(self, image_bytes: bytes) -> Optional[str]:
        """保存字节到临时文件并验证"""
        local_path = self._temp_image_path()
        with open(local_path, "wb") as f:
            f.write(image_bytes)
        return self._save_and_validate(local_path)

    def _generate_with_ark(self, prompt: str, size: str) -> Optional[str]:
        """使用火山方舟生成图片"""
        response = self.ark_client.images.generate(
            model=self.models['ark'], prompt=prompt, size=size, response_format="url"
        )
        return self._download_and_validate(response.data[0].url)

    def _generate_with_dashscope(self, prompt: str, size: str) -> Optional[str]:
        """使用阿里云通义万相生成图片"""
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        headers = {"Authorization": f"Bearer {self.dashscope_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.models['dashscope'],
            "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
            "parameters": {"size": size.replace("x", "*"), "n": 1}
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        try:
            image_url = result["output"]["choices"][0]["message"]["content"][0]["image"]
        except (KeyError, IndexError, TypeError):
            logger.error(f"阿里云 API 响应异常: {result}")
            return None
        return self._download_and_validate(image_url)

    def _generate_with_gemini(self, prompt: str, size: str) -> Optional[str]:
        """使用 Google Gemini 生成图片"""
        model_id = self.models['gemini']
        if model_id.startswith("imagen-"):
            return self._gemini_imagen(prompt, size, model_id)
        else:
            return self._gemini_generate_content(prompt, model_id)

    def _gemini_imagen(self, prompt, size, model_id):
        from google.genai import types
        w, h = map(int, size.split("x"))
        aspect = "1:1" if w == h else ("16:9" if w > h else "9:16")
        response = self.gemini_client.models.generate_images(
            model=model_id, prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio=aspect)
        )
        if not response.generated_images:
            return None
        return self._save_bytes_and_validate(response.generated_images[0].image.image_bytes)

    def _gemini_generate_content(self, prompt, model_id):
        from google.genai import types
        response = self.gemini_client.models.generate_content(
            model=model_id, contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])
        )
        if not response.candidates:
            return None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.mime_type.startswith("image/"):
                data = part.inline_data.data
                if isinstance(data, str):
                    import base64
                    data = base64.b64decode(data)
                return self._save_bytes_and_validate(data)
        return None

    def _download_image(self, url: str, local_path: str):
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    def _validate_image(self, local_path: str) -> bool:
        file_size = os.path.getsize(local_path)
        if file_size < 5 * 1024:  # 与 image_guidelines.yaml 一致
            logger.warning(f"图片文件过小: {file_size} bytes")
            return False
        try:
            from PIL import Image
            with Image.open(local_path) as img:
                if img.size[0] * img.size[1] < 512 * 512:
                    return False
        except ImportError:
            pass
        except Exception:
            return False
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI 图片生成器')
    parser.add_argument('--type', required=True, choices=['architecture', 'flowchart', 'org_chart'])
    parser.add_argument('--topic', required=True)
    parser.add_argument('--components', help='组件列表（逗号分隔）')
    parser.add_argument('--steps', help='步骤列表（逗号分隔）')
    parser.add_argument('--structure', help='组织结构描述')
    parser.add_argument('--output', default='/tmp/test_ai_image.png')
    parser.add_argument('--provider', choices=['ark', 'dashscope', 'gemini'])
    args = parser.parse_args()

    details = {}
    if args.components:
        details['components'] = args.components.split(',')
    if args.steps:
        details['steps'] = args.steps.split(',')
    if args.structure:
        details['structure'] = args.structure

    generator = AIImageGenerator(provider=args.provider)
    result = generator.generate_diagram(diagram_type=args.type, topic=args.topic, details=details)

    if result:
        import shutil
        shutil.copy(result, args.output)
        print(f"图片生成成功: {args.output}")
    else:
        print("图片生成失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
