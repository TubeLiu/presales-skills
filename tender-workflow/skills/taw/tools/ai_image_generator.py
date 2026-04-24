#!/usr/bin/env python3
"""
AI 图片生成器

支持火山方舟 Seedream、阿里云通义万相、Google Gemini Imagen 三 API。
使用中文提示词，生成专业技术图表。模型 ID 可通过配置切换。
"""

import os
import uuid
import logging
import tempfile
import requests
from typing import Optional, Dict, List
from pathlib import Path

# 自动安装 PyYAML（如果缺失）
try:
    import yaml
except ImportError:
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("PyYAML 未安装，正在自动安装...")
    import subprocess
    import sys
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyyaml", "-q"],
            stderr=subprocess.DEVNULL
        )
        import yaml
        logger_temp.info("PyYAML 安装成功")
    except Exception as e:
        logger_temp.error(f"PyYAML 自动安装失败: {e}")
        logger_temp.error("请手动安装：pip install pyyaml")
        yaml = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _load_taw_config() -> Dict:
    """
    从统一配置文件 ~/.config/tender-workflow/config.yaml 读取配置

    Returns:
        配置字典，读取失败返回空字典
    """
    if yaml is None:
        logger.debug("PyYAML 未安装，跳过配置文件读取")
        return {}

    # 尝试导入 tw_config（优先）
    try:
        import sys
        # 将项目根目录加入 path 以便导入 tools.tw_config
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from tools.tw_config import load
        config = load("taw")
        if config:
            logger.info("通过 tw_config 加载统一配置")
            # 扁平化为旧格式兼容
            flat = {}
            flat["ark_api_key"] = (config.get("api_keys", {}) or {}).get("ark")
            flat["dashscope_api_key"] = (config.get("api_keys", {}) or {}).get("dashscope")
            flat["gemini_api_key"] = (config.get("api_keys", {}) or {}).get("gemini")
            flat["ai_image_config"] = config.get("ai_image", {})
            return flat
    except Exception as e:
        logger.debug(f"tw_config 导入失败，回退到直接读取: {e}")

    # 回退：直接读取统一配置文件
    config_path = Path.home() / ".config" / "tender-workflow" / "config.yaml"

    if not config_path.exists():
        logger.debug(f"配置文件不存在: {config_path}")
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f) or {}
            logger.info(f"成功加载配置文件: {config_path}")
            # 扁平化为旧格式兼容
            flat = {}
            flat["ark_api_key"] = (raw.get("api_keys", {}) or {}).get("ark") or (raw.get("ai_keys", {}) or {}).get("ark_api_key")
            flat["dashscope_api_key"] = (raw.get("api_keys", {}) or {}).get("dashscope") or (raw.get("ai_keys", {}) or {}).get("dashscope_api_key")
            flat["gemini_api_key"] = (raw.get("api_keys", {}) or {}).get("gemini")
            ai_image = raw.get("ai_image", {}) or raw.get("ai_keys", {})
            flat["ai_image_config"] = {
                "default_provider": ai_image.get("default_provider", "ark"),
                "models": ai_image.get("models", {}),
            }
            return flat
    except Exception as e:
        logger.warning(f"读取配置文件失败: {e}")
        return {}


class AIImageGenerator:
    """AI 图片生成器（支持火山方舟、阿里云、Google Gemini 三 API）"""

    def __init__(
        self,
        ark_api_key: Optional[str] = None,
        dashscope_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        provider: Optional[str] = None
    ):
        """
        初始化生成器

        Args:
            ark_api_key: 火山方舟 API Key
            dashscope_api_key: 阿里云 DashScope API Key
            gemini_api_key: Google Gemini API Key
            provider: 指定使用的 AI 生图供应商（ark/dashscope/gemini），覆盖配置文件
        """
        # 读取配置文件
        config = _load_taw_config()
        ai_config = config.get('ai_image_config', {})

        # API Key 优先级：参数 > 配置文件 > 环境变量
        self.ark_api_key = (
            ark_api_key or
            config.get('ark_api_key') or
            os.environ.get("ARK_API_KEY")
        )
        self.dashscope_api_key = (
            dashscope_api_key or
            config.get('dashscope_api_key') or
            os.environ.get("DASHSCOPE_API_KEY")
        )
        self.gemini_api_key = (
            gemini_api_key or
            config.get('gemini_api_key') or
            os.environ.get("GEMINI_API_KEY")
        )

        # 供应商选择：参数 > 配置文件 > 默认值（不再自动降级）
        self.provider = (
            provider or
            ai_config.get('default_provider') or
            'ark'
        )

        # 模型 ID：配置文件 > 默认值
        models_config = ai_config.get('models', {})
        self.models = {
            'ark': models_config.get('ark', 'doubao-seedream-5-0-260128'),
            'dashscope': models_config.get('dashscope', 'qwen-image-2.0-pro'),
            'gemini': models_config.get('gemini', 'gemini-2.5-flash-image'),
        }

        # 日志输出（便于调试）
        if self.ark_api_key:
            logger.info("火山方舟 API Key 已配置")
        if self.dashscope_api_key:
            logger.info("阿里云 DashScope API Key 已配置")
        if self.gemini_api_key:
            logger.info("Google Gemini API Key 已配置")
        if not self.ark_api_key and not self.dashscope_api_key and not self.gemini_api_key:
            logger.warning("未配置任何 AI 生图 API Key，请检查配置文件或环境变量")

        # 初始化火山方舟客户端
        self.ark_client = None
        if self.ark_api_key:
            try:
                from volcenginesdkarkruntime import Ark
                self.ark_client = Ark(
                    base_url="https://ark.cn-beijing.volces.com/api/v3",
                    api_key=self.ark_api_key
                )
                logger.info("火山方舟客户端初始化成功")
            except ImportError:
                logger.warning("volcengine-python-sdk 未安装，火山方舟 API 不可用")
            except Exception as e:
                logger.warning(f"火山方舟客户端初始化失败: {e}")

        # 初始化 Google Gemini 客户端
        self.gemini_client = None
        if self.gemini_api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                logger.info("Google Gemini 客户端初始化成功")
            except ImportError:
                logger.warning("google-genai 未安装，Google Gemini API 不可用")
            except Exception as e:
                logger.warning(f"Google Gemini 客户端初始化失败: {e}")

    def generate_diagram(
        self,
        diagram_type: str,
        topic: str,
        details: Dict,
        size: str = "2048x2048"
    ) -> Optional[str]:
        """
        生成图表

        Args:
            diagram_type: 图表类型（architecture/flowchart/org_chart）
            topic: 主题
            details: 详细信息（components/steps/structure）
            size: 图片尺寸（默认 2048x2048，2K分辨率）

        Returns:
            本地图片文件路径，失败返回 None
        """
        # 构建提示词（中文）
        prompt = self._build_prompt(diagram_type, topic, details)
        logger.info(f"生成提示词: {prompt[:100]}...")

        # 调用指定供应商 API（不自动降级）
        provider = self.provider
        logger.info(f"使用 AI 生图供应商: {provider}")

        try:
            if provider == 'ark':
                if not self.ark_client:
                    logger.error("火山方舟 API 未配置（缺少 API Key）")
                    return None
                return self._generate_with_ark(prompt, size)

            elif provider == 'dashscope':
                if not self.dashscope_api_key:
                    logger.error("阿里云 DashScope API 未配置（缺少 API Key）")
                    return None
                return self._generate_with_dashscope(prompt, size)

            elif provider == 'gemini':
                if not self.gemini_client:
                    logger.error("Google Gemini API 未配置（缺少 API Key）")
                    return None
                return self._generate_with_gemini(prompt, size)

            else:
                logger.error(f"未知的 AI 生图供应商: {provider}")
                return None

        except Exception as e:
            logger.error(f"AI 生图失败（供应商: {provider}）: {e}")
            return None

    def _build_prompt(self, diagram_type: str, topic: str, details: Dict) -> str:
        """构建提示词（中文）"""
        if diagram_type == "architecture" or diagram_type == "架构图":
            components = details.get("components", [])
            if isinstance(components, list):
                components_str = "、".join(components)
            else:
                components_str = str(components)
            return (
                f"专业IT技术架构图，展示{topic}，"
                f"主要组件：{components_str}，"
                f"要求：分层架构（应用层/平台层/基础设施层），使用标准IT图标（服务器、数据库、网络、云服务图标），"
                f"配色方案：深蓝色#1E3A8A、浅蓝色#60A5FA、灰色#6B7280为主色调，"
                f"线条：简洁直线连接，箭头清晰，无多余装饰，"
                f"文字：关键组件名称清晰标注，字体适中（14-16pt），黑色或深灰色，"
                f"背景：纯白色#FFFFFF，"
                f"风格：投标文件技术图纸规范，专业正式，层次清晰，"
                f"分辨率：2048x2048像素，高清输出"
            )
        elif diagram_type == "flowchart" or diagram_type == "流程图":
            steps = details.get("steps", [])
            if isinstance(steps, list):
                steps_str = "、".join(steps)
            else:
                steps_str = str(steps)
            return (
                f"专业IT流程图，展示{topic}，"
                f"流程步骤：{steps_str}，"
                f"要求：使用标准流程图符号（矩形表示处理步骤，菱形表示判断节点，圆角矩形表示开始/结束），"
                f"流程方向：从上到下或从左到右，逻辑清晰，"
                f"配色方案：深蓝色#1E3A8A、浅蓝色#60A5FA、灰色#6B7280，"
                f"箭头：实线箭头指示流向，粗细适中，"
                f"文字：每个步骤清晰标注，字体14-16pt，黑色或深灰色，"
                f"背景：纯白色#FFFFFF，"
                f"风格：投标文件技术图纸规范，简洁无装饰，逻辑清晰，"
                f"分辨率：2048x2048像素，高清输出"
            )
        elif diagram_type == "org_chart" or diagram_type == "组织图":
            structure = details.get("structure", "层级结构")
            return (
                f"专业组织架构图，展示{topic}，"
                f"组织结构：{structure}，"
                f"要求：树形布局，从上到下展示层级关系，"
                f"配色方案：深蓝色#1E3A8A、浅蓝色#60A5FA、灰色#6B7280，"
                f"方框：圆角矩形，统一大小，层级清晰，"
                f"连接线：垂直和水平线条，简洁清晰，"
                f"文字：职位/角色名称清晰标注，字体14-16pt，黑色或深灰色，"
                f"背景：纯白色#FFFFFF，"
                f"风格：投标文件技术图纸规范，专业正式，层次分明，"
                f"分辨率：2048x2048像素，高清输出"
            )
        else:
            # 通用模板
            return (
                f"专业IT技术示意图，展示{topic}，"
                f"要求：使用标准IT图标和符号，"
                f"配色方案：深蓝色#1E3A8A、浅蓝色#60A5FA、灰色#6B7280，"
                f"线条：简洁清晰，无多余装饰，"
                f"文字：关键信息清晰标注，字体14-16pt，黑色或深灰色，"
                f"背景：纯白色#FFFFFF，"
                f"风格：投标文件技术图纸规范，专业正式，"
                f"分辨率：2048x2048像素，高清输出"
            )

    def _generate_with_ark(self, prompt: str, size: str) -> Optional[str]:
        """使用火山方舟生成图片"""
        response = self.ark_client.images.generate(
            model=self.models['ark'],
            prompt=prompt,
            size=size,  # 2048x2048
            response_format="url"
        )

        image_url = response.data[0].url
        logger.info(f"火山方舟 AI 生图成功: {image_url}")

        # 下载到本地
        local_path = os.path.join(tempfile.gettempdir(), f"taw_ai_img_{uuid.uuid4().hex[:8]}.png")
        self._download_image(image_url, local_path)

        # 验证图片质量
        if not self._validate_image(local_path):
            logger.warning(f"图片质量验证失败: {local_path}")
            return None

        return local_path

    def _generate_with_dashscope(self, prompt: str, size: str) -> Optional[str]:
        """使用阿里云通义万相生成图片"""
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

        headers = {
            "Authorization": f"Bearer {self.dashscope_api_key}",
            "Content-Type": "application/json"
        }

        # 阿里云使用 "2048*2048" 格式
        dashscope_size = size.replace("x", "*")

        payload = {
            "model": self.models['dashscope'],
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            },
            "parameters": {
                "size": dashscope_size,  # "2048*2048"
                "n": 1
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        try:
            image_url = result["output"]["choices"][0]["message"]["content"][0]["image"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"阿里云 API 响应格式异常: {e}, response={result}")
            return None
        logger.info(f"阿里云 AI 生图成功: {image_url}")

        # 下载到本地
        local_path = os.path.join(tempfile.gettempdir(), f"taw_ai_img_{uuid.uuid4().hex[:8]}.png")
        self._download_image(image_url, local_path)

        # 验证图片质量
        if not self._validate_image(local_path):
            logger.warning(f"图片质量验证失败: {local_path}")
            return None

        return local_path

    def _generate_with_gemini(self, prompt: str, size: str) -> Optional[str]:
        """使用 Google Gemini 生成图片，自动选择 API 接口"""
        model_id = self.models['gemini']

        # Imagen 系列用 generate_images (predict)，Gemini 系列用 generateContent
        if model_id.startswith("imagen-"):
            return self._gemini_imagen(prompt, size, model_id)
        else:
            return self._gemini_generate_content(prompt, model_id)

    def _gemini_imagen(self, prompt: str, size: str, model_id: str) -> Optional[str]:
        """Imagen 系列：通过 generate_images API 生图"""
        from google.genai import types

        w, h = map(int, size.split("x"))
        if w == h:
            aspect = "1:1"
        elif w > h:
            aspect = "16:9"
        else:
            aspect = "9:16"

        response = self.gemini_client.models.generate_images(
            model=model_id,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect,
            )
        )

        if not response.generated_images:
            logger.error("Gemini Imagen 未返回任何图片")
            return None

        image_bytes = response.generated_images[0].image.image_bytes
        return self._save_gemini_image(image_bytes)

    def _gemini_generate_content(self, prompt: str, model_id: str) -> Optional[str]:
        """Gemini 多模态系列：通过 generateContent API 生图"""
        from google.genai import types

        response = self.gemini_client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # 从响应中提取图片
        if not response.candidates:
            logger.error("Gemini generateContent 未返回任何候选")
            return None

        candidate = response.candidates[0]
        if not hasattr(candidate, 'content') or not candidate.content:
            logger.error("Gemini generateContent 候选无 content 字段")
            return None
        if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
            logger.error("Gemini generateContent content 无 parts 字段")
            return None

        for part in candidate.content.parts:
            if not hasattr(part, 'inline_data') or not part.inline_data:
                continue
            if not hasattr(part.inline_data, 'mime_type') or not part.inline_data.mime_type:
                continue
            if part.inline_data.mime_type.startswith("image/"):
                image_data = part.inline_data.data
                # 处理 base64 编码的情况
                if isinstance(image_data, str):
                    import base64
                    image_data = base64.b64decode(image_data)
                return self._save_gemini_image(image_data)

        logger.error("Gemini generateContent 响应中未找到图片")
        return None

    def _save_gemini_image(self, image_bytes: bytes) -> Optional[str]:
        """保存 Gemini 返回的图片字节并验证"""
        local_path = os.path.join(
            tempfile.gettempdir(),
            f"taw_ai_img_{uuid.uuid4().hex[:8]}.png"
        )
        with open(local_path, "wb") as f:
            f.write(image_bytes)
        logger.info(f"Gemini AI 生图成功: {local_path}")

        if not self._validate_image(local_path):
            logger.warning(f"图片质量验证失败: {local_path}")
            return None

        return local_path

    def _download_image(self, url: str, local_path: str):
        """下载图片到本地"""
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"图片已下载: {local_path}")

    def _validate_image(self, local_path: str) -> bool:
        """验证图片质量"""
        # 检查文件大小
        file_size = os.path.getsize(local_path)
        if file_size < 10 * 1024:  # < 10KB
            logger.warning(f"图片文件过小: {file_size} bytes")
            return False

        # 检查图片尺寸（需要 Pillow）
        try:
            from PIL import Image
            img = Image.open(local_path)
            width, height = img.size
            if width * height < 512 * 512:
                logger.warning(f"图片尺寸过小: {width}x{height} ({width*height} pixels)")
                return False
            logger.info(f"图片验证通过: {width}x{height}, {file_size} bytes")
        except ImportError:
            logger.warning("Pillow 未安装，跳过图片尺寸验证（仅通过文件大小检查）")
        except Exception as e:
            logger.error(f"图片格式验证失败: {e}")
            return False

        return True


def main():
    """命令行测试入口"""
    import argparse

    parser = argparse.ArgumentParser(description='AI 图片生成器测试工具')
    parser.add_argument('--type', required=True, choices=['architecture', 'flowchart', 'org_chart'],
                        help='图表类型')
    parser.add_argument('--topic', required=True, help='主题')
    parser.add_argument('--components', help='组件列表（逗号分隔）')
    parser.add_argument('--steps', help='步骤列表（逗号分隔）')
    parser.add_argument('--structure', help='组织结构描述')
    parser.add_argument('--output', default='/tmp/test_ai_image.png', help='输出文件路径')
    parser.add_argument('--provider', choices=['ark', 'dashscope', 'gemini'], help='指定 API 提供商')

    args = parser.parse_args()

    # 构建 details
    details = {}
    if args.components:
        details['components'] = args.components.split(',')
    if args.steps:
        details['steps'] = args.steps.split(',')
    if args.structure:
        details['structure'] = args.structure

    # 初始化生成器
    generator = AIImageGenerator(provider=args.provider)

    # 生成图片
    result = generator.generate_diagram(
        diagram_type=args.type,
        topic=args.topic,
        details=details
    )

    if result:
        # 复制到指定输出路径
        import shutil
        shutil.copy(result, args.output)
        print(f"✅ 图片生成成功: {args.output}")
    else:
        print("❌ 图片生成失败")
        exit(1)


if __name__ == '__main__':
    main()

