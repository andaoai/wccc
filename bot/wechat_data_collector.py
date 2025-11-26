#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信数据采集器 - 高性能版本
专门用于采集微信数据，为后续数据清洗提供原始数据

主要改进：
1. 异步API调用避免阻塞消息处理
2. 智能缓存减少重复API请求
3. 完善的错误处理和重试机制
4. 消息队列缓冲处理
5. 数据结构化存储
"""

import json
import time
import threading
import queue
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
from wechat.WeChatAPI import WeChatAPI


@dataclass
class WeChatMessage:
    """微信消息数据结构"""
    msg_id: str
    from_type: int  # 1:私聊 2:群聊 3:公众号
    from_wxid: str
    final_from_wxid: str = ""
    msg_type: int = 0
    msg_source: int = 0  # 0:别人发送 1:自己发送
    content: str = ""
    parsed_content: Dict = None
    timestamp: str = ""
    member_count: int = 0
    silence: int = 0
    at_wxid_list: List = None
    signature: str = ""

    def __post_init__(self):
        if self.parsed_content is None:
            self.parsed_content = {}
        if self.at_wxid_list is None:
            self.at_wxid_list = []


@dataclass
class GroupInfo:
    """群信息数据结构"""
    group_wxid: str
    group_name: str = ""
    member_count: int = 0
    owner_wxid: str = ""


@dataclass
class MemberInfo:
    """成员信息数据结构"""
    member_wxid: str
    group_wxid: str
    nickname: str = ""
    group_nick: str = ""


class WeChatDataCollector:
    """微信数据采集器"""

    def __init__(self, api: WeChatAPI, data_callback: Optional[Callable] = None, max_workers: int = 5):
        self.api = api
        self.data_callback = data_callback
        self.message_queue = queue.Queue(maxsize=1000)
        self.running = False
        self.bot_wxid = None

        # 异步回调处理线程池
        self.callback_executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="callback")

        # 统计信息
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'api_calls': 0,
            'api_errors': 0
        }

        self._get_bot_wxid()

    def _get_bot_wxid(self):
        """获取机器人wxid"""
        try:
            print("🔍 获取机器人wxid...")
            list_result = self.api.get_wechat_list()
            if list_result.get('code') == 200:
                wechat_list = list_result.get('result', [])
                if wechat_list:
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
        """启动数据采集器"""
        self.running = True
        print("🚀 启动微信数据采集器...")

        # 启动WebSocket接收线程
        ws_thread = threading.Thread(target=self._websocket_receiver, daemon=True)
        ws_thread.start()

        # 启动消息处理线程
        process_thread = threading.Thread(target=self._message_processor, daemon=True)
        process_thread.start()

        # 保持主线程运行
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⚠️ 接收到停止信号")
        finally:
            self.stop()

    def stop(self):
        """停止采集器"""
        self.running = False
        print("⚠️ 正在停止数据采集器...")

        # 关闭回调线程池
        if hasattr(self, 'callback_executor'):
            self.callback_executor.shutdown(wait=True)
            print("✅ 回调线程池已关闭")

    def _websocket_receiver(self):
        """WebSocket接收线程"""
        try:
            import websocket

            ws_url = "ws://192.168.31.6:7778"
            print(f"🔌 连接WebSocket: {ws_url}")

            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if data.get('event') == 10008:  # 群聊消息
                        self.message_queue.put(data)
                        self.stats['messages_received'] += 1
                except Exception as e:
                    print(f"❌ 消息接收错误: {e}")

            def on_error(ws, error):
                print(f"❌ WebSocket错误: {error}")

            def on_close(ws, close_status_code, close_msg):
                print(f"🔌 连接断开，5秒后重连...")
                if self.running:
                    time.sleep(5)
                    self._websocket_receiver()

            def on_open(ws):
                print(f"✅ WebSocket连接成功，开始采集数据...")

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

    def _message_processor(self):
        """消息处理线程"""
        print("📝 消息处理器已启动")

        while self.running:
            try:
                # 从队列获取消息，设置超时避免阻塞
                data = self.message_queue.get(timeout=1.0)

                # 解析消息
                parsed = self.api.parse_group_message(data)
                if 'error' not in parsed:
                    wechat_msg = self._parse_message(parsed)
                    if wechat_msg:
                        self._process_message(wechat_msg)
                        self.stats['messages_processed'] += 1

                self.message_queue.task_done()

            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ 消息处理错误: {e}")

    def _parse_message(self, parsed_data: Dict) -> Optional[WeChatMessage]:
        """解析消息为结构化数据"""
        try:
            msg = parsed_data.get('message', {})
            parsed_msg = msg.get('parsedMsg', {})

            wechat_msg = WeChatMessage(
                msg_id=msg.get('msgId', ''),
                from_type=msg.get('fromType', 0),
                from_wxid=msg.get('fromWxid', ''),
                final_from_wxid=msg.get('finalFromWxid', ''),
                msg_type=msg.get('msgType', 0),
                msg_source=msg.get('msgSource', 0),
                content=parsed_msg.get('content', ''),
                parsed_content=parsed_msg,
                timestamp=parsed_data.get('timeStamp', datetime.now().isoformat()),
                member_count=msg.get('membercount', 0),
                silence=msg.get('silence', 0),
                at_wxid_list=msg.get('atWxidList', []),
                signature=msg.get('signature', '')
            )

            return wechat_msg

        except Exception as e:
            print(f"❌ 消息解析错误: {e}")
            return None

    def _process_message(self, wechat_msg: WeChatMessage):
        """处理单条消息"""
        # 输出结构化数据
        self._output_message(wechat_msg)

  
    def _get_message_info(self, wechat_msg: WeChatMessage):
        """获取消息的群信息和成员信息"""
        group_name = ""
        member_nick = ""

        if wechat_msg.from_type == 2:  # 群聊
            try:
                # 获取群信息
                group_result = self.api.query_group(wechat_msg.from_wxid, self.bot_wxid)
                self.stats['api_calls'] += 1
                if group_result.get('code') == 200:
                    group_info = group_result.get('result', {})
                    group_name = group_info.get('nick', '')
                else:
                    self.stats['api_errors'] += 1
            except Exception as e:
                print(f"❌ 获取群信息失败: {e}")
                self.stats['api_errors'] += 1

            try:
                # 获取成员信息
                member_result = self.api.get_member_nick(wechat_msg.from_wxid, wechat_msg.final_from_wxid, self.bot_wxid)
                self.stats['api_calls'] += 1
                if member_result.get('code') == 200:
                    member_info = member_result.get('result', {})
                    member_nick = member_info.get('groupNick', '')
                else:
                    self.stats['api_errors'] += 1
            except Exception as e:
                print(f"❌ 获取成员信息失败: {e}")
                self.stats['api_errors'] += 1

        return group_name, member_nick

    def _output_message(self, wechat_msg: WeChatMessage):
        """输出结构化消息数据"""
        # 获取群信息和成员信息
        group_name, member_nick = self._get_message_info(wechat_msg)

        # 构建完整消息数据
        complete_data = {
            'message': asdict(wechat_msg),
            'group_info': {
                'group_name': group_name,
                'member_nick': member_nick
            },
            'collection_metadata': {
                'collector_version': '1.0.0',
                'collection_time': datetime.now().isoformat(),
                'stats': self.stats.copy()
            }
        }

        # 异步调用回调函数
        if self.data_callback:
            try:
                self.callback_executor.submit(self._safe_callback, complete_data)
            except Exception as e:
                print(f"❌ 提交回调任务失败: {e}")

    def _safe_callback(self, data):
        """安全执行回调函数"""
        try:
            self.data_callback(data)
        except Exception as e:
            print(f"❌ 数据回调处理错误: {e}")

  
    

# 使用示例
if __name__ == "__main__":
    def data_callback(data):
        """
        数据回调函数示例

        data 参数结构:
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
        # 这里可以添加数据清洗、存储等逻辑
        import time
        print(f"开始处理消息: {data['message']['content'][:50]}...")

        # 模拟耗时操作（10秒）
        time.sleep(10)

        print(f"完成处理消息: {data['message']['msg_id']}")

    api = WeChatAPI(base_url="http://192.168.31.6:7777", safekey=None)
    # 设置最大工作线程数为3，避免过多并发
    collector = WeChatDataCollector(api, data_callback=data_callback, max_workers=3)

    try:
        collector.start()
    except KeyboardInterrupt:
        print("\n⚠️ 数据采集器已停止")