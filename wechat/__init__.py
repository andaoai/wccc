#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信API模块
提供微信自动化相关的API接口和工具
"""

from .WeChatAPI import WeChatAPI
from .debug_websocket import DebugWebSocketListener

__all__ = ['WeChatAPI', 'DebugWebSocketListener']
__version__ = '1.0.0'