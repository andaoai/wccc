#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信数据回调处理模块
专门处理微信数据采集器的回调函数，包括群聊过滤和数据处理逻辑
"""

import time
import json
from typing import Dict, List
from ai.glm_agent import GLMAgent

# 定义需要监听的群聊列表（建筑相关群聊）
MONITORED_GROUPS = [
    "47606308433@chatroom",  # 机电工程交流
    "45692733938@chatroom",  # 建筑资质群3
    "23656456137@chatroom",  # 浙江建筑资质交流群
    "51961740237@chatroom",  # 建筑资质工程资质证书6
    "23488895708@chatroom",  # 宁波 赛冠 资质证书交流群（6）
    "23700138315@chatroom",  # 资质交流群
    "51844141003@chatroom"   # 建筑群-T-02283
]

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
    construction_prompt = load_prompt_from_file("wechat_msg_prompt.md")
    # 创建AI Agent
    wechat_msg_agent = GLMAgent(api_key="9ea7ae31c7864b8a9e696ecdbd062820.KBM8KO07X9dgTjRi")

    # 调用AI进行处理 - 使用系统提示词
    response = wechat_msg_agent.chat(
        msg['content'],  # 用户消息：测试数据
        session_id="construction_test",
        system_prompt=construction_prompt,  # 系统提示词：完整的提示词
        temperature=0.1  # 使用较低的温度以确保输出的准确性
    )
    print(f"AI响应: {response}")

    # 验证JSON格式
    try:
        json_data = json.loads(response)
        print(f"✅ JSON格式验证通过，数据类型: {type(json_data)}")
        if isinstance(json_data, list):
            print(f"📊 解析到 {len(json_data)} 条数据")
        for item in json_data:
            print(f"- {item['certificates']}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON格式验证失败: {e}")
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")

    print(f"完成处理消息: {msg['msg_id']}")


def create_monitored_callback(monitored_groups: List[str],
                           processing_func=None,
                           processing_time: float = 0):
    """
    创建自定义的群聊监听回调函数

    Args:
        monitored_groups (List[str]): 需要监听的群聊ID列表
        processing_func (callable, optional): 自定义处理函数，接收data参数
        processing_time (float): 模拟处理时间（秒）

    Returns:
        callable: 配置好的回调函数
    """
    def custom_callback(data: Dict):
        msg = data['message']

        # 只处理群聊消息
        if msg['from_type'] != 2:
            return

        # 过滤只监听指定群聊
        if msg['from_wxid'] not in monitored_groups:
            return

        # 使用自定义处理函数或默认处理逻辑
        if processing_func:
            processing_func(data)
        else:
            # 默认处理逻辑
            group_name = data['group_info']['group_name']
            print(f"处理消息 [{group_name}]: {msg['content'][:50]}...")

            if processing_time > 0:
                time.sleep(processing_time)

            print(f"完成处理: {msg['msg_id']}")

    return custom_callback


# 可以定义其他专业的处理函数
def construction_cert_processor(data: Dict):
    """
    建筑资质证书专用处理器
    专门处理建筑相关的证书交易信息
    """
    msg = data['message']
    group_name = data['group_info']['group_name']

    # 这里可以添加AI分析、数据提取等逻辑
    print(f"🏗️ 建筑资质处理器 - 群聊: {group_name}")
    print(f"📝 消息内容: {msg['content']}")

    # 可以调用AI模块进行数据分析
    # 例如：提取证书类型、价格、地区等信息

    time.sleep(5)  # 模拟AI处理时间
    print(f"✅ 建筑资质数据处理完成: {msg['msg_id']}")