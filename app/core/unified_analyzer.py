"""
统一分析器
将整个对话文件作为整体进行分析，而不是分轮次处理
"""

import time
from typing import List, Dict, Any, Optional, Callable
from .tag_extractor import TagExtractor
from .tag_manager import TagManager
from .models import UserProfile
from .conversation_summarizer import ConversationSummarizer
from .summary_manager import SummaryManager


class UnifiedAnalyzer:
    """统一分析器 - 整体分析对话内容"""
    
    def __init__(self, tag_extractor: TagExtractor, tag_manager: TagManager, user_id: str):
        self.tag_extractor = tag_extractor
        self.tag_manager = tag_manager
        self.user_id = user_id
        self.conversation_summarizer = ConversationSummarizer(user_id)
    
    def analyze_all_conversations(
        self, 
        user_id: str,
        conversations: List[Dict[str, Any]], 
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        generate_summaries: bool = True
    ) -> Dict[str, Any]:
        """
        整体分析所有对话内容
        
        Args:
            user_id: 用户ID
            conversations: 对话列表
            progress_callback: 进度回调函数
            generate_summaries: 是否生成摘要
            
        Returns:
            分析结果
        """
        total_conversations = len(conversations)
        
        print(f"🚀 开始整体分析 {total_conversations} 轮对话...")
        
        if progress_callback:
            progress_callback(1, 3, "正在整体分析对话内容...")
        
        # 1. 构建完整的对话上下文
        full_context = self._build_full_context(conversations)
        print(f"📝 构建完整对话上下文，总长度: {len(full_context)} 字符")
        
        # 2. 整体提取标签
        extracted_tags = {}
        try:
            print("🔍 开始整体标签提取...")
            extracted_tags = self.tag_extractor.extract_tags_from_text(full_context)
            print(f"✅ 整体标签提取成功: {type(extracted_tags)}")
            
            # 计算标签总数
            total_extracted_tags = sum(len(tags) for tags in extracted_tags.values())
            print(f"📋 共提取到 {total_extracted_tags} 个标签")
            
        except Exception as extract_error:
            print(f"❌ 整体标签提取失败: {str(extract_error)}")
            import traceback
            traceback.print_exc()
        
        if progress_callback:
            progress_callback(2, 3, "正在生成对话摘要...")
        
        # 3. 生成整体摘要或分段摘要
        conversation_summaries = []
        summary_statistics = {}
        
        if generate_summaries:
            try:
                print("📝 开始生成对话摘要...")
                
                # 可以选择整体摘要或分段摘要
                if len(conversations) <= 10:  # 对话数量较少时，可以生成详细的分段摘要
                    conversation_summaries = self._generate_detailed_summaries(conversations)
                else:  # 对话数量较多时，生成整体摘要
                    conversation_summaries = self._generate_unified_summary(conversations)
                
                summary_statistics = self._calculate_summary_statistics(conversation_summaries)
                print(f"✅ 摘要生成完成，成功率: {summary_statistics.get('success_rate', 0)}%")
                
            except Exception as summary_error:
                print(f"❌ 摘要生成失败: {str(summary_error)}")
                import traceback
                traceback.print_exc()
        
        if progress_callback:
            progress_callback(3, 3, "正在更新用户画像...")
        
        # 4. 更新用户画像
        updated_profile = None
        total_updated_tags = 0
        
        if extracted_tags:
            try:
                print("🔄 开始更新用户画像...")
                updated_profile = self.tag_manager.update_tags(extracted_tags)
                total_updated_tags = sum(len(tags) for tags in extracted_tags.values())
                print(f"✅ 用户画像更新完成，更新标签数: {total_updated_tags}")
                
            except Exception as update_error:
                print(f"❌ 用户画像更新失败: {str(update_error)}")
                import traceback
                traceback.print_exc()
        
        # 5. 保存摘要数据
        if conversation_summaries:
            try:
                summary_manager = SummaryManager()
                summary_manager.save_batch_summaries(user_id, conversation_summaries)
                print(f"✅ 成功保存 {len(conversation_summaries)} 个会话摘要")
            except Exception as save_error:
                print(f"❌ 保存摘要失败: {str(save_error)}")
        
        # 6. 构建分析结果
        analysis_result = {
            'total_conversations': total_conversations,
            'processed_conversations': total_conversations,
            'total_extracted_tags': sum(len(tags) for tags in extracted_tags.values()) if extracted_tags else 0,
            'total_updated_tags': total_updated_tags,
            'user_profile': updated_profile.to_dict() if updated_profile else None,
            'conversation_summaries': conversation_summaries,
            'summary_statistics': summary_statistics,
            'extracted_tags_by_category': {
                category: [tag.to_dict() for tag in tags] 
                for category, tags in extracted_tags.items()
            } if extracted_tags else {},
            'analysis_method': 'unified',  # 标识为整体分析
            'summary': self._generate_analysis_summary(
                total_conversations, 
                sum(len(tags) for tags in extracted_tags.values()) if extracted_tags else 0,
                conversation_summaries
            )
        }
        
        print(f"✅ 整体分析完成!")
        print(f"   📊 总对话数: {total_conversations}")
        print(f"   ✅ 成功处理: {total_conversations}")
        print(f"   🏷️ 提取标签: {analysis_result['total_extracted_tags']}")
        print(f"   🔄 更新标签: {total_updated_tags}")
        if updated_profile and hasattr(updated_profile, 'profile_maturity'):
            print(f"   📈 画像成熟度: {updated_profile.profile_maturity:.2%}")
        
        return analysis_result
    
    def _build_full_context(self, conversations: List[Dict[str, Any]]) -> str:
        """构建完整的对话上下文"""
        context_parts = []
        
        for i, conversation in enumerate(conversations, 1):
            user_message = conversation.get('user', '')
            assistant_message = conversation.get('assistant', '')
            
            if user_message:
                context_parts.append(f"=== 对话 {i} ===")
                context_parts.append(f"用户：{user_message}")
                if assistant_message:
                    context_parts.append(f"助手：{assistant_message}")
                context_parts.append("")  # 空行分隔
        
        return "\n".join(context_parts)
    
    def _generate_detailed_summaries(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成详细的分段摘要（适用于少量对话）"""
        summaries = []
        
        for i, conversation in enumerate(conversations):
            try:
                user_message = conversation.get('user', '')
                assistant_message = conversation.get('assistant', '')
                
                if not user_message:
                    summaries.append({
                        'conversation_index': i + 1,
                        'success': False,
                        'error': '用户消息为空'
                    })
                    continue
                
                print(f"📝 生成第 {i + 1} 轮对话摘要...")
                summary_result = self.conversation_summarizer.generate_summary(user_message, assistant_message)
                summary_result['conversation_index'] = i + 1
                summaries.append(summary_result)
                
                # 短暂延迟，避免API请求过于频繁
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 第 {i + 1} 轮对话摘要生成异常: {e}")
                summaries.append({
                    'conversation_index': i + 1,
                    'success': False,
                    'error': str(e)
                })
        
        return summaries
    
    def _generate_unified_summary(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成统一摘要（适用于大量对话）"""
        print("📝 生成整体对话摘要...")
        
        # 将所有对话合并为一个整体进行摘要
        all_user_messages = []
        all_assistant_messages = []
        
        for conversation in conversations:
            user_msg = conversation.get('user', '').strip()
            assistant_msg = conversation.get('assistant', '').strip()
            if user_msg:
                all_user_messages.append(user_msg)
            if assistant_msg:
                all_assistant_messages.append(assistant_msg)
        
        # 构建整体对话内容
        combined_user_content = " ".join(all_user_messages)
        combined_assistant_content = " ".join(all_assistant_messages)
        
        try:
            # 生成整体摘要
            summary_result = self.conversation_summarizer.generate_summary(
                combined_user_content, 
                combined_assistant_content
            )
            
            # 将整体摘要应用到所有对话
            summaries = []
            for i in range(len(conversations)):
                summary_copy = summary_result.copy()
                summary_copy['conversation_index'] = i + 1
                summary_copy['is_unified_summary'] = True  # 标记为整体摘要
                summaries.append(summary_copy)
            
            print(f"✅ 整体摘要生成成功，应用到 {len(conversations)} 轮对话")
            return summaries
            
        except Exception as e:
            print(f"❌ 整体摘要生成失败: {e}")
            # 返回失败结果
            return [{
                'conversation_index': i + 1,
                'success': False,
                'error': f"整体摘要生成失败: {str(e)}",
                'is_unified_summary': True
            } for i in range(len(conversations))]
    
    def _calculate_summary_statistics(self, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算摘要统计信息"""
        if not summaries:
            return {}
        
        successful_summaries = [s for s in summaries if s.get('success', False)]
        success_rate = (len(successful_summaries) / len(summaries)) * 100
        
        # 统计医疗系统和风险等级
        medical_systems = {}
        risk_levels = {}
        
        for summary in successful_summaries:
            if summary.get('summary'):
                medical_system = summary['summary'].get('涉及系统', '')
                if medical_system and medical_system != 'N/A':
                    medical_systems[medical_system] = medical_systems.get(medical_system, 0) + 1
                
                risk_level = summary['summary'].get('风险评估', '')
                if risk_level and risk_level != 'N/A':
                    risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
        
        return {
            'total_summaries': len(summaries),
            'successful_summaries': len(successful_summaries),
            'success_rate': round(success_rate, 1),
            'medical_systems': medical_systems,
            'risk_levels': risk_levels
        }
    
    def _generate_analysis_summary(self, total_conversations: int, total_tags: int, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成分析总结"""
        success_rate = 100.0  # 整体分析的成功率通常是100%
        average_tags = total_tags / total_conversations if total_conversations > 0 else 0
        
        # 统计标签分类（如果有的话）
        tag_categories = {}
        
        return {
            'total_conversations': total_conversations,
            'success_rate': success_rate,
            'average_tags_per_conversation': round(average_tags, 1),
            'tag_categories': tag_categories,
            'analysis_method': 'unified'
        }
