"""Утилиты для изображений к сообщениям бота."""
from pathlib import Path
from typing import Optional

# Путь к папке с картинами (относительно корня проекта)
ASSETS_ART_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "art"

# Соответствие шагов и изображений
STEP_IMAGES = {
    "1": "02_picasso_product_team.png",
    "2_upload": "04_shishkin_data_forest.png",
    "2_result": "08_vangogh_cloud_night.png",
    "2_extra_ask": "09_dali_agile_sprint.png",
    "2_extra_result": "16_vangogh_cloud_sunflowers.png",
    "0H_1": "18_picasso_burnout.png",
    "0H_3": "22_caravaggio_recruiting.png",
}


def get_step_image_path(step: str) -> Optional[str]:
    """Возвращает путь к изображению для шага или None, если изображения нет."""
    filename = STEP_IMAGES.get(step)
    if not filename:
        return None
    path = ASSETS_ART_DIR / filename
    return str(path) if path.exists() else None
