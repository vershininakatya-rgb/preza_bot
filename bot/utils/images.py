"""Утилиты для изображений к сообщениям бота."""
import random
from pathlib import Path
from typing import Optional

# Путь к папке с картинами (assets/art)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ART_DIR = PROJECT_ROOT / "assets" / "art"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _list_images(directory: Path) -> list[Path]:
    """Список файлов изображений в папке."""
    if not directory.exists() or not directory.is_dir():
        return []
    return [p for p in directory.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS]


def get_step_image_path(step: str) -> Optional[str]:
    """Возвращает путь к случайному изображению из pictures или assets/art."""
    folders = [
        PROJECT_ROOT / "pictures",
        ART_DIR,
        Path.cwd() / "pictures",
        Path.cwd() / "assets" / "art",
    ]
    seen = set()
    for folder in folders:
        folder = folder.resolve()
        if folder in seen:
            continue
        seen.add(folder)
        images = _list_images(folder)
        if images:
            return str(random.choice(images))
    return None
