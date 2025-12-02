#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信原始消息数据模型 - 用于去重
专门存储采集器的原始数据，用于去重判断
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from .database import db_manager

logger = logging.getLogger(__name__)


@dataclass
class WeChatRawMessage:
    """微信原始消息数据结构 - 用于去重"""
    # 消息基本信息
    msg_id: str = ""
    from_type: int = 0               # 1:私聊 2:群聊 3:公众号
    from_wxid: str = ""              # 来源wxid
    final_from_wxid: str = ""        # 最终发送者wxid
    msg_type: int = 0                # 消息类型
    msg_source: int = 0              # 0:别人发送 1:自己发送
    content: str = ""                # 消息内容
    timestamp: str = ""              # 时间戳
    member_count: int = 0            # 群成员数量
    silence: int = 0                 # 是否静默
    signature: str = ""              # 签名

    # 解析内容
    parsed_content: Dict = None      # 解析后的消息内容
    at_wxid_list: List = None        # @用户列表

    # 群信息
    group_name: str = ""             # 群名称
    member_nick: str = ""            # 发言者群昵称

    # 采集器元数据
    collector_version: str = ""      # 采集器版本
    collection_time: str = ""        # 采集时间

    def __post_init__(self):
        if self.parsed_content is None:
            self.parsed_content = {}
        if self.at_wxid_list is None:
            self.at_wxid_list = []

    @classmethod
    def from_callback_data(cls, data: Dict) -> 'WeChatRawMessage':
        """从callback_handler.py中的回调数据创建实例"""
        message = data.get('message', {})
        group_info = data.get('group_info', {})
        metadata = data.get('collection_metadata', {})

        return cls(
            msg_id=message.get('msg_id', ''),
            from_type=message.get('from_type', 0),
            from_wxid=message.get('from_wxid', ''),
            final_from_wxid=message.get('final_from_wxid', ''),
            msg_type=message.get('msg_type', 0),
            msg_source=message.get('msg_source', 0),
            content=message.get('content', ''),
            timestamp=message.get('timestamp', ''),
            member_count=message.get('member_count', 0),
            silence=message.get('silence', 0),
            signature=message.get('signature', ''),
            parsed_content=message.get('parsed_content', {}),
            at_wxid_list=message.get('at_wxid_list', []),
            group_name=group_info.get('group_name', ''),
            member_nick=group_info.get('member_nick', ''),
            collector_version=metadata.get('collector_version', ''),
            collection_time=metadata.get('collection_time', '')
        )


# SQL语句：创建wechat_raw_messages表（用于去重）
CREATE_WECHAT_RAW_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS wechat_raw_messages (
    id SERIAL PRIMARY KEY,

    -- 消息基本信息
    msg_id VARCHAR(100) NOT NULL DEFAULT '',
    from_type INTEGER NOT NULL DEFAULT 0,              -- 1:私聊 2:群聊 3:公众号
    from_wxid VARCHAR(100) NOT NULL DEFAULT '',        -- 来源wxid
    final_from_wxid VARCHAR(100) NOT NULL DEFAULT '',  -- 最终发送者wxid
    msg_type INTEGER NOT NULL DEFAULT 0,               -- 消息类型
    msg_source INTEGER NOT NULL DEFAULT 0,             -- 0:别人发送 1:自己发送
    content TEXT NOT NULL DEFAULT '',                  -- 消息内容
    timestamp TIMESTAMP,                               -- 消息时间戳
    member_count INTEGER NOT NULL DEFAULT 0,           -- 群成员数量
    silence INTEGER NOT NULL DEFAULT 0,                -- 是否静默
    signature VARCHAR(500) NOT NULL DEFAULT '',        -- 签名

    -- JSON字段存储复杂数据
    parsed_content JSONB,                              -- 解析后的消息内容
    at_wxid_list JSONB,                                -- @用户列表

    -- 群信息
    group_name VARCHAR(200) NOT NULL DEFAULT '',       -- 群名称
    member_nick VARCHAR(100) NOT NULL DEFAULT '',      -- 发言者群昵称

    -- 采集器元数据
    collector_version VARCHAR(50) NOT NULL DEFAULT '', -- 采集器版本
    collection_time TIMESTAMP,                         -- 采集时间

    -- 系统字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 创建索引优化查询性能
CREATE_RAW_MESSAGE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_msg_id ON wechat_raw_messages(msg_id);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_from_wxid ON wechat_raw_messages(from_wxid);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_final_from_wxid ON wechat_raw_messages(final_from_wxid);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_from_type ON wechat_raw_messages(from_type);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_timestamp ON wechat_raw_messages(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_group_name ON wechat_raw_messages(group_name);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_collection_time ON wechat_raw_messages(collection_time);",
    # 基于内容的哈希索引（避免长文本索引问题）
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_content_hash ON wechat_raw_messages USING hash (md5(content));",
    # JSON字段索引
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_parsed_content ON wechat_raw_messages USING GIN(parsed_content);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_raw_messages_at_wxid_list ON wechat_raw_messages USING GIN(at_wxid_list);",
    # 创建更新时间触发器
    """
    CREATE OR REPLACE FUNCTION update_raw_messages_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """,
    """
    DROP TRIGGER IF EXISTS update_wechat_raw_messages_updated_at ON wechat_raw_messages;
    CREATE TRIGGER update_wechat_raw_messages_updated_at
        BEFORE UPDATE ON wechat_raw_messages
        FOR EACH ROW
        EXECUTE FUNCTION update_raw_messages_updated_at();
    """
]

def init_raw_messages_database():
    """初始化原始消息数据库表结构"""
    try:
        with db_manager.get_cursor() as cursor:
            # 创建主表
            cursor.execute(CREATE_WECHAT_RAW_MESSAGES_TABLE)
            logger.info("✅ wechat_raw_messages表创建成功")

            # 创建索引和触发器
            for index_sql in CREATE_RAW_MESSAGE_INDEXES:
                try:
                    cursor.execute(index_sql)
                except Exception as e:
                    logger.warning(f"创建索引/触发器时出现警告: {e}")

            logger.info("✅ 原始消息数据库索引和触发器创建完成")

    except Exception as e:
        logger.error(f"❌ 原始消息数据库初始化失败: {e}")
        raise

def test_raw_messages_table_exists():
    """测试表是否存在并可以正常插入数据"""
    try:
        with db_manager.get_cursor() as cursor:
            # 测试表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'wechat_raw_messages'
                );
            """)
            table_exists = cursor.fetchone()[0]

            if table_exists:
                logger.info("✅ wechat_raw_messages表已存在")
                # 测试插入一条测试数据
                cursor.execute("""
                    INSERT INTO wechat_raw_messages (msg_id, final_from_wxid, content, timestamp)
                    VALUES ('test_id', 'test_wxid', 'test_content', NOW())
                    ON CONFLICT (msg_id, final_from_wxid, timestamp) DO NOTHING;
                """)
                logger.info("✅ 原始消息测试数据插入成功")
            else:
                logger.warning("⚠️ wechat_raw_messages表不存在，请先运行init_raw_messages_database()")

    except Exception as e:
        logger.error(f"❌ 测试原始消息表结构失败: {e}")
        raise

if __name__ == "__main__":
    # 如果直接运行此文件，则初始化数据库
    logger.info("开始初始化原始消息数据库...")
    init_raw_messages_database()
    test_raw_messages_table_exists()
    logger.info("原始消息数据库初始化完成！")