#!/usr/bin/env python3
"""
PPT Master - SVG Post-processing Tool (Unified Entry Point)

Processes SVG files from svg_output/ and outputs them to svg_final/.
By default, all processing steps are executed. You can also specify
individual steps via arguments.

Usage:
    # Execute all processing steps (recommended)
    python3 scripts/finalize_svg.py <project_directory>

    # Execute only specific steps
    python3 scripts/finalize_svg.py <project_directory> --only embed-icons fix-rounded

Examples:
    python3 scripts/finalize_svg.py projects/my_project
    python3 scripts/finalize_svg.py examples/ppt169_demo --only embed-icons

Processing options:
    normalize-layout - Normalize colored-block text alignment
    embed-icons   - Replace <use data-icon="..."/> with actual icon SVG
    align-images  - Single-pass align (slice/meet) + Base64 embed all <image>
                    (replaces the legacy crop-images + fix-aspect + embed-images
                    trio in default-all mode; the legacy names remain accepted
                    via --only for explicit single-step rollback)
    crop-images   - [legacy] Smart crop images based on preserveAspectRatio="slice"
    fix-aspect    - [legacy] Fix image aspect ratio
    embed-images  - [legacy] Convert external images to Base64 embedded
    flatten-text  - Convert <tspan> to independent <text> (for special renderers)
    fix-rounded   - Convert <rect rx="..."/> to <path> (for PPT shape conversion)
"""

import sys as _sys; from pathlib import Path as _Path; _sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _ensure_deps import ensure_deps; ensure_deps()

import os
import sys
import shutil
import argparse
from pathlib import Path

# Import finalize helpers from the internal package.
sys.path.insert(0, str(Path(__file__).parent))
from svg_finalize.align_embed_images import align_and_embed_images_in_svg
from svg_finalize.crop_images import process_svg_images as crop_images_in_svg
from svg_finalize.embed_icons import process_svg_file as embed_icons_in_file
from svg_finalize.embed_images import embed_images_in_svg
from svg_finalize.fix_image_aspect import fix_image_aspect_in_svg
from svg_finalize.normalize_layout import normalize_colored_block_text_in_file


def safe_print(text: str) -> None:
    """Print text while tolerating Windows terminal encoding limits."""
    try:
        print(text)
    except UnicodeEncodeError:
        replacements = {
            chr(0x23F3): "[..]",
            chr(0x2705): "[DONE]",
            chr(0x274C): "[ERROR]",
            chr(0x26A0) + chr(0xFE0F): "[WARN]",
            chr(0x1F4C1): "[DIR]",
            chr(0x1F4C4): "[FILE]",
            chr(0x1F4E6): "[OK]",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        print(text)


def process_flatten_text(svg_file: Path, verbose: bool = False) -> bool:
    """Flatten text in a single SVG file (in-place modification)"""
    try:
        from svg_finalize.flatten_tspan import flatten_text_with_tspans
        from xml.etree import ElementTree as ET

        tree = ET.parse(str(svg_file))
        changed = flatten_text_with_tspans(tree)

        if changed:
            tree.write(str(svg_file), encoding='unicode', xml_declaration=False)
            if verbose:
                safe_print(f"   [OK] {svg_file.name}: text flattened")
        return changed
    except Exception as e:
        if verbose:
            safe_print(f"   [ERROR] {svg_file.name}: {e}")
        return False


def process_rounded_rect(svg_file: Path, verbose: bool = False) -> int:
    """Convert rounded rectangles in a single SVG file (in-place modification)"""
    try:
        from svg_finalize.svg_rect_to_path import process_svg

        with open(svg_file, 'r', encoding='utf-8') as f:
            content = f.read()

        processed, count = process_svg(content, verbose=False)

        if count > 0:
            with open(svg_file, 'w', encoding='utf-8') as f:
                f.write(processed)
            if verbose:
                safe_print(f"   [OK] {svg_file.name}: {count} rounded rectangle(s)")
        return count
    except Exception as e:
        if verbose:
            safe_print(f"   [ERROR] {svg_file.name}: {e}")
        return 0


def finalize_project(
    project_dir: Path,
    options: dict[str, bool],
    dry_run: bool = False,
    quiet: bool = False,
    compress: bool = False,
    max_dimension: int | None = None,
) -> bool:
    """
    Finalize SVG files in the project

    Args:
        project_dir: Project directory path
        options: Processing options dictionary
        dry_run: Preview only, do not execute
        quiet: Quiet mode, reduce output
        compress: Compress images before embedding
        max_dimension: Downscale images exceeding this dimension
    """
    svg_output = project_dir / 'svg_output'
    svg_final = project_dir / 'svg_final'
    icons_dir = Path(__file__).parent.parent / 'templates' / 'icons'

    # Check if svg_output exists
    if not svg_output.exists():
        safe_print(f"[ERROR] svg_output directory not found: {svg_output}")
        return False

    # Get list of SVG files
    svg_files = list(svg_output.glob('*.svg'))
    if not svg_files:
        safe_print(f"[ERROR] No SVG files in svg_output")
        return False

    if not quiet:
        print()
        safe_print(f"[DIR] Project: {project_dir.name}")
        safe_print(f"[FILE] {len(svg_files)} SVG file(s)")

    if dry_run:
        safe_print("[PREVIEW] Preview mode, no operations will be performed")
        return True

    # Step 1: Copy directory
    if svg_final.exists():
        shutil.rmtree(svg_final)
    shutil.copytree(svg_output, svg_final)

    if not quiet:
        print()

    # Count active steps for progress prefix.
    active_steps = [
        ('normalize_layout', 'normalize-layout'),
        ('embed_icons', 'embed-icons'),
        ('align_images', 'align-images'),
        ('crop_images', 'crop-images'),
        ('fix_aspect', 'fix-aspect'),
        ('embed_images', 'embed-images'),
        ('flatten_text', 'flatten-text'),
        ('fix_rounded', 'fix-rounded'),
    ]
    enabled_count = sum(1 for k, _ in active_steps if options.get(k))
    step_idx = [0]

    def step_label(label: str) -> str:
        step_idx[0] += 1
        return f"[{step_idx[0]}/{enabled_count}] {label}"

    # Step: Normalize layout primitives (our quality work)
    if options.get('normalize_layout'):
        if not quiet:
            safe_print(step_label("Normalizing colored-block text..."))
        normalized_count = 0
        for svg_file in svg_final.glob('*.svg'):
            normalized_count += normalize_colored_block_text_in_file(svg_file, verbose=False)
        if not quiet:
            if normalized_count > 0:
                safe_print(f"      {normalized_count} colored-block label(s) normalized")
            else:
                safe_print("      No colored-block labels")

    # Step: Embed icons
    if options.get('embed_icons'):
        if not quiet:
            safe_print(step_label("Embedding icons..."))
        icons_count = 0
        for svg_file in svg_final.glob('*.svg'):
            count = embed_icons_in_file(svg_file, icons_dir, dry_run=False, verbose=False)
            icons_count += count
        if not quiet:
            if icons_count > 0:
                safe_print(f"      {icons_count} icon(s) embedded")
            else:
                safe_print("      No icons")

    # Step: Single-pass align + embed images (default; replaces the legacy
    # crop+fix-aspect+embed trio). Each <image> is read once from disk and
    # the spatial transform (slice → crop, meet → fit-box) is fused with
    # Base64 embed. Mutually exclusive with the legacy trio per --only.
    if options.get('align_images'):
        if not quiet:
            safe_print(step_label("Aligning + embedding images..."))
        img_count = 0
        img_errors = 0
        for svg_file in svg_final.glob('*.svg'):
            count, errs = align_and_embed_images_in_svg(
                svg_file,
                dry_run=False,
                verbose=False,
                compress=compress,
                max_dimension=max_dimension,
            )
            img_count += count
            img_errors += errs
        if not quiet:
            if img_count > 0:
                msg = f"      {img_count} image(s) aligned + embedded"
                if img_errors:
                    msg += f"  ({img_errors} error(s))"
                safe_print(msg)
            else:
                safe_print("      No images")

    # Step: [legacy] Smart crop images — only fires when explicitly named
    # in --only, for rollback compatibility with old automation scripts.
    if options.get('crop_images'):
        if not quiet:
            safe_print(step_label("[legacy] Smart cropping images..."))
        crop_count = 0
        crop_errors = 0
        for svg_file in svg_final.glob('*.svg'):
            count, errors = crop_images_in_svg(str(svg_file), dry_run=False, verbose=False)
            crop_count += count
            crop_errors += errors
        if not quiet:
            if crop_count > 0:
                safe_print(f"      {crop_count} image(s) cropped")
            else:
                safe_print("      No cropping needed (no images with slice attribute)")

    # Step: [legacy] Fix image aspect ratio — only fires when explicit.
    if options.get('fix_aspect'):
        if not quiet:
            safe_print(step_label("[legacy] Fixing image aspect ratios..."))
        aspect_count = 0
        for svg_file in svg_final.glob('*.svg'):
            count = fix_image_aspect_in_svg(str(svg_file), dry_run=False, verbose=False)
            aspect_count += count
        if not quiet:
            if aspect_count > 0:
                safe_print(f"      {aspect_count} image(s) fixed")
            else:
                safe_print("      No images")

    # Step: [legacy] Embed images — only fires when explicit.
    if options.get('embed_images'):
        if not quiet:
            safe_print(step_label("[legacy] Embedding images..."))
        images_count = 0
        for svg_file in svg_final.glob('*.svg'):
            count, _ = embed_images_in_svg(str(svg_file), dry_run=False,
                                           compress=compress,
                                           max_dimension=max_dimension)
            images_count += count
        if not quiet:
            if images_count > 0:
                safe_print(f"      {images_count} image(s) embedded")
            else:
                safe_print("      No images")

    # Step: Flatten text
    if options.get('flatten_text'):
        if not quiet:
            safe_print(step_label("Flattening text..."))
        flatten_count = 0
        for svg_file in svg_final.glob('*.svg'):
            if process_flatten_text(svg_file, verbose=False):
                flatten_count += 1
        if not quiet:
            if flatten_count > 0:
                safe_print(f"      {flatten_count} file(s) processed")
            else:
                safe_print("      No processing needed")

    # Step: Convert rounded rects to Path
    if options.get('fix_rounded'):
        if not quiet:
            safe_print(step_label("Converting rounded rects to Path..."))
        rounded_count = 0
        for svg_file in svg_final.glob('*.svg'):
            count = process_rounded_rect(svg_file, verbose=False)
            rounded_count += count
        if not quiet:
            if rounded_count > 0:
                safe_print(f"      {rounded_count} rounded rectangle(s) converted")
            else:
                safe_print("      No rounded rectangles")

    # Done
    if not quiet:
        print()
        safe_print("[OK] Done!")
        print()
        print("Next steps:")
        print(f"  python scripts/svg_to_pptx.py \"{project_dir}\"")

    return True


def main() -> None:
    """Run the CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PPT Master - SVG Post-processing Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s projects/my_project           # Execute all processing (default)
  %(prog)s projects/my_project --only embed-icons fix-rounded
  %(prog)s projects/my_project -q        # Quiet mode

Processing options (for --only):
  normalize-layout Normalize colored-block text alignment
  embed-icons   Embed icons
  align-images  Single-pass align (slice/meet) + Base64 embed (default path)
  crop-images   [legacy] Smart crop images (based on preserveAspectRatio)
  fix-aspect    [legacy] Fix image aspect ratio
  embed-images  [legacy] Embed images
  flatten-text  Flatten text
  fix-rounded   Convert rounded rects to Path
        '''
    )

    parser.add_argument('project_dir', type=Path, help='Project directory path')
    parser.add_argument('--only', nargs='+', metavar='OPTION',
                        choices=['normalize-layout', 'embed-icons', 'align-images', 'crop-images', 'fix-aspect', 'embed-images', 'flatten-text', 'fix-rounded'],
                        help='Execute only specified processing steps (default: all)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Preview only, do not execute')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Quiet mode, reduce output')
    parser.add_argument('--compress', action='store_true',
                        help='Compress images before embedding (JPEG quality=85, PNG optimize)')
    parser.add_argument('--max-dimension', type=int, default=None,
                        help='Downscale images exceeding this dimension on either axis (e.g., 2560)')

    args = parser.parse_args()

    if not args.project_dir.exists():
        safe_print(f"[ERROR] Project directory does not exist: {args.project_dir}")
        sys.exit(1)

    # Determine processing options
    if args.only:
        # Execute only specified steps. Legacy aliases (crop-images / fix-aspect /
        # embed-images) and the new align-images are mutually exclusive within
        # a single --only invocation: each runs the step the user named.
        options = {
            'normalize_layout': 'normalize-layout' in args.only,
            'embed_icons': 'embed-icons' in args.only,
            'align_images': 'align-images' in args.only,
            'crop_images': 'crop-images' in args.only,
            'fix_aspect': 'fix-aspect' in args.only,
            'embed_images': 'embed-images' in args.only,
            'flatten_text': 'flatten-text' in args.only,
            'fix_rounded': 'fix-rounded' in args.only,
        }
    else:
        # Default-all: use the new merged align_images step instead of the
        # legacy crop+fix-aspect+embed trio (single-pass parse + bitmap read).
        options = {
            'normalize_layout': True,
            'embed_icons': True,
            'align_images': True,
            'crop_images': False,
            'fix_aspect': False,
            'embed_images': False,
            'flatten_text': True,
            'fix_rounded': True,
        }

    success = finalize_project(args.project_dir, options, args.dry_run, args.quiet,
                               compress=args.compress,
                               max_dimension=args.max_dimension)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
