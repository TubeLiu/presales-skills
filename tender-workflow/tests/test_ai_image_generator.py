#!/usr/bin/env python3
"""
AI 图片生成器单元测试
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# 添加 tools 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / '.claude' / 'skills' / 'taw' / 'tools'))

from ai_image_generator import AIImageGenerator


class TestAIImageGenerator:
    """AI 图片生成器测试类"""

    def test_init_with_env_vars(self):
        """测试从环境变量初始化（配置文件不存在时，fallback 到环境变量）"""
        with patch('ai_image_generator._load_taw_config', return_value={}), \
             patch.dict(os.environ, {
                 'ARK_API_KEY': 'test-ark-key',
                 'DASHSCOPE_API_KEY': 'test-dashscope-key'
             }):
            generator = AIImageGenerator()
            assert generator.ark_api_key == 'test-ark-key'
            assert generator.dashscope_api_key == 'test-dashscope-key'
            assert generator.provider == 'ark'

    def test_init_with_params(self):
        """测试通过参数初始化"""
        generator = AIImageGenerator(
            ark_api_key='param-ark-key',
            dashscope_api_key='param-dashscope-key',
            provider='dashscope'
        )
        assert generator.ark_api_key == 'param-ark-key'
        assert generator.dashscope_api_key == 'param-dashscope-key'
        assert generator.provider == 'dashscope'

    def test_build_prompt_architecture(self):
        """测试架构图提示词生成（中文）"""
        generator = AIImageGenerator()
        prompt = generator._build_prompt(
            diagram_type='architecture',
            topic='容器云平台总体架构',
            details={'components': ['基础设施层', 'K8s编排层', 'ACP平台层', '业务应用层']}
        )
        assert '专业IT技术架构图' in prompt
        assert '容器云平台总体架构' in prompt
        assert '基础设施层' in prompt
        assert '分层架构' in prompt
        assert '标准IT图标' in prompt
        assert '#1E3A8A' in prompt  # 深蓝色
        assert '#60A5FA' in prompt  # 浅蓝色
        assert '#6B7280' in prompt  # 灰色
        assert '文字：关键组件名称清晰标注' in prompt
        assert '投标文件技术图纸规范' in prompt
        assert '2048x2048像素' in prompt

    def test_build_prompt_flowchart(self):
        """测试流程图提示词生成（中文）"""
        generator = AIImageGenerator()
        prompt = generator._build_prompt(
            diagram_type='flowchart',
            topic='DevOps CI/CD流水线',
            details={'steps': ['代码提交', '构建', '测试', '部署']}
        )
        assert '专业IT流程图' in prompt
        assert 'DevOps CI/CD流水线' in prompt
        assert '代码提交' in prompt
        assert '标准流程图符号' in prompt
        assert '箭头' in prompt
        assert '#1E3A8A' in prompt  # 深蓝色
        assert '文字：每个步骤清晰标注' in prompt
        assert '投标文件技术图纸规范' in prompt

    def test_build_prompt_org_chart(self):
        """测试组织图提示词生成（中文）"""
        generator = AIImageGenerator()
        prompt = generator._build_prompt(
            diagram_type='org_chart',
            topic='项目团队组织架构',
            details={'structure': '项目经理-技术架构-各模块负责人'}
        )
        assert '专业组织架构图' in prompt
        assert '项目团队组织架构' in prompt
        assert '组织结构' in prompt
        assert '树形布局' in prompt
        assert '#1E3A8A' in prompt  # 深蓝色
        assert '文字：职位/角色名称清晰标注' in prompt
        assert '投标文件技术图纸规范' in prompt

    def test_prompt_contains_color_scheme(self):
        """测试提示词包含配色方案"""
        generator = AIImageGenerator()
        prompt = generator._build_prompt(
            diagram_type='architecture',
            topic='容器云平台',
            details={'components': ['K8s', 'Docker']}
        )
        assert '#1E3A8A' in prompt  # 深蓝色
        assert '#60A5FA' in prompt  # 浅蓝色
        assert '#6B7280' in prompt  # 灰色

    def test_prompt_contains_standard_icons(self):
        """测试提示词包含标准图标要求"""
        generator = AIImageGenerator()
        prompt = generator._build_prompt(
            diagram_type='architecture',
            topic='系统架构',
            details={'components': ['服务器', '数据库']}
        )
        assert '标准IT图标' in prompt

    def test_prompt_contains_text_requirement(self):
        """测试提示词包含文字标注要求"""
        generator = AIImageGenerator()
        prompt = generator._build_prompt(
            diagram_type='flowchart',
            topic='CI/CD流程',
            details={'steps': ['构建', '测试', '部署']}
        )
        assert '文字' in prompt
        assert '清晰标注' in prompt

    @patch('ai_image_generator.requests.get')
    def test_download_image_success(self, mock_get):
        """测试图片下载成功"""
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b'fake_image_data' * 1000  # 模拟图片数据
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        generator = AIImageGenerator()
        local_path = '/tmp/test_download.png'

        generator._download_image('http://example.com/image.png', local_path)

        # 验证文件已创建
        assert os.path.exists(local_path)
        os.remove(local_path)  # 清理

    @patch('ai_image_generator.requests.get')
    def test_download_image_failure(self, mock_get):
        """测试图片下载失败"""
        # Mock HTTP 错误
        mock_get.side_effect = Exception("Network error")

        generator = AIImageGenerator()

        with pytest.raises(Exception):
            generator._download_image('http://example.com/image.png', '/tmp/test.png')

    def test_validate_image_too_small(self):
        """测试图片文件过小验证"""
        generator = AIImageGenerator()

        # 创建一个小文件
        test_file = '/tmp/test_small.png'
        with open(test_file, 'wb') as f:
            f.write(b'small')

        result = generator._validate_image(test_file)
        assert result is False

        os.remove(test_file)  # 清理

    @patch('ai_image_generator.AIImageGenerator._generate_with_ark')
    def test_generate_diagram_ark_success(self, mock_ark):
        """测试使用火山方舟生成图片成功"""
        mock_ark.return_value = '/tmp/test_ark.png'

        generator = AIImageGenerator(ark_api_key='test-key')
        generator.ark_client = Mock()  # Mock 客户端

        result = generator.generate_diagram(
            diagram_type='architecture',
            topic='测试架构',
            details={'components': ['组件1', '组件2']}
        )

        assert result == '/tmp/test_ark.png'
        mock_ark.assert_called_once()

    @patch('ai_image_generator.AIImageGenerator._generate_with_ark')
    def test_generate_diagram_provider_fail_no_fallback(self, mock_ark):
        """测试指定供应商失败后不降级（返回 None）"""
        mock_ark.side_effect = Exception("Ark API error")

        generator = AIImageGenerator(
            ark_api_key='test-ark-key',
            dashscope_api_key='test-dashscope-key',
            provider='ark'
        )
        generator.ark_client = Mock()

        result = generator.generate_diagram(
            diagram_type='flowchart',
            topic='测试流程',
            details={'steps': ['步骤1', '步骤2']}
        )

        assert result is None
        mock_ark.assert_called_once()

    @patch('ai_image_generator.AIImageGenerator._generate_with_gemini')
    @patch('ai_image_generator.AIImageGenerator._generate_with_dashscope')
    @patch('ai_image_generator.AIImageGenerator._generate_with_ark')
    def test_generate_diagram_all_fail(self, mock_ark, mock_dashscope, mock_gemini):
        """测试所有 API 都失败"""
        # 三个 API 都失败
        mock_ark.side_effect = Exception("Ark API error")
        mock_dashscope.side_effect = Exception("DashScope API error")
        mock_gemini.side_effect = Exception("Gemini API error")

        generator = AIImageGenerator(
            ark_api_key='test-ark-key',
            provider='ark'
        )
        generator.ark_client = Mock()

        result = generator.generate_diagram(
            diagram_type='architecture',
            topic='测试架构',
            details={'components': ['组件1']}
        )

        assert result is None

    def test_provider_custom(self):
        """测试自定义供应商"""
        generator = AIImageGenerator(
            dashscope_api_key='test-dashscope-key',
            provider='dashscope'
        )

        assert generator.provider == 'dashscope'

    @patch('ai_image_generator.AIImageGenerator._generate_with_ark')
    def test_single_provider_no_fallback(self, mock_ark):
        """测试指定供应商失败时不降级（返回 None）"""
        mock_ark.side_effect = Exception("Ark fail")

        generator = AIImageGenerator(
            ark_api_key='k1', dashscope_api_key='k2',
            provider='ark'
        )
        generator.ark_client = Mock()

        result = generator.generate_diagram(
            diagram_type='architecture', topic='测试', details={'components': ['A']}
        )

        # 不应降级到 dashscope，直接返回 None
        assert result is None
        assert mock_ark.call_count == 1

    def test_unknown_provider_returns_none(self):
        """测试未知供应商返回 None"""
        generator = AIImageGenerator(
            ark_api_key='k1',
            provider='unknown_provider'
        )

        result = generator.generate_diagram(
            diagram_type='architecture', topic='测试', details={'components': ['A']}
        )

        assert result is None

    def test_no_api_keys_returns_none(self):
        """测试无任何 API Key 时返回 None"""
        with patch('ai_image_generator._load_taw_config', return_value={}), \
             patch.dict(os.environ, {}, clear=True):
            generator = AIImageGenerator()
            result = generator.generate_diagram(
                diagram_type='architecture', topic='测试', details={'components': ['A']}
            )
            assert result is None

    def test_validate_image_file_too_small(self):
        """测试文件大小验证"""
        generator = AIImageGenerator()
        test_file = '/tmp/test_tiny.png'
        with open(test_file, 'wb') as f:
            f.write(b'x' * 100)  # 100 bytes < 10KB threshold
        assert generator._validate_image(test_file) is False
        os.remove(test_file)

    def test_validate_image_large_enough(self):
        """测试大文件通过文件大小检查"""
        generator = AIImageGenerator()
        test_file = '/tmp/test_large.png'
        with open(test_file, 'wb') as f:
            f.write(b'x' * 20000)  # 20KB > 10KB threshold
        # Pillow 打开假文件会失败，但文件大小检查通过
        # _validate_image 会 catch Pillow 异常并返回 False
        result = generator._validate_image(test_file)
        os.remove(test_file)
        # 文件不是真正的图片，Pillow 验证会失败
        assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
