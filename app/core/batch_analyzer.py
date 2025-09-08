"""
批量对话分析器
用于处理文件上传的对话分析
支持整体分析的模式
"""

from typing import List, Dict, Any, Callable, Optional
from .tag_extractor import TagExtractor
from .tag_manager import TagManager
from .unified_analyzer import UnifiedAnalyzer


class BatchAnalyzer:
    """批量对话分析器"""
    
    def __init__(self, tag_extractor: TagExtractor, tag_manager: TagManager, user_id: str):
        self.tag_extractor = tag_extractor
        self.tag_manager = tag_manager
        self.user_id = user_id
        self.unified_analyzer = UnifiedAnalyzer(tag_extractor, tag_manager, user_id)
    
    def analyze_conversations(
        self, 
        user_id: str,
        conversations: List[Dict[str, Any]], 
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        generate_summaries: bool = True
    ) -> Dict[str, Any]:
        """
        批量分析对话并更新用户画像
        
        Args:
            user_id: 用户ID
            conversations: 对话列表
            progress_callback: 进度回调函数 (current, total, message)
            generate_summaries: 是否生成对话摘要
            
        Returns:
            分析结果
        """
        print(f"🚀 使用整体分析模式处理 {len(conversations)} 轮对话...")
        return self.unified_analyzer.analyze_all_conversations(
            user_id=user_id,
            conversations=conversations,
            progress_callback=progress_callback,
            generate_summaries=generate_summaries
        )
    
    def analyze_single_conversation(
        self, 
        user_id: str, 
        user_message: str, 
        assistant_message: str = ""
    ) -> Dict[str, Any]:
        """
        分析单轮对话
        
        Args:
            user_id: 用户ID
            user_message: 用户消息
            assistant_message: 助手回复
            
        Returns:
            分析结果
        """
        # 构建对话上下文
        context = f"用户：{user_message}"
        if assistant_message:
            context += f"\n助手：{assistant_message}"
        
        # 提取标签
        extracted_tags = self.tag_extractor.extract_tags_from_text(context)
        
        # 计算提取的标签总数
        total_extracted = sum(len(tags) for tags in extracted_tags.values()) if extracted_tags else 0
        
        # 更新用户画像
        updated_count = 0
        if extracted_tags:
            updated_profile = self.tag_manager.update_tags(extracted_tags)
            updated_count = total_extracted
        
        # 获取用户画像
        user_profile = self.tag_manager.get_user_profile(user_id)
        
        return {
            'extracted_tags_count': total_extracted,
            'updated_tags_count': updated_count,
            'extracted_tags': {
                category: [tag.to_dict() for tag in tags] 
                for category, tags in extracted_tags.items()
            } if extracted_tags else {},
            'user_profile': user_profile.to_dict() if user_profile else None
        }
