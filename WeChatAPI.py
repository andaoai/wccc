#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import threading
import time
from typing import Dict, Callable


class WeChatAPI:
    def __init__(self, base_url: str = "http://127.0.0.1:7777", safekey: str = None):
        self.base_url = base_url.rstrip('/')
        self.safekey = safekey
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _clean_json_string(self, json_str: str) -> str:
        """
        清理JSON字符串中的控制字符和非法字符

        Args:
            json_str: 原始JSON字符串

        Returns:
            str: 清理后的JSON字符串
        """
        import re

        # 移除控制字符（除了常用的空白字符）
        # 保留：\t (9), \n (10), \r (13)
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', json_str)

        # 替换其他可能有问题的字符
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', cleaned)

        # 特别处理一些可能出现在字符串中的控制字符序列
        cleaned = re.sub(r'\\[b-f]', '', cleaned)  # 移除一些转义控制字符

        return cleaned

    def _make_request(self, api_type: str, data: Dict = None, wxid: str = None) -> Dict:
        url = f"{self.base_url}/qianxun/httpapi"
        params = {}
        if self.safekey:
            params['safekey'] = self.safekey
        if wxid:
            params['wxid'] = wxid

        payload = {"type": api_type, "data": data or {}}

        try:
            response = self.session.post(url, params=params, json=payload, timeout=30)
            response.raise_for_status()

            # 尝试解析JSON，如果失败则清理控制字符后重试
            try:
                return response.json()
            except json.JSONDecodeError as e:
                # 尝试清理控制字符后重新解析
                raw_response = response.text
                try:
                    # 移除或替换控制字符
                    cleaned_response = self._clean_json_string(raw_response)
                    return json.loads(cleaned_response)
                except:
                    # 如果还是失败，输出原始响应用于调试
                    print(f"🐛 DEBUG: 原始响应文本: {raw_response}")
                    return {
                        'error': f'JSON解析失败: {str(e)}',
                        'msg': 'JSON解析失败',
                        'raw_response': raw_response
                    }
        except requests.exceptions.ConnectionError:
            return {'error': 'Connection failed', 'msg': '连接失败'}
        except requests.exceptions.Timeout:
            return {'error': 'Request timeout', 'msg': '请求超时'}
        except requests.exceptions.RequestException as e:
            return {'error': str(e), 'msg': '请求失败'}

    def get_wechat_list(self) -> Dict:
        return self._make_request("getWeChatList")

    def check_wechat_status(self, wxid: str) -> Dict:
        if not wxid:
            return {'error': 'wxid is required', 'msg': '微信ID不能为空'}
        return self._make_request("checkWeChat", {}, wxid=wxid)

    def get_member_nick(self, group_wxid: str, member_wxid: str, bot_wxid: str = None) -> Dict:
        """
        获取群成员昵称

        Args:
            group_wxid: 群聊wxid
            member_wxid: 群成员wxid
            bot_wxid: 机器人wxid（可选，某些情况下需要）

        Returns:
            Dict: 包含成员昵称的响应
        """
        if not group_wxid or not member_wxid:
            return {'error': 'group_wxid and member_wxid are required', 'msg': '群ID和成员ID不能为空'}

        data = {
            "wxid": group_wxid,
            "objWxid": member_wxid
        }

        return self._make_request("getMemberNick", data, wxid=bot_wxid)

    def query_group(self, group_wxid: str, bot_wxid: str = None, cache_type: str = "1") -> Dict:
        """
        查询群聊信息

        Args:
            group_wxid: 群聊wxid
            bot_wxid: 机器人wxid（可选）
            cache_type: 缓存类型，"1"=从缓存获取，"2"=从内存获取

        Returns:
            Dict: 包含群信息的响应
        """
        if not group_wxid:
            return {'error': 'group_wxid is required', 'msg': '群ID不能为空'}

        data = {
            "wxid": group_wxid,
            "type": cache_type
        }

        return self._make_request("queryGroup", data, wxid=bot_wxid)

    def parse_group_message(self, event_data: Dict) -> Dict:
        if event_data.get('event') != 10008:
            return {'error': 'Not a group message event'}

        try:
            data = event_data.get('data', {})
            msg_data = data.get('data', {})

            # 获取所有文档中定义的字段
            from_type = msg_data.get('fromType', 0)          # 来源类型：1|私聊 2|群聊 3|公众号
            msg_type = msg_data.get('msgType', 0)            # 消息类型：1|文本 3|图片 ...
            msg_source = msg_data.get('msgSource', 0)        # 消息来源：0|别人发送 1|自己发送
            msg_content = msg_data.get('msg', '')            # 消息内容
            timestamp = msg_data.get('timeStamp', '')        # 时间戳

            # 解析消息内容
            parsed_msg = self._parse_message_content(msg_content, msg_type)

            return {
                'event': event_data.get('event'),
                'timeStamp': timestamp,  # 添加时间戳
                'wxid': data.get('wxid'),
                'message': {
                    'fromType': from_type,                    # 来源类型
                    'msgType': msg_type,                      # 消息类型
                    'msgSource': msg_source,                  # 消息来源
                    'fromWxid': msg_data.get('fromWxid'),     # 来源wxid
                    'finalFromWxid': msg_data.get('finalFromWxid'),  # 群内发言人wxid
                    'atWxidList': msg_data.get('atWxidList', []),    # @用户列表
                    'silence': msg_data.get('silence', 0),     # 消息免打扰状态
                    'membercount': msg_data.get('membercount', 0),   # 群成员数量
                    'signature': msg_data.get('signature'),   # 消息签名
                    'rawMsg': msg_content,                    # 原始消息内容
                    'parsedMsg': parsed_msg,                  # 解析后的消息内容
                    'msgId': msg_data.get('msgId'),           # 消息ID
                    'sendId': msg_data.get('sendId')          # 发送请求ID
                }
            }
        except Exception as e:
            return {'error': f'Parse failed: {str(e)}'}

    def _parse_message_content(self, msg: str, msg_type: int) -> Dict:
        """解析消息内容，支持所有消息类型"""

        if msg_type == 1:  # 文本消息
            return {'type': 'text', 'content': msg}

        elif msg_type == 3:  # 图片消息
            if msg.startswith('[pic='):
                content = msg[5:-1]  # 去掉 [pic= 和 ]
                parts = content.split(',')
                path = parts[0]
                is_decrypt = 0
                for part in parts[1:]:
                    if part.startswith('isDecrypt='):
                        is_decrypt = int(part.split('=')[1])
                return {
                    'type': 'image',
                    'path': path,
                    'isDecrypt': is_decrypt,
                    'decryptStatus': '已解密' if is_decrypt == 1 else '未解密'
                }
            else:
                return {'type': 'image', 'content': msg}

        elif msg_type == 34:  # 语音消息
            return {'type': 'voice', 'content': msg}

        elif msg_type == 42:  # 名片消息
            return {'type': 'card', 'content': msg}

        elif msg_type == 43:  # 视频消息
            return {'type': 'video', 'content': msg}

        elif msg_type == 47:  # 动态表情
            return {'type': 'sticker', 'content': msg}

        elif msg_type == 48:  # 地理位置
            return {'type': 'location', 'content': msg}

        elif msg_type == 49:  # 分享链接或附件
            return {'type': 'share', 'content': msg}

        elif msg_type == 2001:  # 红包
            return {'type': 'redpacket', 'content': msg}

        elif msg_type == 2002:  # 小程序
            return {'type': 'miniprogram', 'content': msg}

        elif msg_type == 2003:  # 群邀请
            return {'type': 'group_invite', 'content': msg}

        elif msg_type == 10000:  # 系统消息
            return {'type': 'system', 'content': msg}

        else:
            # 未知消息类型，保留原始内容
            return {'type': 'unknown', 'content': msg, 'msgType': msg_type}

    def start_websocket_listener(self, callback: Callable = None, ws_url: str = None):
        """
        启动WebSocket消息监听器

        Args:
            callback: 消息回调函数，接收解析后的消息数据
            ws_url: WebSocket地址，默认为http地址的7778端口
        """
        if ws_url is None:
            # 将HTTP地址转换为WebSocket地址
            ws_base = self.base_url.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_url = ws_base.replace(':7777', ':7778')

        if callback is None:
            callback = self.default_callback

        # 启动WebSocket监听线程
        thread = threading.Thread(target=self.websocket_client, args=(ws_url, callback), daemon=True)
        thread.start()
        return True

    def default_callback(self, message_data):
        """默认消息处理回调函数 - 添加断点调试支持"""
        # 🔍 DEBUG BREAKPOINT - 在这里设置断点
        import pdb; pdb.set_trace()  # 可以删掉这行，这是为了演示

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

            # 🔍 DEBUG BREAKPOINT - 针对文本消息的断点
            if 'hello' in content.lower() or '你好' in content:
                print("🐛 DEBUG: 检测到问候消息，可以在这里设置断点")

        elif msg_type == 'image':
            print(f"🖼️ 图片: {parsed_msg.get('path')}")
        else:
            print(f"📄 内容: {parsed_msg.get('content')}")

        at_list = msg.get('atWxidList', [])
        if at_list:
            print(f"📌 @用户: {', '.join(at_list)}")
        print("-" * 40)

    def on_message(self, callback, ws, message):
        """WebSocket消息处理 - 调试断点可以在这里设置"""
        try:
            data = json.loads(message)
            if data.get('event') == 10008:  # 群聊消息
                parsed = self.parse_group_message(data)
                if 'error' not in parsed:
                    callback(parsed)
        except Exception as e:
            print(f"❌ 消息处理错误: {e}")

    def on_error(self, ws, error):
        """WebSocket错误处理 - 调试断点可以在这里设置"""
        print(f"❌ WebSocket错误: {error}")

    def on_close(self, ws_url, callback, ws, close_status_code, close_msg):
        """WebSocket连接关闭处理 - 调试断点可以在这里设置"""
        print(f"🔌 连接断开，5秒后重连...")
        time.sleep(5)
        self.websocket_client(ws_url, callback)

    def on_open(self, ws):
        """WebSocket连接成功处理 - 调试断点可以在这里设置"""
        print(f"✅ WebSocket连接成功，开始监听消息...")

    def websocket_client(self, ws_url: str, callback):
        """WebSocket客户端主函数 - 调试断点可以在这里设置"""
        try:
            import websocket
            import queue

            print(f"🔌 连接WebSocket: {ws_url}")

            # 创建WebSocket连接
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=lambda ws, message: self.on_message(callback, ws, message),
                on_error=self.on_error,
                on_close=lambda ws, code, msg: self.on_close(ws_url, callback, ws, code, msg),
                on_open=self.on_open
            )

            ws.run_forever()

        except ImportError:
            print("❌ 需要安装websocket-client库: pip install websocket-client")
        except Exception as e:
            print(f"❌ WebSocket连接失败: {e}")