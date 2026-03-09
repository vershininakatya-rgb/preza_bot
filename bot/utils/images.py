"""Утилиты для изображений к сообщениям бота."""
import random
from pathlib import Path
from typing import Optional

# Путь к папке с картинками нерпы (assets/art)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ART_DIR = PROJECT_ROOT / "assets" / "art"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
# К постам прикладываем только картинки нерпы (имя начинается с nerpa_)
NERPA_PREFIX = "nerpa_"


def _list_images(directory: Path, name_prefix: Optional[str] = None) -> list[Path]:
    """Список файлов изображений в папке. Если задан name_prefix — только файлы с таким началом имени."""
    if not directory.exists() or not directory.is_dir():
        return []
    images = [p for p in directory.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS]
    if name_prefix:
        images = [p for p in images if p.name.lower().startswith(name_prefix.lower())]
    return images


def get_step_image_path(step: str) -> Optional[str]:
    """Возвращает путь к случайному изображению нерпы из assets/art. К постам — только нерпа."""
    folders = [
        ART_DIR,
        PROJECT_ROOT / "assets" / "art",
        Path.cwd() / "assets" / "art",
    ]
    seen = set()
    for folder in folders:
        folder = folder.resolve()
        if folder in seen:
            continue
        seen.add(folder)
        images = _list_images(folder, name_prefix=NERPA_PREFIX)
        if images:
            return str(random.choice(images))
    return None
