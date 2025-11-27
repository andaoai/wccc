#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket调试版本 - 在主线程中处理消息，便于调试
"""
import json
import time
import threading
import queue
from WeChatAPI import WeChatAPI


class DebugWebSocketListener:
    def __init__(self, api: WeChatAPI):
        self.api = api
        self.message_queue = queue.Queue()
        self.running = False
        self.bot_wxid = None
        self._get_bot_wxid()

    def _get_bot_wxid(self):
        """获取机器人wxid"""
        try:
            print("🔍 获取机器人wxid...")
            list_result = self.api.get_wechat_list()
            if list_result.get('code') == 200:
                wechat_list = list_result.get('result', [])
                if wechat_list:
                    # 取第一个可用的微信实例作为机器人
                    self.bot_wxid = wechat_list[0].get('wxid', '')
                    if self.bot_wxid:
                        print(f"🤖 机器人wxid: {self.bot_wxid}")
                    else:
                        print("❌ 无法获取机器人wxid")
                else:
                    print("❌ 未找到可用的微信实例")
            else:
                print(f"❌ 获取微信列表失败: {list_result.get('msg')}")
        except Exception as e:
            print(f"❌ 获取机器人wxid时出错: {e}")

    def start(self):
        """启动调试模式的WebSocket监听器"""
        self.running = True
        print("🔍 启动调试模式WebSocket监听器...")

        # 启动WebSocket接收线程
        ws_thread = threading.Thread(target=self._websocket_receiver, daemon=True)
        ws_thread.start()

        # 在主线程中处理消息
        self._process_messages()

    def _websocket_receiver(self):
        """WebSocket接收线程 - 只负责接收消息放入队列"""
        try:
            import websocket

            ws_url = "ws://192.168.1.12:7778"
            print(f"🔌 连接WebSocket: {ws_url}")

            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if data.get('event') == 10008:  # 群聊消息
                        # 🔍 DEBUG BREAKPOINT - 在这里可以调试原始消息
                        print("🐛 DEBUG: 收到原始WebSocket消息")
                        self.message_queue.put(data)  # 放入队列，主线程处理
                except Exception as e:
                    print(f"❌ 消息处理错误: {e}")

            def on_error(ws, error):
                print(f"❌ WebSocket错误: {error}")

            def on_close(ws, close_status_code, close_msg):
                print(f"🔌 连接断开，5秒后重连...")
                if self.running:
                    time.sleep(5)
                    self._websocket_receiver()

            def on_open(ws):
                print(f"✅ WebSocket连接成功，开始监听消息...")

            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )

            ws.run_forever()

        except ImportError:
            print("❌ 需要安装websocket-client库")
        except Exception as e:
            print(f"❌ WebSocket连接失败: {e}")

    def _process_messages(self):
        """在主线程中处理消息 - 调试器可以正常工作"""
        print("🔍 主线程消息处理器已启动")

        while self.running:
            try:
                # 从队列获取消息，设置超时避免阻塞
                data = self.message_queue.get(timeout=1.0)

                # 🔍 DEBUG BREAKPOINT - 在这里设置断点调试消息处理
                print("🐛 DEBUG: 主线程开始处理消息")

                # 解析消息
                parsed = self.api.parse_group_message(data)
                if 'error' not in parsed:
                    self._handle_parsed_message(parsed)

                self.message_queue.task_done()

            except queue.Empty:
                continue
            except KeyboardInterrupt:
                print("\n⚠️ 停止消息处理")
                break
            except Exception as e:
                print(f"❌ 消息处理错误: {e}")

    def _handle_parsed_message(self, parsed_data):
        """处理解析后的消息 - 完整的消息分类实现"""
        msg = parsed_data.get('message', {})
        parsed_msg = msg.get('parsedMsg', {})

        # 基本消息信息
        from_type = msg.get('fromType', 0)  # 1:私聊 2:群聊 3:公众号
        msg_type_num = msg.get('msgType', 0)  # 原始数字类型
        msg_source = msg.get('msgSource', 0)  # 0:别人发送 1:自己发送

        print(f"\n🔔 收到消息:")
        print(f"⏰ 时间戳: {parsed_data.get('timeStamp', 'N/A')}")

        # 显示消息来源类型
        from_type_map = {1: "私聊", 2: "群聊", 3: "公众号"}
        from_type_desc = from_type_map.get(from_type, f"未知类型({from_type})")
        from_emoji = {1: "👤", 2: "👥", 3: "📢"}.get(from_type, "❓")
        print(f"{from_emoji} 来源类型: {from_type_desc}")

        # 显示消息来源
        msg_source_desc = "自己发送" if msg_source == 1 else "别人发送"
        msg_source_emoji = "📤" if msg_source == 1 else "📥"
        print(f"{msg_source_emoji} 消息来源: {msg_source_desc}")

        # 显示具体的发送者信息
        if from_type == 1:  # 私聊
            print(f"👤 好友: {msg.get('fromWxid')}")
        elif from_type == 2:  # 群聊
            group_wxid = msg.get('fromWxid')
            member_wxid = msg.get('finalFromWxid')

            print(f"👥 群聊: {group_wxid}")
            print(f"🗣️ 发言: {member_wxid}")

            # 获取并显示群名称和成员昵称
            self._show_group_and_member_info(group_wxid, member_wxid)

            print(f"👥 成员数: {msg.get('membercount', 0)}")
            print(f"🔕 免打扰: {'是' if msg.get('silence') == 1 else '否'}")
        elif from_type == 3:  # 公众号
            print(f"📢 公众号: {msg.get('fromWxid')}")

        # 显示消息ID和签名
        msg_id = msg.get('msgId')
        if msg_id:
            print(f"🆔 消息ID: {msg_id}")

        signature = msg.get('signature')
        if signature:
            print(f"🔐 签名: {signature}")

        # 根据消息类型处理内容
        self._handle_message_by_type(msg_type_num, parsed_msg, msg)

        # 处理@信息（仅群聊有效）
        if from_type == 2:
            at_list = msg.get('atWxidList', [])
            if at_list:
                print(f"📌 @用户: {', '.join(at_list)}")

        print("-" * 60)

    def _handle_message_by_type(self, msg_type: int, parsed_msg: dict, original_msg: dict):
        """根据消息类型处理具体内容"""

        # 消息类型映射
        msg_type_map = {
            1: ("文本", "💬", self._handle_text_message),
            3: ("图片", "🖼️", self._handle_image_message),
            34: ("语音", "🎵", self._handle_voice_message),
            42: ("名片", "👤", self._handle_card_message),
            43: ("视频", "🎬", self._handle_video_message),
            47: ("动态表情", "😄", self._handle_sticker_message),
            48: ("地理位置", "📍", self._handle_location_message),
            49: ("分享链接或附件", "🔗", self._handle_share_message),
            2001: ("红包", "🧧", self._handle_redpacket_message),
            2002: ("小程序", "📱", self._handle_miniprogram_message),
            2003: ("群邀请", "👥", self._handle_group_invite_message),
            10000: ("系统消息", "⚙️", self._handle_system_message)
        }

        if msg_type in msg_type_map:
            type_name, emoji, handler = msg_type_map[msg_type]
            print(f"{emoji} 消息类型: {type_name} ({msg_type})")
            handler(parsed_msg, original_msg)
        else:
            print(f"❓ 未知消息类型: {msg_type}")
            print(f"📄 原始内容: {parsed_msg.get('content', '')}")

    def _handle_text_message(self, parsed_msg: dict, original_msg: dict):
        """处理文本消息"""
        content = parsed_msg.get('content', '')
        print(f"💬 文本内容: {content}")

        # 🔍 DEBUG BREAKPOINT - 针对特定内容的断点
        if 'hello' in content.lower() or '你好' in content:
            print("🐛 DEBUG: 检测到问候消息 - 在这里设置断点")

    def _handle_image_message(self, parsed_msg: dict, original_msg: dict):
        """处理图片消息"""
        path = parsed_msg.get('path', '')
        is_decrypt = parsed_msg.get('isDecrypt', 0)
        decrypt_status = parsed_msg.get('decryptStatus', '未知')
        print(f"🖼️ 图片路径: {path}")
        print(f"🔓 解密状态: {decrypt_status}")

    def _handle_voice_message(self, parsed_msg: dict, original_msg: dict):
        """处理语音消息"""
        content = parsed_msg.get('content', '')
        print(f"🎵 语音信息: {content}")

    def _handle_card_message(self, parsed_msg: dict, original_msg: dict):
        """处理名片消息"""
        content = parsed_msg.get('content', '')
        print(f"👤 名片信息: {content}")

    def _handle_video_message(self, parsed_msg: dict, original_msg: dict):
        """处理视频消息"""
        content = parsed_msg.get('content', '')
        print(f"🎬 视频信息: {content}")

    def _handle_sticker_message(self, parsed_msg: dict, original_msg: dict):
        """处理动态表情消息"""
        content = parsed_msg.get('content', '')
        print(f"😄 动态表情: {content}")

    def _handle_location_message(self, parsed_msg: dict, original_msg: dict):
        """处理地理位置消息"""
        content = parsed_msg.get('content', '')
        print(f"📍 位置信息: {content}")

    def _handle_share_message(self, parsed_msg: dict, original_msg: dict):
        """处理分享链接或附件消息"""
        content = parsed_msg.get('content', '')
        print(f"🔗 分享内容: {content}")

    def _handle_redpacket_message(self, parsed_msg: dict, original_msg: dict):
        """处理红包消息"""
        content = parsed_msg.get('content', '')
        print(f"🧧 红包信息: {content}")

    def _handle_miniprogram_message(self, parsed_msg: dict, original_msg: dict):
        """处理小程序消息"""
        content = parsed_msg.get('content', '')
        print(f"📱 小程序信息: {content}")

    def _handle_group_invite_message(self, parsed_msg: dict, original_msg: dict):
        """处理群邀请消息"""
        content = parsed_msg.get('content', '')
        print(f"👥 群邀请信息: {content}")

    def _handle_system_message(self, parsed_msg: dict, original_msg: dict):
        """处理系统消息"""
        content = parsed_msg.get('content', '')
        print(f"⚙️ 系统消息: {content}")

    def _show_group_and_member_info(self, group_wxid: str, member_wxid: str):
        """
        获取并显示群名称和成员昵称

        Args:
            group_wxid: 群聊wxid
            member_wxid: 群成员wxid
        """
        if not self.bot_wxid:
            print("❌ 机器人wxid未设置，无法获取群信息")
            return

        try:
            # 获取群信息
            group_result = self.api.query_group(group_wxid, self.bot_wxid)
            if group_result.get('code') == 200:
                group_info = group_result.get('result', {})
                group_name = group_info.get('nick', '')  # 修正字段名：nick 而不是 nickname
                if group_name:
                    print(f"📛 群名称: {group_name}")
            else:
                print(f"❌ 获取群信息失败: {group_result.get('msg', '未知错误')}")
                if 'error' in group_result:
                    print(f"❌ 详细错误: {group_result.get('error')}")
                if 'raw_response' in group_result:
                    print(f"🐛 DEBUG: 原始响应: {group_result.get('raw_response')}")

            # 获取群成员昵称
            member_result = self.api.get_member_nick(group_wxid, member_wxid, self.bot_wxid)
            if member_result.get('code') == 200:
                member_info = member_result.get('result', {})
                member_nick = member_info.get('groupNick', '')
                if member_nick:
                    print(f"👤 成员昵称: {member_nick}")
            else:
                print(f"❌ 获取成员昵称失败: {member_result.get('msg', '未知错误')}")

        except Exception as e:
            print(f"❌ 获取群信息或成员昵称时出错: {e}")

    def stop(self):
        """停止监听器"""
        self.running = False


if __name__ == "__main__":
    # 使用调试版本
    api = WeChatAPI(base_url="http://192.168.1.12:7777", safekey=None)

    print("🚀 微信API调试工具")

    # 检查微信状态
    print("\n1️⃣ 获取微信列表...")
    list_result = api.get_wechat_list()

    if list_result.get('code') == 200:
        wechat_list = list_result.get('result', [])
        print(f"📱 找到 {len(wechat_list)} 个微信实例")

        if wechat_list:
            # 启动调试模式的WebSocket监听器
            debug_listener = DebugWebSocketListener(api)
            try:
                debug_listener.start()
            except KeyboardInterrupt:
                print("\n⚠️ 调试监听器已停止")
                debug_listener.stop()
        else:
            print("❌ 未找到可用微信实例")
    else:
        print(f"❌ 获取微信列表失败: {list_result.get('msg')}")