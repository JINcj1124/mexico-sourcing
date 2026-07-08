"""节日权重动态调整器

基于墨西哥营销日历，使用高斯衰减模型计算品类节日权重。
提前1-2个月权重逐渐上升，节日当天达到峰值，节日过后归零。
"""
import math
import json
from datetime import date, datetime
from typing import Dict, List, Optional
from backend.config import settings


class FestivalWeighter:
    """节日权重引擎"""

    BASE_WEIGHT = 1.0
    DECAY_SIGMA = 30  # 高斯衰减标准差（天）

    def __init__(self, calendar_path: str = None):
        self.calendar_path = calendar_path or settings.festival_calendar_path
        self.festivals: List[dict] = []
        self._load()

    def _load(self):
        try:
            with open(self.calendar_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.festivals = data.get("festivals", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.festivals = []

    def reload(self):
        self._load()

    def calc_category_weight(self, category: str, target_date: Optional[date] = None) -> float:
        """计算品类在指定日期的节日加权分值"""
        today = target_date or date.today()
        total_weight = self.BASE_WEIGHT

        for festival in self.festivals:
            if category not in festival.get("categories", []):
                continue

            try:
                festival_date = datetime.strptime(festival["date"], "%Y-%m-%d").date()
            except (ValueError, KeyError):
                continue

            days_until = (festival_date - today).days
            lead_days = festival.get("lead_months", 2) * 30

            if days_until < 0 or days_until > lead_days:
                continue

            # 高斯衰减：节日越近权重越高
            festival_weight = festival.get("weight", 1.0)
            gaussian = festival_weight * math.exp(
                -(days_until**2) / (2 * self.DECAY_SIGMA**2)
            )
            total_weight += gaussian

        return round(total_weight, 4)

    def get_active_festivals(self, target_date: Optional[date] = None) -> List[dict]:
        """获取当前活跃节日（未来2个月内）"""
        today = target_date or date.today()
        active = []

        for festival in self.festivals:
            try:
                festival_date = datetime.strptime(festival["date"], "%Y-%m-%d").date()
            except (ValueError, KeyError):
                continue

            lead_days = festival.get("lead_months", 2) * 30
            days_until = (festival_date - today).days

            if 0 <= days_until <= lead_days:
                w = math.exp(-(days_until**2) / (2 * self.DECAY_SIGMA**2))
                active.append({
                    "id": festival["id"],
                    "name_zh": festival["name_zh"],
                    "name_es": festival.get("name_es", ""),
                    "date": festival["date"],
                    "days_until": days_until,
                    "weight": round(festival.get("weight", 1.0) * w, 4),
                })

        return sorted(active, key=lambda x: x["days_until"])

    def get_festival_keywords_zh(self, target_date: Optional[date] = None) -> List[str]:
        """获取当前活跃节日的1688中文搜索关键词"""
        active = self.get_active_festivals(target_date)
        keywords = []
        for f in active:
            # 找到原始节日数据获取关键词
            original = next((x for x in self.festivals if x["id"] == f["id"]), None)
            if original:
                keywords.extend(original.get("keywords_zh", []))
        return list(dict.fromkeys(keywords))  # 去重保序

    def get_festival_keywords_es(self, target_date: Optional[date] = None) -> List[str]:
        """获取当前活跃节日的西班牙语搜索关键词（用于竞品比价）"""
        active = self.get_active_festivals(target_date)
        keywords = []
        for f in active:
            original = next((x for x in self.festivals if x["id"] == f["id"]), None)
            if original:
                keywords.extend(original.get("keywords_es", []))
        return list(dict.fromkeys(keywords))

    def get_festival_categories(self, target_date: Optional[date] = None) -> Dict[str, float]:
        """获取所有品类的节日权重映射"""
        today = target_date or date.today()
        categories = set()
        for f in self.festivals:
            categories.update(f.get("categories", []))

        return {c: self.calc_category_weight(c, today) for c in categories}
