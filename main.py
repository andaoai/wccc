#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time
from WeChatAPI import WeChatAPI


def handle_list_result(result):
    if result.get('code') == 200:
        wechat_list = result.get('result', [])
        print(f"📱 找到 {len(wechat_list)} 个微信实例")
        for wechat in wechat_list:
            print(f"👤 {wechat.get('nick')} - {wechat.get('wxid')}")
    else:
        print(f"❌ API返回错误: {result.get('msg')}")


def handle_status_result(result):
    if result.get('code') == 200:
        res = result.get('result', {})
        print(f"✅ 状态正常")
        print(f"👤 {res.get('nick')} - 接收:{res.get('recv')} 发送:{res.get('send')}")
    else:
        print(f"❌ 状态检测失败: {result.get('msg')}")


def main():
    print("🚀 微信API工具")

    api = WeChatAPI(base_url="http://192.168.31.6:7777", safekey=None)

    # 1. 获取微信列表
    print("\n1️⃣ 获取微信列表...")
    list_result = api.get_wechat_list()

    wechat_list = []
    if list_result.get('code') == 200:
        wechat_list = list_result.get('result', [])
        handle_list_result(list_result)
    else:
        print(f"❌ 获取微信列表失败: {list_result.get('msg')}")
        return

    if not wechat_list:
        print("❌ 未找到可用微信实例，退出")
        return

    # 2. 检测状态
    print(f"\n2️⃣ 检测微信状态...")
    all_status_ok = True
    for wechat in wechat_list:
        wxid = wechat.get('wxid')
        if wxid:
            print(f"\n检测 {wechat.get('nick')} (wxid: {wxid}) 状态...")
            status_result = api.check_wechat_status(wxid)
            handle_status_result(status_result)
            if status_result.get('code') != 200:
                all_status_ok = False

    if not all_status_ok:
        print("❌ 状态检测未全部通过")
        return

    # 3. 启动WebSocket监听
    print(f"\n3️⃣ 启动WebSocket监听...")
    print("\n📡 启动微信消息监听...")
    ws_url = "ws://192.168.31.6:7778"

    def custom_message_handler(message_data):
        msg = message_data.get('message', {})
        parsed_msg = msg.get('parsedMsg', {})
        msg_type = parsed_msg.get('type', 'unknown')

        print(f"\n🔔 收到消息:")
        print(f"👥 群聊: {msg.get('fromWxid')}")
        print(f"🗣️ 发言: {msg.get('finalFromWxid')}")
        print(f"📝 类型: {msg_type}")

        if msg_type == 'text':
            content = parsed_msg.get('content', '')
            print(f"💬 内容: {content}")

            if 'hello' in content.lower() or '你好' in content:
                print(f"🤖 检测到问候消息")

        elif msg_type == 'image':
            print(f"🖼️ 图片: {parsed_msg.get('path')}")
        else:
            print(f"📄 内容: {parsed_msg.get('content')}")

        at_list = msg.get('atWxidList', [])
        if at_list:
            print(f"📌 @用户: {', '.join(at_list)}")
        print("-" * 30)

    success = api.start_websocket_listener(custom_message_handler, ws_url)
    if success:
        print("📡 消息监听器已启动，按Ctrl+C停止")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⚠️ 监听器已停止")
    else:
        print("❌ 启动监听器失败")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ 操作已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")