#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型和表结构
WeChatMessageData数据结构定义和对应的PostgreSQL表结构
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from .database import db_manager

logger = logging.getLogger(__name__)


@dataclass
class WeChatMessageData:
    """微信消息数据结构规范"""
    type: str = ""                    # 交易类型（如：收、接、招聘、寻、出等）
    certificates: str = ""            # 原始证书信息（未拆分）
    social_security: str = ""         # 社保要求（如：唯一社保、转社保、无要求等）
    location: str = ""               # 地区信息（如：浙江省、宁波市等）
    price: int = 0                   # 价格信息
    other_info: str = ""             # 其他信息
    original_info: str = ""          # 原始消息内容
    split_certificates: Optional[List[str]] = None  # 证书拆分后的列表（前期可以为空）
    # 微信消息元数据
    group_name: str = ""             # 群名称
    member_nick: str = ""            # 群成员昵称
    group_wxid: str = ""             # 微信群ID
    member_wxid: str = ""            # 群成员微信ID
    bot_wxid: str = ""               # 机器人微信ID
    msg_time: str = ""               # 消息时间戳
    msg_id: str = ""                 # 消息ID
    timestamp: str = ""              # 消息时间戳

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "type": self.type,
            "certificates": self.certificates,
            "social_security": self.social_security,
            "location": self.location,
            "price": self.price,
            "other_info": self.other_info,
            "original_info": self.original_info,
            "split_certificates": self.split_certificates,
            # 微信消息元数据
            "group_name": self.group_name,
            "member_nick": self.member_nick,
            "group_wxid": self.group_wxid,
            "member_wxid": self.member_wxid,
            "msg_id": self.msg_id,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WeChatMessageData':
        """从字典创建dataclass实例"""
        return cls(
            type=data.get("type", ""),
            certificates=data.get("certificates", ""),
            social_security=data.get("social_security", ""),
            location=data.get("location", ""),
            price=data.get("price", 0),
            other_info=data.get("other_info", ""),
            original_info=data.get("original_info", ""),
            split_certificates=data.get("split_certificates"),
            # 微信消息元数据
            group_name=data.get("group_name", ""),
            member_nick=data.get("member_nick", ""),
            group_wxid=data.get("group_wxid", ""),
            member_wxid=data.get("member_wxid", ""),
            msg_id=data.get("msg_id", ""),
            timestamp=data.get("timestamp", "")
        )

# SQL语句：创建wechat_messages表
CREATE_WECHAT_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS wechat_messages (
    id SERIAL PRIMARY KEY,

    -- 业务字段
    type VARCHAR(50) NOT NULL DEFAULT '',
    certificates TEXT NOT NULL DEFAULT '',
    social_security VARCHAR(100) NOT NULL DEFAULT '',
    location VARCHAR(100) NOT NULL DEFAULT '',
    price INTEGER NOT NULL DEFAULT 0,
    other_info TEXT NOT NULL DEFAULT '',
    original_info TEXT NOT NULL DEFAULT '',

    -- PostgreSQL数组字段存储拆分后的证书列表
    split_certificates TEXT[],

    -- 微信消息元数据
    group_name VARCHAR(200) NOT NULL DEFAULT '',
    member_nick VARCHAR(100) NOT NULL DEFAULT '',
    group_wxid VARCHAR(100) NOT NULL DEFAULT '',
    member_wxid VARCHAR(100) NOT NULL DEFAULT '',
    msg_id VARCHAR(100) NOT NULL DEFAULT '',
    timestamp TIMESTAMP,

    -- 系统字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 创建索引优化查询性能
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_wechat_messages_type ON wechat_messages(type);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_messages_location ON wechat_messages(location);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_messages_group_wxid ON wechat_messages(group_wxid);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_messages_timestamp ON wechat_messages(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_wechat_messages_msg_id ON wechat_messages(msg_id);",
    # 创建GIN索引支持数组查询
    "CREATE INDEX IF NOT EXISTS idx_wechat_messages_split_certificates ON wechat_messages USING GIN(split_certificates);",
    # 创建更新时间触发器
    """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """,
    """
    DROP TRIGGER IF EXISTS update_wechat_messages_updated_at ON wechat_messages;
    CREATE TRIGGER update_wechat_messages_updated_at
        BEFORE UPDATE ON wechat_messages
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """
]

def init_database():
    """初始化数据库表结构"""
    try:
        with db_manager.get_cursor() as cursor:
            # 创建主表
            cursor.execute(CREATE_WECHAT_MESSAGES_TABLE)
            logger.info("✅ wechat_messages表创建成功")

            # 创建索引和触发器
            for index_sql in CREATE_INDEXES:
                try:
                    cursor.execute(index_sql)
                except Exception as e:
                    logger.warning(f"创建索引/触发器时出现警告: {e}")

            logger.info("✅ 数据库索引和触发器创建完成")

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise

def test_table_exists():
    """测试表是否存在并可以正常插入数据"""
    try:
        with db_manager.get_cursor() as cursor:
            # 测试表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'wechat_messages'
                );
            """)
            table_exists = cursor.fetchone()[0]

            if table_exists:
                logger.info("✅ wechat_messages表已存在")
                # 测试插入一条测试数据
                cursor.execute("""
                    INSERT INTO wechat_messages (type, group_name, member_nick)
                    VALUES ('test', 'test_group', 'test_member')
                    ON CONFLICT DO NOTHING;
                """)
                logger.info("✅ 测试数据插入成功")
            else:
                logger.warning("⚠️ wechat_messages表不存在，请先运行init_database()")

    except Exception as e:
        logger.error(f"❌ 测试表结构失败: {e}")
        raise

if __name__ == "__main__":
    # 如果直接运行此文件，则初始化数据库
    logger.info("开始初始化数据库...")
    init_database()
    test_table_exists()
    logger.info("数据库初始化完成！")