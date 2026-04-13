#!/usr/bin/env python3
"""Generate OpenWhisper icon files.

Run this script to regenerate the icon.png and icon.ico files in the assets directory.

Requirements:
    pip install Pillow

Usage:
    python scripts/generate_icons.py
"""
from __future__ import annotations

import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    raise SystemExit(1)


def create_openwhisper_icon(size: int = 256) -> Image.Image:
    """Create an OpenWhisper icon.

    Design: A circular icon with a gradient background (teal to blue),
    featuring a stylized microphone/sound wave symbol representing
    voice-to-text functionality.
    """
    # Create a new RGBA image
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Colors
    bg_color_1 = (20, 184, 166)  # Teal
    bg_color_2 = (59, 130, 246)  # Blue
    white = (255, 255, 255)

    # Draw circular background with gradient effect
    center = size // 2
    radius = size // 2 - 4

    # Simple radial gradient simulation
    for r in range(radius, 0, -1):
        # Interpolate color based on radius
        t = r / radius
        color = (
            int(bg_color_1[0] * t + bg_color_2[0] * (1 - t)),
            int(bg_color_1[1] * t + bg_color_2[1] * (1 - t)),
            int(bg_color_1[2] * t + bg_color_2[2] * (1 - t)),
        )
        draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill=color
        )

    # Draw stylized "OW" text or microphone symbol
    # For simplicity, let's draw sound waves emanating from a dot (microphone)

    # Central microphone dot
    mic_radius = size // 10
    draw.ellipse(
        [center - mic_radius, center - mic_radius,
         center + mic_radius, center + mic_radius],
        fill=white
    )

    # Sound wave arcs
    wave_widths = [size // 40, size // 50, size // 60]
    wave_radii = [size // 4, size // 3, size // 2.5]

    for i, (radius, width) in enumerate(zip(wave_radii, wave_widths)):
        # Right side waves
        draw.arc(
            [center - radius, center - radius, center + radius, center + radius],
            start=-60, end=60,
            fill=white, width=width
        )
        # Left side waves
        draw.arc(
            [center - radius, center - radius, center + radius, center + radius],
            start=120, end=240,
            fill=white, width=width
        )

    return img


def main() -> None:
    """Generate icon files."""
    # Determine paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    assets_dir = repo_root / "assets"
    assets_dir.mkdir(exist_ok=True)

    # Generate main icon at 256x256
    print("Generating icon...")
    icon_256 = create_openwhisper_icon(256)

    # Save PNG
    png_path = assets_dir / "icon.png"
    icon_256.save(png_path, "PNG")
    print(f"Saved: {png_path}")

    # Generate multiple sizes for ICO file
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = []
    for s in sizes:
        if s == 256:
            icons.append(icon_256)
        else:
            icons.append(icon_256.resize((s, s), Image.Resampling.LANCZOS))

    # Save ICO
    ico_path = assets_dir / "icon.ico"
    icons[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:]
    )
    print(f"Saved: {ico_path}")

    print("Done!")


if __name__ == "__main__":
    main()
