#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot 模块
包含微信数据采集器和回调处理器
"""

# 导入配置和回调函数，避免循环导入
from .config import MONITORED_GROUPS
from .callback_handler import data_callback

# WeChatDataCollector可以独立运行，不在这里导入以避免循环依赖
# 如需使用，请直接从 bot.wechat_data_collector 导入

__all__ = [
    'data_callback',
    'MONITORED_GROUPS'
]