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


def main(auto_mode=False):
    print("🚀 微信API工具")

    base_url = "http://192.168.31.6:7777" if auto_mode else input("API地址: ").strip()
    safekey = "" if auto_mode else input("安全秘钥(可选): ").strip()

    api = WeChatAPI(base_url=base_url, safekey=safekey if safekey else None)

    if auto_mode:
        print("\n1️⃣ 获取微信列表...")
        list_result = api.get_wechat_list()

        if list_result.get('code') == 200:
            wechat_list = list_result.get('result', [])
            handle_list_result(list_result)

            if wechat_list:
                wxid = wechat_list[0].get('wxid')
                print(f"\n2️⃣ 检测状态 (wxid: {wxid})...")
                status_result = api.check_wechat_status(wxid)
                handle_status_result(status_result)
        else:
            print("❌ 获取微信列表失败")
    else:
        print("\n🎯 选择功能:")
        print("1. 获取微信列表")
        print("2. 微信状态检测")
        print("3. 获取列表并检测状态")
        print("4. 监听微信消息")

        choice = input("选择 (1-4): ").strip()

        if choice == "1":
            result = api.get_wechat_list()
            handle_list_result(result)

        elif choice == "2":
            wxid = input("微信wxid: ").strip()
            if wxid:
                result = api.check_wechat_status(wxid)
                handle_status_result(result)
            else:
                print("❌ 微信ID不能为空")

        elif choice == "3":
            list_result = api.get_wechat_list()
            if list_result.get('code') == 200:
                wechat_list = list_result.get('result', [])
                handle_list_result(list_result)

                for wechat in wechat_list:
                    wxid = wechat.get('wxid')
                    if wxid:
                        print(f"\n检测 {wxid} 状态...")
                        status_result = api.check_wechat_status(wxid)
                        handle_status_result(status_result)
            else:
                print("❌ 获取微信列表失败")

        elif choice == "4":
            print("\n📡 启动微信消息监听...")
            ws_url = "ws://192.168.31.6:7778"

            # 自定义消息处理回调
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

                    # 简单的自动回复示例
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

        else:
            print("❌ 无效选择")


if __name__ == "__main__":
    try:
        auto_mode = len(sys.argv) > 1 and sys.argv[1] == "--auto"
        main(auto_mode=auto_mode)
    except KeyboardInterrupt:
        print("\n⚠️ 操作已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")