"""关键词生成器

结合基础关键词模板和节日驱动关键词，生成每日搜索关键词列表。
"""
import json
import logging
from typing import List, Dict
from datetime import date

from backend.algorithms.festival_weighter import FestivalWeighter
from backend.config import settings

logger = logging.getLogger(__name__)


class KeywordGenerator:
    """动态关键词生成器"""

    def __init__(self, festival_weighter: FestivalWeighter = None):
        self.weighter = festival_weighter or FestivalWeighter()
        self._base_keywords: List[Dict] = []
        self._load_templates()

    def _load_templates(self):
        try:
            with open(settings.keyword_templates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._base_keywords = data.get("base_keywords", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self._base_keywords = []

    def generate(self, target_date: date = None) -> List[str]:
        """生成当日搜索关键词列表（中文1688搜索用）"""
        keywords: List[str] = []

        # 1. 基础关键词（常驻）
        for kw in self._base_keywords[:15]:  # 取前15个基础词
            keywords.append(kw["zh"])

        # 2. 节日驱动关键词
        festival_kw = self.weighter.get_festival_keywords_zh(target_date)
        keywords.extend(festival_kw)

        # 3. 去重
        seen = set()
        unique = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique.append(k)

        logger.info(f"Generated {len(unique)} keywords ({len(festival_kw)} festival-driven)")
        return unique

    def generate_es(self, target_date: date = None) -> List[str]:
        """生成西班牙语关键词（竞品比价用）"""
        keywords: List[str] = []

        # 基础关键词ES
        for kw in self._base_keywords[:10]:
            keywords.append(kw.get("es", ""))

        # 节日关键词ES
        festival_kw = self.weighter.get_festival_keywords_es(target_date)
        keywords.extend(festival_kw)

        seen = set()
        return [k for k in keywords if k and k not in seen and not seen.add(k)]
