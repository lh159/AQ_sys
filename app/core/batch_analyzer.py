"""
批量对话分析器
用于处理文件上传的多轮对话分析
"""

import time
from typing import List, Dict, Any, Callable, Optional
from .tag_extractor import TagExtractor
from .tag_manager import TagManager
from .models import UserProfile


class BatchAnalyzer:
    """批量对话分析器"""
    
    def __init__(self, tag_extractor: TagExtractor, tag_manager: TagManager):
        self.tag_extractor = tag_extractor
        self.tag_manager = tag_manager
    
    def analyze_conversations(
        self, 
        user_id: str,
        conversations: List[Dict[str, Any]], 
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        批量分析对话并更新用户画像
        
        Args:
            user_id: 用户ID
            conversations: 对话列表
            progress_callback: 进度回调函数 (current, total, message)
            
        Returns:
            分析结果
        """
        total_conversations = len(conversations)
        extracted_tags_count = 0
        updated_tags_count = 0
        analysis_results = []
        
        print(f"🔄 开始批量分析 {total_conversations} 轮对话...")
        
        for i, conversation in enumerate(conversations):
            try:
                # 更新进度
                if progress_callback:
                    progress_callback(i + 1, total_conversations, f"正在分析第 {i + 1} 轮对话...")
                
                user_message = conversation.get('user', '')
                assistant_message = conversation.get('assistant', '')
                
                if not user_message:
                    print(f"⚠️ 第 {i + 1} 轮对话用户消息为空，跳过")
                    continue
                
                # 构建完整的对话上下文
                full_context = f"用户：{user_message}"
                if assistant_message:
                    full_context += f"\n助手：{assistant_message}"
                
                # 提取标签
                print(f"🔍 分析第 {i + 1} 轮对话: {user_message[:50]}...")
                print(f"🔧 调用标签提取器: {type(self.tag_extractor)}")
                print(f"🔧 标签提取器方法: {dir(self.tag_extractor)}")
                
                try:
                    extracted_tags = self.tag_extractor.extract_tags_from_text(full_context)
                    print(f"✅ 标签提取成功: {type(extracted_tags)}")
                except Exception as extract_error:
                    print(f"❌ 标签提取失败: {str(extract_error)}")
                    import traceback
                    traceback.print_exc()
                    extracted_tags = {}
                
                if extracted_tags:
                    # 计算所有类别的标签总数
                    total_tags_in_conversation = sum(len(tags) for tags in extracted_tags.values())
                    extracted_tags_count += total_tags_in_conversation
                    print(f"📋 第 {i + 1} 轮对话提取到 {total_tags_in_conversation} 个标签")
                    
                    # 更新用户画像
                    updated_profile = self.tag_manager.update_tags(extracted_tags)
                    updated_count = total_tags_in_conversation  # 简化：假设所有标签都被更新
                    updated_tags_count += updated_count
                    
                    # 记录分析结果
                    analysis_results.append({
                        'conversation_index': i + 1,
                        'user_message': user_message,
                        'assistant_message': assistant_message,
                        'extracted_tags': total_tags_in_conversation,
                        'tags': {
                            category: [tag.to_dict() for tag in tags] 
                            for category, tags in extracted_tags.items()
                        }
                    })
                else:
                    print(f"⚠️ 第 {i + 1} 轮对话未提取到标签")
                    analysis_results.append({
                        'conversation_index': i + 1,
                        'user_message': user_message,
                        'assistant_message': assistant_message,
                        'extracted_tags': 0,
                        'tags': []
                    })
                
                # 短暂延迟，避免API请求过于频繁
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 第 {i + 1} 轮对话分析失败: {e}")
                analysis_results.append({
                    'conversation_index': i + 1,
                    'user_message': conversation.get('user', ''),
                    'assistant_message': conversation.get('assistant', ''),
                    'extracted_tags': 0,
                    'tags': [],
                    'error': str(e)
                })
        
        # 获取更新后的用户画像
        user_profile = self.tag_manager.get_user_profile(user_id)
        
        # 最终进度更新
        if progress_callback:
            progress_callback(total_conversations, total_conversations, "分析完成！")
        
        result = {
            'total_conversations': total_conversations,
            'processed_conversations': len([r for r in analysis_results if r['extracted_tags'] > 0]),
            'total_extracted_tags': extracted_tags_count,
            'total_updated_tags': updated_tags_count,
            'user_profile': user_profile.to_dict() if user_profile else None,
            'analysis_results': analysis_results,
            'summary': self._generate_summary(analysis_results, user_profile)
        }
        
        print(f"✅ 批量分析完成:")
        print(f"   📊 总对话数: {total_conversations}")
        print(f"   ✅ 成功处理: {result['processed_conversations']}")
        print(f"   🏷️ 提取标签: {extracted_tags_count}")
        print(f"   🔄 更新标签: {updated_tags_count}")
        if user_profile:
            print(f"   📈 画像成熟度: {user_profile.profile_maturity:.2f}%")
        
        return result
    
    def _generate_summary(self, analysis_results: List[Dict], user_profile: Optional[UserProfile]) -> Dict[str, Any]:
        """生成分析摘要"""
        # 统计各类标签数量
        tag_categories = {}
        total_tags = 0
        
        for result in analysis_results:
            tags_dict = result.get('tags', {})
            # tags_dict 的格式: {category: [tag_dict, ...]}
            for category, tag_list in tags_dict.items():
                tag_categories[category] = tag_categories.get(category, 0) + len(tag_list)
                total_tags += len(tag_list)
        
        # 找出最活跃的对话（提取标签最多的）
        most_active_conversation = max(
            analysis_results, 
            key=lambda x: x.get('extracted_tags', 0),
            default=None
        )
        
        # 成功率统计
        successful_conversations = [r for r in analysis_results if r.get('extracted_tags', 0) > 0]
        success_rate = len(successful_conversations) / len(analysis_results) if analysis_results else 0
        
        # 计算用户画像中的总标签数
        total_unique_tags = 0
        if user_profile:
            for level1_dict in user_profile.tag_dimensions.values():
                for tag_list in level1_dict.values():
                    total_unique_tags += len(tag_list)
        
        summary = {
            'success_rate': round(success_rate * 100, 2),
            'tag_categories': tag_categories,
            'total_unique_tags': total_unique_tags,
            'most_active_conversation_index': most_active_conversation.get('conversation_index') if most_active_conversation else None,
            'most_active_conversation_tags': most_active_conversation.get('extracted_tags', 0) if most_active_conversation else 0,
            'average_tags_per_conversation': round(total_tags / len(analysis_results), 2) if analysis_results else 0,
            'maturity_score': user_profile.profile_maturity if user_profile else 0
        }
        
        return summary
    
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
        
        # 更新用户画像
        updated_count = 0
        if extracted_tags:
            updated_profile = self.tag_manager.update_tags(extracted_tags)
            updated_count = total_extracted
        
        # 获取用户画像
        user_profile = self.tag_manager.get_user_profile(user_id)
        
        # 计算提取的标签总数
        total_extracted = sum(len(tags) for tags in extracted_tags.values()) if extracted_tags else 0
        
        return {
            'extracted_tags_count': total_extracted,
            'updated_tags_count': updated_count,
            'extracted_tags': {
                category: [tag.to_dict() for tag in tags] 
                for category, tags in extracted_tags.items()
            } if extracted_tags else {},
            'user_profile': user_profile.to_dict() if user_profile else None
        }
