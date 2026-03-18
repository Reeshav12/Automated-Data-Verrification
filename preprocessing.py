from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


def preprocess_image(image_path: str | Path, processed_dir: str | Path) -> Path:
    source_path = Path(image_path)
    destination_dir = Path(processed_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1600, 1600))
        grayscale = ImageOps.autocontrast(image.convert("L"))

        processed_path = destination_dir / f"{source_path.stem}_processed.png"
        grayscale.save(processed_path, format="PNG")

    return processed_path
