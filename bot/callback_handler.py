#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信数据回调处理模块
专门处理微信数据采集器的回调函数，包括群聊过滤和数据处理逻辑
"""

import time
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from ai.glm_agent import GLMAgent


@dataclass
class WeChatMessageData:
    """微信消息数据结构规范"""
    type: str = ""                    # 交易类型（如：招聘、寻证、出场等）
    certificates: str = ""            # 原始证书信息（未拆分）
    social_security: str = ""         # 社保要求（如：唯一社保、转社保、无要求等）
    location: str = ""               # 地区信息（如：浙江省、宁波市等）
    price: int = 0                   # 价格信息
    other_info: str = ""             # 其他信息
    original_info: str = ""          # 原始消息内容
    split_certificates: Optional[List[str]] = None  # 证书拆分后的列表（前期可以为空）
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "type": self.type,
            "certificates": self.certificates,
            "social_security": self.social_security,
            "location": self.location,
            "price": self.price,
            "other_info": self.other_info,
            "original_info": self.original_info,
            "split_certificates": self.split_certificates
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WeChatMessageData':
        """从字典创建dataclass实例"""
        return cls(
            type=data.get("type", ""),
            certificates=data.get("certificates", ""),
            social_security=data.get("social_security", ""),
            location=data.get("location", ""),
            price=data.get("price", 0),
            other_info=data.get("other_info", ""),
            original_info=data.get("original_info", ""),
            split_certificates=data.get("split_certificates")
        )


def json_to_wechat_message_data_list(json_data: List[Dict]) -> List[WeChatMessageData]:
    """
    将JSON数据转换为WeChatMessageData对象列表

    Args:
        json_data: AI返回的JSON数据列表

    Returns:
        List[WeChatMessageData]: 转换后的dataclass对象列表
    """
    if not isinstance(json_data, list):
        return []

    result = []
    for item in json_data:
        if isinstance(item, dict):
            # 创建dataclass对象，会自动进行类型转换
            wechat_data = WeChatMessageData.from_dict(item)
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

    # 转换为dataclass对象列表
    wechat_data_list = json_to_wechat_message_data_list(json_data)
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

            # 这里可以进一步处理证书列表，比如存入数据库等
            # process_certificates(cert_list, wechat_data)
        else:
            print(f"❌ 证书列表解析失败")

        # 添加分隔线，便于阅读
        print("-" * 50)

    print(f"完成处理消息: {msg['msg_id']}")


