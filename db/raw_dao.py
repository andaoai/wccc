#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信原始消息数据访问对象层
专门用于原始消息的存储和去重判断
"""

import json
from typing import Optional, Dict, Any
import logging
from datetime import datetime
from .raw_models import WeChatRawMessage
from .database import db_manager

logger = logging.getLogger(__name__)

class WeChatRawMessageDAO:
    """微信原始消息数据访问对象"""

    def __init__(self):
        self.table_name = "wechat_raw_messages"

    def is_message_duplicate(self, content: str) -> bool:
        """
        根据消息内容检查是否重复

        Args:
            content: 消息内容

        Returns:
            bool: True表示重复，False表示不重复
        """
        sql = f"""
            SELECT EXISTS (
                SELECT 1 FROM {self.table_name}
                WHERE content = %s
            );
        """

        try:
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql, (content,))
                result = cursor.fetchone()
                is_duplicate = result[0] if result else False

                if is_duplicate:
                    logger.debug(f"🔄 发现重复消息内容: {content[:50]}...")

                return is_duplicate

        except Exception as e:
            logger.error(f"❌ 检查消息重复失败: {e}")
            # 出错时默认不重复，避免丢失数据
            return False

    def insert_raw_message(self, raw_message: WeChatRawMessage) -> Optional[int]:
        """
        插入原始消息数据（如果不存在重复）

        Args:
            raw_message: WeChatRawMessage对象

        Returns:
            int: 插入记录的ID，重复返回None，失败返回None
        """
        # 先检查是否重复（基于内容）
        if self.is_message_duplicate(raw_message.content):
            logger.info(f"🔄 消息内容重复，跳过存储: {raw_message.content[:50]}...")
            return None

        sql = f"""
            INSERT INTO {self.table_name} (
                msg_id, from_type, from_wxid, final_from_wxid, msg_type, msg_source,
                content, timestamp, member_count, silence, signature, parsed_content,
                at_wxid_list, group_name, member_nick, collector_version, collection_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            ) RETURNING id;
        """

        try:
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql, (
                    raw_message.msg_id,
                    raw_message.from_type,
                    raw_message.from_wxid,
                    raw_message.final_from_wxid,
                    raw_message.msg_type,
                    raw_message.msg_source,
                    raw_message.content,
                    self._parse_timestamp(raw_message.timestamp),
                    raw_message.member_count,
                    raw_message.silence,
                    raw_message.signature,
                    json.dumps(raw_message.parsed_content) if raw_message.parsed_content else None,
                    json.dumps(raw_message.at_wxid_list) if raw_message.at_wxid_list else None,
                    raw_message.group_name,
                    raw_message.member_nick,
                    raw_message.collector_version,
                    self._parse_timestamp(raw_message.collection_time)
                ))
                result = cursor.fetchone()
                if result:
                    message_id = result[0]
                    logger.info(f"✅ 成功插入原始消息，ID: {message_id}")
                    return message_id
                return None

        except Exception as e:
            logger.error(f"❌ 插入原始消息失败: {e}")
            return None

    def upsert_raw_message(self, raw_message: WeChatRawMessage) -> Optional[int]:
        """
        插入原始消息（基于内容去重）
        如果消息内容存在则跳过，不存在则插入

        Args:
            raw_message: WeChatRawMessage对象

        Returns:
            int: 记录的ID，重复返回None，失败返回None
        """
        # 检查内容是否存在
        if self.is_message_duplicate(raw_message.content):
            # 消息内容存在，直接跳过
            logger.info(f"🔄 消息内容已存在，跳过存储: {raw_message.content[:50]}...")
            return None
        else:
            # 消息内容不存在，插入新记录
            return self.insert_raw_message(raw_message)

    def get_raw_message_by_id(self, message_id: int) -> Optional[Dict]:
        """根据ID获取原始消息"""
        sql = f"SELECT * FROM {self.table_name} WHERE id = %s;"

        try:
            with db_manager.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(sql, (message_id,))
                result = cursor.fetchone()
                return result

        except Exception as e:
            logger.error(f"❌ 获取原始消息失败: {e}")
            return None

    def get_duplicate_statistics(self) -> Dict[str, Any]:
        """获取重复消息统计信息"""
        sql = f"""
            SELECT
                COUNT(*) as total_messages,
                COUNT(DISTINCT content) as unique_messages,
                COUNT(*) - COUNT(DISTINCT content) as duplicate_count,
                MAX(created_at) as last_message_time
            FROM {self.table_name};
        """

        try:
            with db_manager.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return result if result else {}

        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {}

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """解析时间戳字符串"""
        if not timestamp_str:
            return None

        try:
            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%SZ'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue

            # 如果都不匹配，尝试直接解析ISO格式
            try:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                pass

            # 尝试解析为毫秒时间戳
            try:
                timestamp_ms = int(timestamp_str)
                # 判断是否为毫秒级时间戳（13位数字）
                if timestamp_ms > 1e12:  # 大于1万亿，认为是毫秒时间戳
                    return datetime.fromtimestamp(timestamp_ms / 1000)
                else:  # 秒级时间戳
                    return datetime.fromtimestamp(timestamp_ms)
            except (ValueError, OSError):
                pass

        except Exception as e:
            logger.warning(f"时间戳解析失败: {timestamp_str}, 错误: {e}")
            return None

    def delete_old_messages(self, days: int = 30) -> int:
        """删除指定天数前的旧消息"""
        sql = f"""
            DELETE FROM {self.table_name}
            WHERE created_at < NOW() - INTERVAL '{days} days';
        """

        try:
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql)
                deleted_count = cursor.rowcount
                logger.info(f"✅ 清理了 {deleted_count} 条旧消息")
                return deleted_count

        except Exception as e:
            logger.error(f"❌ 清理旧消息失败: {e}")
            return 0

# 全局原始消息DAO实例
raw_message_dao = WeChatRawMessageDAO()

# 便捷函数
def store_raw_message_safely(data: Dict) -> Optional[int]:
    """
    安全存储原始消息的便捷函数

    Args:
        data: callback_handler.py中的回调数据

    Returns:
        int: 存储结果ID，重复或失败返回None
    """
    try:
        raw_message = WeChatRawMessage.from_callback_data(data)
        return raw_message_dao.upsert_raw_message(raw_message)
    except Exception as e:
        logger.error(f"❌ 安全存储原始消息失败: {e}")
        return None