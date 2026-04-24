#!/usr/bin/env python3
"""
draw.io 图表生成器

使用 draw.io CLI 生成专业的流程图、架构图、组织图等，
支持导出为 PNG 格式（带嵌入 XML，可在 draw.io 中再次编辑）。
"""

import os
import platform
import subprocess
import logging
import tempfile
import shutil
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _find_drawio_cli() -> Optional[str]:
    """
    查找 draw.io CLI 可执行文件路径

    Returns:
        draw.io CLI 路径，未找到返回 None
    """
    # 常见路径列表
    possible_paths = [
        # macOS 标准安装路径
        "/Applications/draw.io.app/Contents/MacOS/draw.io",
        "/Applications/diagrams.net.app/Contents/MacOS/diagrams.net",
        # Linux 路径
        "/usr/bin/drawio",
        "/usr/local/bin/drawio",
        # Windows 路径
        r"C:\Program Files\draw.io\draw.io.exe",
    ]

    # 检查 PATH 中的 drawio（跨平台：Linux/macOS 查 which 语义，Windows 查 where 语义）
    drawio_on_path = shutil.which("drawio")
    if drawio_on_path:
        return drawio_on_path

    # 检查常见安装路径
    for path in possible_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    # macOS Spotlight 搜索
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["mdfind", "-name", "draw.io"],
                capture_output=True,
                text=True,
                timeout=10
            )
            for line in result.stdout.strip().split("\n"):
                if line.endswith(".app"):
                    cli_path = os.path.join(line, "Contents/MacOS/draw.io")
                    if os.path.isfile(cli_path):
                        return cli_path
                elif line.endswith("draw.io"):
                    return line
        except Exception:
            pass

    return None


class DrawioGenerator:
    """draw.io 图表生成器"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化生成器

        Args:
            output_dir: 输出目录，默认系统临时目录下 drawio_output
        """
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "drawio_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.drawio_path = _find_drawio_cli()

        if self.drawio_path:
            logger.info(f"找到 draw.io CLI: {self.drawio_path}")
        else:
            logger.warning("draw.io CLI 未找到，图表生成功能将不可用")

    def is_available(self) -> bool:
        """检查 draw.io 是否可用"""
        return self.drawio_path is not None

    def generate_diagram(
        self,
        diagram_type: str,
        topic: str,
        details: Dict
    ) -> Optional[str]:
        """
        生成图表

        Args:
            diagram_type: 图表类型 (architecture | flowchart | org_chart | sequence | other)
            topic: 主题描述
            details: 详细信息（components/steps/structure 等）

        Returns:
            本地 PNG 文件路径，失败返回 None
        """
        if not self.is_available():
            logger.error("draw.io CLI 不可用")
            return None

        # 1. 生成 draw.io XML
        xml_content = self._build_drawio_xml(diagram_type, topic, details)
        if not xml_content:
            logger.error("XML 生成失败")
            return None

        # 2. 写入临时 .drawio 文件
        drawio_file = self._write_temp_drawio(xml_content, topic)
        if not drawio_file:
            return None

        # 3. 导出为 PNG（带嵌入 XML）
        png_file = self._export_to_png(drawio_file)

        # 4. 保留 .drawio 文件（便于调试和手动编辑）
        # 不删除源文件

        return png_file

    def _build_drawio_xml(
        self,
        diagram_type: str,
        topic: str,
        details: Dict
    ) -> Optional[str]:
        """
        构建 draw.io XML 内容

        Args:
            diagram_type: 图表类型
            topic: 主题描述
            details: 详细信息

        Returns:
            draw.io XML 字符串，失败返回 None
        """
        # 标准 draw.io XML 模板
        # 使用 mxGraph 格式

        # 转义用户输入，防止 XML 注入
        topic = xml_escape(topic)

        # 根据图表类型选择不同的模板
        if diagram_type == "architecture":
            return self._build_architecture_xml(topic, details)
        elif diagram_type == "flowchart":
            return self._build_flowchart_xml(topic, details)
        elif diagram_type == "org_chart":
            return self._build_org_chart_xml(topic, details)
        elif diagram_type == "sequence":
            return self._build_sequence_xml(topic, details)
        else:
            return self._build_generic_xml(topic, details)

    def _build_architecture_xml(
        self,
        topic: str,
        details: Dict
    ) -> str:
        """构建架构图 XML"""
        components = details.get("components", [])
        layers = details.get("layers", [])

        # 计算画布大小
        width = max(800, len(components) * 200 if components else 800)
        height = max(600, (len(layers) + 1) * 150 if layers else 600)

        # 构建组件 XML
        shapes_xml = ""
        y_offset = 100

        # 如果有分层，先画层
        if layers:
            for i, layer in enumerate(layers):
                layer_y = 50 + i * 150
                layer_name = xml_escape(layer.get('name', f'Layer {i+1}') if isinstance(layer, dict) else str(layer))
                shapes_xml += f'''
        <mxCell id="layer_{i}" value="{layer_name}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;" vertex="1" parent="1">
          <mxGeometry x="40" y="{layer_y}" width="{width - 80}" height="120" as="geometry"/>
        </mxCell>'''

        # 画组件
        for i, comp in enumerate(components):
            x = 80 + (i % 4) * 200
            y = y_offset + (i // 4) * 120
            comp_name = xml_escape(comp.get("name", f"Component {i+1}") if isinstance(comp, dict) else str(comp))
            shapes_xml += f'''
        <mxCell id="comp_{i}" value="{comp_name}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="160" height="80" as="geometry"/>
        </mxCell>'''

        # 画连接线（如果有）
        connections = details.get("connections", [])
        for idx, conn in enumerate(connections):
            if isinstance(conn, dict) and "from" in conn and "to" in conn:
                shapes_xml += f'''
        <mxCell id="conn_{idx}" value="" style="endArrow=classic;html=1;exitX=1;exitY=0.5;entryX=0;entryY=0.5;" edge="1" parent="1" source="comp_{conn.get('from', 0)}" target="comp_{conn.get('to', 1)}">
          <mxGeometry width="50" height="50" relative="1" as="geometry"/>
        </mxCell>'''

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="draw.io" modified="2026-03-16T00:00:00.000Z" agent="taw-drawio-generator" etag="taw" version="24.1.0" type="device">
  <diagram id="architecture" name="架构图">
    <mxGraphModel dx="{width}" dy="{height}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="title" value="{topic}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontStyle=1;fontSize=18;" vertex="1" parent="1">
          <mxGeometry x="{width//2 - 100}" y="20" width="200" height="30" as="geometry"/>
        </mxCell>
        {shapes_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    def _build_flowchart_xml(
        self,
        topic: str,
        details: Dict
    ) -> str:
        """构建流程图 XML"""
        steps = details.get("steps", [])

        width = 800
        height = max(600, len(steps) * 100)

        shapes_xml = ""
        for i, step in enumerate(steps):
            step_name = xml_escape(step.get("name", f"Step {i+1}") if isinstance(step, dict) else str(step))
            y = 80 + i * 100
            # 开始/结束用圆角矩形，中间步骤用矩形
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;" if i == 0 or i == len(steps) - 1 else "whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
            shapes_xml += f'''
        <mxCell id="step_{i}" value="{step_name}" style="{style}" vertex="1" parent="1">
          <mxGeometry x="{width//2 - 150}" y="{y}" width="300" height="60" as="geometry"/>
        </mxCell>'''

            # 画箭头
            if i < len(steps) - 1:
                shapes_xml += f'''
        <mxCell id="arrow_{i}" value="" style="endArrow=classic;html=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="1" source="step_{i}" target="step_{i+1}">
          <mxGeometry width="50" height="50" relative="1" as="geometry"/>
        </mxCell>'''

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="draw.io" modified="2026-03-16T00:00:00.000Z" agent="taw-drawio-generator" etag="taw" version="24.1.0" type="device">
  <diagram id="flowchart" name="流程图">
    <mxGraphModel dx="{width}" dy="{height}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="title" value="{topic}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontStyle=1;fontSize=18;" vertex="1" parent="1">
          <mxGeometry x="{width//2 - 100}" y="20" width="200" height="30" as="geometry"/>
        </mxCell>
        {shapes_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    def _build_org_chart_xml(
        self,
        topic: str,
        details: Dict
    ) -> str:
        """构建组织架构图 XML"""
        structure = details.get("structure", [])

        width = 1000
        height = 600

        shapes_xml = ""
        # 顶层
        if structure:
            root = structure[0] if isinstance(structure[0], dict) else {"name": str(structure[0])}
            shapes_xml += f'''
        <mxCell id="root" value="{xml_escape(root.get('name', 'Root'))}" style="whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;" vertex="1" parent="1">
          <mxGeometry x="{width//2 - 100}" y="80" width="200" height="60" as="geometry"/>
        </mxCell>'''

            # 第二层
            children = root.get("children", [])
            for i, child in enumerate(children):
                child_name = xml_escape(child.get("name", f"Dept {i+1}") if isinstance(child, dict) else str(child))
                x = width//2 - 150 + i * 200
                shapes_xml += f'''
        <mxCell id="child_{i}" value="{child_name}" style="whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="200" width="160" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="edge_{i}" value="" style="endArrow=classic;html=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;" edge="1" parent="1" source="root" target="child_{i}">
          <mxGeometry width="50" height="50" relative="1" as="geometry"/>
        </mxCell>'''

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="draw.io" modified="2026-03-16T00:00:00.000Z" agent="taw-drawio-generator" etag="taw" version="24.1.0" type="device">
  <diagram id="org_chart" name="组织架构图">
    <mxGraphModel dx="{width}" dy="{height}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="title" value="{topic}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontStyle=1;fontSize=18;" vertex="1" parent="1">
          <mxGeometry x="{width//2 - 100}" y="20" width="200" height="30" as="geometry"/>
        </mxCell>
        {shapes_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    def _build_sequence_xml(
        self,
        topic: str,
        details: Dict
    ) -> str:
        """构建序列图 XML（简化版）"""
        participants = details.get("participants", [])
        messages = details.get("messages", [])

        width = 800
        height = 600

        shapes_xml = ""
        # 画参与者
        for i, participant in enumerate(participants):
            part_name = xml_escape(participant.get("name", f"Actor {i+1}") if isinstance(participant, dict) else str(participant))
            x = 100 + i * 200
            shapes_xml += f'''
        <mxCell id="actor_{i}" value="{part_name}" style="shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;outlineConnect=0;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="80" width="100" height="400" as="geometry"/>
        </mxCell>'''

        # 画消息
        for i, msg in enumerate(messages):
            if isinstance(msg, dict):
                from_idx = msg.get("from", 0)
                to_idx = msg.get("to", 1)
                msg_text = xml_escape(msg.get("message", "Message"))
                y = 150 + i * 50
                x1 = 150 + from_idx * 200
                x2 = 150 + to_idx * 200
                shapes_xml += f'''
        <mxCell id="msg_{i}" value="{msg_text}" style="endArrow=classic;html=1;" edge="1" parent="1">
          <mxGeometry x="{x1}" y="{y}" width="{x2-x1}" height="50" as="geometry"/>
        </mxCell>'''

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="draw.io" modified="2026-03-16T00:00:00.000Z" agent="taw-drawio-generator" etag="taw" version="24.1.0" type="device">
  <diagram id="sequence" name="序列图">
    <mxGraphModel dx="{width}" dy="{height}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="title" value="{topic}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontStyle=1;fontSize=18;" vertex="1" parent="1">
          <mxGeometry x="{width//2 - 100}" y="20" width="200" height="30" as="geometry"/>
        </mxCell>
        {shapes_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    def _build_generic_xml(
        self,
        topic: str,
        details: Dict
    ) -> str:
        """构建通用图表 XML"""
        items = details.get("items", [])

        width = 800
        height = 600

        shapes_xml = ""
        for i, item in enumerate(items):
            item_name = xml_escape(item.get("name", f"Item {i+1}") if isinstance(item, dict) else str(item))
            x = 100 + (i % 3) * 250
            y = 100 + (i // 3) * 120
            shapes_xml += f'''
        <mxCell id="item_{i}" value="{item_name}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="200" height="80" as="geometry"/>
        </mxCell>'''

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="draw.io" modified="2026-03-16T00:00:00.000Z" agent="taw-drawio-generator" etag="taw" version="24.1.0" type="device">
  <diagram id="generic" name="图表">
    <mxGraphModel dx="{width}" dy="{height}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="title" value="{topic}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontStyle=1;fontSize=18;" vertex="1" parent="1">
          <mxGeometry x="{width//2 - 100}" y="20" width="200" height="30" as="geometry"/>
        </mxCell>
        {shapes_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    def _write_temp_drawio(
        self,
        xml_content: str,
        topic: str
    ) -> Optional[Path]:
        """
        写入临时 .drawio 文件

        Args:
            xml_content: draw.io XML 内容
            topic: 主题描述（用于文件名）

        Returns:
            .drawio 文件路径，失败返回 None
        """
        try:
            # 生成安全的文件名
            safe_topic = "".join(c if c.isalnum() else "_" for c in topic[:30])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_topic}_{timestamp}.drawio"
            filepath = self.output_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            logger.info(f"已写入 .drawio 文件：{filepath}")
            return filepath

        except Exception as e:
            logger.error(f"写入 .drawio 文件失败：{e}")
            return None

    def _export_to_png(
        self,
        drawio_file: Path
    ) -> Optional[Path]:
        """
        导出 .drawio 文件为 PNG（带嵌入 XML）

        Args:
            drawio_file: .drawio 文件路径

        Returns:
            PNG 文件路径，失败返回 None
        """
        try:
            # 生成 PNG 文件名
            png_file = drawio_file.with_suffix('.png')

            # 调用 draw.io CLI 导出
            # --export 导出文件
            # --embed-xml 嵌入 XML（可在 draw.io 中再次编辑）
            # --transparent 透明背景（可选）
            cmd = [
                self.drawio_path,
                "--export",
                str(drawio_file),
                "--format", "png",
                "--embed-xml",
                "--output", str(png_file)
            ]

            logger.info(f"执行 draw.io 导出：{' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                logger.error(f"draw.io 导出失败：{result.stderr}")
                return None

            if not png_file.exists():
                logger.error("PNG 文件未生成")
                return None

            # 验证文件大小
            file_size = png_file.stat().st_size
            if file_size < 1024:  # 小于 1KB 可能有问题
                logger.warning(f"PNG 文件过小：{file_size} 字节")

            logger.info(f"PNG 导出成功：{png_file} ({file_size} 字节)")
            return png_file

        except subprocess.TimeoutExpired:
            logger.error("draw.io 导出超时（60 秒）")
            return None
        except Exception as e:
            logger.error(f"导出 PNG 失败：{e}")
            return None


def main():
    """命令行入口"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="draw.io 图表生成器")
    parser.add_argument("--type", required=True, help="图表类型：architecture|flowchart|org_chart|sequence|other")
    parser.add_argument("--topic", required=True, help="主题描述")
    parser.add_argument("--details", required=True, help="详细信息（JSON 格式）")
    parser.add_argument("--output", help="输出目录（默认系统临时目录下 drawio_output）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        details = json.loads(args.details)
    except json.JSONDecodeError as e:
        logger.error(f"解析 --details JSON 失败：{e}")
        return 1

    generator = DrawioGenerator(output_dir=args.output)

    if not generator.is_available():
        logger.error("draw.io CLI 不可用，请确认已安装 draw.io Desktop")
        return 1

    result = generator.generate_diagram(args.type, args.topic, details)

    if result:
        print(f"图表生成成功：{result}")
        return 0
    else:
        logger.error("图表生成失败")
        return 1


if __name__ == "__main__":
    exit(main())
