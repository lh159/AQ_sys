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
            with open("config.yaml", 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
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
        
        try:
            # 调用LLM进行标签提取
            llm_response = self.llm_client.chat.completions.create(
                model=self.config.get('llm', {}).get('model', 'deepseek-chat'),
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=self.config.get('llm', {}).get('max_tokens', 1000),
                temperature=self.config.get('llm', {}).get('temperature', 0.3),
                response_format={"type": "json_object"}
            ).choices[0].message.content
            
            # 解析LLM响应
            extracted_tags = self._parse_llm_response(llm_response, text)
            
            print(f"📋 成功提取标签，共 {sum(len(tags) for tags in extracted_tags.values())} 个")
            return extracted_tags
            
        except Exception as e:
            print(f"❌ 标签提取错误: {e}")
            return {}
    
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
    
    def _parse_llm_response(self, response: str, original_text: str) -> Dict[str, List[TagInfo]]:
        """解析LLM响应为结构化标签"""
        try:
            tag_data = json.loads(response)
            parsed_tags = {}
            
            # 遍历一级标签
            for level1_name, level2_dict in tag_data.items():
                if level1_name not in parsed_tags:
                    parsed_tags[level1_name] = []
                
                # 遍历二级标签
                for level2_name, tag_list in level2_dict.items():
                    for tag_info in tag_list:
                        tag = TagInfo(
                            name=tag_info.get("tag_name", ""),
                            confidence=float(tag_info.get("confidence", 0.5)),
                            evidence=tag_info.get("evidence", ""),
                            category=level1_name,
                            subcategory=level2_name
                        )
                        parsed_tags[level1_name].append(tag)
            
            return parsed_tags
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            print(f"LLM响应内容: {response}")
            return {}
        except Exception as e:
            print(f"❌ 解析LLM响应错误: {e}")
            return {}
