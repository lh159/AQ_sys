"""
会话摘要管理器
用于管理会话摘要的持久化存储和检索
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class SummaryManager:
    """会话摘要管理器"""
    
    def __init__(self, user_id: str):
        """初始化摘要管理器"""
        self.user_id = user_id
        self.user_data_path = f"user_data/{user_id}"
        self.summaries_file = f"{self.user_data_path}/conversation_summaries.json"
        self._ensure_summaries_file()
    
    def _ensure_summaries_file(self):
        """确保摘要文件存在"""
        os.makedirs(self.user_data_path, exist_ok=True)
        
        if not os.path.exists(self.summaries_file):
            self._create_empty_summaries_file()
    
    def _create_empty_summaries_file(self):
        """创建空的摘要文件"""
        empty_summaries = {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "conversation_summaries": [],
            "total_summaries": 0
        }
        
        with open(self.summaries_file, 'w', encoding='utf-8') as f:
            json.dump(empty_summaries, f, ensure_ascii=False, indent=2)
    
    def save_summaries(self, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        保存会话摘要列表
        
        Args:
            summaries: 摘要列表
            
        Returns:
            保存结果
        """
        try:
            # 加载现有数据
            current_data = self._load_summaries_data()
            
            # 添加时间戳到每个摘要
            timestamped_summaries = []
            for summary in summaries:
                summary_with_timestamp = summary.copy()
                if 'timestamp' not in summary_with_timestamp:
                    summary_with_timestamp['timestamp'] = datetime.now().isoformat()
                timestamped_summaries.append(summary_with_timestamp)
            
            # 合并摘要（最新的在前面）
            current_data['conversation_summaries'] = timestamped_summaries + current_data['conversation_summaries']
            
            # 限制最多保存100个摘要
            if len(current_data['conversation_summaries']) > 100:
                current_data['conversation_summaries'] = current_data['conversation_summaries'][:100]
            
            # 更新元数据
            current_data['last_updated'] = datetime.now().isoformat()
            current_data['total_summaries'] = len(current_data['conversation_summaries'])
            
            # 保存到文件
            with open(self.summaries_file, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 成功保存 {len(summaries)} 个会话摘要")
            return {
                'success': True,
                'saved_count': len(summaries),
                'total_summaries': current_data['total_summaries']
            }
            
        except Exception as e:
            print(f"❌ 保存摘要失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_summaries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取会话摘要列表
        
        Args:
            limit: 限制返回数量
            
        Returns:
            摘要列表
        """
        try:
            data = self._load_summaries_data()
            summaries = data.get('conversation_summaries', [])
            
            if limit:
                summaries = summaries[:limit]
            
            return summaries
            
        except Exception as e:
            print(f"❌ 获取摘要失败: {str(e)}")
            return []
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        获取摘要统计信息
        
        Returns:
            统计信息
        """
        try:
            data = self._load_summaries_data()
            return {
                'total_summaries': data.get('total_summaries', 0),
                'last_updated': data.get('last_updated'),
                'created_at': data.get('created_at')
            }
            
        except Exception as e:
            print(f"❌ 获取摘要统计失败: {str(e)}")
            return {
                'total_summaries': 0,
                'last_updated': None,
                'created_at': None
            }
    
    def _load_summaries_data(self) -> Dict[str, Any]:
        """加载摘要数据"""
        try:
            with open(self.summaries_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载摘要数据失败: {str(e)}")
            # 返回默认结构
            return {
                "user_id": self.user_id,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "conversation_summaries": [],
                "total_summaries": 0
            }
    
    def clear_summaries(self) -> Dict[str, Any]:
        """
        清除所有摘要
        
        Returns:
            清除结果
        """
        try:
            self._create_empty_summaries_file()
            print(f"✅ 成功清除用户 {self.user_id} 的所有摘要")
            return {'success': True}
            
        except Exception as e:
            print(f"❌ 清除摘要失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
