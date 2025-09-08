#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器 - 统一管理系统配置
"""

import yaml
import os
from typing import Dict, Any

class ConfigManager:
    """配置管理器类"""
    
    _config_cache = None
    _config_file = "config.yaml"
    
    @classmethod
    def _get_config_path(cls):
        """获取配置文件的绝对路径"""
        # 首先尝试当前目录
        current_dir_config = os.path.join(os.getcwd(), cls._config_file)
        if os.path.exists(current_dir_config):
            return current_dir_config
        
        # 然后尝试项目根目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(script_dir))  # 回到项目根目录
        root_config = os.path.join(root_dir, cls._config_file)
        if os.path.exists(root_config):
            return root_config
        
        # 最后返回默认路径
        return cls._config_file
    
    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """加载配置文件"""
        if cls._config_cache is None:
            cls._config_cache = cls._load_config_from_file()
        return cls._config_cache
    
    @classmethod
    def _load_config_from_file(cls) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            config_path = cls._get_config_path()
            
            if not os.path.exists(config_path):
                # 如果配置文件不存在，创建默认配置
                cls._create_default_config()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config if config else {}
                
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            return cls._get_default_config()
    
    @classmethod
    def _create_default_config(cls):
        """创建默认配置文件"""
        default_config = cls._get_default_config()
        try:
            with open(cls._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            print(f"✅ 已创建默认配置文件: {cls._config_file}")
        except Exception as e:
            print(f"❌ 创建默认配置文件失败: {e}")
    
    @classmethod
    def _get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'app': {
                'name': 'AQ-用户标签系统',
                'version': '1.0.0',
                'debug': True
            },
            'llm': {
                'provider': 'deepseek',
                'model': 'deepseek-r1',
                'api_key': '',
                'base_url': 'https://api.deepseek.com',
                'max_tokens': 4096,
                'temperature': 0.3
            },
            'storage': {
                'type': 'local',
                'base_path': './user_data',
                'backup_enabled': True,
                'cleanup_days': 90
            }
        }
    
    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """获取LLM配置"""
        config = cls.load_config()
        return config.get('llm', {})
    
    @classmethod
    def get_storage_config(cls) -> Dict[str, Any]:
        """获取存储配置"""
        config = cls.load_config()
        return config.get('storage', {})
    
    @classmethod
    def get_app_config(cls) -> Dict[str, Any]:
        """获取应用配置"""
        config = cls.load_config()
        return config.get('app', {})
    
    @classmethod
    def reload_config(cls):
        """重新加载配置"""
        cls._config_cache = None
        return cls.load_config()
    
    @classmethod
    def update_config(cls, updates: Dict[str, Any]):
        """更新配置"""
        try:
            current_config = cls.load_config()
            cls._deep_update(current_config, updates)
            
            with open(cls._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(current_config, f, default_flow_style=False, allow_unicode=True)
            
            # 重新加载缓存
            cls._config_cache = current_config
            print("✅ 配置更新成功")
            
        except Exception as e:
            print(f"❌ 配置更新失败: {e}")
    
    @staticmethod
    def _deep_update(base_dict: Dict, update_dict: Dict):
        """深度更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                ConfigManager._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
