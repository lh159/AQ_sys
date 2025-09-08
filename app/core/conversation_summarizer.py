"""
对话摘要生成器
为每次通话内容生成AI概括报告
"""

import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
from .config_manager import ConfigManager


class ConversationSummarizer:
    """对话摘要生成器"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.config = ConfigManager.load_config()
        self.llm_client = self._init_llm_client()
        
    def _init_llm_client(self) -> OpenAI:
        """初始化LLM客户端"""
        llm_config = self.config.get('llm', {})
        api_key = llm_config.get('api_key')
        base_url = llm_config.get('base_url')
        
        if not api_key:
            raise ValueError("❌ LLM API密钥未配置")
        
        return OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    def generate_summary(self, user_message: str, assistant_message: str = "", context: Dict = None) -> Dict[str, Any]:
        """
        为单次对话生成AI概括报告
        
        Args:
            user_message: 用户消息
            assistant_message: 助手回复
            context: 额外上下文信息
            
        Returns:
            包含摘要信息的字典
        """
        try:
            # 构建对话内容
            conversation_content = f"用户：{user_message}"
            if assistant_message:
                conversation_content += f"\n助手：{assistant_message}"
            
            # 构建摘要提示词
            summary_prompt = self._build_summary_prompt(conversation_content, context)
            
            # 添加重试机制
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    # 调用DeepSeek R1生成摘要，增加max_tokens避免截断
                    llm_response = self.llm_client.chat.completions.create(
                        model=self.config.get('llm', {}).get('model', 'deepseek-reasoner'),
                        messages=[{"role": "user", "content": summary_prompt}],
                        max_tokens=4096,  # 增加token限制避免JSON截断
                        temperature=self.config.get('llm', {}).get('temperature', 0.3)
                        # 注意：DeepSeek R1可能不支持response_format参数，所以移除它
                    ).choices[0].message.content
                    
                    # 解析LLM响应
                    summary_data = self._parse_summary_response(llm_response)
                    
                    # 如果解析成功，跳出重试循环
                    break
                    
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        print(f"⚠️ 摘要生成失败（尝试 {attempt + 1}/{max_retries}）：{e}")
                        import time
                        time.sleep(1)  # 短暂等待后重试
                    else:
                        # 最后一次尝试失败，抛出异常
                        raise e
            
            print(f"✅ 对话摘要生成成功")
            return {
                'success': True,
                'summary': summary_data,
                'conversation_content': conversation_content
            }
            
        except Exception as e:
            print(f"❌ 对话摘要生成失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'conversation_content': conversation_content
            }
    
    def _build_summary_prompt(self, conversation_content: str, context: Dict = None) -> str:
        """构建摘要生成的提示词"""
        
        # 医师角色的system prompt
        system_prompt = """你是一个概括能力很精准的医师，具备以下特点：
1. 专业的医学知识背景，能够准确理解患者的症状描述和医疗咨询内容
2. 优秀的信息提取和概括能力，能够从对话中抽取关键医疗信息
3. 严谨的分析思维，能够识别重要的健康问题和风险因素
4. 清晰的表达能力，能够用简洁专业的语言总结对话要点

你的任务是对医患对话或健康咨询对话进行精准概括，提取关键信息并生成结构化的摘要报告。"""
        
        prompt = f"""{system_prompt}

请对以下对话内容进行专业的医疗概括分析：

对话内容：
{conversation_content}

请严格按照以下JSON格式输出概括报告，确保输出的是有效的JSON格式：

```json
{{
    "主要问题": "患者咨询的核心健康问题或症状",
    "关键症状": ["症状1", "症状2", "症状3"],
    "涉及系统": "涉及的身体系统或科室（如：消化系统、心血管系统等）",
    "风险评估": "初步的风险评估（低风险/中风险/高风险/需要紧急处理）",
    "建议要点": ["建议1", "建议2", "建议3"],
    "后续行动": "是否需要进一步检查或就医建议",
    "对话质量": "对话的完整性和信息充分程度评价",
    "专业摘要": "用1-2句话总结整个对话的核心内容"
}}
```

重要要求：
1. 必须返回有效的JSON格式，不要包含额外的文字说明
2. 如果对话不是医疗相关内容，请在"涉及系统"字段标注"非医疗咨询"
3. 保持客观专业，不做过度解读
4. 风险评估要谨慎，避免误导
5. 摘要要简洁准确，突出重点
6. 所有字段都必须填写，不能为空"""
        
        return prompt
    
    def _parse_summary_response(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM生成的摘要响应"""
        try:
            # 尝试直接解析JSON
            try:
                summary_data = json.loads(llm_response)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取JSON部分
                import re
                # 查找JSON代码块
                json_match = re.search(r'```json\s*\n(.*?)\n```', llm_response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    # 尝试修复截断的JSON
                    json_content = self._fix_truncated_json(json_content)
                    summary_data = json.loads(json_content)
                else:
                    # 尝试查找花括号内容
                    json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(0)
                        # 尝试修复截断的JSON
                        json_content = self._fix_truncated_json(json_content)
                        summary_data = json.loads(json_content)
                    else:
                        raise json.JSONDecodeError("No JSON found", llm_response, 0)
            
            # 验证必要字段
            required_fields = ["主要问题", "关键症状", "涉及系统", "风险评估", "建议要点", "后续行动", "对话质量", "专业摘要"]
            for field in required_fields:
                if field not in summary_data:
                    summary_data[field] = "未提供"
            
            # 确保关键症状和建议要点是列表格式
            if not isinstance(summary_data.get("关键症状"), list):
                symptoms = summary_data.get("关键症状", "")
                if isinstance(symptoms, str) and symptoms:
                    # 如果是字符串，尝试按逗号分割
                    summary_data["关键症状"] = [s.strip() for s in symptoms.split(',') if s.strip()]
                else:
                    summary_data["关键症状"] = [str(symptoms)] if symptoms else ["无明确症状"]
            
            if not isinstance(summary_data.get("建议要点"), list):
                suggestions = summary_data.get("建议要点", "")
                if isinstance(suggestions, str) and suggestions:
                    # 如果是字符串，尝试按逗号或分号分割
                    summary_data["建议要点"] = [s.strip() for s in suggestions.replace(';', ',').split(',') if s.strip()]
                else:
                    summary_data["建议要点"] = [str(suggestions)] if suggestions else ["无具体建议"]
            
            print(f"✅ 摘要解析成功: {summary_data.get('主要问题', 'Unknown')}")
            return summary_data
            
        except Exception as e:
            print(f"❌ 摘要解析失败: {e}")
            print(f"原始响应: {llm_response[:200]}...")
            
            # 返回基本摘要结构
            return {
                "主要问题": "解析失败",
                "关键症状": ["无法解析"],
                "涉及系统": "未知",
                "风险评估": "无法评估",
                "建议要点": ["请重新生成摘要"],
                "后续行动": "建议重新分析",
                "对话质量": "解析异常",
                "专业摘要": "摘要生成过程中出现解析错误"
            }
    
    def _fix_truncated_json(self, json_content: str) -> str:
        """修复截断的JSON字符串"""
        try:
            # 首先尝试直接解析
            json.loads(json_content)
            return json_content
        except json.JSONDecodeError as e:
            print(f"🔧 检测到JSON截断，尝试修复...")
            
            # 尝试补全缺失的结构
            fixed_content = json_content.strip()
            
            # 如果字符串没有以}结尾，可能是截断了
            if not fixed_content.endswith('}'):
                # 计算花括号的平衡
                open_braces = fixed_content.count('{')
                close_braces = fixed_content.count('}')
                
                # 如果缺少闭合花括号
                if open_braces > close_braces:
                    # 检查最后一个字段是否完整
                    lines = fixed_content.split('\n')
                    last_line = lines[-1].strip() if lines else ''
                    
                    # 如果最后一行不完整（没有引号结尾或逗号）
                    if last_line and not (last_line.endswith('"') or last_line.endswith(',') or last_line.endswith('}')):
                        # 尝试补全最后一个字段
                        if ':' in last_line:
                            # 这可能是一个被截断的字符串值
                            key_part, value_part = last_line.split(':', 1)
                            if value_part.strip().startswith('"') and not value_part.strip().endswith('"'):
                                # 补全字符串值
                                fixed_content = fixed_content.rsplit('\n', 1)[0] + '\n' + key_part + ': ' + value_part.strip() + '截断"'
                    
                    # 补全缺失的花括号
                    for _ in range(open_braces - close_braces):
                        fixed_content += '}'
            
            # 尝试解析修复后的JSON
            try:
                json.loads(fixed_content)
                print(f"✅ JSON修复成功")
                return fixed_content
            except json.JSONDecodeError:
                print(f"❌ JSON修复失败，返回原内容")
                return json_content
    
    def generate_batch_summaries(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为多个对话批量生成摘要
        
        Args:
            conversations: 对话列表
            
        Returns:
            摘要列表
        """
        summaries = []
        total_conversations = len(conversations)
        
        print(f"🔄 开始批量生成 {total_conversations} 个对话摘要...")
        
        for i, conversation in enumerate(conversations):
            try:
                user_message = conversation.get('user', '')
                assistant_message = conversation.get('assistant', '')
                
                if not user_message:
                    print(f"⚠️ 第 {i + 1} 轮对话用户消息为空，跳过摘要生成")
                    summaries.append({
                        'conversation_index': i + 1,
                        'success': False,
                        'error': '用户消息为空'
                    })
                    continue
                
                print(f"📝 生成第 {i + 1} 轮对话摘要...")
                
                # 生成摘要
                summary_result = self.generate_summary(user_message, assistant_message)
                summary_result['conversation_index'] = i + 1
                summaries.append(summary_result)
                
                if summary_result['success']:
                    print(f"✅ 第 {i + 1} 轮对话摘要生成成功")
                else:
                    print(f"❌ 第 {i + 1} 轮对话摘要生成失败: {summary_result.get('error', 'Unknown error')}")
                
                # 短暂延迟，避免API请求过于频繁
                import time
                time.sleep(0.2)
                
            except Exception as e:
                print(f"❌ 第 {i + 1} 轮对话摘要生成异常: {e}")
                summaries.append({
                    'conversation_index': i + 1,
                    'success': False,
                    'error': str(e)
                })
        
        successful_summaries = len([s for s in summaries if s.get('success', False)])
        print(f"✅ 批量摘要生成完成: {successful_summaries}/{total_conversations}")
        
        return summaries
    
    def get_summary_statistics(self, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取摘要统计信息"""
        total_summaries = len(summaries)
        successful_summaries = len([s for s in summaries if s.get('success', False)])
        
        # 统计涉及的医疗系统
        medical_systems = {}
        risk_levels = {}
        
        for summary in summaries:
            if summary.get('success') and 'summary' in summary:
                summary_data = summary['summary']
                
                # 统计医疗系统
                system = summary_data.get('涉及系统', '未知')
                medical_systems[system] = medical_systems.get(system, 0) + 1
                
                # 统计风险等级
                risk = summary_data.get('风险评估', '未知')
                risk_levels[risk] = risk_levels.get(risk, 0) + 1
        
        return {
            'total_summaries': total_summaries,
            'successful_summaries': successful_summaries,
            'success_rate': round(successful_summaries / total_summaries * 100, 2) if total_summaries > 0 else 0,
            'medical_systems': medical_systems,
            'risk_levels': risk_levels
        }
