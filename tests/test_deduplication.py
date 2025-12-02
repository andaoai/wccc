#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试微信消息去重功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from bot.callback_handler import init_callback_system, data_callback
from db.raw_dao import raw_message_dao
from db.raw_models import WeChatRawMessage

def create_test_data(msg_id: str, content: str) -> dict:
    """创建测试数据"""
    return {
        'message': {
            'msg_id': msg_id,
            'from_type': 2,  # 群聊
            'from_wxid': 'test_group_wxid',
            'final_from_wxid': 'test_user_wxid',
            'msg_type': 1,   # 文本消息
            'msg_source': 0, # 别人发送
            'content': content,
            'parsed_content': {},
            'timestamp': '2024-01-01 12:00:00',
            'member_count': 100,
            'silence': 0,
            'at_wxid_list': [],
            'signature': 'test_signature'
        },
        'group_info': {
            'group_name': '测试群聊',
            'member_nick': '测试用户'
        },
        'collection_metadata': {
            'collector_version': '1.0.0',
            'collection_time': '2024-01-01 12:00:01',
            'stats': {
                'messages_received': 1,
                'messages_processed': 1
            }
        }
    }

def test_deduplication():
    """测试去重功能"""
    print("🧪 开始测试微信消息去重功能")

    # 初始化数据库
    init_callback_system()

    # 创建测试数据
    test_data_1 = create_test_data('msg_001', '第一条测试消息')
    test_data_2 = create_test_data('msg_002', '第二条测试消息')
    test_data_1_duplicate = create_test_data('msg_001', '第一条测试消息')  # 完全相同的内容

    print("\n📥 测试1: 存储第一条消息")
    result_1 = raw_message_dao.upsert_raw_message(
        WeChatRawMessage.from_callback_data(test_data_1)
    )
    print(f"结果: {result_1}")

    print("\n📥 测试2: 存储第二条消息")
    result_2 = raw_message_dao.upsert_raw_message(
        WeChatRawMessage.from_callback_data(test_data_2)
    )
    print(f"结果: {result_2}")

    print("\n📥 测试3: 存储重复的第一条消息")
    result_3 = raw_message_dao.upsert_raw_message(
        WeChatRawMessage.from_callback_data(test_data_1_duplicate)
    )
    print(f"结果: {result_3}")

    # 检查统计信息
    print("\n📊 统计信息:")
    stats = raw_message_dao.get_duplicate_statistics()

    # 转换datetime对象为字符串以便JSON序列化
    def convert_datetime(obj):
        if hasattr(obj, 'strftime'):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return obj

    safe_stats = {k: convert_datetime(v) for k, v in stats.items()}
    print(json.dumps(safe_stats, indent=2, ensure_ascii=False))

    print("\n✅ 去重功能测试完成!")

def test_callback_integration():
    """测试与回调函数的集成"""
    print("\n🔗 测试回调函数集成")

    test_data = create_test_data('msg_callback_001', '回调测试消息')

    # 调用回调函数
    print("调用data_callback...")
    data_callback(test_data)

    print("✅ 回调函数集成测试完成!")

if __name__ == "__main__":
    test_deduplication()
    test_callback_integration()