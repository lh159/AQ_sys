#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签提取器 - 从用户文本中提取结构化标签
"""

import json
import yaml
import openai
from datetime import datetime
from typing import Dict, List
from app.core.models import TagInfo
from app.core.config_manager import ConfigManager

class TagExtractor:
    """标签提取器类"""
    
    def __init__(self, user_id: str):
        """初始化标签提取器"""
        self.user_id = user_id
        self.config = self._load_config()
        self.llm_client = self._create_llm_client()
        self.tag_schema = self._load_tag_schema()
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            return ConfigManager.load_config()
        except Exception as e:
            print(f"警告: 无法加载配置文件: {e}")
            return {}
            
    def _create_llm_client(self):
        """创建LLM客户端"""
        llm_config = self.config.get('llm', {})
        api_key = llm_config.get('api_key')
        base_url = llm_config.get('base_url')
        
        if not api_key:
            raise ValueError("配置文件中缺少API key")
        
        return openai.OpenAI(api_key=api_key, base_url=base_url)
    
    def _load_tag_schema(self) -> Dict:
        """加载标签体系定义"""
        try:
            with open("tag_schema.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 无法加载标签体系文件: {e}")
            return {}
    
    def extract_tags_from_text(self, text: str, context: Dict = None) -> Dict[str, List[TagInfo]]:
        """从文本中提取标签"""
        extraction_prompt = self._build_extraction_prompt(text, context)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 调用LLM进行标签提取，增加max_tokens避免截断
                llm_response = self.llm_client.chat.completions.create(
                    model=self.config.get('llm', {}).get('model', 'deepseek-reasoner'),
                    messages=[{"role": "user", "content": extraction_prompt}],
                    max_tokens=4096,  # 增加token限制避免JSON截断
                    temperature=self.config.get('llm', {}).get('temperature', 0.1)
                    # 注意：DeepSeek R1可能不支持response_format参数，所以移除它
                ).choices[0].message.content
                
                # 解析LLM响应
                extracted_tags = self._parse_llm_response(llm_response, text)
                
                # 如果成功解析到标签，返回结果
                if extracted_tags:
                    print(f"📋 成功提取标签，共 {sum(len(tags) for tags in extracted_tags.values())} 个")
                    return extracted_tags
                
                # 如果没有解析到标签，可能是正常情况（文本中确实没有相关标签）
                print(f"📋 成功提取标签，共 0 个")
                return {}
                
            except Exception as e:
                print(f"❌ 标签提取第 {attempt + 1} 次尝试失败: {e}")
                if attempt == max_retries - 1:
                    print(f"❌ 经过 {max_retries} 次尝试，标签提取失败")
                    return {}
                
                # 等待一段时间后重试
                import time
                time.sleep(1)
    
    def _build_extraction_prompt(self, text: str, context: Dict = None) -> str:
        """构建用于标签提取的Prompt"""
        
        # 构建标签体系说明
        tag_system_desc = "## 标签体系结构\n\n"
        
        for level1_tag in self.tag_schema.get("user_tags_system", []):
            tag_system_desc += f"### {level1_tag['level_1_tag']}\n"
            tag_system_desc += f"{level1_tag['description']}\n\n"
            
            for level2_tag in level1_tag.get("level_2_tags", []):
                tag_system_desc += f"#### {level2_tag['level_2_tag']}\n"
                for value in level2_tag.get("values", []):
                    tag_system_desc += f"- **{value['name']}**: {value['description']}\n"
                tag_system_desc += "\n"
        
        prompt = f"""你是一个专业的用户画像分析师，专门分析医疗健康领域的用户对话，从中提取用户标签。

{tag_system_desc}

## 分析任务
请分析以下用户文本，从上述标签体系中提取适合的标签：

**用户文本**: "{text}"

## 输出要求
1. 仔细分析文本内容，判断用户可能的年龄段、性别、健康角色、意图等
2. 只提取有明确证据的标签，不要过度推测
3. 每个标签提供0.1-1.0的置信度评分
4. 必须提供从原文中提取的证据

## 输出格式
请严格按照以下JSON格式输出，所有字段都是必需的：

{{
  "用户核心画像": {{
    "年龄段": [
      {{
        "tag_name": "具体年龄段标签",
        "confidence": 0.8,
        "evidence": "从原文提取的支持证据",
        "subcategory": "年龄段"
      }}
    ],
    "性别": [],
    "所在地区": [],
    "健康角色": []
  }},
  "产品使用路径与偏好": {{
    "核心功能偏好": [],
    "交互方式偏好": []
  }},
  "用户意图与转化阶段": {{
    "具体意图分类": [],
    "转化阶段": []
  }},
  "用户商业价值": {{
    "价值等级": [],
    "付费敏感度": []
  }}
}}

注意：
- 如果某个子类别没有匹配的标签，请保持空数组 []
- 置信度要基于文本证据的强度合理评估
- 证据必须是原文的直接引用或合理概括"""

        return prompt
    
    def _fix_truncated_json(self, json_str: str) -> str:
        """尝试修复截断的JSON字符串"""
        import re
        
        # 移除首尾空白
        json_str = json_str.strip()
        
        # 如果不是以{开头，尝试找到第一个{
        if not json_str.startswith('{'):
            match = re.search(r'\{', json_str)
            if match:
                json_str = json_str[match.start():]
            else:
                return json_str
        
        # 检查是否在字符串值中截断
        if json_str.count('"') % 2 != 0:
            # 在字符串中截断，需要闭合字符串
            json_str += '"'
        
        # 如果最后一个字符不是标点符号，可能需要添加适当的结构
        if json_str and json_str[-1] not in '"}],':
            # 检查最后的上下文来决定如何结束
            if '"' in json_str[-20:]:  # 如果最近有引号，可能是在对象值中
                json_str += '"'
        
        # 计算花括号和方括号的平衡
        open_braces = 0
        close_braces = 0
        open_brackets = 0
        close_brackets = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(json_str):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    open_braces += 1
                elif char == '}':
                    close_braces += 1
                elif char == '[':
                    open_brackets += 1
                elif char == ']':
                    close_brackets += 1
        
        # 补全缺失的方括号和花括号
        missing_brackets = open_brackets - close_brackets
        missing_braces = open_braces - close_braces
        
        if missing_brackets > 0:
            json_str += ']' * missing_brackets
        
        if missing_braces > 0:
            json_str += '}' * missing_braces
        
        return json_str
    
    def _extract_tags_from_text_fallback(self, response: str) -> Dict:
        """从文本中提取标签的回退方法"""
        import re
        
        # 简化的标签提取，适用于解析失败的情况
        # 由于JSON解析失败，我们直接返回空结果，让系统继续运行
        print("⚠️ 使用回退标签提取方法")
        
        # 尝试从文本中提取一些基本信息
        fallback_data = {}
        
        # 查找年龄相关信息
        age_match = re.search(r'(\d+)\s*岁', response)
        if age_match:
            age = int(age_match.group(1))
            if age < 18:
                age_group = "未成年 (0-17岁)"
            elif age <= 40:
                age_group = "青年 (18-40岁)"
            elif age <= 60:
                age_group = "中年 (41-60岁)"
            else:
                age_group = "老年 (60岁以上)"
            
            fallback_data["用户核心画像"] = {
                "年龄段": [{"tag_name": age_group, "confidence": 0.8, "evidence": age_match.group(0)}]
            }
        
        return fallback_data
    
    def _parse_llm_response(self, response: str, original_text: str) -> Dict[str, List[TagInfo]]:
        """解析LLM响应为结构化标签"""
        # 尝试多种解析方式
        tag_data = None
        
        # 方式1: 直接解析JSON
        try:
            tag_data = json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 方式2: 提取```json代码块中的内容
        if tag_data is None:
            try:
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    tag_data = json.loads(json_match.group(1))
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # 方式3: 提取花括号内容
        if tag_data is None:
            try:
                import re
                # 查找第一个完整的JSON对象
                brace_match = re.search(r'\{.*\}', response, re.DOTALL)
                if brace_match:
                    json_content = brace_match.group(0)
                    # 尝试修复截断的JSON
                    json_content = self._fix_truncated_json(json_content)
                    tag_data = json.loads(json_content)
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # 如果仍然无法解析，尝试修复截断的JSON
        if tag_data is None:
            try:
                fixed_json = self._fix_truncated_json(response)
                tag_data = json.loads(fixed_json)
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # 如果仍然无法解析，尝试使用更宽容的方法
        if tag_data is None:
            try:
                # 尝试从响应中提取任何可能的标签信息
                tag_data = self._extract_tags_from_text_fallback(response)
            except Exception:
                pass
        
        # 如果仍然无法解析，返回空结果
        if tag_data is None:
            print(f"❌ 无法解析LLM响应为JSON格式")
            print(f"LLM响应内容 (前500字符): {response[:500]}...")
            return {}
        
        try:
            parsed_tags = {}
            
            # 遍历一级标签
            for level1_name, level2_dict in tag_data.items():
                if level1_name not in parsed_tags:
                    parsed_tags[level1_name] = []
                
                # 确保 level2_dict 是字典类型
                if not isinstance(level2_dict, dict):
                    print(f"⚠️ 一级标签 {level1_name} 的值不是字典类型: {type(level2_dict)}")
                    continue
                
                # 遍历二级标签
                for level2_name, tag_list in level2_dict.items():
                    # 确保 tag_list 是列表类型
                    if not isinstance(tag_list, list):
                        print(f"⚠️ 二级标签 {level2_name} 的值不是列表类型: {type(tag_list)}")
                        continue
                    
                    for tag_info in tag_list:
                        # 确保 tag_info 是字典类型
                        if not isinstance(tag_info, dict):
                            print(f"⚠️ 标签信息不是字典类型: {type(tag_info)}")
                            continue
                        
                        tag = TagInfo(
                            name=tag_info.get("tag_name", ""),
                            confidence=float(tag_info.get("confidence", 0.5)),
                            evidence=tag_info.get("evidence", ""),
                            category=level1_name,
                            subcategory=level2_name
                        )
                        parsed_tags[level1_name].append(tag)
            
            return parsed_tags
            
        except Exception as e:
            print(f"❌ 解析LLM响应错误: {e}")
            print(f"LLM响应内容: {response}")
            return {}
