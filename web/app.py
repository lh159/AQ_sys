#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AQ-用户标签系统 Flask Web应用 - 文件上传分析版本
"""

from flask import Flask, render_template, request, jsonify, session
import uuid
import json
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
print(f"📂 项目根目录: {project_root}")
print(f"🔍 Python路径: {sys.path[:3]}")  # 只显示前3个路径

from app.core.tag_extractor import TagExtractor
from app.core.tag_manager import TagManager
from app.core.file_parser import FileParser
from app.core.batch_analyzer import BatchAnalyzer

app = Flask(__name__)
app.secret_key = 'aq_tag_system_secret_key_2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """获取用户画像接口"""
    try:
        if 'user_id' not in session:
            return jsonify({
                "success": False,
                "error": "用户会话未初始化"
            }), 400
        
        user_id = session['user_id']
        tag_manager = TagManager(user_id)
        user_profile = tag_manager.get_user_tags()
        
        return jsonify({
            "success": True,
            "user_profile": user_profile.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取用户画像失败: {str(e)}"
        }), 500

@app.route('/api/timeline', methods=['GET'])
def get_timeline():
    """获取标签变化时间线"""
    try:
        if 'user_id' not in session:
            return jsonify({
                "success": False,
                "error": "用户会话未初始化"
            }), 400
        
        user_id = session['user_id']
        tag_manager = TagManager(user_id)
        timeline = tag_manager.get_tag_timeline()
        
        return jsonify({
            "success": True,
            "timeline": timeline
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取时间线失败: {str(e)}"
        }), 500

@app.route('/api/reset_user', methods=['POST'])
def reset_user():
    """重置用户会话"""
    old_user_id = session.get('user_id', 'none')
    session.pop('user_id', None)
    
    print(f"🔄 重置用户会话: {old_user_id}")
    
    return jsonify({
        "success": True,
        "message": "用户会话已重置，下次分析将创建新的用户画像"
    })

@app.route('/api/upload_file', methods=['POST'])
def upload_file():
    """文件上传和批量分析接口"""
    try:
        # 检查用户会话
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
            print(f"🆔 创建新用户会话: {session['user_id']}")
        
        user_id = session['user_id']
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "未选择文件"
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "未选择文件"
            }), 400
        
        # 检查文件类型
        allowed_extensions = {'.txt', '.json', '.md'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            return jsonify({
                "success": False,
                "error": f"不支持的文件类型：{file_extension}。支持的类型：{', '.join(allowed_extensions)}"
            }), 400
        
        # 读取文件内容
        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return jsonify({
                "success": False,
                "error": "文件编码错误，请确保文件为UTF-8编码"
            }), 400
        
        # 解析文件
        conversations, parse_status = FileParser.parse_file(file.filename, content)
        
        if not conversations:
            return jsonify({
                "success": False,
                "error": f"文件解析失败或未找到有效对话：{parse_status}"
            }), 400
        
        # 验证对话数据
        valid_conversations = FileParser.validate_conversations(conversations)
        
        if not valid_conversations:
            return jsonify({
                "success": False,
                "error": "文件中没有找到有效的对话内容"
            }), 400
        
        print(f"📁 文件解析成功: {file.filename}")
        print(f"📊 解析状态: {parse_status}")
        print(f"✅ 有效对话数: {len(valid_conversations)}")
        
        # 保存文件内容到会话中，以便后续分析使用
        session['uploaded_file_content'] = content
        session['uploaded_file_name'] = file.filename
        session['valid_conversations'] = valid_conversations
        
        # 返回解析结果，等待用户确认
        return jsonify({
            "success": True,
            "message": "文件解析成功",
            "parse_status": parse_status,
            "total_conversations": len(conversations),
            "valid_conversations": len(valid_conversations),
            "preview": valid_conversations[:3] if valid_conversations else [],  # 预览前3条
            "ready_for_analysis": True
        })
        
    except Exception as e:
        print(f"❌ 文件上传处理失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"文件处理失败: {str(e)}"
        }), 500

@app.route('/api/analyze_file', methods=['POST'])
def analyze_file():
    """批量分析文件中的对话"""
    try:
        # 检查用户会话
        if 'user_id' not in session:
            return jsonify({
                "success": False,
                "error": "用户会话未初始化"
            }), 400
        
        user_id = session['user_id']
        data = request.json or {}
        
        # 尝试从前端传递的数据获取文件内容
        file_content = data.get('file_content', '')
        file_name = data.get('file_name', '')
        
        # 如果前端没有传递，尝试从会话中获取
        if not file_content and 'uploaded_file_content' in session:
            file_content = session['uploaded_file_content']
            file_name = session.get('uploaded_file_name', 'unknown.txt')
            print("📋 使用会话中保存的文件内容")
        
        if not file_content:
            return jsonify({
                "success": False,
                "error": "文件内容为空，请先上传文件"
            }), 400
        
        # 解析对话
        print(f"📄 解析文件: {file_name}")
        conversations, parse_status = FileParser.parse_file(file_name, file_content)
        print(f"📊 解析结果: {parse_status}, 对话数: {len(conversations)}")
        
        valid_conversations = FileParser.validate_conversations(conversations)
        print(f"✅ 有效对话数: {len(valid_conversations)}")
        
        # 调试：打印前几个对话的格式
        for i, conv in enumerate(valid_conversations[:2]):
            print(f"🔍 对话 {i+1}: {type(conv)} - {conv}")
            if isinstance(conv, dict):
                print(f"   用户: {conv.get('user', 'N/A')}")
                print(f"   助手: {conv.get('assistant', 'N/A')}")
            else:
                print(f"   ❌ 非字典格式: {conv}")
        
        if not valid_conversations:
            return jsonify({
                "success": False,
                "error": "没有找到有效的对话内容"
            }), 400
        
        # 初始化分析器
        print(f"🔧 初始化分析器...")
        tag_extractor = TagExtractor(user_id)
        tag_manager = TagManager(user_id)
        batch_analyzer = BatchAnalyzer(tag_extractor, tag_manager, user_id)
        
        # 检查是否需要生成摘要
        generate_summaries = data.get('generate_summaries', True)  # 默认生成摘要
        print(f"📝 生成摘要: {'是' if generate_summaries else '否'}")
        
        # 使用整体分析模式
        print(f"🔧 分析模式: 整体分析")
        
        # 执行批量分析
        print(f"🚀 开始批量分析 {len(valid_conversations)} 轮对话...")
        
        try:
            analysis_result = batch_analyzer.analyze_conversations(
                user_id=user_id,
                conversations=valid_conversations,
                generate_summaries=generate_summaries
            )
            
            print(f"✅ 批量分析完成!")
            return jsonify({
                "success": True,
                "message": "批量分析完成",
                "analysis_result": analysis_result
            })
            
        except Exception as analysis_error:
            print(f"❌ 分析过程出错: {str(analysis_error)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": f"分析过程出错: {str(analysis_error)}"
            }), 500
        
    except Exception as e:
        print(f"❌ 批量分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"批量分析失败: {str(e)}"
        }), 500

@app.route('/api/conversation_summaries', methods=['GET'])
def get_conversation_summaries():
    """获取最近分析的对话摘要"""
    try:
        # 检查用户会话
        if 'user_id' not in session:
            return jsonify({
                "success": False,
                "error": "用户会话未初始化"
            }), 400
        
        user_id = session['user_id']
        
        # 使用摘要管理器获取摘要数据
        from app.core.summary_manager import SummaryManager
        summary_manager = SummaryManager(user_id)
        
        # 获取最近20个摘要
        limit = request.args.get('limit', 20, type=int)
        summaries = summary_manager.get_summaries(limit=limit)
        summary_stats = summary_manager.get_summary_stats()
        
        return jsonify({
            "success": True,
            "message": "对话摘要获取成功",
            "summaries": summaries,
            "stats": summary_stats
        })
        
    except Exception as e:
        print(f"❌ 获取对话摘要失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取对话摘要失败: {str(e)}"
        }), 500

@app.route('/api/analysis_progress', methods=['GET'])
def get_analysis_progress():
    """获取分析进度（WebSocket的简化版本）"""
    # 这里可以实现进度查询逻辑
    # 当前版本返回静态信息
    return jsonify({
        "success": True,
        "progress": {
            "current": 0,
            "total": 0,
            "message": "等待开始分析...",
            "completed": True
        }
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取系统统计信息"""
    try:
        if 'user_id' not in session:
            return jsonify({
                "success": False,
                "error": "用户会话未初始化"
            }), 400
        
        user_id = session['user_id']
        tag_manager = TagManager(user_id)
        user_profile = tag_manager.get_user_tags()
        timeline = tag_manager.get_tag_timeline()
        
        # 计算统计信息
        total_dimensions = len(user_profile.dimension_summaries)
        total_tags = sum(
            len(tags) 
            for level2_dict in user_profile.tag_dimensions.values()
            for tags in level2_dict.values()
        )
        confident_tags = sum(
            len([t for t in tags if t.confidence >= 0.6])
            for level2_dict in user_profile.tag_dimensions.values()
            for tags in level2_dict.values()
        )
        
        stats = {
            "user_id": user_id,
            "total_interactions": user_profile.total_interactions,
            "total_dimensions": total_dimensions,
            "total_tags": total_tags,
            "confident_tags": confident_tags,
            "profile_maturity": user_profile.profile_maturity,
            "timeline_events": len(timeline.get("tag_events", [])),
            "created_at": user_profile.created_at,
            "last_updated": user_profile.last_updated
        }
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取统计信息失败: {str(e)}"
        }), 500

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        "success": False,
        "error": "页面不存在"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({
        "success": False,
        "error": "服务器内部错误"
    }), 500

if __name__ == '__main__':
    print("🚀 启动 AQ-用户标签系统（文件上传分析版本）...")
    app.run(debug=True, host='127.0.0.1', port=8080)
