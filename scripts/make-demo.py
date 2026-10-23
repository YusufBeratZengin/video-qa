#!/usr/bin/env python3
"""Generate docs/demo.svg showing a real CLI command and real output."""

import html
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from video_qa.analyzer import analyze, find_ffmpeg
from video_qa.profiles import Profile
from video_qa.reports import human_report


def run_real_analysis() -> tuple[str, list[str]]:
    """Create a synthetic video clip and run the real analyzer."""
    ffmpeg = find_ffmpeg()
    profile = Profile(name="shorts")

    with tempfile.TemporaryDirectory() as td:
        clip = Path(td) / "out.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=1080x1920:rate=30",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440",
                "-t",
                "3",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                str(clip),
            ],
            capture_output=True,
            check=True,
        )

        report = analyze(clip, profile, ffmpeg=ffmpeg)
        clean_report = replace(report, path="out.mp4")
        output = human_report(clean_report)

    cmd = "video-qa check out.mp4 --profile shorts"
    lines = output.strip().splitlines()
    return cmd, lines


def build_terminal_svg(cmd: str, output_lines: list[str]) -> str:
    """Render a terminal window SVG with syntax highlighting."""
    line_height = 20
    top_bar_height = 42
    padding_x = 24
    padding_y = 20

    # Total rows: command line + empty line + output lines
    total_text_rows = 1 + len(output_lines)
    content_height = total_text_rows * line_height
    window_height = top_bar_height + padding_y * 2 + content_height
    window_width = 820
    font_stack = (
        "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "
        "'Liberation Mono', 'Courier New', monospace"
    )

    svg_lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {window_width} {window_height}" '
        f'width="100%" height="{window_height}">',
        "  <defs>",
        '    <linearGradient id="terminal-border" x1="0" y1="0" x2="1" y2="1">',
        '      <stop offset="0%" stop-color="#30363d" stop-opacity="0.8"/>',
        '      <stop offset="100%" stop-color="#21262d" stop-opacity="0.4"/>',
        "    </linearGradient>",
        '    <filter id="terminal-shadow" x="-5%" y="-5%" width="110%" height="115%">',
        '      <feDropShadow dx="0" dy="12" stdDeviation="18" '
        'flood-color="#000000" flood-opacity="0.4"/>',
        "    </filter>",
        "    <style>",
        "      .code {",
        f"        font-family: {font_stack};",
        "        font-size: 13px;",
        "        white-space: pre;",
        "      }",
        "      .title { fill: #8b949e; font-size: 12px; font-weight: 500; }",
        "      .prompt { fill: #58a6ff; font-weight: 600; }",
        "      .cmd { fill: #f0f6fc; font-weight: 600; }",
        "      .meta { fill: #8b949e; }",
        "      .hdr { fill: #8b949e; font-weight: 600; }",
        "      .pass { fill: #3fb950; font-weight: 700; }",
        "      .warn { fill: #d29922; font-weight: 700; }",
        "      .fail { fill: #f85149; font-weight: 700; }",
        "      .rule { fill: #79c0ff; }",
        "      .detail { fill: #c9d1d9; }",
        "      .summary { fill: #e6edf3; font-weight: 600; }",
        "    </style>",
        "  </defs>",
        "",
        '  <g filter="url(#terminal-shadow)">',
        f'    <rect x="10" y="10" width="{window_width - 20}" height="{window_height - 20}" '
        'rx="10" ry="10" fill="#0d1117" stroke="url(#terminal-border)" stroke-width="1"/>',
        f'    <rect x="10" y="10" width="{window_width - 20}" height="{top_bar_height}" '
        'rx="10" ry="10" fill="#161b22"/>',
        f'    <rect x="10" y="40" width="{window_width - 20}" height="12" fill="#161b22"/>',
        f'    <line x1="10" y1="{top_bar_height + 10}" x2="{window_width - 10}" '
        f'y2="{top_bar_height + 10}" stroke="#21262d" stroke-width="1"/>',
        "",
        "    <!-- Window Controls -->",
        '    <circle cx="32" cy="28" r="6" fill="#ff5f56" stroke="#e0443e" stroke-width="0.5"/>',
        '    <circle cx="52" cy="28" r="6" fill="#ffbd2e" stroke="#dea123" stroke-width="0.5"/>',
        '    <circle cx="72" cy="28" r="6" fill="#27c93f" stroke="#1aab29" stroke-width="0.5"/>',
        f'    <text x="{window_width / 2}" y="32" text-anchor="middle" '
        'class="code title">video-qa — terminal</text>',
        "  </g>",
        "",
        "  <!-- Terminal Content -->",
        f'  <g transform="translate({padding_x + 6}, {top_bar_height + padding_y + 12})">',
    ]

    # Command line
    curr_y = 0
    cmd_escaped = html.escape(cmd)
    svg_lines.append(
        f'    <text x="0" y="{curr_y}" class="code">'
        f'<tspan class="prompt">$ </tspan>'
        f'<tspan class="cmd">{cmd_escaped}</tspan>'
        "</text>"
    )
    curr_y += line_height

    for line in output_lines:
        line_clean = line.rstrip()
        if not line_clean:
            curr_y += line_height
            continue

        if line_clean.startswith("STATUS  CHECK"):
            escaped = html.escape(line_clean)
            svg_lines.append(f'    <text x="0" y="{curr_y}" class="code hdr">{escaped}</text>')
        elif line_clean.startswith("PASS:"):
            escaped = html.escape(line_clean)
            svg_lines.append(f'    <text x="0" y="{curr_y}" class="code summary">{escaped}</text>')
        elif (
            line_clean.startswith("PASS")
            or line_clean.startswith("WARN")
            or line_clean.startswith("FAIL")
        ):
            parts = line_clean.split(None, 2)
            tag = parts[0]
            check_name = parts[1] if len(parts) > 1 else ""
            detail = parts[2] if len(parts) > 2 else ""

            tag_class = tag.lower()
            tag_escaped = html.escape(f"{tag:<8}")
            check_escaped = html.escape(f"{check_name:<16}")
            detail_escaped = html.escape(detail)

            svg_lines.append(
                f'    <text x="0" y="{curr_y}" class="code">'
                f'<tspan class="{tag_class}">{tag_escaped}</tspan>'
                f'<tspan class="rule">{check_escaped}</tspan>'
                f'<tspan class="detail">{detail_escaped}</tspan>'
                "</text>"
            )
        else:
            escaped = html.escape(line_clean)
            svg_lines.append(f'    <text x="0" y="{curr_y}" class="code meta">{escaped}</text>')

        curr_y += line_height

    svg_lines.append("  </g>")
    svg_lines.append("</svg>")
    svg_lines.append("")

    return "\n".join(svg_lines)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(exist_ok=True)

    cmd, output_lines = run_real_analysis()
    svg_content = build_terminal_svg(cmd, output_lines)

    target_svg = docs_dir / "demo.svg"
    target_svg.write_text(svg_content, encoding="utf-8")
    print(f"Generated {target_svg} ({len(output_lines) + 1} lines).")


if __name__ == "__main__":
    main()
