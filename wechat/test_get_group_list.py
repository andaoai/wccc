#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试获取群聊列表功能
"""
from WeChatAPI import WeChatAPI
import json

def test_get_group_list():
    """测试获取群聊列表功能"""

    # 初始化API (使用与debug_websocket.py相同的连接地址)
    api = WeChatAPI(base_url="http://192.168.1.12:7777", safekey=None)

    print("=" * 50)
    print("🔍 测试获取群聊列表功能")
    print("=" * 50)

    # 1. 先检查微信连接状态
    print("\n📱 检查微信连接状态...")
    wechat_list = api.get_wechat_list()

    if 'error' in wechat_list:
        print(f"❌ 获取微信列表失败: {wechat_list.get('msg', '未知错误')}")
        return

    if not wechat_list.get('result'):
        print("⚠️  未找到登录的微信账号")
        return

    # 获取第一个微信账号的wxid
    first_wxid = wechat_list['result'][0]['wxid']
    print(f"✅ 找到微信账号: {first_wxid}")

    # 2. 从缓存获取群聊列表
    print("\n📋 方式1: 从缓存获取群聊列表...")
    groups_cache = api.get_group_list(bot_wxid=first_wxid, cache_type="1")

    if 'error' in groups_cache:
        print(f"❌ 获取群聊列表失败: {groups_cache.get('msg', '未知错误')}")
        return

    if groups_cache.get('code') == 200:
        group_list = groups_cache.get('result', [])
        print(f"✅ 从缓存获取到 {len(group_list)} 个群聊")

        # 显示所有群聊信息（每行一个群）
        print(f"\n📋 所有群聊列表:")
        for i, group in enumerate(group_list):
            group_name = group.get('nick', 'N/A')
            group_wxid = group.get('wxid', 'N/A')
            member_count = group.get('groupMemberNum', 0)
            group_owner = group.get('groupManger', 'N/A')
            print(f"   {i+1:2d}. {group_name} | {member_count}人 | 群主: {group_owner} | {group_wxid}")
    else:
        print(f"❌ 获取群聊列表失败: {groups_cache.get('msg', '未知错误')}")

    # 3. 重新刷新缓存获取群聊列表
    print("\n🔄 方式2: 重新刷新缓存获取群聊列表...")
    groups_refresh = api.get_group_list(bot_wxid=first_wxid, cache_type="2")

    if 'error' in groups_refresh:
        print(f"❌ 刷新群聊列表失败: {groups_refresh.get('msg', '未知错误')}")
        return

    if groups_refresh.get('code') == 200:
        group_list = groups_refresh.get('result', [])
        print(f"✅ 刷新后获取到 {len(group_list)} 个群聊")
    else:
        print(f"❌ 刷新群聊列表失败: {groups_refresh.get('msg', '未知错误')}")

    # 4. 显示详细统计信息
    if groups_cache.get('code') == 200:
        group_list = groups_cache.get('result', [])
        print(f"\n📊 群聊统计信息:")
        print(f"   总群聊数: {len(group_list)}")

        # 统计成员数量
        total_members = sum(group.get('groupMemberNum', 0) for group in group_list)
        print(f"   总成员数: {total_members}")

        # 找出最大的群
        if group_list:
            max_group = max(group_list, key=lambda x: x.get('groupMemberNum', 0))
            print(f"   最大群聊: {max_group.get('nick', 'N/A')} ({max_group.get('groupMemberNum', 0)}人)")

    print("\n✅ 测试完成!")

def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 50)
    print("🧪 测试错误处理")
    print("=" * 50)

    api = WeChatAPI(base_url="http://192.168.1.12:7777", safekey=None)

    # 测试无效的cache_type
    print("\n❌ 测试无效的cache_type...")
    result = api.get_group_list(cache_type="invalid")
    if 'error' in result:
        print(f"✅ 正确捕获错误: {result.get('msg')}")
    else:
        print("⚠️  未正确处理无效参数")

    # 测试不存在的机器人wxid
    print("\n❌ 测试不存在的机器人wxid...")
    result = api.get_group_list(bot_wxid="nonexistent_wxid")
    if 'error' in result or result.get('code') != 200:
        print(f"✅ 正确处理不存在的wxid")
    else:
        print("⚠️  可能需要更好的错误处理")

if __name__ == "__main__":
    try:
        test_get_group_list()
        test_error_handling()
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()