"""
文件解析器模块
支持 txt、json、md 格式的对话文件解析
"""

import json
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path


class FileParser:
    """文件解析器，支持多种格式的对话文件"""
    
    @staticmethod
    def parse_txt_file(content: str) -> List[Dict[str, Any]]:
        """
        解析txt格式的对话文件
        支持以下格式：
        1. 用户：xxx\nAI：xxx
        2. Q：xxx\nA：xxx
        3. Human：xxx\nAssistant：xxx
        4. 我：xxx\n系统：xxx
        """
        conversations = []
        
        # 多种对话分隔符模式
        patterns = [
            r'用户[：:]\s*(.*?)\s*(?:AI|助手|系统)[：:]\s*(.*?)(?=用户[：:]|$)',
            r'Q[：:]\s*(.*?)\s*A[：:]\s*(.*?)(?=Q[：:]|$)',
            r'Human[：:]\s*(.*?)\s*Assistant[：:]\s*(.*?)(?=Human[：:]|$)',
            r'我[：:]\s*(.*?)\s*(?:系统|AI)[：:]\s*(.*?)(?=我[：:]|$)',
            r'问[：:]\s*(.*?)\s*答[：:]\s*(.*?)(?=问[：:]|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            if matches:
                for user_msg, ai_msg in matches:
                    conversations.append({
                        'user': user_msg.strip(),
                        'assistant': ai_msg.strip(),
                        'timestamp': None
                    })
                break
        
        # 如果没有匹配到标准格式，尝试按行分割
        if not conversations:
            lines = content.strip().split('\n')
            current_user = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检查是否是用户输入
                if any(prefix in line for prefix in ['用户:', '我:', 'Q:', 'Human:', '问:']):
                    current_user = re.sub(r'^(用户|我|Q|Human|问)[：:]?\s*', '', line)
                elif any(prefix in line for prefix in ['AI:', '助手:', 'A:', 'Assistant:', '系统:', '答:']):
                    if current_user:
                        ai_response = re.sub(r'^(AI|助手|A|Assistant|系统|答)[：:]?\s*', '', line)
                        conversations.append({
                            'user': current_user,
                            'assistant': ai_response,
                            'timestamp': None
                        })
                        current_user = None
        
        return conversations
    
    @staticmethod
    def parse_json_file(content: str) -> List[Dict[str, Any]]:
        """
        解析JSON格式的对话文件
        支持以下结构：
        1. {"conversations": [{"user": "xxx", "assistant": "xxx"}]}
        2. [{"user": "xxx", "assistant": "xxx"}]
        3. {"messages": [{"role": "user", "content": "xxx"}, {"role": "assistant", "content": "xxx"}]}
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {e}")
        
        conversations = []
        
        # 格式1: {"conversations": [...]}
        if isinstance(data, dict) and 'conversations' in data:
            for conv in data['conversations']:
                if 'user' in conv and 'assistant' in conv:
                    conversations.append({
                        'user': conv['user'],
                        'assistant': conv['assistant'],
                        'timestamp': conv.get('timestamp')
                    })
        
        # 格式2: [{"user": "xxx", "assistant": "xxx"}]
        elif isinstance(data, list) and data and 'user' in data[0]:
            for conv in data:
                if 'user' in conv and 'assistant' in conv:
                    conversations.append({
                        'user': conv['user'],
                        'assistant': conv['assistant'],
                        'timestamp': conv.get('timestamp')
                    })
        
        # 格式3: OpenAI消息格式
        elif isinstance(data, dict) and 'messages' in data:
            messages = data['messages']
            user_msg = None
            
            for msg in messages:
                if msg.get('role') == 'user':
                    user_msg = msg.get('content', '')
                elif msg.get('role') == 'assistant' and user_msg:
                    conversations.append({
                        'user': user_msg,
                        'assistant': msg.get('content', ''),
                        'timestamp': msg.get('timestamp')
                    })
                    user_msg = None
        
        # 格式4: 纯消息列表
        elif isinstance(data, list) and data and 'role' in data[0]:
            user_msg = None
            
            for msg in data:
                if msg.get('role') == 'user':
                    user_msg = msg.get('content', '')
                elif msg.get('role') == 'assistant' and user_msg:
                    conversations.append({
                        'user': user_msg,
                        'assistant': msg.get('content', ''),
                        'timestamp': msg.get('timestamp')
                    })
                    user_msg = None
        
        return conversations
    
    @staticmethod
    def parse_md_file(content: str) -> List[Dict[str, Any]]:
        """
        解析Markdown格式的对话文件
        支持以下格式：
        1. ## 用户\nxxx\n## 助手\nxxx
        2. **用户：** xxx\n**助手：** xxx
        3. > 用户：xxx\n> 助手：xxx
        """
        conversations = []
        
        # 格式1: 使用标题分隔
        pattern1 = r'##?\s*(?:用户|User|Human|我|问)[：:]?\s*\n(.*?)\n##?\s*(?:助手|Assistant|AI|系统|答)[：:]?\s*\n(.*?)(?=\n##?|$)'
        matches1 = re.findall(pattern1, content, re.DOTALL | re.IGNORECASE)
        
        if matches1:
            for user_msg, ai_msg in matches1:
                conversations.append({
                    'user': user_msg.strip(),
                    'assistant': ai_msg.strip(),
                    'timestamp': None
                })
        
        # 格式2: 使用粗体标记
        pattern2 = r'\*\*(?:用户|User|Human|我|问)[：:]?\*\*\s*(.*?)\s*\*\*(?:助手|Assistant|AI|系统|答)[：:]?\*\*\s*(.*?)(?=\*\*(?:用户|User|Human|我|问)|$)'
        matches2 = re.findall(pattern2, content, re.DOTALL | re.IGNORECASE)
        
        if matches2 and not conversations:
            for user_msg, ai_msg in matches2:
                conversations.append({
                    'user': user_msg.strip(),
                    'assistant': ai_msg.strip(),
                    'timestamp': None
                })
        
        # 格式3: 使用引用块
        pattern3 = r'>\s*(?:用户|User|Human|我|问)[：:]?\s*(.*?)\s*>\s*(?:助手|Assistant|AI|系统|答)[：:]?\s*(.*?)(?=>\s*(?:用户|User|Human|我|问)|$)'
        matches3 = re.findall(pattern3, content, re.DOTALL | re.IGNORECASE)
        
        if matches3 and not conversations:
            for user_msg, ai_msg in matches3:
                conversations.append({
                    'user': user_msg.strip(),
                    'assistant': ai_msg.strip(),
                    'timestamp': None
                })
        
        # 如果没有匹配到，尝试作为普通文本解析
        if not conversations:
            conversations = FileParser.parse_txt_file(content)
        
        return conversations
    
    @staticmethod
    def parse_file(file_path: str, content: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        根据文件扩展名自动选择解析器
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            Tuple[对话列表, 解析状态信息]
        """
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension == '.txt':
                conversations = FileParser.parse_txt_file(content)
                status = f"成功解析TXT文件，提取到 {len(conversations)} 轮对话"
                
            elif file_extension == '.json':
                conversations = FileParser.parse_json_file(content)
                status = f"成功解析JSON文件，提取到 {len(conversations)} 轮对话"
                
            elif file_extension == '.md':
                conversations = FileParser.parse_md_file(content)
                status = f"成功解析Markdown文件，提取到 {len(conversations)} 轮对话"
                
            else:
                # 尝试作为文本文件解析
                conversations = FileParser.parse_txt_file(content)
                status = f"未知文件格式，尝试作为文本解析，提取到 {len(conversations)} 轮对话"
            
            if not conversations:
                status = "警告：未能从文件中提取到有效的对话内容"
            
            return conversations, status
            
        except Exception as e:
            return [], f"文件解析失败: {str(e)}"
    
    @staticmethod
    def validate_conversations(conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证和清理对话数据"""
        valid_conversations = []
        
        for conv in conversations:
            user_msg = conv.get('user', '').strip()
            assistant_msg = conv.get('assistant', '').strip()
            
            # 过滤空对话和过短对话
            if user_msg and assistant_msg and len(user_msg) > 2 and len(assistant_msg) > 2:
                valid_conversations.append({
                    'user': user_msg,
                    'assistant': assistant_msg,
                    'timestamp': conv.get('timestamp')
                })
        
        return valid_conversations
