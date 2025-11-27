#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据访问对象层
WeChatMessageData的数据库操作
"""

import psycopg2
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from .models import WeChatMessageData
from .database import db_manager

logger = logging.getLogger(__name__)

class WeChatMessageDAO:
    """微信消息数据访问对象"""

    def __init__(self):
        self.table_name = "wechat_messages"

    def insert_message(self, wechat_data: WeChatMessageData) -> Optional[int]:
        """
        插入单条微信消息数据

        Args:
            wechat_data: WeChatMessageData对象

        Returns:
            int: 插入记录的ID，失败返回None
        """
        sql = f"""
            INSERT INTO {self.table_name} (
                type, certificates, social_security, location, price, other_info, original_info,
                split_certificates, group_name, member_nick, group_wxid, member_wxid, msg_id, timestamp
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id;
        """

        try:
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql, (
                    wechat_data.type,
                    wechat_data.certificates,
                    wechat_data.social_security,
                    wechat_data.location,
                    wechat_data.price,
                    wechat_data.other_info,
                    wechat_data.original_info,
                    wechat_data.split_certificates,  # PostgreSQL自动处理数组类型
                    wechat_data.group_name,
                    wechat_data.member_nick,
                    wechat_data.group_wxid,
                    wechat_data.member_wxid,
                    wechat_data.msg_id,
                    self._parse_timestamp(wechat_data.timestamp)
                ))
                result = cursor.fetchone()
                if result:
                    message_id = result[0]
                    logger.info(f"✅ 成功插入微信消息，ID: {message_id}")
                    return message_id
                return None

        except Exception as e:
            logger.error(f"❌ 插入微信消息失败: {e}")
            return None

    def insert_messages_batch(self, wechat_data_list: List[WeChatMessageData]) -> List[int]:
        """
        批量插入微信消息数据

        Args:
            wechat_data_list: WeChatMessageData对象列表

        Returns:
            List[int]: 插入记录的ID列表
        """
        if not wechat_data_list:
            return []

        sql = f"""
            INSERT INTO {self.table_name} (
                type, certificates, social_security, location, price, other_info, original_info,
                split_certificates, group_name, member_nick, group_wxid, member_wxid, msg_id, timestamp
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id;
        """

        inserted_ids = []

        try:
            with db_manager.get_cursor() as cursor:
                for wechat_data in wechat_data_list:
                    cursor.execute(sql, (
                        wechat_data.type,
                        wechat_data.certificates,
                        wechat_data.social_security,
                        wechat_data.location,
                        wechat_data.price,
                        wechat_data.other_info,
                        wechat_data.original_info,
                        wechat_data.split_certificates,
                        wechat_data.group_name,
                        wechat_data.member_nick,
                        wechat_data.group_wxid,
                        wechat_data.member_wxid,
                        wechat_data.msg_id,
                        self._parse_timestamp(wechat_data.timestamp)
                    ))
                    result = cursor.fetchone()
                    if result:
                        inserted_ids.append(result[0])

            logger.info(f"✅ 成功批量插入 {len(inserted_ids)} 条微信消息")
            return inserted_ids

        except Exception as e:
            logger.error(f"❌ 批量插入微信消息失败: {e}")
            return []

    def find_by_msg_id(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """
        根据消息ID查找消息

        Args:
            msg_id: 消息ID

        Returns:
            Dict: 消息数据，未找到返回None
        """
        sql = f"""
            SELECT * FROM {self.table_name}
            WHERE msg_id = %s
            LIMIT 1;
        """

        try:
            with db_manager.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(sql, (msg_id,))
                result = cursor.fetchone()
                return dict(result) if result else None

        except Exception as e:
            logger.error(f"❌ 根据消息ID查找失败: {e}")
            return None

    def find_by_certificate(self, certificate: str) -> List[Dict[str, Any]]:
        """
        根据证书名称查找消息（使用PostgreSQL数组查询）

        Args:
            certificate: 证书名称

        Returns:
            List[Dict]: 消息列表
        """
        sql = f"""
            SELECT * FROM {self.table_name}
            WHERE %s = ANY(split_certificates)
            ORDER BY created_at DESC;
        """

        try:
            with db_manager.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(sql, (certificate,))
                results = cursor.fetchall()
                logger.info(f"✅ 查找到包含 '{certificate}' 的消息 {len(results)} 条")
                return [dict(result) for result in results]

        except Exception as e:
            logger.error(f"❌ 根据证书查找失败: {e}")
            return []

    def find_by_group(self, group_wxid: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        根据群组ID查找消息

        Args:
            group_wxid: 群组ID
            limit: 返回记录数限制

        Returns:
            List[Dict]: 消息列表
        """
        sql = f"""
            SELECT * FROM {self.table_name}
            WHERE group_wxid = %s
            ORDER BY created_at DESC
            LIMIT %s;
        """

        try:
            with db_manager.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(sql, (group_wxid, limit))
                results = cursor.fetchall()
                logger.info(f"✅ 查找到群组 '{group_wxid}' 的消息 {len(results)} 条")
                return [dict(result) for result in results]

        except Exception as e:
            logger.error(f"❌ 根据群组查找失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict: 统计信息
        """
        sql = f"""
            SELECT
                COUNT(*) as total_messages,
                COUNT(DISTINCT group_wxid) as unique_groups,
                COUNT(DISTINCT member_wxid) as unique_members,
                COUNT(CASE WHEN split_certificates IS NOT NULL AND array_length(split_certificates, 1) > 0 THEN 1 END) as messages_with_certificates,
                AVG(price) as avg_price,
                MAX(created_at) as latest_message
            FROM {self.table_name};
        """

        try:
            with db_manager.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                stats = dict(result)
                logger.info("✅ 获取统计信息成功")
                return stats

        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {}

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """
        解析时间戳字符串为datetime对象

        Args:
            timestamp_str: 时间戳字符串

        Returns:
            datetime: 解析后的datetime对象
        """
        if not timestamp_str:
            return None

        try:
            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S.%f'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue

            logger.warning(f"无法解析时间戳格式: {timestamp_str}")
            return None

        except Exception as e:
            logger.error(f"解析时间戳失败: {e}")
            return None

# 创建全局DAO实例
wechat_message_dao = WeChatMessageDAO()