#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接模块
PostgreSQL数据库连接和管理
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库连接配置
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '54768'), 
    'database': os.getenv('POSTGRES_DB', 'postgres'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'your_secure_password_here')
}

class DatabaseManager:
    """数据库管理器"""

    def __init__(self):
        self.config = DB_CONFIG
        self._test_connection()

    def _test_connection(self):
        """测试数据库连接"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = psycopg2.connect(**self.config)
            conn.autocommit = False
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库连接错误: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self, dict_cursor=False):
        """获取数据库游标的上下文管理器"""
        with self.get_connection() as conn:
            cursor_type = RealDictCursor if dict_cursor else None
            with conn.cursor(cursor_factory=cursor_type) as cursor:
                yield cursor
                conn.commit()

# 全局数据库管理器实例
db_manager = DatabaseManager()