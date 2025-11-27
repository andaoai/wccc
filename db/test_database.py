#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库功能测试脚本
测试PostgreSQL连接和WeChatMessageData存储功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接运行脚本时的导入方式
if __name__ == "__main__":
    from db.models import WeChatMessageData, init_database
    from db.dao import wechat_message_dao
    from db.database import db_manager
else:
    # 作为模块导入时的相对导入
    from .models import WeChatMessageData, init_database
    from .dao import wechat_message_dao
    from .database import db_manager
from datetime import datetime

def test_database_connection():
    """测试数据库连接"""
    print("🔌 测试数据库连接...")
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] == 1:
                print("✅ 数据库连接成功")
                return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def test_insert_and_retrieve_message():
    """测试插入和检索消息"""
    print("\n📝 测试插入和检索消息...")

    # 创建测试数据
    test_message = WeChatMessageData(
        type="收",
        certificates="一级建造师,二级建造师",
        social_security="唯一社保",
        location="浙江省宁波市",
        price=8000,
        other_info="急招，待遇优厚",
        original_info="收一级建造师，要求唯一社保，地点宁波，月薪8000",
        split_certificates=["一级建造师", "二级建造师"],
        group_name="建筑资质交流群",
        member_nick="张工",
        group_wxid="45692733938@chatroom",
        member_wxid="zhang_gong_wxid",
        msg_id="test_msg_001",
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    # 插入数据
    try:
        message_id = wechat_message_dao.insert_message(test_message)
        if message_id:
            print(f"✅ 成功插入测试消息，ID: {message_id}")
        else:
            print("❌ 插入消息失败")
            return False
    except Exception as e:
        print(f"❌ 插入消息异常: {e}")
        return False

    # 检索数据
    try:
        retrieved_message = wechat_message_dao.find_by_msg_id("test_msg_001")
        if retrieved_message:
            print("✅ 成功检索到测试消息")
            print(f"   类型: {retrieved_message['type']}")
            print(f"   证书: {retrieved_message['certificates']}")
            print(f"   地区: {retrieved_message['location']}")
            print(f"   价格: {retrieved_message['price']}")
            print(f"   拆分证书: {retrieved_message['split_certificates']}")
        else:
            print("❌ 未检索到测试消息")
            return False
    except Exception as e:
        print(f"❌ 检索消息异常: {e}")
        return False

    return True

def test_certificate_query():
    """测试证书查询功能"""
    print("\n🔍 测试证书查询功能...")

    try:
        messages = wechat_message_dao.find_by_certificate("一级建造师")
        print(f"✅ 查找到包含 '一级建造师' 的消息 {len(messages)} 条")
        for msg in messages[:3]:  # 只显示前3条
            print(f"   - {msg['type']} | {msg['group_name']} | {msg['certificates']}")
        return True
    except Exception as e:
        print(f"❌ 证书查询失败: {e}")
        return False

def test_group_query():
    """测试群组查询功能"""
    print("\n👥 测试群组查询功能...")

    try:
        messages = wechat_message_dao.find_by_group("45692733938@chatroom")
        print(f"✅ 查找到群组消息 {len(messages)} 条")
        for msg in messages[:3]:  # 只显示前3条
            print(f"   - {msg['type']} | {msg['member_nick']} | {msg['certificates']}")
        return True
    except Exception as e:
        print(f"❌ 群组查询失败: {e}")
        return False

def test_statistics():
    """测试统计功能"""
    print("\n📊 测试统计功能...")

    try:
        stats = wechat_message_dao.get_statistics()
        if stats:
            print("✅ 获取统计信息成功:")
            print(f"   总消息数: {stats.get('total_messages', 0)}")
            print(f"   群组数: {stats.get('unique_groups', 0)}")
            print(f"   成员数: {stats.get('unique_members', 0)}")
            print(f"   包含证书的消息: {stats.get('messages_with_certificates', 0)}")
            print(f"   平均价格: {stats.get('avg_price', 0)}")
            print(f"   最新消息: {stats.get('latest_message', 'N/A')}")
            return True
        else:
            print("❌ 未能获取统计信息")
            return False
    except Exception as e:
        print(f"❌ 统计查询失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始数据库功能测试...\n")

    tests = [
        ("数据库连接测试", test_database_connection),
        ("插入和检索测试", test_insert_and_retrieve_message),
        ("证书查询测试", test_certificate_query),
        ("群组查询测试", test_group_query),
        ("统计功能测试", test_statistics),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"{'='*50}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")

    print(f"\n{'='*50}")
    print(f"🎯 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！数据库功能正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)