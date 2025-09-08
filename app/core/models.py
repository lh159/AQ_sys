#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AQ-用户标签系统数据模型定义
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class TagInfo:
    """标签信息类"""
    name: str                    # 标签名称
    confidence: float           # 置信度 (0.0-1.0)
    evidence: str              # 证据原文
    category: str              # 一级标签分类
    subcategory: str           # 二级标签分类
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "category": self.category,
            "subcategory": self.subcategory,
            "timestamp": self.timestamp
        }

@dataclass
class TagInstance:
    """用户画像中的标签实例"""
    tag_name: str               # 标签名称
    confidence: float          # 当前置信度
    reinforcement_count: int   # 强化次数
    first_seen: str           # 首次出现时间
    last_reinforced: str      # 最后强化时间
    evidence_list: List[str] = field(default_factory=list)  # 历史证据列表
    decay_rate: float = 0.1   # 衰减率
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "tag_name": self.tag_name,
            "confidence": self.confidence,
            "reinforcement_count": self.reinforcement_count,
            "first_seen": self.first_seen,
            "last_reinforced": self.last_reinforced,
            "evidence_list": self.evidence_list,
            "decay_rate": self.decay_rate
        }

@dataclass
class DimensionSummary:
    """维度摘要信息"""
    dimension_name: str        # 维度名称（一级标签）
    subdimension_name: str     # 子维度名称（二级标签）
    dominant_tag: str          # 主导标签
    confidence: float          # 主导标签置信度
    tag_count: int            # 该维度下的标签总数
    last_updated: str         # 最后更新时间
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "dimension_name": self.dimension_name,
            "subdimension_name": self.subdimension_name,
            "dominant_tag": self.dominant_tag,
            "confidence": self.confidence,
            "tag_count": self.tag_count,
            "last_updated": self.last_updated
        }

@dataclass
class UserProfile:
    """用户画像类"""
    user_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 标签维度数据 - 层级结构: 一级标签 -> 二级标签 -> 标签列表
    tag_dimensions: Dict[str, Dict[str, List[TagInstance]]] = field(default_factory=dict)
    
    # 计算指标
    profile_maturity: float = 0.0      # 画像成熟度 (0.0-1.0)
    total_interactions: int = 0        # 总交互次数
    
    # 维度摘要（用于快速展示）
    dimension_summaries: List[DimensionSummary] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典格式用于JSON序列化"""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "tag_dimensions": {
                level1: {
                    level2: [tag.to_dict() for tag in tags]
                    for level2, tags in level2_dict.items()
                }
                for level1, level2_dict in self.tag_dimensions.items()
            },
            "profile_maturity": self.profile_maturity,
            "total_interactions": self.total_interactions,
            "dimension_summaries": [summary.to_dict() for summary in self.dimension_summaries]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserProfile':
        """从字典创建UserProfile实例"""
        profile = cls(
            user_id=data["user_id"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            profile_maturity=data.get("profile_maturity", 0.0),
            total_interactions=data.get("total_interactions", 0)
        )
        
        # 重建tag_dimensions
        for level1, level2_dict in data.get("tag_dimensions", {}).items():
            profile.tag_dimensions[level1] = {}
            for level2, tag_list in level2_dict.items():
                profile.tag_dimensions[level1][level2] = [
                    TagInstance(
                        tag_name=tag["tag_name"],
                        confidence=tag["confidence"],
                        reinforcement_count=tag["reinforcement_count"],
                        first_seen=tag["first_seen"],
                        last_reinforced=tag["last_reinforced"],
                        evidence_list=tag.get("evidence_list", []),
                        decay_rate=tag.get("decay_rate", 0.1)
                    )
                    for tag in tag_list
                ]
        
        # 重建dimension_summaries
        profile.dimension_summaries = [
            DimensionSummary(
                dimension_name=summary["dimension_name"],
                subdimension_name=summary["subdimension_name"],
                dominant_tag=summary["dominant_tag"],
                confidence=summary["confidence"],
                tag_count=summary["tag_count"],
                last_updated=summary["last_updated"]
            )
            for summary in data.get("dimension_summaries", [])
        ]
        
        return profile
