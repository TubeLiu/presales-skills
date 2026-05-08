#!/usr/bin/env python3
"""
PPT Master - SVG Quality Check Tool

Checks whether SVG files comply with project technical specifications.

Usage:
    python3 scripts/svg_quality_checker.py <svg_file>
    python3 scripts/svg_quality_checker.py <directory>
    python3 scripts/svg_quality_checker.py --all examples
    python3 scripts/svg_quality_checker.py --lint <svg_file_or_directory>

Modes:
    Default (no flag) — full 10-dimension check, called at SKILL.md Step 6 Quality Check Gate.
    --lint            — Pre-flight subset (viewBox / forbidden elements / fonts only),
                         called at SKILL.md Step 7.0 just before total_md_split / finalize_svg /
                         svg_to_pptx; finalize_svg.py rewrites SVG and would mask violations,
                         so this is the last cheap chance (<1s) to catch banned features.
                         Skips: dimensions, text wrapping, image refs, spec_lock drift
                                (those need project context that is not yet available).

Other flags (combinable with default or --lint):
    --format <name>   — Expected canvas format (e.g., ppt169 / ppt43 / red / moments / story)
    --export          — Write text report to disk (default: svg_quality_report.txt)
    --output <file>   — Override export filename
"""

import sys as _sys; from pathlib import Path as _Path; _sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _ensure_deps import ensure_deps; ensure_deps()

import sys
import re
import html
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
from svg_finalize.layout_semantics import (
    alignment_issues as _semantic_alignment_issues,
    component_emphasis_alignment_issues as _semantic_component_emphasis_alignment_issues,
    estimate_text_width as _semantic_estimate_text_width,
)

try:
    from project_utils import CANVAS_FORMATS
    from error_helper import ErrorHelper
except ImportError:
    print("Warning: Unable to import dependency modules")
    CANVAS_FORMATS = {}
    ErrorHelper = None

try:
    from update_spec import parse_lock as _parse_spec_lock
except ImportError:
    _parse_spec_lock = None  # spec_lock drift check will be skipped


HEX_VALUE_RE = re.compile(r"#[0-9A-Fa-f]{3,8}")

# Ramp envelope for font-size drift detection.
# From design_spec_reference.md §IV — Font Size Hierarchy: the ramp spans
# from page-number floor (0.5x body) to cover-title ceiling (5.0x body).
# Intermediate px values within this envelope are permitted per
# executor-base.md §2.1 ("Executor may use an intermediate size ... provided
# the size's ratio to body falls within the corresponding role's band"); only
# values outside every band — i.e. outside this envelope — are drift.
RAMP_MIN_RATIO = 0.5
RAMP_MAX_RATIO = 5.0

# Conservative text layout heuristics. These are warnings only; they catch the
# obvious "labels drawn on top of labels" failures without pretending to be a
# browser-grade text shaper.
TEXT_COLLISION_MAX_ELEMENTS = 180
TEXT_COLLISION_MIN_OVERLAP_RATIO = 0.35
TEXT_COLLISION_MIN_AREA = 32.0
TEXT_CONTAINER_PADDING = 3.0
SEMANTIC_PARENT_PADDING = 6.0
SEMANTIC_CHILD_PADDING = 3.0
INTERMEDIATE_SLOT_TEXT_X_INSET = 3.0
INTERMEDIATE_SLOT_TEXT_Y_INSET = 1.0
TEXT_CONTAINER_MAX_AREA_RATIO = 0.75
TEXT_OCCLUSION_MIN_AREA = 36.0
TEXT_OCCLUSION_MIN_RATIO = 0.03
TEXT_OCCLUSION_PADDING = 6.0
CONNECTOR_ARROW_MIN_WIDTH = 28.0
CONNECTOR_ARROW_MIN_ASPECT = 1.2
CONNECTOR_TEXT_LANE_MIN_GAP = 72.0
CONNECTOR_TEXT_LANE_MIN_Y_OVERLAP = 0.35
CONNECTOR_CONTAINER_CLEARANCE = 8.0
CONNECTOR_CONTAINER_INTRUSION_MIN_AREA = 24.0
TEXT_CONTAINER_MIN_AREA = 100.0
SHAPE_TEXT_CENTER_TOLERANCE = 3.0
SHAPE_TEXT_LABEL_MAX_HEIGHT = 180.0
SHAPE_TEXT_LABEL_MAX_WIDTH = 1150.0
SHAPE_TEXT_STRIP_MAX_HEIGHT = 80.0
SHAPE_TEXT_STACK_TOLERANCE = 8.0
SEMANTIC_COMPONENT_MIN_GAP = 6.0
SEMANTIC_COMPONENT_MIN_AXIS_OVERLAP = 0.22
SEMANTIC_COMPONENT_OVERLAP_MIN_AREA = 32.0

VISIBLE_METADATA_RE = re.compile(
    r'(?:样张\s*P\d+|'
    r'\b(?:platform_panorama|architecture_stack|migration_bridge|mapping_table|process_flow|timeline|'
    r'capability_canvas|comparison|evidence_argument|kpi_metrics|risk_matrix|code_sample|'
    r'screenshot_evidence|parallel_value)\b|'
    r'\b(?:dense_technical|balanced_technical|breathing_argument)\b)'
)


class SVGQualityChecker:
    """SVG quality checker"""

    def __init__(self):
        self.results = []
        self.summary = {
            'total': 0,
            'passed': 0,
            'warnings': 0,
            'errors': 0
        }
        self.issue_types = defaultdict(int)
        # spec_lock drift state (populated only when _parse_spec_lock is available
        # and a spec_lock.md is found near the SVG)
        self._lock_cache: Dict[Path, Dict] = {}
        self._drift_summary: Dict[str, Dict[str, set]] = {
            'colors': defaultdict(set),
            'fonts': defaultdict(set),
            'sizes': defaultdict(set),
            'icons': defaultdict(set),
        }
        self._lock_seen = False  # True once we locate at least one spec_lock.md

    def check_file(self, svg_file: str, expected_format: str = None, lint_only: bool = False) -> Dict:
        """
        Check a single SVG file

        Args:
            svg_file: SVG file path
            expected_format: Expected canvas format (e.g., 'ppt169')
            lint_only: If True, run Step 7.0 pre-flight subset only —
                       dimensions 1 (viewBox) / 2 (forbidden elements) / 3 (fonts).
                       Skip dimensions 4 (width/height) / 5 (text wrapping) /
                       6 (image refs) / 7 (spec_lock drift) which need project
                       context not yet available before total_md_split.

        Returns:
            Check result dictionary
        """
        svg_path = Path(svg_file)

        if not svg_path.exists():
            return {
                'file': str(svg_file),
                'exists': False,
                'errors': ['File does not exist'],
                'warnings': [],
                'passed': False
            }

        result = {
            'file': svg_path.name,
            'path': str(svg_path),
            'exists': True,
            'errors': [],
            'warnings': [],
            'info': {},
            'passed': True
        }

        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 1. Check viewBox
            self._check_viewbox(content, result, expected_format)

            # 2. Check forbidden elements
            self._check_forbidden_elements(content, result)

            # 3. Check fonts
            self._check_fonts(content, result)

            if not lint_only:
                # 4. Check width/height consistency with viewBox
                self._check_dimensions(content, result)

                # 5. Check text wrapping methods
                self._check_text_elements(content, result)

                # 6. Check image references (file existence and resolution)
                self._check_image_references(content, svg_path, result)

                # 7. Check spec_lock drift (colors / font-family / font-size)
                self._check_spec_lock_drift(content, svg_path, result)

                # 8. Check viewBox overflow (shapes extending past canvas)
                self._check_viewbox_overflow(content, result)

                # 9. Check footer zone intrusion (content blocks past y=682)
                self._check_footer_zone_intrusion(content, result)

                # 10. Check content block fit (excessive empty space in cards)
                self._check_content_block_fit(content, result)

            # Determine pass/fail
            result['passed'] = len(result['errors']) == 0

        except Exception as e:
            result['errors'].append(f"Failed to read file: {e}")
            result['passed'] = False

        # Update statistics
        self.summary['total'] += 1
        if result['passed']:
            if result['warnings']:
                self.summary['warnings'] += 1
            else:
                self.summary['passed'] += 1
        else:
            self.summary['errors'] += 1

        # Categorize issue types
        for error in result['errors']:
            self.issue_types[self._categorize_issue(error)] += 1

        self.results.append(result)
        return result

    def _check_viewbox(self, content: str, result: Dict, expected_format: str = None):
        """Check viewBox attribute"""
        viewbox_match = re.search(r'viewBox="([^"]+)"', content)

        if not viewbox_match:
            result['errors'].append("Missing viewBox attribute")
            return

        viewbox = viewbox_match.group(1)
        result['info']['viewbox'] = viewbox

        # Check format
        if not re.match(r'0 0 \d+ \d+', viewbox):
            result['warnings'].append(f"Unusual viewBox format: {viewbox}")

        # Check if it matches expected format
        if expected_format and expected_format in CANVAS_FORMATS:
            expected_viewbox = CANVAS_FORMATS[expected_format]['viewbox']
            if viewbox != expected_viewbox:
                result['errors'].append(
                    f"viewBox mismatch: expected '{expected_viewbox}', got '{viewbox}'"
                )

    def _check_forbidden_elements(self, content: str, result: Dict):
        """Check forbidden elements (blocklist)"""
        content_lower = content.lower()

        # ============================================================
        # Forbidden elements blocklist - PPT incompatible
        # ============================================================

        # Clipping / masking
        # clipPath is ONLY allowed on <image> elements (converter maps to DrawingML
        # picture geometry).  On shapes it is pointless (just draw the target shape)
        # and breaks the SVG PPTX rendering.
        if '<clippath' in content_lower:
            # clip-path on non-image elements → error
            clip_on_non_image = re.search(
                r'<(?!image\b)\w+[^>]*\bclip-path\s*=', content, re.IGNORECASE)
            if clip_on_non_image:
                result['errors'].append(
                    "clip-path is only allowed on <image> elements — "
                    "for shapes, draw the target shape directly instead of clipping")
            # Check that every clip-path reference has a matching <clipPath> def
            clip_refs = re.findall(r'clip-path\s*=\s*["\']url\(#([^)]+)\)', content)
            for ref_id in clip_refs:
                if f'id="{ref_id}"' not in content and f"id='{ref_id}'" not in content:
                    result['errors'].append(
                        f"clip-path references #{ref_id} but no matching "
                        f"<clipPath id=\"{ref_id}\"> definition found")
        if '<mask' in content_lower:
            result['errors'].append("Detected forbidden <mask> element (PPT does not support SVG masks)")

        # Style system
        if '<style' in content_lower:
            result['errors'].append("Detected forbidden <style> element (use inline attributes instead)")
        if re.search(r'\bclass\s*=', content):
            result['errors'].append("Detected forbidden class attribute (use inline styles instead)")
        # id attribute: only report error when <style> also exists (id is harmful only with CSS selectors)
        # id inside <defs> for linearGradient/filter etc. is required, Inkscape also auto-adds id to elements,
        # standalone id attributes have no impact on PPT export
        if '<style' in content_lower and re.search(r'\bid\s*=', content):
            result['errors'].append(
                "Detected id attribute used with <style> (CSS selectors forbidden, use inline styles instead)"
            )
        if re.search(r'<\?xml-stylesheet\b', content_lower):
            result['errors'].append("Detected forbidden xml-stylesheet (external CSS references forbidden)")
        if re.search(r'<link[^>]*rel\s*=\s*["\']stylesheet["\']', content_lower):
            result['errors'].append("Detected forbidden <link rel=\"stylesheet\"> (external CSS references forbidden)")
        if re.search(r'@import\s+', content_lower):
            result['errors'].append("Detected forbidden @import (external CSS references forbidden)")

        # Structure / nesting
        if '<foreignobject' in content_lower:
            result['errors'].append(
                "Detected forbidden <foreignObject> element (use <tspan> for manual line breaks)")
        has_symbol = '<symbol' in content_lower
        has_use = re.search(r'<use\b', content_lower) is not None
        if has_symbol and has_use:
            result['errors'].append("Detected forbidden <symbol> + <use> complex usage (use basic shapes or simple <use> instead)")
        # marker-start / marker-end are conditionally allowed (see shared-standards.md §1.1).
        # The converter maps qualifying <marker> defs to native DrawingML <a:headEnd>/<a:tailEnd>.
        # We only warn when a marker is used without an obvious <defs> definition in the same file.
        if re.search(r'\bmarker-(?:start|end)\s*=\s*["\']url\(#([^)]+)\)', content_lower):
            if '<marker' not in content_lower:
                result['errors'].append(
                    "Detected marker-start/marker-end referencing a marker id, "
                    "but no <marker> element found in the file")

        # Text / fonts
        if '<textpath' in content_lower:
            result['errors'].append("Detected forbidden <textPath> element (path text is incompatible with PPT)")
        if '@font-face' in content_lower:
            result['errors'].append("Detected forbidden @font-face (use system font stack)")

        # Animation / interaction
        if re.search(r'<animate', content_lower):
            result['errors'].append("Detected forbidden SMIL animation element <animate*> (SVG animations are not exported)")
        if re.search(r'<set\b', content_lower):
            result['errors'].append("Detected forbidden SMIL animation element <set> (SVG animations are not exported)")
        if '<script' in content_lower:
            result['errors'].append("Detected forbidden <script> element (scripts and event handlers forbidden)")
        if re.search(r'\bon\w+\s*=', content):  # onclick, onload etc.
            result['errors'].append("Detected forbidden event attributes (e.g., onclick, onload)")

        # Other discouraged elements
        if '<iframe' in content_lower:
            result['errors'].append("Detected <iframe> element (should not appear in SVG)")
        if re.search(r'rgba\s*\(', content_lower):
            result['errors'].append("Detected forbidden rgba() color (use fill-opacity/stroke-opacity instead)")
        if re.search(r'<g[^>]*\sopacity\s*=', content_lower):
            result['errors'].append("Detected forbidden <g opacity> (set opacity on each child element individually)")
        if re.search(r'<image[^>]*\sopacity\s*=', content_lower):
            result['errors'].append("Detected forbidden <image opacity> (use overlay mask approach)")

    def _check_fonts(self, content: str, result: Dict):
        """Check font usage.

        PPTX stores a single `typeface` per run with no runtime fallback, so every
        stack must END with a cross-platform pre-installed family. See
        strategist.md §g "PPT-safe font discipline".
        """
        font_matches = re.findall(
            r'font-family[:\s]*["\']([^"\']+)["\']', content, re.IGNORECASE)

        if not font_matches:
            return

        result['info']['fonts'] = list(set(font_matches))

        # Pre-installed on Windows + macOS out of the box (plus their direct
        # FONT_FALLBACK_WIN mappings). A stack whose last concrete family is in
        # this set survives the PPTX round-trip on any viewer machine.
        ppt_safe_tail = {
            'microsoft yahei', 'simhei', 'simsun', 'kaiti', 'fangsong',
            'pingfang sc', 'heiti sc', 'songti sc', 'stsong',
            'arial', 'arial black', 'calibri', 'segoe ui', 'verdana',
            'helvetica', 'helvetica neue', 'tahoma', 'trebuchet ms',
            'times new roman', 'times', 'georgia', 'cambria', 'palatino',
            'consolas', 'courier new', 'menlo', 'monaco',
            'impact',
        }

        for font_family in font_matches:
            # Drop the generic CSS fallback (sans-serif / serif / monospace)
            # and inspect the last concrete family.
            parts = [p.strip().strip('"').strip("'").lower()
                     for p in font_family.split(',')]
            parts = [p for p in parts
                     if p and p not in ('sans-serif', 'serif', 'monospace',
                                        'cursive', 'fantasy', 'system-ui')]
            if not parts:
                continue
            tail = parts[-1]
            if tail not in ppt_safe_tail:
                result['warnings'].append(
                    f"Font stack does not end on a PPT-safe family "
                    f"(expected e.g. Microsoft YaHei / SimSun / Arial / "
                    f"Times New Roman / Consolas): {font_family}"
                )
                break

    def _check_dimensions(self, content: str, result: Dict):
        """Check width/height consistency with viewBox"""
        width_match = re.search(r'width="(\d+)"', content)
        height_match = re.search(r'height="(\d+)"', content)

        if width_match and height_match:
            width = width_match.group(1)
            height = height_match.group(1)
            result['info']['dimensions'] = f"{width}x{height}"

            # Check consistency with viewBox
            if 'viewbox' in result['info']:
                viewbox_parts = result['info']['viewbox'].split()
                if len(viewbox_parts) == 4:
                    vb_width, vb_height = viewbox_parts[2], viewbox_parts[3]
                    if width != vb_width or height != vb_height:
                        result['warnings'].append(
                            f"width/height ({width}x{height}) does not match viewBox "
                            f"({vb_width}x{vb_height})"
                        )

    def _check_text_elements(self, content: str, result: Dict):
        """Check text elements and wrapping methods"""
        # Count text and tspan elements
        text_count = content.count('<text')
        tspan_count = content.count('<tspan')

        result['info']['text_elements'] = text_count
        result['info']['tspan_elements'] = tspan_count

        # Check for overly long single-line text (may need wrapping)
        text_matches = re.findall(r'<text[^>]*>([^<]{100,})</text>', content)
        if text_matches:
            result['warnings'].append(
                f"Detected {len(text_matches)} potentially overly long single-line text(s) (consider using tspan for wrapping)"
            )

        self._check_visible_metadata_leaks(content, result)
        self._check_text_layout_heuristics(content, result)

    def _check_visible_metadata_leaks(self, content: str, result: Dict):
        leaked = []
        for line in self._all_visible_text_lines(content):
            if VISIBLE_METADATA_RE.search(line):
                leaked.append(line)
        if leaked:
            examples = ", ".join(self._short_text(item, limit=28) for item in leaked[:3])
            result['warnings'].append(
                f"Detected {len(leaked)} visible eval/internal metadata text item(s): {examples}"
            )

    def _check_text_layout_heuristics(self, content: str, result: Dict):
        """Warn on obvious text overlap and clipping using approximate boxes.

        This deliberately stays heuristic: it estimates text width from glyph
        counts and declared font-size. The goal is to catch blatant layout
        mistakes before export, not to replace screenshot review.
        """
        connector_container_issues = self._find_connector_container_intrusions(content)
        if connector_container_issues:
            result['warnings'].append(
                f"Detected {len(connector_container_issues)} connector arrow(s) intruding into card/container border safe zone"
            )

        shape_text_issues = self._find_shape_text_centering_issues(content)
        if shape_text_issues:
            examples = ", ".join(self._short_text(item['text']) for item in shape_text_issues[:4])
            result['warnings'].append(
                f"Detected {len(shape_text_issues)} possible shape text centering issue(s): {examples}"
            )

        component_spacing_issues = self._find_semantic_component_spacing_issues(content)
        if component_spacing_issues:
            examples = ", ".join(
                f"{self._semantic_shape_label(a)} ↔ {self._semantic_shape_label(b)}"
                for a, b in component_spacing_issues[:3]
            )
            result['warnings'].append(
                f"Detected {len(component_spacing_issues)} semantic component overlap/spacing issue(s): {examples}"
            )

        boxes = self._extract_text_boxes(content, result)
        if not boxes:
            return

        clipped = []
        viewbox = result.get('info', {}).get('viewbox', '')
        vb = self._parse_viewbox(viewbox)
        if vb:
            _, _, vb_w, vb_h = vb
            for box in boxes:
                if box['x1'] < -1 or box['y1'] < -1 or box['x2'] > vb_w + 1 or box['y2'] > vb_h + 1:
                    clipped.append(box)
            if clipped:
                examples = ", ".join(self._short_text(b['text']) for b in clipped[:3])
                result['warnings'].append(
                    f"Detected {len(clipped)} possible text box clipping/out-of-canvas issue(s): {examples}"
                )

        if len(boxes) > TEXT_COLLISION_MAX_ELEMENTS:
            result['warnings'].append(
                f"Skipped text overlap heuristic: {len(boxes)} text boxes exceeds safe O(n^2) limit"
            )
            return

        collisions = []
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                inter_w = min(a['x2'], b['x2']) - max(a['x1'], b['x1'])
                inter_h = min(a['y2'], b['y2']) - max(a['y1'], b['y1'])
                if inter_w <= 0 or inter_h <= 0:
                    continue
                inter_area = inter_w * inter_h
                smaller_area = min(a['area'], b['area'])
                if smaller_area <= 0:
                    continue
                if inter_area >= TEXT_COLLISION_MIN_AREA and inter_area / smaller_area >= TEXT_COLLISION_MIN_OVERLAP_RATIO:
                    collisions.append((a, b))

        if collisions:
            examples = "; ".join(
                f"{self._short_text(a['text'])} ↔ {self._short_text(b['text'])}"
                for a, b in collisions[:3]
            )
            result['warnings'].append(
                f"Detected {len(collisions)} possible text overlap/collision(s): {examples}"
            )

        container_overflows = self._find_text_container_overflows(content, boxes, result)
        if container_overflows:
            examples = ", ".join(self._short_text(b['text']) for b in container_overflows[:4])
            result['warnings'].append(
                f"Detected {len(container_overflows)} possible text container overflow(s): {examples}"
            )

        semantic_overflows = self._find_semantic_parent_overflows(content, boxes)
        if semantic_overflows:
            examples = ", ".join(self._short_text(item['text']) for item in semantic_overflows[:4])
            result['warnings'].append(
                f"Detected {len(semantic_overflows)} semantic parent overflow(s): {examples}"
            )

        occlusions = self._find_text_shape_occlusions(content, boxes, result)
        if occlusions:
            examples = ", ".join(self._short_text(b['text']) for b in occlusions[:4])
            result['warnings'].append(
                f"Detected {len(occlusions)} possible shape-over-text occlusion(s): {examples}"
            )

        connector_lane_issues = self._find_connector_text_lane_issues(content, boxes)
        if connector_lane_issues:
            examples = ", ".join(self._short_text(b['text']) for b in connector_lane_issues[:4])
            result['warnings'].append(
                f"Detected {len(connector_lane_issues)} connector arrow(s) sharing a text lane too closely: {examples}"
            )

    def _extract_text_boxes(self, content: str, result: Dict) -> List[Dict]:
        boxes = []
        for m in re.finditer(r'<text\b([^>]*)>(.*?)</text>', content, re.IGNORECASE | re.DOTALL):
            attrs = m.group(1)
            inner = m.group(2)
            transform = self._attr_value(attrs, 'transform') or ''
            if 'rotate' in transform:
                continue
            x = self._attr_float(attrs, 'x')
            y = self._attr_float(attrs, 'y')
            if x is None or y is None:
                continue
            font_size = self._attr_float(attrs, 'font-size') or 16.0
            lines = self._text_lines(inner)
            if not lines:
                continue
            font_weight = (self._attr_value(attrs, 'font-weight') or '').strip().lower()
            width = max(self._estimate_text_width(line, font_size, font_weight) for line in lines)
            height = max(font_size * 1.25 * len(lines), font_size)
            anchor = (self._attr_value(attrs, 'text-anchor') or 'start').strip()
            dominant_baseline = (self._attr_value(attrs, 'dominant-baseline') or '').strip().lower()
            x1 = x
            if anchor == 'middle':
                x1 = x - width / 2
            elif anchor == 'end':
                x1 = x - width
            y1 = y - height / 2 if dominant_baseline in {'middle', 'central'} else y - font_size
            boxes.append({
                'x1': x1,
                'y1': y1,
                'x2': x1 + width,
                'y2': y1 + height,
                'area': width * height,
                'text': " ".join(lines),
                'anchor_x': x,
                'anchor_y': y,
                'font_size': font_size,
                'font_weight': font_weight,
            })
        return boxes

    def _find_semantic_component_spacing_issues(self, content: str) -> List[Tuple[Dict, Dict]]:
        """Find sibling semantic boxes that overlap or leave no readable gap.

        This operates on inferred component semantics, not on color/coordinate
        special cases.  A label inside a card is compared with its sibling
        labels; a card, bridge, or wide status strip inside the same parent
        panel is compared with peer components in that panel.
        """
        shapes = [
            shape
            for shape in self._extract_container_boxes(content)
            if self._is_semantic_layout_box(shape)
            and not self._is_page_or_decorative_shape(shape)
        ]
        if len(shapes) < 2:
            return []

        groups: Dict[str, List[Dict]] = defaultdict(list)
        for shape in shapes:
            parent = self._nearest_containing_semantic_parent(shape, shapes)
            parent_id = parent.get('shape_id') if parent else '__root__'
            groups[parent_id].append(shape)

        issues: List[Tuple[Dict, Dict]] = []
        seen = set()
        for siblings in groups.values():
            if len(siblings) < 2:
                continue
            ordered = sorted(siblings, key=lambda item: (item['y1'], item['x1'], item['area']))
            for i, upper in enumerate(ordered):
                for lower in ordered[i + 1:]:
                    if self._horizontal_overlap_ratio(upper, lower) < SEMANTIC_COMPONENT_MIN_AXIS_OVERLAP:
                        continue
                    vertical_gap = lower['y1'] - upper['y2']
                    if vertical_gap >= SEMANTIC_COMPONENT_MIN_GAP:
                        continue
                    if vertical_gap < 0:
                        inter_w = min(upper['x2'], lower['x2']) - max(upper['x1'], lower['x1'])
                        inter_h = min(upper['y2'], lower['y2']) - max(upper['y1'], lower['y1'])
                        if inter_w <= 0 or inter_h <= 0:
                            continue
                        if inter_w * inter_h < SEMANTIC_COMPONENT_OVERLAP_MIN_AREA:
                            continue
                    key = tuple(sorted((upper.get('shape_id'), lower.get('shape_id'))))
                    if key in seen:
                        continue
                    seen.add(key)
                    issues.append((upper, lower))
        return issues

    def _find_text_container_overflows(self, content: str, boxes: List[Dict], result: Dict) -> List[Dict]:
        """Find text that appears to spill outside its nearest rect container.

        Many PPT-quality defects are not text-vs-text collisions, but text
        leaving the card/tag/table-cell that should contain it. Before
        finalize_svg.py converts rounded rects to paths, most generated
        containers are <rect>; use those as a conservative containment signal.
        """
        rects = self._extract_container_boxes(content)
        if not rects:
            return []

        vb = self._parse_viewbox(result.get('info', {}).get('viewbox', ''))
        max_area = None
        if vb:
            _, _, vb_w, vb_h = vb
            max_area = vb_w * vb_h * TEXT_CONTAINER_MAX_AREA_RATIO

        overflows = []
        for box in boxes:
            cx = (box['x1'] + box['x2']) / 2
            cy = (box['y1'] + box['y2']) / 2
            candidates = []
            for rect in rects:
                if max_area and rect['area'] > max_area:
                    continue
                if not (rect['x1'] <= cx <= rect['x2'] and rect['y1'] <= cy <= rect['y2']):
                    continue
                candidates.append(rect)
            if not candidates:
                continue
            containing = [rect for rect in candidates if self._box_fits_in_rect(box, rect)]
            if containing:
                continue
            overflows.append(box)
        return overflows

    def _find_semantic_parent_overflows(self, content: str, boxes: List[Dict]) -> List[Dict]:
        """Find child shapes/text that escape explicit component containers.

        The basic text-container pass checks the smallest enclosing rect, which
        is good for labels but misses a common PPT defect: a pill may fit its
        own shape while that pill hangs outside the parent card.  This pass
        treats explicit semantic components as parent boxes and verifies that
        contained child shapes and text stay inside their parent with a small
        safety margin.
        """
        shapes = self._extract_container_boxes(content)
        parents = [shape for shape in shapes if self._is_semantic_parent_container(shape)]
        if not parents:
            return []

        overflows: List[Dict] = []
        for box in boxes:
            parent = self._nearest_semantic_parent(box, parents)
            if not parent:
                continue
            slot = self._intermediate_text_slot_for(box, shapes, parent)
            if slot:
                if (
                    not self._box_fits_in_rect(slot, parent, SEMANTIC_CHILD_PADDING)
                    or not self._box_inside_rect_xy(
                        box,
                        slot,
                        INTERMEDIATE_SLOT_TEXT_X_INSET,
                        INTERMEDIATE_SLOT_TEXT_Y_INSET,
                    )
                ):
                    overflows.append({**box, 'parent': slot, 'text': box.get('text', 'text')})
                continue
            if not self._semantic_parent_text_requires_tight_fit(box, parent):
                continue
            if not self._box_inside_rect(box, parent, SEMANTIC_PARENT_PADDING):
                overflows.append({**box, 'parent': parent, 'text': box.get('text', 'text')})

        for child in shapes:
            if self._is_page_or_decorative_shape(child):
                continue
            parent = self._nearest_semantic_parent(child, parents, exclude=child, strict_child_size=True)
            if not parent:
                continue
            if not self._box_fits_in_rect(child, parent, SEMANTIC_CHILD_PADDING):
                overflows.append({
                    **child,
                    'parent': parent,
                    'text': self._semantic_shape_label(child),
                })
        return overflows

    def _intermediate_text_slot_for(self, box: Dict, shapes: List[Dict], parent: Dict) -> Dict | None:
        cx = (box['x1'] + box['x2']) / 2
        cy = (box['y1'] + box['y2']) / 2
        slots = []
        for shape in shapes:
            if shape.get('shape_id') == parent.get('shape_id') or shape['area'] >= parent['area']:
                continue
            if not (shape['x1'] <= cx <= shape['x2'] and shape['y1'] <= cy <= shape['y2']):
                continue
            if not self._is_intermediate_text_slot(shape):
                continue
            slots.append(shape)
        if not slots:
            return None
        return min(slots, key=lambda item: item['area'])

    @classmethod
    def _is_intermediate_text_slot(cls, shape: Dict) -> bool:
        role = (shape.get('role') or '').strip().lower()
        slot = (shape.get('slot') or '').strip().lower()
        if role in {'label', 'header', 'table-header', 'header-cell', 'table-cell', 'badge', 'tag', 'label-slot'}:
            return True
        if slot in {'label', 'header', 'cell', 'badge', 'tag'}:
            return True
        height = shape['y2'] - shape['y1']
        width = shape['x2'] - shape['x1']
        return height <= 54 and width >= 40 and cls._is_colored_label_fill(shape.get('fill') or '')

    @classmethod
    def _semantic_parent_text_requires_tight_fit(cls, box: Dict, parent: Dict) -> bool:
        role = (parent.get('role') or '').strip().lower()
        height = parent['y2'] - parent['y1']
        fill = (parent.get('fill') or '').strip()
        font_size = float(box.get('font_size') or 16.0)
        if role in {'bridge', 'label', 'header', 'table-header', 'header-cell', 'table-cell'}:
            return True
        if height <= 92 and cls._is_colored_label_fill(fill):
            return True
        if height <= 70:
            return True
        if font_size >= 24:
            return True
        return False

    @classmethod
    def _nearest_semantic_parent(
        cls,
        box: Dict,
        parents: List[Dict],
        exclude: Dict | None = None,
        strict_child_size: bool = False,
    ) -> Dict | None:
        cx = (box['x1'] + box['x2']) / 2
        cy = (box['y1'] + box['y2']) / 2
        candidates = []
        for parent in parents:
            if exclude is parent or parent.get('shape_id') == (exclude or {}).get('shape_id'):
                continue
            if parent['area'] <= box['area'] * 1.18:
                continue
            if strict_child_size:
                box_width = box['x2'] - box['x1']
                box_height = box['y2'] - box['y1']
                parent_width = parent['x2'] - parent['x1']
                parent_height = parent['y2'] - parent['y1']
                if box_width > parent_width * 1.18 or box_height > parent_height * 1.18:
                    continue
                if box_width > parent_width * 0.9 and box['y2'] > parent['y2'] + SEMANTIC_CHILD_PADDING:
                    continue
            if parent['x1'] <= cx <= parent['x2'] and parent['y1'] <= cy <= parent['y2']:
                candidates.append(parent)
        if not candidates:
            return None
        return min(candidates, key=lambda item: item['area'])

    @classmethod
    def _nearest_containing_semantic_parent(cls, box: Dict, shapes: List[Dict]) -> Dict | None:
        candidates = []
        for parent in shapes:
            if parent.get('shape_id') == box.get('shape_id'):
                continue
            if parent['area'] <= box['area'] * 1.18:
                continue
            if cls._box_fits_in_rect(box, parent, padding=1.0):
                candidates.append(parent)
        if not candidates:
            return None
        return min(candidates, key=lambda item: item['area'])

    @staticmethod
    def _is_semantic_parent_container(shape: Dict) -> bool:
        role = (shape.get('role') or '').strip().lower()
        slot = (shape.get('slot') or '').strip().lower()
        if role in {
            'content-card', 'bridge', 'process-step', 'metric-card', 'risk-quadrant',
            'risk-matrix', 'table', 'mapping-row', 'architecture-layer', 'layer-stack',
            'callout-content', 'section', 'panel',
        }:
            return True
        if slot in {'panel', 'layer', 'body-slot'}:
            return True
        return False

    @classmethod
    def _is_semantic_layout_box(cls, shape: Dict) -> bool:
        role = (shape.get('role') or '').strip().lower()
        slot = (shape.get('slot') or '').strip().lower()
        if cls._is_semantic_parent_container(shape):
            return True
        if role in {'label', 'header', 'table-header', 'header-cell', 'table-cell', 'badge', 'tag', 'label-slot'}:
            return True
        if slot in {'label', 'header', 'cell', 'badge', 'tag'}:
            return True
        return False

    @staticmethod
    def _is_page_or_decorative_shape(shape: Dict) -> bool:
        role = (shape.get('role') or '').strip().lower()
        return role in {'page-background', 'background', 'geometric-accent', 'decorative-accent', 'accent-bar'}

    @staticmethod
    def _semantic_shape_label(shape: Dict) -> str:
        role = (shape.get('role') or '').strip().lower()
        slot = (shape.get('slot') or '').strip().lower()
        kind = shape.get('kind') or 'shape'
        return f"{role or slot or kind} child"

    @staticmethod
    def _box_fits_in_rect(box: Dict, rect: Dict, padding: float = TEXT_CONTAINER_PADDING) -> bool:
        return (
            box['x1'] >= rect['x1'] - padding
            and box['y1'] >= rect['y1'] - padding
            and box['x2'] <= rect['x2'] + padding
            and box['y2'] <= rect['y2'] + padding
        )

    @staticmethod
    def _box_inside_rect(box: Dict, rect: Dict, padding: float = TEXT_CONTAINER_PADDING) -> bool:
        return (
            box['x1'] >= rect['x1'] + padding
            and box['y1'] >= rect['y1'] + padding
            and box['x2'] <= rect['x2'] - padding
            and box['y2'] <= rect['y2'] - padding
        )

    @staticmethod
    def _box_inside_rect_xy(box: Dict, rect: Dict, x_padding: float, y_padding: float) -> bool:
        return (
            box['x1'] >= rect['x1'] + x_padding
            and box['y1'] >= rect['y1'] + y_padding
            and box['x2'] <= rect['x2'] - x_padding
            and box['y2'] <= rect['y2'] - y_padding
        )

    def _extract_rect_boxes(self, content: str) -> List[Dict]:
        rects = []
        for m in re.finditer(r'<rect\b([^>]*)/?>', content, re.IGNORECASE):
            attrs = m.group(1)
            x = self._attr_float(attrs, 'x') or 0.0
            y = self._attr_float(attrs, 'y') or 0.0
            w = self._attr_float(attrs, 'width')
            h = self._attr_float(attrs, 'height')
            if w is None or h is None or w <= 0 or h <= 0:
                continue
            rects.append({
                'kind': 'rect',
                'shape_id': f"rect:{len(rects)}",
                'x1': x,
                'y1': y,
                'x2': x + w,
                'y2': y + h,
                'area': w * h,
                'fill': self._attr_value(attrs, 'fill') or '',
                'text_align': self._attr_value(attrs, 'data-text-align') or '',
                'role': self._attr_value(attrs, 'data-role') or '',
                'slot': self._attr_value(attrs, 'data-slot') or '',
            })
        return rects

    def _extract_circle_label_boxes(self, content: str) -> List[Dict]:
        boxes = []
        for m in re.finditer(r'<(circle|ellipse)\b([^>]*)/?>', content, re.IGNORECASE):
            tag = (m.group(1) or '').lower()
            attrs = m.group(2) or ''
            if self._shape_is_outline_only(attrs):
                continue
            box = self._shape_box(tag, attrs)
            if not box:
                continue
            width = box['x2'] - box['x1']
            height = box['y2'] - box['y1']
            if width > SHAPE_TEXT_LABEL_MAX_WIDTH or height > SHAPE_TEXT_LABEL_MAX_HEIGHT:
                continue
            box.update({'kind': tag, 'shape_id': f"{tag}:{len(boxes)}", 'fill': self._attr_value(attrs, 'fill') or ''})
            box.update({
                'kind': 'path',
                'shape_id': f"path:{len(boxes)}",
                'fill': self._attr_value(attrs, 'fill') or '',
                'text_align': self._attr_value(attrs, 'data-text-align') or '',
                'role': self._attr_value(attrs, 'data-role') or '',
                'slot': self._attr_value(attrs, 'data-slot') or '',
            })
            boxes.append(box)
        return boxes

    def _extract_container_boxes(self, content: str) -> List[Dict]:
        """Extract possible text containers from rects and finalized rect paths.

        finalize_svg.py converts rounded <rect> containers to <path> elements.
        If we only inspect <rect>, helper strips used to square off rounded
        headers can be mistaken for the actual text container and cause false
        overflow warnings. Path boxes are coarse but good enough for containment.
        """
        boxes = self._extract_rect_boxes(content)
        for m in re.finditer(r'<path\b([^>]*)/?>', content, re.IGNORECASE):
            attrs = m.group(1) or ''
            if self._shape_is_outline_only(attrs):
                continue
            d = self._attr_value(attrs, 'd')
            if not d:
                continue
            box = self._path_bbox(d)
            if not box or box['area'] < TEXT_CONTAINER_MIN_AREA:
                continue
            box.update({
                'kind': 'path',
                'shape_id': f"path:{len(boxes)}",
                'fill': self._attr_value(attrs, 'fill') or '',
                'text_align': self._attr_value(attrs, 'data-text-align') or '',
                'role': self._attr_value(attrs, 'data-role') or '',
                'slot': self._attr_value(attrs, 'data-slot') or '',
            })
            boxes.append(box)
        return boxes

    def _find_shape_text_centering_issues(self, content: str) -> List[Dict]:
        """Warn when semantic label/header/cell slots are not centered."""
        return _semantic_alignment_issues(content) + _semantic_component_emphasis_alignment_issues(content)

    def _smallest_label_shape_containing(self, shapes: List[Dict], x: float, y: float) -> Dict | None:
        candidates = []
        for shape in shapes:
            if not (shape['x1'] <= x <= shape['x2'] and shape['y1'] <= y <= shape['y2']):
                continue
            candidates.append(shape)
        if not candidates:
            return None
        return min(candidates, key=lambda item: item['area'])

    @staticmethod
    def _shape_is_stack_card(shape: Dict) -> bool:
        return (shape['y2'] - shape['y1']) > SHAPE_TEXT_STRIP_MAX_HEIGHT

    @classmethod
    def _shape_or_text_declares_left_aligned_exception(cls, shape: Dict, text_attrs: str) -> bool:
        values = [
            (shape.get('text_align') or '').strip().lower(),
            (shape.get('role') or '').strip().lower(),
            (cls._attr_value(text_attrs, 'data-text-align') or '').strip().lower(),
            (cls._attr_value(text_attrs, 'data-role') or '').strip().lower(),
        ]
        return any(value in {'left', 'left-aligned', 'content', 'callout-content'} for value in values)

    @classmethod
    def _rect_requires_centered_label(cls, rect: Dict) -> bool:
        width = rect['x2'] - rect['x1']
        height = rect['y2'] - rect['y1']
        if width <= 0 or height <= 0 or height > SHAPE_TEXT_LABEL_MAX_HEIGHT:
            return False
        fill = (rect.get('fill') or '').strip()
        return cls._is_colored_label_fill(fill)

    @staticmethod
    def _is_colored_label_fill(fill: str) -> bool:
        if not HEX_VALUE_RE.fullmatch(fill):
            return False
        raw = fill.lstrip('#')
        if len(raw) == 3:
            raw = ''.join(ch * 2 for ch in raw)
        if len(raw) < 6:
            return False
        r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
        chroma = max(r, g, b) - min(r, g, b)
        saturation = chroma / max(max(r, g, b), 1)
        # White/off-white and neutral gray cards are usually content containers
        # with intentionally padded labels. Colored label blocks, including the
        # pale Alauda tints (#D8EFF9, #F0FDF4, #FFF7D6, #CCFBF1), default to
        # centered text unless the layout creates an explicit left-aligned text
        # area outside the colored primitive.
        if r >= 248 and g >= 248 and b >= 248:
            return False
        if chroma < 12 and saturation < 0.06:
            return False
        return True

    @staticmethod
    def _path_bbox(d: str) -> Dict | None:
        tokens = re.findall(r'[MmLlHhVvAaZz]|-?\d+(?:\.\d+)?', d)
        index = 0
        cmd = None
        x = y = 0.0
        points = []

        def num() -> float:
            nonlocal index
            value = float(tokens[index])
            index += 1
            return value

        while index < len(tokens):
            if re.fullmatch(r'[A-Za-z]', tokens[index]):
                cmd = tokens[index]
                index += 1
                if cmd in {'Z', 'z'}:
                    continue
            try:
                if cmd in {'M', 'm', 'L', 'l'}:
                    if index + 1 >= len(tokens):
                        break
                    nx, ny = num(), num()
                    if cmd.islower():
                        x += nx
                        y += ny
                    else:
                        x, y = nx, ny
                    points.append((x, y))
                    if cmd == 'M':
                        cmd = 'L'
                    elif cmd == 'm':
                        cmd = 'l'
                elif cmd in {'H', 'h'}:
                    nx = num()
                    x = x + nx if cmd.islower() else nx
                    points.append((x, y))
                elif cmd in {'V', 'v'}:
                    ny = num()
                    y = y + ny if cmd.islower() else ny
                    points.append((x, y))
                elif cmd in {'A', 'a'}:
                    if index + 6 >= len(tokens):
                        break
                    _rx, _ry, _rot, _large, _sweep, nx, ny = num(), num(), num(), num(), num(), num(), num()
                    if cmd.islower():
                        x += nx
                        y += ny
                    else:
                        x, y = nx, ny
                    points.append((x, y))
                else:
                    index += 1
            except (IndexError, ValueError):
                break

        if not points:
            return None
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        if width <= 0 or height <= 0:
            return None
        return {'x1': min(xs), 'y1': min(ys), 'x2': max(xs), 'y2': max(ys), 'area': width * height}

    def _find_text_shape_occlusions(self, content: str, boxes: List[Dict], result: Dict) -> List[Dict]:
        """Warn when later non-text shapes appear to cover text boxes.

        SVG paint order matters. If a filled polygon/rect/circle appears after
        a text element and its bounding box substantially overlaps that text,
        the shape can visually cover the text even when text-vs-text checks
        pass. Keep this conservative and ignore outline-only shapes.
        """
        elements = self._extract_paint_order_elements(content)
        if not elements:
            return []
        text_elements = [e for e in elements if e['kind'] == 'text']
        shape_elements = [e for e in elements if e['kind'] == 'shape']
        if not text_elements or not shape_elements:
            return []
        occluded = []
        for text_el in text_elements:
            box = text_el['box']
            for shape_el in shape_elements:
                if shape_el['index'] <= text_el['index']:
                    continue
                shape = shape_el['box']
                padded = self._padded_box(box, TEXT_OCCLUSION_PADDING)
                inter_w = min(padded['x2'], shape['x2']) - max(padded['x1'], shape['x1'])
                inter_h = min(padded['y2'], shape['y2']) - max(padded['y1'], shape['y1'])
                if inter_w <= 0 or inter_h <= 0:
                    continue
                inter_area = inter_w * inter_h
                if inter_area >= TEXT_OCCLUSION_MIN_AREA and inter_area / box['area'] >= TEXT_OCCLUSION_MIN_RATIO:
                    occluded.append(box)
                    break
        return occluded

    def _find_connector_text_lane_issues(self, content: str, boxes: List[Dict]) -> List[Dict]:
        """Warn when horizontal connector arrows run in the same visual lane as text.

        Some presales diagrams look wrong even without literal overlap: an
        arrow can sit directly beside a heading or row label, making the visual
        read as if the connector belongs to the text. Detect horizontal arrow
        polygons and require a clear lane around nearby text at the same y band.
        """
        arrows = self._extract_horizontal_arrow_boxes(content)
        if not arrows or not boxes:
            return []

        issues = []
        seen_texts = set()
        for arrow in arrows:
            arrow_h = max(arrow['y2'] - arrow['y1'], 1.0)
            for box in boxes:
                inter_h = min(arrow['y2'], box['y2']) - max(arrow['y1'], box['y1'])
                if inter_h <= 0 or inter_h / min(arrow_h, max(box['y2'] - box['y1'], 1.0)) < CONNECTOR_TEXT_LANE_MIN_Y_OVERLAP:
                    continue
                if box['x2'] < arrow['x1']:
                    gap = arrow['x1'] - box['x2']
                elif arrow['x2'] < box['x1']:
                    gap = box['x1'] - arrow['x2']
                else:
                    gap = 0.0
                if gap <= CONNECTOR_TEXT_LANE_MIN_GAP:
                    text_key = (round(box['x1'], 1), round(box['y1'], 1), box['text'])
                    if text_key not in seen_texts:
                        issues.append(box)
                        seen_texts.add(text_key)
                    break
        return issues

    def _find_connector_container_intrusions(self, content: str) -> List[Dict]:
        """Warn when connector arrows intrude into card/container borders.

        Connectors should live in gutters between visual groups. A small gap is
        enough, but the arrow head or shaft should not enter the filled card
        body or sit on top of its border.
        """
        arrows = self._extract_horizontal_arrow_boxes(content)
        if not arrows:
            return []
        containers = self._extract_container_boxes(content)
        if not containers:
            return []

        issues = []
        for arrow in arrows:
            # Ignore tiny text-cell containers and page-sized background boxes.
            for container in containers:
                cw = container['x2'] - container['x1']
                ch = container['y2'] - container['y1']
                if cw < 120 or ch < 80:
                    continue
                if cw > 1100 and ch > 560:
                    continue
                safe = self._padded_box(container, CONNECTOR_CONTAINER_CLEARANCE)
                inter_w = min(arrow['x2'], safe['x2']) - max(arrow['x1'], safe['x1'])
                inter_h = min(arrow['y2'], safe['y2']) - max(arrow['y1'], safe['y1'])
                if inter_w <= 0 or inter_h <= 0:
                    continue
                if inter_w * inter_h >= CONNECTOR_CONTAINER_INTRUSION_MIN_AREA:
                    issues.append(arrow)
                    break
        return issues

    def _extract_horizontal_arrow_boxes(self, content: str) -> List[Dict]:
        arrows = []
        for m in re.finditer(r'<polygon\b([^>]*)/?>', content, re.IGNORECASE):
            attrs = m.group(1) or ''
            if self._shape_is_outline_only(attrs):
                continue
            raw = self._attr_value(attrs, 'points')
            if not raw:
                continue
            nums = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', raw)]
            if len(nums) < 12:
                continue
            xs = nums[0::2]
            ys = nums[1::2]
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            if height <= 0:
                continue
            if width < CONNECTOR_ARROW_MIN_WIDTH or width / height < CONNECTOR_ARROW_MIN_ASPECT:
                continue
            # Horizontal connector arrows usually have a pointed tip and a
            # rectangular shaft, so one x extremum appears fewer times than the
            # shaft/notch x coordinates. This avoids treating ordinary panels as arrows.
            min_x_count = sum(1 for x in xs if abs(x - min(xs)) < 0.1)
            max_x_count = sum(1 for x in xs if abs(x - max(xs)) < 0.1)
            if min(min_x_count, max_x_count) > 2:
                continue
            arrows.append({'x1': min(xs), 'y1': min(ys), 'x2': max(xs), 'y2': max(ys), 'area': width * height})
        return arrows

    @staticmethod
    def _padded_box(box: Dict, padding: float) -> Dict:
        return {
            **box,
            'x1': box['x1'] - padding,
            'y1': box['y1'] - padding,
            'x2': box['x2'] + padding,
            'y2': box['y2'] + padding,
        }

    @staticmethod
    def _horizontal_overlap_ratio(a: Dict, b: Dict) -> float:
        inter_w = min(a['x2'], b['x2']) - max(a['x1'], b['x1'])
        if inter_w <= 0:
            return 0.0
        return inter_w / max(min(a['x2'] - a['x1'], b['x2'] - b['x1']), 1.0)

    def _extract_paint_order_elements(self, content: str) -> List[Dict]:
        raw_elements = []
        text_pattern = re.compile(r'<text\b(?P<attrs>[^>]*)>(?P<inner>.*?)</text>', re.IGNORECASE | re.DOTALL)
        shape_pattern = re.compile(
            r'<(?P<tag>rect|polygon|circle|ellipse)\b(?P<attrs>[^>]*?)(?:/>|></(?P=tag)>)',
            re.IGNORECASE | re.DOTALL,
        )

        for m in text_pattern.finditer(content):
            box = self._text_box_from_attrs(m.group('attrs') or '', m.group('inner') or '')
            if box:
                raw_elements.append({'kind': 'text', 'pos': m.start(), 'box': box})

        for m in shape_pattern.finditer(content):
            attrs = m.group('attrs') or ''
            if self._shape_is_outline_only(attrs):
                continue
            box = self._shape_box((m.group('tag') or '').lower(), attrs)
            if box:
                raw_elements.append({'kind': 'shape', 'pos': m.start(), 'box': box})

        raw_elements.sort(key=lambda e: e['pos'])
        return [
            {'kind': item['kind'], 'index': index, 'box': item['box']}
            for index, item in enumerate(raw_elements)
        ]

    def _text_box_from_attrs(self, attrs: str, inner: str) -> Dict | None:
        transform = self._attr_value(attrs, 'transform') or ''
        if 'rotate' in transform:
            return None
        x = self._attr_float(attrs, 'x')
        y = self._attr_float(attrs, 'y')
        if x is None or y is None:
            return None
        font_size = self._attr_float(attrs, 'font-size') or 16.0
        lines = self._text_lines(inner)
        if not lines:
            return None
        font_weight = (self._attr_value(attrs, 'font-weight') or '').strip().lower()
        width = max(self._estimate_text_width(line, font_size, font_weight) for line in lines)
        height = max(font_size * 1.25 * len(lines), font_size)
        anchor = (self._attr_value(attrs, 'text-anchor') or 'start').strip()
        dominant_baseline = (self._attr_value(attrs, 'dominant-baseline') or '').strip().lower()
        x1 = x
        if anchor == 'middle':
            x1 = x - width / 2
        elif anchor == 'end':
            x1 = x - width
        y1 = y - height / 2 if dominant_baseline in {'middle', 'central'} else y - font_size
        return {
            'x1': x1,
            'y1': y1,
            'x2': x1 + width,
            'y2': y1 + height,
            'area': width * height,
            'text': " ".join(lines),
        }

    def _shape_box(self, tag: str, attrs: str) -> Dict | None:
        if tag == 'rect':
            x = self._attr_float(attrs, 'x') or 0.0
            y = self._attr_float(attrs, 'y') or 0.0
            w = self._attr_float(attrs, 'width')
            h = self._attr_float(attrs, 'height')
            if w is None or h is None or w <= 0 or h <= 0:
                return None
            return {'x1': x, 'y1': y, 'x2': x + w, 'y2': y + h, 'area': w * h}
        if tag == 'polygon':
            raw = self._attr_value(attrs, 'points')
            if not raw:
                return None
            nums = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', raw)]
            if len(nums) < 4:
                return None
            xs = nums[0::2]
            ys = nums[1::2]
            area = max(max(xs) - min(xs), 0) * max(max(ys) - min(ys), 0)
            return {'x1': min(xs), 'y1': min(ys), 'x2': max(xs), 'y2': max(ys), 'area': area}
        if tag == 'circle':
            cx = self._attr_float(attrs, 'cx')
            cy = self._attr_float(attrs, 'cy')
            r = self._attr_float(attrs, 'r')
            if cx is None or cy is None or r is None:
                return None
            return {'x1': cx - r, 'y1': cy - r, 'x2': cx + r, 'y2': cy + r, 'area': (2 * r) ** 2}
        if tag == 'ellipse':
            cx = self._attr_float(attrs, 'cx')
            cy = self._attr_float(attrs, 'cy')
            rx = self._attr_float(attrs, 'rx')
            ry = self._attr_float(attrs, 'ry')
            if cx is None or cy is None or rx is None or ry is None:
                return None
            return {'x1': cx - rx, 'y1': cy - ry, 'x2': cx + rx, 'y2': cy + ry, 'area': 4 * rx * ry}
        return None

    @classmethod
    def _shape_is_outline_only(cls, attrs: str) -> bool:
        fill = (cls._attr_value(attrs, 'fill') or '').strip().lower()
        return fill == 'none'

    @staticmethod
    def _attr_value(attrs: str, name: str) -> str | None:
        m = re.search(rf'\b{name}\s*=\s*(["\'])(.*?)\1', attrs)
        return m.group(2) if m else None

    @classmethod
    def _attr_float(cls, attrs: str, name: str) -> float | None:
        raw = cls._attr_value(attrs, name)
        if raw is None:
            return None
        m = re.match(r'\s*(-?\d+(?:\.\d+)?)', raw)
        if not m:
            return None
        return float(m.group(1))

    @staticmethod
    def _text_lines(inner: str) -> List[str]:
        tspan_matches = re.findall(r'<tspan\b[^>]*>(.*?)</tspan>', inner, re.IGNORECASE | re.DOTALL)
        raw_lines = tspan_matches if tspan_matches else [inner]
        lines = []
        for raw in raw_lines:
            text = re.sub(r'<[^>]+>', '', raw)
            text = html.unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                lines.append(text)
        return lines

    @classmethod
    def _all_visible_text_lines(cls, content: str) -> List[str]:
        lines = []
        for m in re.finditer(r'<text\b[^>]*>(.*?)</text>', content, re.IGNORECASE | re.DOTALL):
            lines.extend(cls._text_lines(m.group(1) or ''))
        return lines

    @staticmethod
    def _estimate_text_width(text: str, font_size: float, font_weight: str | float | int | None = None) -> float:
        return _semantic_estimate_text_width(text, font_size, font_weight)

    @staticmethod
    def _parse_viewbox(value: str) -> Tuple[float, float, float, float] | None:
        parts = value.split()
        if len(parts) != 4:
            return None
        try:
            return tuple(float(p) for p in parts)  # type: ignore[return-value]
        except ValueError:
            return None

    @staticmethod
    def _short_text(text: str, limit: int = 18) -> str:
        text = text.strip()
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def _check_viewbox_overflow(self, content: str, result: Dict):
        """Detect shapes extending past the viewBox boundary.

        SVG viewBox clips in browsers, but PPTX has no such clipping — shapes
        that extend past the canvas become visible as protruding elements.
        """
        vb_str = result.get('info', {}).get('viewbox', '')
        vb = self._parse_viewbox(vb_str)
        if not vb:
            return
        vb_x, vb_y, vb_w, vb_h = vb
        tol = 2.0
        overflows: List[Dict] = []

        for m in re.finditer(r'<circle\b([^>]*)/?>', content):
            attrs = m.group(1)
            cx = self._attr_float(attrs, 'cx') or 0
            cy = self._attr_float(attrs, 'cy') or 0
            r = self._attr_float(attrs, 'r') or 0
            if (cx + r > vb_x + vb_w + tol or cy + r > vb_y + vb_h + tol
                    or cx - r < vb_x - tol or cy - r < vb_y - tol):
                overflows.append({'tag': 'circle', 'overflow': max(cx + r - vb_w, cy + r - vb_h, vb_x - (cx - r), vb_y - (cy - r))})

        for m in re.finditer(r'<ellipse\b([^>]*)/?>', content):
            attrs = m.group(1)
            cx = self._attr_float(attrs, 'cx') or 0
            cy = self._attr_float(attrs, 'cy') or 0
            rx = self._attr_float(attrs, 'rx') or 0
            ry = self._attr_float(attrs, 'ry') or 0
            if (cx + rx > vb_x + vb_w + tol or cy + ry > vb_y + vb_h + tol
                    or cx - rx < vb_x - tol or cy - ry < vb_y - tol):
                overflows.append({'tag': 'ellipse', 'overflow': max(cx + rx - vb_w, cy + ry - vb_h)})

        for m in re.finditer(r'<rect\b([^>]*)/?>', content):
            attrs = m.group(1)
            x = self._attr_float(attrs, 'x') or 0
            y = self._attr_float(attrs, 'y') or 0
            w = self._attr_float(attrs, 'width') or 0
            h = self._attr_float(attrs, 'height') or 0
            if w < 10 or h < 10:
                continue
            if (x + w > vb_x + vb_w + tol or y + h > vb_y + vb_h + tol
                    or x < vb_x - tol or y < vb_y - tol):
                role_m = re.search(r'data-role="([^"]*)"', attrs)
                role = role_m.group(1) if role_m else 'none'
                overflows.append({'tag': 'rect', 'overflow': max(x + w - vb_w, y + h - vb_h), 'role': role})

        if overflows:
            result['warnings'].append(
                f"Detected {len(overflows)} shape(s) extending past viewBox boundary "
                f"(will protrude in PPTX — SVG viewBox clipping does not survive conversion)"
            )

    def _check_footer_zone_intrusion(self, content: str, result: Dict):
        """Detect content components that extend into the footer zone (y >= 682 on 720px canvas)."""
        vb_str = result.get('info', {}).get('viewbox', '')
        vb = self._parse_viewbox(vb_str)
        if not vb:
            return
        _vb_x, _vb_y, _vb_w, vb_h = vb
        footer_y = vb_h - 38
        intrusions: List[str] = []
        content_roles = {
            'content-card', 'callout-content', 'panel-card', 'metric-card',
            'process-step', 'bridge', 'risk-strip', 'table', 'mapping-row',
            'architecture-layer', 'layer-stack', 'section', 'chart-frame',
            'kpi-card', 'risk-quadrant', 'risk-matrix',
        }
        for m in re.finditer(r'<rect\b([^>]*)/?>', content):
            attrs = m.group(1)
            y = self._attr_float(attrs, 'y') or 0
            w = self._attr_float(attrs, 'width') or 0
            h = self._attr_float(attrs, 'height') or 0
            if h < 20:
                continue
            if w >= 1000 and h >= 600:
                continue
            bottom = y + h
            if bottom <= footer_y:
                continue
            role_m = re.search(r'data-role="([^"]*)"', attrs)
            role = role_m.group(1) if role_m else ''
            bg_roles = {'page-background', 'background', 'accent-background'}
            if role in bg_roles:
                continue
            if role in content_roles or (not role and h > 40):
                intrusions.append(f'{role or "rect"} y={y:.0f} h={h:.0f} bottom={bottom:.0f}')
        if intrusions:
            result['warnings'].append(
                f"Content component(s) intrude into footer zone (y>={footer_y:.0f}): "
                + '; '.join(intrusions[:3])
            )

    def _check_content_block_fit(self, content: str, result: Dict):
        """Detect content blocks with excessive empty space below their text."""
        content_roles = {
            'content-card', 'callout-content', 'panel-card', 'metric-card',
            'kpi-card',
        }
        loose_blocks: List[str] = []
        for m in re.finditer(r'<rect\b([^>]*)/?>', content):
            attrs = m.group(1)
            role_m = re.search(r'data-role="([^"]*)"', attrs)
            if not role_m or role_m.group(1) not in content_roles:
                continue
            role = role_m.group(1)
            x = self._attr_float(attrs, 'x') or 0
            y = self._attr_float(attrs, 'y') or 0
            w = self._attr_float(attrs, 'width') or 0
            h = self._attr_float(attrs, 'height') or 0
            if h < 60 or w < 60:
                continue
            bottom = y + h
            last_text_y = 0.0
            for tm in re.finditer(r'<text\b([^>]*)>', content):
                tattrs = tm.group(1)
                tx = self._attr_float(tattrs, 'x') or 0
                ty = self._attr_float(tattrs, 'y') or 0
                fs = self._attr_float(tattrs, 'font-size') or 14
                if not (x - 2 <= tx <= x + w + 2 and y - 2 <= ty <= bottom + 2):
                    continue
                slot_m = re.search(r'data-slot="([^"]*)"', tattrs)
                if slot_m and slot_m.group(1) == 'footer':
                    continue
                last_text_y = max(last_text_y, ty + fs)
            if last_text_y > 0:
                empty = bottom - last_text_y
                if empty > 60 and empty / h > 0.3:
                    loose_blocks.append(f'{role} y={y:.0f} h={h:.0f} empty={empty:.0f}px ({empty/h:.0%})')
        if loose_blocks:
            result['warnings'].append(
                'Content block(s) with excessive empty space below text (card height should fit content): '
                + '; '.join(loose_blocks[:3])
            )

    def _check_image_references(self, content: str, svg_path: Path, result: Dict):
        """Check image file existence and resolution vs display size."""
        # Find all <image ...> elements (capture the full tag)
        img_tag_pattern = re.compile(r'<image\b([^>]*)/?>', re.IGNORECASE)

        svg_dir = svg_path.parent
        checked = set()

        for tag_match in img_tag_pattern.finditer(content):
            attrs = tag_match.group(1)

            # Extract href (prefer href over xlink:href)
            href_match = (
                re.search(r'\bhref="(?!data:)([^"]+)"', attrs) or
                re.search(r'\bxlink:href="(?!data:)([^"]+)"', attrs)
            )
            if not href_match:
                continue

            href = href_match.group(1)
            if href in checked:
                continue
            checked.add(href)

            # Resolve path relative to SVG file directory
            img_path = (svg_dir / href).resolve()

            if not img_path.exists():
                result['errors'].append(
                    f"Image file not found: {href} (resolved to {img_path})")
                continue

            # Check resolution vs display size
            w_match = re.search(r'\bwidth="([^"]+)"', attrs)
            h_match = re.search(r'\bheight="([^"]+)"', attrs)
            display_w_str = w_match.group(1) if w_match else None
            display_h_str = h_match.group(1) if h_match else None
            if not display_w_str or not display_h_str:
                continue

            try:
                display_w = float(display_w_str)
                display_h = float(display_h_str)
            except (ValueError, TypeError):
                continue

            try:
                from PIL import Image as PILImage
                with PILImage.open(img_path) as img:
                    actual_w, actual_h = img.size

                if actual_w < display_w or actual_h < display_h:
                    result['warnings'].append(
                        f"Image {href} is {actual_w}x{actual_h} but displayed at "
                        f"{int(display_w)}x{int(display_h)} — may appear blurry")
                elif actual_w > display_w * 4 and actual_h > display_h * 4:
                    result['warnings'].append(
                        f"Image {href} is {actual_w}x{actual_h} but displayed at "
                        f"{int(display_w)}x{int(display_h)} — consider downsizing "
                        f"to reduce file size")
            except ImportError:
                pass  # PIL not available, skip resolution check
            except Exception:
                pass  # Image unreadable, skip resolution check

    def _get_spec_lock(self, svg_path: Path):
        """Locate and parse spec_lock.md near the SVG. Returns dict or None.

        Looks in svg_path.parent and svg_path.parent.parent (covers the two
        common layouts: SVG directly under <project>/ or under
        <project>/svg_output/). Results are cached per lock path.
        """
        if _parse_spec_lock is None:
            return None
        for candidate in (svg_path.parent / 'spec_lock.md',
                          svg_path.parent.parent / 'spec_lock.md'):
            if candidate in self._lock_cache:
                return self._lock_cache[candidate]
            if candidate.exists():
                try:
                    data = _parse_spec_lock(candidate)
                except Exception:
                    data = None
                self._lock_cache[candidate] = data
                if data is not None:
                    self._lock_seen = True
                return data
        return None

    def _check_spec_lock_drift(self, content: str, svg_path: Path, result: Dict):
        """Detect values used in the SVG that fall outside spec_lock.md.

        Covers colors (fill / stroke / stop-color), font-family, font-size,
        and icon placeholders / embedded icon comments.
        Emits per-file warnings summarising the drift counts; exact drifting
        values are accumulated in self._drift_summary for the end-of-run
        aggregation. When spec_lock.md is missing, silently skip (consistent
        with executor-base.md §2.1's 'missing lock → warn and proceed' policy).
        """
        lock = self._get_spec_lock(svg_path)
        if lock is None:
            return

        # Build allow-sets from the lock
        allowed_colors = set()
        for v in lock.get('colors', {}).values():
            if HEX_VALUE_RE.fullmatch(v):
                allowed_colors.add(v.upper())

        typo = lock.get('typography', {})
        # Font families: default `font_family` plus any per-role `*_family`
        # override (title_family / body_family / emphasis_family / code_family,
        # per spec_lock_reference.md). Any of these is a legitimate declared
        # value; an SVG that uses any one of them is not drifting.
        allowed_fonts = set()
        if typo:
            default_font = typo.get('font_family', '').strip()
            if default_font:
                allowed_fonts.add(default_font)
            for k, v in typo.items():
                if k == 'font_family' or not k.endswith('_family'):
                    continue
                v_clean = v.strip()
                # Skip placeholder text like "same as body (omit if identical)"
                if not v_clean or v_clean.lower().startswith('same as'):
                    continue
                allowed_fonts.add(v_clean)

        # Sizes: declared slots are anchors; body is the ramp baseline.
        allowed_sizes = set()
        body_px = None
        for k, v in typo.items():
            if k == 'font_family' or k.endswith('_family'):
                continue
            allowed_sizes.add(self._normalize_size(v))
            if k == 'body':
                try:
                    body_px = float(self._normalize_size(v))
                except (ValueError, TypeError):
                    body_px = None

        # Icons: `icons` is the canonical lock; `visual_system` may mirror a
        # larger template inventory. Accept either so finalized SVGs generated
        # from a visual-system-aware spec do not false-positive when
        # `icons.inventory` was intentionally kept narrower for a page subset.
        allowed_icon_library = lock.get('icons', {}).get('library', '').strip()
        allowed_icons = set()
        for section_name in ('icons', 'visual_system'):
            inventory = lock.get(section_name, {}).get('inventory') or lock.get(section_name, {}).get('icon_inventory')
            if not inventory:
                continue
            for item in re.split(r'\s*,\s*', inventory):
                icon = item.strip()
                if icon:
                    allowed_icons.add(icon)

        # Scan SVG for used values
        color_drifts = set()
        for attr in ('fill', 'stroke', 'stop-color'):
            pattern = re.compile(rf'\b{attr}\s*=\s*["\'](#[0-9A-Fa-f]{{3,8}})["\']')
            for m in pattern.finditer(content):
                val = m.group(1).upper()
                if val not in allowed_colors:
                    color_drifts.add(val)

        font_drifts = set()
        for m in re.finditer(r'font-family\s*=\s*["\']([^"\']+)["\']', content):
            val = m.group(1).strip()
            if allowed_fonts and val not in allowed_fonts:
                font_drifts.add(val)

        size_drifts = set()
        for m in re.finditer(r'font-size\s*=\s*["\']([^"\']+)["\']', content):
            val = self._normalize_size(m.group(1))
            if not allowed_sizes or val in allowed_sizes:
                continue
            # Intermediate values are allowed when they sit inside the ramp
            # envelope (ratio to body within [RAMP_MIN_RATIO, RAMP_MAX_RATIO]).
            if body_px and body_px > 0:
                try:
                    ratio = float(val) / body_px
                    if RAMP_MIN_RATIO <= ratio <= RAMP_MAX_RATIO:
                        continue
                except ValueError:
                    pass
            size_drifts.add(val)

        icon_drifts = set()
        icon_refs = set()
        for m in re.finditer(r'data-icon\s*=\s*["\']([^"\']+)["\']', content):
            icon_refs.add(m.group(1).strip())
        # finalized SVGs keep `<!-- icon: library/name -->` comments after
        # `finalize_svg.py` embeds the placeholder, so drift remains auditable.
        for m in re.finditer(r'<!--\s*icon:\s*([^>]+?)\s*-->', content):
            icon_refs.add(m.group(1).strip())
        for ref in icon_refs:
            if not ref:
                continue
            if '/' in ref:
                lib, name = ref.split('/', 1)
            else:
                lib, name = 'chunk', ref
            if allowed_icon_library and lib != allowed_icon_library:
                icon_drifts.add(f"{lib}/{name}")
                continue
            if allowed_icons and name not in allowed_icons:
                icon_drifts.add(f"{lib}/{name}")

        # Record in run-wide aggregation
        fname = svg_path.name
        for v in color_drifts:
            self._drift_summary['colors'][v].add(fname)
        for v in font_drifts:
            self._drift_summary['fonts'][v].add(fname)
        for v in size_drifts:
            self._drift_summary['sizes'][v].add(fname)
        for v in icon_drifts:
            self._drift_summary['icons'][v].add(fname)

        # Per-file warning (one condensed line; details live in summary)
        parts = []
        if color_drifts:
            parts.append(f"{len(color_drifts)} color(s)")
        if font_drifts:
            parts.append(f"{len(font_drifts)} font-family value(s)")
        if size_drifts:
            parts.append(f"{len(size_drifts)} font-size value(s)")
        if icon_drifts:
            parts.append(f"{len(icon_drifts)} icon(s)")
        if parts:
            result['warnings'].append(
                f"spec_lock drift: {', '.join(parts)} not in spec_lock.md "
                "(see drift summary for details)"
            )

    @staticmethod
    def _normalize_size(value: str) -> str:
        """Normalize a font-size value for comparison: lowercase, strip spaces,
        strip trailing 'px'. Other units (em / rem / %) are kept as-is so that
        e.g. '1.5em' vs '24' stay distinct."""
        v = value.strip().lower()
        if v.endswith('px'):
            v = v[:-2].strip()
        return v

    def _categorize_issue(self, error_msg: str) -> str:
        """Categorize issue type"""
        if 'viewBox' in error_msg:
            return 'viewBox issues'
        elif 'foreignObject' in error_msg:
            return 'foreignObject'
        elif 'font' in error_msg.lower():
            return 'Font issues'
        else:
            return 'Other'

    def check_directory(self, directory: str, expected_format: str = None, lint_only: bool = False) -> List[Dict]:
        """
        Check all SVG files in a directory

        Args:
            directory: Directory path
            expected_format: Expected canvas format
            lint_only: If True, run Step 7.0 pre-flight subset (see check_file docstring)

        Returns:
            List of check results
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"[ERROR] Directory does not exist: {directory}")
            return []

        # Find all SVG files
        if dir_path.is_file():
            svg_files = [dir_path]
        else:
            svg_output = dir_path / \
                'svg_output' if (
                    dir_path / 'svg_output').exists() else dir_path
            svg_files = sorted(svg_output.glob('*.svg'))

        if not svg_files:
            print(f"[WARN] No SVG files found")
            return []

        mode_label = "lint (pre-flight 3-dim)" if lint_only else "full (7-dim)"
        print(f"\n[SCAN] Checking {len(svg_files)} SVG file(s) in {mode_label} mode...\n")

        for svg_file in svg_files:
            result = self.check_file(str(svg_file), expected_format, lint_only=lint_only)
            self._print_result(result)

        return self.results

    def _print_result(self, result: Dict):
        """Print check result for a single file"""
        if result['passed']:
            if result['warnings']:
                icon = "[WARN]"
                status = "Passed (with warnings)"
            else:
                icon = "[OK]"
                status = "Passed"
        else:
            icon = "[ERROR]"
            status = "Failed"

        print(f"{icon} {result['file']} - {status}")

        # Display basic info
        if result['info']:
            info_items = []
            if 'viewbox' in result['info']:
                info_items.append(f"viewBox: {result['info']['viewbox']}")
            if info_items:
                print(f"   {' | '.join(info_items)}")

        # Display errors
        if result['errors']:
            for error in result['errors']:
                print(f"   [ERROR] {error}")

        # Display warnings
        if result['warnings']:
            for warning in result['warnings'][:2]:  # Only show first 2 warnings
                print(f"   [WARN] {warning}")
            if len(result['warnings']) > 2:
                print(f"   ... and {len(result['warnings']) - 2} more warning(s)")

        print()

    def print_summary(self):
        """Print check summary"""
        print("=" * 80)
        print("[SUMMARY] Check Summary")
        print("=" * 80)

        print(f"\nTotal files: {self.summary['total']}")
        print(
            f"  [OK] Fully passed: {self.summary['passed']} ({self._percentage(self.summary['passed'])}%)")
        print(
            f"  [WARN] With warnings: {self.summary['warnings']} ({self._percentage(self.summary['warnings'])}%)")
        print(
            f"  [ERROR] With errors: {self.summary['errors']} ({self._percentage(self.summary['errors'])}%)")

        if self.issue_types:
            print(f"\nIssue categories:")
            for issue_type, count in sorted(self.issue_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  {issue_type}: {count}")

        # spec_lock drift aggregation (only printed when a lock was found)
        self._print_drift_summary()

        # Fix suggestions
        if self.summary['errors'] > 0 or self.summary['warnings'] > 0:
            print(f"\n[TIP] Common fixes:")
            print(f"  1. viewBox issues: Ensure consistency with canvas format (see references/canvas-formats.md)")
            print(f"  2. foreignObject: Use <text> + <tspan> for manual line breaks")
            print(f"  3. Font issues: end every font-family stack with a PPT-safe family (e.g. Microsoft YaHei / Arial / Consolas)")

    def _print_drift_summary(self):
        """Print spec_lock drift aggregation if any was observed.

        Values are sorted by file-count descending so frequent drift surfaces
        first. Frequent drift usually means spec_lock.md is missing entries
        the Strategist should have included; rare drift is more likely actual
        Executor drift and warrants SVG review.
        """
        if not self._lock_seen:
            return
        has_drift = any(self._drift_summary[cat] for cat in self._drift_summary)
        if not has_drift:
            print("\n[OK] spec_lock drift: none — all colors, fonts, sizes, and icons are anchored to spec_lock.md")
            return

        print("\nspec_lock drift — values used outside spec_lock.md:")
        labels = [('colors', 'Colors'),
                  ('fonts', 'Font families'),
                  ('sizes', 'Font sizes'),
                  ('icons', 'Icons')]
        for category, label in labels:
            items = self._drift_summary.get(category, {})
            if not items:
                continue
            entries = sorted(items.items(), key=lambda x: (-len(x[1]), x[0]))
            print(f"  {label}:")
            for val, files in entries:
                n = len(files)
                suffix = "file" if n == 1 else "files"
                print(f"    {val}  ({n} {suffix})")
        print(
            "Tip: frequent out-of-lock values usually mean spec_lock.md is missing\n"
            "     entries — extend the lock (scripts/update_spec.py or manual edit).\n"
            "     Rare ones are likely Executor drift — review the affected SVGs."
        )

    def _percentage(self, count: int) -> int:
        """Calculate percentage"""
        if self.summary['total'] == 0:
            return 0
        return int(count / self.summary['total'] * 100)

    def export_report(self, output_file: str = 'svg_quality_report.txt'):
        """Export check report"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("PPT Master SVG Quality Check Report\n")
            f.write("=" * 80 + "\n\n")

            for result in self.results:
                status = "[OK] Passed" if result['passed'] else "[ERROR] Failed"
                f.write(f"{status} - {result['file']}\n")
                f.write(f"Path: {result.get('path', 'N/A')}\n")

                if result['info']:
                    f.write(f"Info: {result['info']}\n")

                if result['errors']:
                    f.write(f"\nErrors:\n")
                    for error in result['errors']:
                        f.write(f"  - {error}\n")

                if result['warnings']:
                    f.write(f"\nWarnings:\n")
                    for warning in result['warnings']:
                        f.write(f"  - {warning}\n")

                f.write("\n" + "-" * 80 + "\n\n")

            # Write summary
            f.write("\n" + "=" * 80 + "\n")
            f.write("Check Summary\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total files: {self.summary['total']}\n")
            f.write(f"Fully passed: {self.summary['passed']}\n")
            f.write(f"With warnings: {self.summary['warnings']}\n")
            f.write(f"With errors: {self.summary['errors']}\n")

        print(f"\n[REPORT] Check report exported: {output_file}")


def main() -> None:
    """Run the CLI entry point."""
    if len(sys.argv) < 2:
        print("PPT Master - SVG Quality Check Tool\n")
        print("Usage:")
        print("  python3 scripts/svg_quality_checker.py <svg_file>")
        print("  python3 scripts/svg_quality_checker.py <directory>")
        print("  python3 scripts/svg_quality_checker.py --all examples")
        print("  python3 scripts/svg_quality_checker.py --lint <svg_file_or_directory>")
        print("\nModes:")
        print("  default — Full 7-dimension check (Step 6 Quality Check Gate)")
        print("  --lint  — Pre-flight 3-dim subset (Step 7.0 entry, <1s)")
        print("            viewBox / forbidden elements / fonts only")
        print("\nExamples:")
        print("  python3 scripts/svg_quality_checker.py examples/project/svg_output/slide_01.svg")
        print("  python3 scripts/svg_quality_checker.py examples/project/svg_output")
        print("  python3 scripts/svg_quality_checker.py examples/project")
        print("  python3 scripts/svg_quality_checker.py --lint examples/project")
        sys.exit(0)

    checker = SVGQualityChecker()

    # Parse arguments
    expected_format = None
    lint_only = '--lint' in sys.argv

    if '--format' in sys.argv:
        idx = sys.argv.index('--format')
        if idx + 1 < len(sys.argv):
            expected_format = sys.argv[idx + 1]

    # Determine target (skip flag tokens)
    flag_tokens = {'--lint', '--all', '--format', '--export', '--output'}
    target = None
    skip_next = False
    for arg in sys.argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg in flag_tokens:
            if arg in ('--format', '--output'):
                skip_next = True
            continue
        target = arg
        break

    if target is None and '--all' not in sys.argv:
        print("[ERROR] No target file or directory provided")
        sys.exit(2)

    # Execute check
    if '--all' in sys.argv:
        # base_dir = the first non-flag positional arg (already resolved as `target`),
        # falling back to 'examples'. This handles any ordering: `--all examples`,
        # `--all --lint my_projects`, `--lint --all my_projects`, etc.
        base_dir = target if target is not None else 'examples'
        from project_utils import find_all_projects
        projects = find_all_projects(base_dir)

        for project in projects:
            print(f"\n{'=' * 80}")
            print(f"Checking project: {project.name}")
            print('=' * 80)
            checker.check_directory(str(project), lint_only=lint_only)
    else:
        checker.check_directory(target, expected_format, lint_only=lint_only)

    # Print summary
    checker.print_summary()

    # Export report (if specified)
    if '--export' in sys.argv:
        output_file = 'svg_quality_report.txt'
        if '--output' in sys.argv:
            idx = sys.argv.index('--output')
            if idx + 1 < len(sys.argv):
                output_file = sys.argv[idx + 1]
        checker.export_report(output_file)

    # Return exit code
    if checker.summary['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
