#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试批量分析功能的脚本
"""

import requests
import json

# 服务器地址
BASE_URL = "http://127.0.0.1:8080"

def test_batch_analysis():
    """测试完整的批量分析流程"""
    
    # 创建会话
    session = requests.Session()
    
    print("🚀 开始测试批量分析功能...")
    
    # 1. 先建立用户会话
    print("\n1. 建立用户会话...")
    chat_response = session.post(f"{BASE_URL}/api/chat", json={
        "message": "初始化会话"
    })
    
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        print(f"✅ 会话建立成功，用户ID: {chat_data.get('user_id', 'unknown')}")
    else:
        print(f"❌ 会话建立失败: {chat_response.status_code}")
        return
    
    # 2. 上传文件进行解析
    print("\n2. 上传文件进行解析...")
    with open("test_conversations.txt", "rb") as f:
        upload_response = session.post(f"{BASE_URL}/api/upload_file", files={
            "file": ("test_conversations.txt", f, "text/plain")
        })
    
    if upload_response.status_code == 200:
        upload_data = upload_response.json()
        if upload_data["success"]:
            print(f"✅ 文件上传成功: {upload_data['parse_status']}")
            print(f"📊 总对话数: {upload_data['total_conversations']}")
            print(f"✅ 有效对话数: {upload_data['valid_conversations']}")
        else:
            print(f"❌ 文件上传失败: {upload_data['error']}")
            return
    else:
        print(f"❌ 文件上传失败: {upload_response.status_code}")
        return
    
    # 3. 开始批量分析
    print("\n3. 开始批量分析...")
    with open("test_conversations.txt", "r", encoding="utf-8") as f:
        file_content = f.read()
    
    analysis_response = session.post(f"{BASE_URL}/api/analyze_file", json={
        "file_content": file_content,
        "file_name": "test_conversations.txt"
    })
    
    if analysis_response.status_code == 200:
        analysis_data = analysis_response.json()
        if analysis_data["success"]:
            result = analysis_data["analysis_result"]
            
            print("✅ 批量分析完成!")
            print(f"📊 分析统计:")
            print(f"   总对话数: {result['total_conversations']}")
            print(f"   成功处理: {result['processed_conversations']}")
            print(f"   提取标签: {result['total_extracted_tags']}")
            print(f"   更新标签: {result['total_updated_tags']}")
            
            # 显示用户画像
            user_profile = result.get('user_profile')
            if user_profile:
                print(f"📈 用户画像:")
                print(f"   成熟度: {user_profile['profile_maturity']:.2%}")
                print(f"   交互次数: {user_profile['total_interactions']}")
                
                # 显示标签维度
                tag_dimensions = user_profile.get('tag_dimensions', {})
                for level1, level2_dict in tag_dimensions.items():
                    for level2, tag_list in level2_dict.items():
                        if tag_list:
                            print(f"   {level1} -> {level2}: {len(tag_list)} 个标签")
                            for tag in tag_list[:2]:  # 显示前2个标签
                                print(f"     - {tag['tag_name']} (置信度: {tag['confidence']:.2f})")
            
            # 显示分析摘要
            summary = result.get('summary', {})
            if summary:
                print(f"📋 分析摘要:")
                print(f"   成功率: {summary['success_rate']:.1f}%")
                print(f"   平均每轮标签数: {summary['average_tags_per_conversation']:.1f}")
                print(f"   标签类别分布: {summary['tag_categories']}")
            
        else:
            print(f"❌ 批量分析失败: {analysis_data['error']}")
    else:
        print(f"❌ 批量分析请求失败: {analysis_response.status_code}")
        print(f"响应内容: {analysis_response.text}")

if __name__ == "__main__":
    test_batch_analysis()
