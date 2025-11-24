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
            return response.json()
        except requests.exceptions.ConnectionError:
            return {'error': 'Connection failed', 'msg': '连接失败'}
        except requests.exceptions.Timeout:
            return {'error': 'Request timeout', 'msg': '请求超时'}
        except requests.exceptions.RequestException as e:
            return {'error': str(e), 'msg': '请求失败'}
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON response', 'msg': 'JSON解析失败'}

    def get_wechat_list(self) -> Dict:
        return self._make_request("getWeChatList")

    def check_wechat_status(self, wxid: str) -> Dict:
        if not wxid:
            return {'error': 'wxid is required', 'msg': '微信ID不能为空'}
        return self._make_request("checkWeChat", {}, wxid=wxid)

    def parse_group_message(self, event_data: Dict) -> Dict:
        if event_data.get('event') != 10008:
            return {'error': 'Not a group message event'}

        try:
            data = event_data.get('data', {})
            msg_data = data.get('data', {})

            from_type = msg_data.get('fromType', 0)
            msg_type = msg_data.get('msgType', 0)
            msg_content = msg_data.get('msg', '')
            parsed_msg = self._parse_message_content(msg_content, msg_type)

            return {
                'event': event_data.get('event'),
                'wxid': data.get('wxid'),
                'message': {
                    'fromType': from_type,
                    'msgType': msg_type,
                    'fromWxid': msg_data.get('fromWxid'),
                    'finalFromWxid': msg_data.get('finalFromWxid'),
                    'atWxidList': msg_data.get('atWxidList', []),
                    'membercount': msg_data.get('membercount', 0),
                    'rawMsg': msg_content,
                    'parsedMsg': parsed_msg,
                    'msgId': msg_data.get('msgId')
                }
            }
        except Exception as e:
            return {'error': f'Parse failed: {str(e)}'}

    def _parse_message_content(self, msg: str, msg_type: int) -> Dict:
        if msg_type == 1:
            return {'type': 'text', 'content': msg}
        elif msg_type == 3 and msg.startswith('[pic='):
            content = msg[5:-1]
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
            return {'type': 'unknown', 'content': msg}

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
            def default_callback(message_data):
                msg = message_data.get('message', {})
                parsed_msg = msg.get('parsedMsg', {})
                msg_type = parsed_msg.get('type', 'unknown')

                print(f"\n🔔 收到消息:")
                print(f"👥 群聊: {msg.get('fromWxid')}")
                print(f"🗣️ 发言: {msg.get('finalFromWxid')}")
                print(f"📝 类型: {msg_type}")

                if msg_type == 'text':
                    print(f"💬 内容: {parsed_msg.get('content')}")
                elif msg_type == 'image':
                    print(f"🖼️ 图片: {parsed_msg.get('path')}")
                else:
                    print(f"📄 内容: {parsed_msg.get('content')}")

                at_list = msg.get('atWxidList', [])
                if at_list:
                    print(f"📌 @用户: {', '.join(at_list)}")
                print("-" * 40)

            callback = default_callback

        def websocket_client():
            """WebSocket客户端线程"""
            try:
                import websocket
                import queue

                print(f"🔌 连接WebSocket: {ws_url}")

                def on_message(ws, message):
                    try:
                        data = json.loads(message)
                        if data.get('event') == 10008:  # 群聊消息
                            parsed = self.parse_group_message(data)
                            if 'error' not in parsed:
                                callback(parsed)
                    except Exception as e:
                        print(f"❌ 消息处理错误: {e}")

                def on_error(ws, error):
                    print(f"❌ WebSocket错误: {error}")

                def on_close(ws, close_status_code, close_msg):
                    print(f"🔌 连接断开，5秒后重连...")
                    time.sleep(5)
                    websocket_client()

                def on_open(ws):
                    print(f"✅ WebSocket连接成功，开始监听消息...")

                # 创建WebSocket连接
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open
                )

                ws.run_forever()

            except ImportError:
                print("❌ 需要安装websocket-client库: pip install websocket-client")
                return False
            except Exception as e:
                print(f"❌ WebSocket连接失败: {e}")
                return False

        # 启动WebSocket监听线程
        thread = threading.Thread(target=websocket_client, daemon=True)
        thread.start()

        return True