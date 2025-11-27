#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信数据回调处理模块
专门处理微信数据采集器的回调函数，包括群聊过滤和数据处理逻辑
"""

import time
import json
import sys
import os
from typing import Dict, List
from ai.glm_agent import GLMAgent
from db import wechat_message_dao, init_database
from db import WeChatMessageData
from .config import MONITORED_GROUPS


def json_to_wechat_message_data_list(json_data: List[Dict], callback_data: Dict = None) -> List[WeChatMessageData]:
    """
    将JSON数据转换为WeChatMessageData对象列表

    Args:
        json_data: AI返回的JSON数据列表
        callback_data: 回调数据，包含微信消息元数据

    Returns:
        List[WeChatMessageData]: 转换后的dataclass对象列表
    """
    if not isinstance(json_data, list):
        return []

    result = []

    # 提取微信元数据
    group_name = ""
    member_nick = ""
    group_wxid = ""
    member_wxid = ""
    msg_id = ""
    timestamp = ""

    if callback_data:
        msg = callback_data.get('message', {})
        group_info = callback_data.get('group_info', {})

        group_name = group_info.get('group_name', "")
        member_nick = group_info.get('member_nick', "")
        group_wxid = msg.get('from_wxid', "")
        member_wxid = msg.get('final_from_wxid', "")
        msg_id = msg.get('msg_id', "")
        timestamp = msg.get('timestamp', "")

    for item in json_data:
        if isinstance(item, dict):
            # 先创建基础的dataclass对象
            wechat_data = WeChatMessageData.from_dict(item)

            # 添加微信元数据
            wechat_data.group_name = group_name
            wechat_data.member_nick = member_nick
            wechat_data.group_wxid = group_wxid
            wechat_data.member_wxid = member_wxid
            wechat_data.msg_id = msg_id
            wechat_data.timestamp = timestamp

            # 设置原始信息为消息内容
            if not wechat_data.original_info and callback_data:
                msg_content = callback_data.get('message', {}).get('content', '')
                wechat_data.original_info = msg_content

            result.append(wechat_data)

    return result


def clean_ai_response(response: str) -> str:
    """清洗AI响应数据，移除markdown标记等"""
    if not isinstance(response, str):
        return str(response) if response else ""

    cleaned = response.strip()

    # 移除代码块标记
    if cleaned.startswith('```python'):
        cleaned = cleaned[9:]
    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]
    if cleaned.startswith('```'):
        cleaned = cleaned[3:]
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]

    return cleaned.strip()

def parse_json_response(response: str) -> dict:
    """解析JSON格式的AI响应"""
    try:
        cleaned_json = clean_ai_response(response)
        return json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return {}
    except Exception as e:
        print(f"❌ 处理JSON响应时发生错误: {e}")
        return {}

def parse_list_response(response: str) -> list:
    """解析列表格式的AI响应"""
    try:
        import ast
        cleaned_list = clean_ai_response(response)
        return ast.literal_eval(cleaned_list)
    except (ValueError, SyntaxError) as e:
        print(f"❌ 列表解析失败: {e}")
        # 备用方案：按逗号分割
        try:
            cleaned = clean_ai_response(response)
            return [cert.strip() for cert in cleaned.strip('[]').split(',') if cert.strip()]
        except:
            return []
    except Exception as e:
        print(f"❌ 处理列表响应时发生错误: {e}")
        return []

# MONITORED_GROUPS已移至config.py

def init_wechat_database():
    """初始化微信消息数据库"""
    try:
        print("🗄️ 初始化PostgreSQL数据库...")
        init_database()
        print("✅ 数据库初始化完成")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False

# 在模块加载时初始化数据库
_DB_INITIALIZED = init_wechat_database()

def load_prompt_from_file(prompt_file: str = "wechat_msg_prompt.md") -> str:
    """从文件加载提示词"""
    import os
    # 从bot目录回到根目录，再进入ai目录
    base_dir = os.path.dirname(os.path.dirname(__file__))
    prompt_path = os.path.join(base_dir, "ai", prompt_file)

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ 提示词文件 {prompt_path} 不存在")
        return ""
    except Exception as e:
        print(f"❌ 读取提示词文件失败: {e}")
        return ""

def data_callback(data: Dict):
    """
    数据回调函数示例

    Args:
        data (Dict): 回调数据，包含以下结构:
            {
                'message': {
                    'msg_id': str,                    # 消息ID
                    'from_type': int,                 # 消息类型 1:私聊 2:群聊 3:公众号
                    'from_wxid': str,                 # 来源wxid
                    'final_from_wxid': str,           # 最终发送者wxid
                    'msg_type': int,                  # 消息类型
                    'msg_source': int,                # 消息来源 0:别人发送 1:自己发送
                    'content': str,                   # 消息内容
                    'parsed_content': dict,           # 解析后的消息内容
                    'timestamp': str,                 # 时间戳
                    'member_count': int,              # 群成员数量
                    'silence': int,                   # 是否静默
                    'at_wxid_list': list,             # @用户列表
                    'signature': str                  # 签名
                },
                'group_info': {
                    'group_name': str,                # 群名称
                    'member_nick': str                # 发言者群昵称
                },
                'collection_metadata': {
                    'collector_version': str,         # 采集器版本
                    'collection_time': str,           # 采集时间
                    'stats': dict                     # 统计信息
                }
            }
    """
    msg = data['message']

    # 只处理群聊消息
    if msg['from_type'] != 2:  # 2表示群聊
        return
    # 只处理消息类型为文本的消息（可根据需要调整）
    if msg['msg_type'] != 1:  # 1表示文本消息
        return
    # 过滤只监听指定群聊
    if msg['from_wxid'] not in MONITORED_GROUPS:
        return

    # 这里可以添加数据清洗、存储等逻辑
    print(f"开始处理消息: {data['group_info']['group_name']} - {msg['content'][:50]}...")
    # 从文件加载建筑行业数据转换提示词
    wechat_msg_construction_prompt = load_prompt_from_file("wechat_msg_prompt.md")
    cert_split_construction_prompt = load_prompt_from_file("cert_split_prompt.md")

    # 文本结构化 AI Agent
    wechat_msg_agent = GLMAgent(api_key="9ea7ae31c7864b8a9e696ecdbd062820.KBM8KO07X9dgTjRi")
    # 证书拆分 AI Agent
    cert_split_agent = GLMAgent(api_key="9ea7ae31c7864b8a9e696ecdbd062820.KBM8KO07X9dgTjRi")
    # 调用AI进行处理 - 使用系统提示词
    response = wechat_msg_agent.chat(
        msg['content'],  # 用户消息：测试数据
        system_prompt=wechat_msg_construction_prompt,  # 系统提示词：完整的提示词
        temperature=0.1  # 使用较低的温度以确保输出的准确性
    )
    print(f"📝 微信消息AI响应: {response}")

    # 使用数据清洗函数解析JSON响应
    json_data = parse_json_response(response)
    if not json_data:
        print(f"❌ JSON解析失败，跳过证书拆分")
        return

    print(f"✅ JSON格式验证通过，数据类型: {type(json_data)}")

    # 转换为dataclass对象列表，传入回调数据以包含微信元数据
    wechat_data_list = json_to_wechat_message_data_list(json_data, data)
    if not wechat_data_list:
        print(f"❌ 转换为dataclass对象失败")
        return

    print(f"📊 解析到 {len(wechat_data_list)} 条数据")

    # 处理每条数据的证书信息
    for wechat_data in wechat_data_list:
        if not wechat_data.certificates:  # 使用dataclass属性访问
            continue

        print(f"🔍 处理证书: {wechat_data.certificates}")
        print(f"📋 交易类型: {wechat_data.type}")
        print(f"📍 地区: {wechat_data.location}")
        print(f"💰 价格: {wechat_data.price}")
        print(f"🛡️ 社保要求: {wechat_data.social_security}")
        # 显示微信元数据
        print(f"👥 群名称: {wechat_data.group_name}")
        print(f"👤 发送者: {wechat_data.member_nick} ({wechat_data.member_wxid})")
        print(f"🏷️ 群ID: {wechat_data.group_wxid}")
        print(f"📅 时间: {wechat_data.timestamp}")

        # 调用证书拆分AI
        cert_response = cert_split_agent.chat(
            wechat_data.certificates,  # 使用dataclass属性
            system_prompt=cert_split_construction_prompt,  # 系统提示词：完整的提示词
            temperature=0.1  # 使用较低的温度以确保输出的准确性
        )
        print(f"📋 证书拆分AI响应: {cert_response}")

        # 使用数据清洗函数解析证书列表
        cert_list = parse_list_response(cert_response)
        if cert_list:
            print(f"✅ 转换后的证书列表: {cert_list}")
            print(f"📊 证书类型: {type(cert_list)}, 数量: {len(cert_list)}")

            # 更新dataclass对象的证书信息，将拆分后的证书列表存储到对象中
            wechat_data.split_certificates = cert_list
            print(f"💾 已保存拆分后的证书列表到dataclass对象")

            # 存储到PostgreSQL数据库
            message_id = wechat_message_dao.insert_message(wechat_data)
            if message_id:
                print(f"🗄️ 已保存消息到数据库，ID: {message_id}")
            else:
                print(f"❌ 保存到数据库失败")
        else:
            print(f"❌ 证书列表解析失败")

        # 添加分隔线，便于阅读
        print("-" * 50)

    print(f"完成处理消息: {msg['msg_id']}")


