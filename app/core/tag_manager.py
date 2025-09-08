#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签管理器 - 管理用户画像的动态更新和维护
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from app.core.models import TagInfo, TagInstance, UserProfile, DimensionSummary

class TagManager:
    """标签管理器类"""
    
    def __init__(self, user_id: str):
        """初始化标签管理器"""
        self.user_id = user_id
        self.user_data_path = f"user_data/{user_id}"
        self.tags_file = f"{self.user_data_path}/user_tags.json"
        self.timeline_file = f"{self.user_data_path}/tag_timeline.json"
        self._ensure_tag_files()
        
    def _ensure_tag_files(self):
        """确保标签文件存在"""
        os.makedirs(self.user_data_path, exist_ok=True)
        
        if not os.path.exists(self.tags_file):
            self._create_empty_tags_file()
        
        if not os.path.exists(self.timeline_file):
            timeline_data = {
                "user_id": self.user_id,
                "tag_events": []
            }
            with open(self.timeline_file, 'w', encoding='utf-8') as f:
                json.dump(timeline_data, f, ensure_ascii=False, indent=2)
    
    def _create_empty_tags_file(self):
        """创建空的用户画像文件"""
        empty_profile = UserProfile(user_id=self.user_id)
        
        # 初始化标签维度结构
        tag_dimensions = {
            "用户核心画像": {
                "年龄段": [],
                "性别": [],
                "所在地区": [],
                "健康角色": []
            },
            "产品使用路径与偏好": {
                "核心功能偏好": [],
                "交互方式偏好": []
            },
            "用户意图与转化阶段": {
                "具体意图分类": [],
                "转化阶段": []
            },
            "用户商业价值": {
                "价值等级": [],
                "付费敏感度": []
            }
        }
        
        empty_profile.tag_dimensions = tag_dimensions
        
        with open(self.tags_file, 'w', encoding='utf-8') as f:
            json.dump(empty_profile.to_dict(), f, ensure_ascii=False, indent=2)
    
    def update_tags(self, extracted_tags: Dict[str, List[TagInfo]]) -> UserProfile:
        """更新用户画像标签"""
        print(f"🔄 开始更新用户 {self.user_id} 的画像标签...")
        
        current_profile = self._load_current_tags()
        
        # 更新交互计数
        current_profile.total_interactions += 1
        
        # 处理提取的标签
        for level1_category, new_tags in extracted_tags.items():
            if level1_category in current_profile.tag_dimensions:
                for tag_info in new_tags:
                    self._update_tag_in_dimension(
                        current_profile, 
                        level1_category, 
                        tag_info
                    )
        
        # 应用时间衰减
        self._apply_time_decay(current_profile)
        
        # 重新计算指标和摘要
        self._recalculate_metrics(current_profile)
        
        # 更新时间戳
        current_profile.last_updated = datetime.now().isoformat()
        
        # 保存更新后的画像
        self._save_tags(current_profile)
        
        # 记录到时间线
        self._record_tag_timeline(extracted_tags)
        
        print(f"✅ 用户画像更新完成，画像成熟度: {current_profile.profile_maturity:.2%}")
        return current_profile
    
    def _update_tag_in_dimension(self, profile: UserProfile, level1_category: str, tag_info: TagInfo):
        """在特定维度中更新标签"""
        level2_category = tag_info.subcategory
        
        # 确保维度存在
        if level2_category not in profile.tag_dimensions[level1_category]:
            profile.tag_dimensions[level1_category][level2_category] = []
        
        tag_list = profile.tag_dimensions[level1_category][level2_category]
        
        # 查找是否已存在相同标签
        existing_tag = None
        for tag_instance in tag_list:
            if tag_instance.tag_name == tag_info.name:
                existing_tag = tag_instance
                break
        
        if existing_tag:
            # 强化现有标签
            self._reinforce_tag(existing_tag, tag_info)
            print(f"  💪 强化标签: {tag_info.name} (置信度: {existing_tag.confidence:.2f})")
        else:
            # 处理冲突（某些维度只能有一个主导标签）
            if self._is_exclusive_dimension(level1_category, level2_category):
                self._resolve_exclusive_conflict(tag_list, tag_info)
            
            # 添加新标签
            new_tag_instance = TagInstance(
                tag_name=tag_info.name,
                confidence=tag_info.confidence,
                reinforcement_count=1,
                first_seen=tag_info.timestamp,
                last_reinforced=tag_info.timestamp,
                evidence_list=[tag_info.evidence]
            )
            tag_list.append(new_tag_instance)
            print(f"  ➕ 新增标签: {tag_info.name} (置信度: {tag_info.confidence:.2f})")
    
    def _reinforce_tag(self, existing_tag: TagInstance, new_tag_info: TagInfo):
        """强化现有标签"""
        # 更新强化计数和时间
        existing_tag.reinforcement_count += 1
        existing_tag.last_reinforced = new_tag_info.timestamp
        
        # 更新置信度（使用加权平均）
        weight = 0.3  # 新证据的权重
        existing_tag.confidence = (
            existing_tag.confidence * (1 - weight) + 
            new_tag_info.confidence * weight
        )
        
        # 确保置信度不超过1.0
        existing_tag.confidence = min(existing_tag.confidence, 1.0)
        
        # 添加新证据
        existing_tag.evidence_list.append(new_tag_info.evidence)
        
        # 保持证据列表大小合理（最多保留10个最新证据）
        if len(existing_tag.evidence_list) > 10:
            existing_tag.evidence_list = existing_tag.evidence_list[-10:]
    
    def _is_exclusive_dimension(self, level1_category: str, level2_category: str) -> bool:
        """判断某个维度是否是互斥的（只能有一个主导标签）"""
        exclusive_dimensions = {
            "用户核心画像": ["年龄段", "性别"],  # 年龄段和性别通常是互斥的
        }
        
        return (level1_category in exclusive_dimensions and 
                level2_category in exclusive_dimensions[level1_category])
    
    def _resolve_exclusive_conflict(self, tag_list: List[TagInstance], new_tag_info: TagInfo):
        """解决互斥维度的冲突"""
        if not tag_list:
            return
        
        # 找到当前最强的标签
        strongest_tag = max(tag_list, key=lambda t: t.confidence)
        
        # 如果新标签的置信度更高，移除旧标签
        if new_tag_info.confidence > strongest_tag.confidence:
            tag_list.remove(strongest_tag)
            print(f"  🔄 替换标签: {strongest_tag.tag_name} -> {new_tag_info.name}")
    
    def _apply_time_decay(self, profile: UserProfile):
        """应用时间衰减"""
        now = datetime.now()
        
        for level1_category, level2_dict in profile.tag_dimensions.items():
            for level2_category, tag_list in level2_dict.items():
                for tag_instance in tag_list:
                    try:
                        last_reinforced = datetime.fromisoformat(tag_instance.last_reinforced)
                        days_since = (now - last_reinforced).days
                        
                        # 计算衰减因子（30天衰减周期）
                        decay_factor = max(0.1, 1.0 - (days_since * tag_instance.decay_rate / 30))
                        
                        # 应用衰减，但保持最小置信度
                        base_confidence = tag_instance.confidence / (1 + tag_instance.reinforcement_count * 0.1)
                        tag_instance.confidence = max(0.1, base_confidence * decay_factor)
                        
                    except (ValueError, TypeError):
                        # 如果时间格式有问题，跳过衰减
                        continue
    
    def _recalculate_metrics(self, profile: UserProfile):
        """重新计算画像指标和摘要"""
        # 清空旧的摘要
        profile.dimension_summaries = []
        
        total_tags = 0
        confident_tags = 0
        
        # 计算每个维度的摘要
        for level1_category, level2_dict in profile.tag_dimensions.items():
            for level2_category, tag_list in level2_dict.items():
                if tag_list:
                    # 找到该子维度的主导标签
                    dominant_tag = max(tag_list, key=lambda t: t.confidence)
                    
                    summary = DimensionSummary(
                        dimension_name=level1_category,
                        subdimension_name=level2_category,
                        dominant_tag=dominant_tag.tag_name,
                        confidence=dominant_tag.confidence,
                        tag_count=len(tag_list),
                        last_updated=dominant_tag.last_reinforced
                    )
                    profile.dimension_summaries.append(summary)
                    
                    total_tags += len(tag_list)
                    confident_tags += len([t for t in tag_list if t.confidence >= 0.6])
        
        # 计算画像成熟度
        if total_tags > 0:
            profile.profile_maturity = min(1.0, (confident_tags / total_tags) * (total_tags / 10))
        else:
            profile.profile_maturity = 0.0
    
    def _record_tag_timeline(self, extracted_tags: Dict[str, List[TagInfo]]):
        """记录标签变化到时间线"""
        try:
            with open(self.timeline_file, 'r', encoding='utf-8') as f:
                timeline_data = json.load(f)
        except:
            timeline_data = {"user_id": self.user_id, "tag_events": []}
        
        # 创建事件记录
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "tag_extraction",
            "extracted_tags": {
                category: [tag.to_dict() for tag in tags]
                for category, tags in extracted_tags.items()
            }
        }
        
        timeline_data["tag_events"].append(event)
        
        # 保持时间线合理大小（最多1000个事件）
        if len(timeline_data["tag_events"]) > 1000:
            timeline_data["tag_events"] = timeline_data["tag_events"][-1000:]
        
        with open(self.timeline_file, 'w', encoding='utf-8') as f:
            json.dump(timeline_data, f, ensure_ascii=False, indent=2)
    
    def _load_current_tags(self) -> UserProfile:
        """加载当前用户画像"""
        try:
            with open(self.tags_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return UserProfile.from_dict(data)
        except Exception as e:
            print(f"❌ 加载用户画像失败: {e}")
            return UserProfile(user_id=self.user_id)
    
    def _save_tags(self, profile: UserProfile):
        """保存用户画像"""
        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存用户画像失败: {e}")
    
    def get_user_tags(self) -> UserProfile:
        """获取用户画像"""
        return self._load_current_tags()
    
    def get_user_profile(self, user_id: str = None) -> UserProfile:
        """获取用户画像（兼容方法）"""
        return self._load_current_tags()
    
    def get_tag_timeline(self) -> Dict:
        """获取标签时间线"""
        try:
            with open(self.timeline_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"user_id": self.user_id, "tag_events": []}
