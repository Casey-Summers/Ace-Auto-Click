from __future__ import annotations

from pathlib import Path

REQUIRED_ICON_PATHS = [
    "icons/32x32.png",
    "icons/128x128.png",
    "icons/128x128@2x.png",
    "icons/icon.ico",
]


def missing_icon_paths(config: dict, tauri_dir: Path) -> list[str]:
    icon_paths = config.get("bundle", {}).get("icon", [])
    return [path for path in icon_paths if not (tauri_dir / path).exists()]


def ensure_icons(tauri_dir: Path) -> bool:
    icons_dir = tauri_dir / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    missing = [path for path in REQUIRED_ICON_PATHS if not (tauri_dir / path).exists()]
    if not missing:
        return False

    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        raise SystemExit(f"Pillow is required to generate icons: {exc}") from exc

    png_sizes = {
        "icons/32x32.png": 32,
        "icons/128x128.png": 128,
        "icons/128x128@2x.png": 256,
    }
    images = []
    for relative_path, size in png_sizes.items():
        image = _make_icon(size)
        image.save(tauri_dir / relative_path)
        images.append(image)
    images[1].save(tauri_dir / "icons/icon.ico", sizes=[(32, 32), (64, 64), (128, 128), (256, 256)])
    return True


def _make_icon(size: int):
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (size, size), "#07080a")
    draw = ImageDraw.Draw(image)
    margin = max(3, size // 10)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=max(6, size // 8),
        fill="#101111",
        outline="#ff6363",
        width=max(1, size // 24),
    )
    cursor = [
        (size * 0.35, size * 0.23),
        (size * 0.35, size * 0.72),
        (size * 0.48, size * 0.61),
        (size * 0.58, size * 0.79),
        (size * 0.69, size * 0.73),
        (size * 0.58, size * 0.56),
        (size * 0.75, size * 0.55),
    ]
    draw.polygon(cursor, fill="#f9f9f9")
    draw.ellipse(
        [size * 0.57, size * 0.24, size * 0.76, size * 0.43],
        outline="#55b3ff",
        width=max(1, size // 18),
    )
    return image
