#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLM AI Agent
基于智谱AI GLM-4.6模型的AI对话代理
"""

import os
import json
import asyncio
from typing import List, Dict, Optional, AsyncGenerator
from zai import ZhipuAiClient


class GLMAgent:
    def __init__(self, api_key: str = None, model: str = "glm-4.6"):
        """
        初始化GLM Agent

        Args:
            api_key: 智谱AI API密钥
            model: 使用的模型名称，默认为glm-4.6
        """
        self.api_key = api_key or os.getenv("ZHIPUAI_API_KEY")
        if not self.api_key:
            raise ValueError("API密钥未设置，请传入api_key参数或设置ZHIPUAI_API_KEY环境变量")

        self.model = model
        self.client = ZhipuAiClient(api_key=self.api_key)
        self.conversation_history: Dict[str, List[Dict]] = {}  # 存储不同会话的历史记录

    def chat(self,
             message: str,
             session_id: str = "default",
             system_prompt: str = None,
             max_tokens: int = 4096,
             temperature: float = 0.7,
             enable_thinking: bool = True) -> str:
        """
        与AI进行对话

        Args:
            message: 用户消息
            session_id: 会话ID，用于维护上下文
            system_prompt: 系统提示词
            max_tokens: 最大输出token数
            temperature: 温度参数，控制创造性
            enable_thinking: 是否启用思考模式

        Returns:
            str: AI回复
        """
        # 初始化会话历史
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
            # 添加系统提示词
            if system_prompt:
                self.conversation_history[session_id].append({
                    "role": "system",
                    "content": system_prompt
                })

        # 添加用户消息
        self.conversation_history[session_id].append({
            "role": "user",
            "content": message
        })

        try:
            # 调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history[session_id],
                max_tokens=max_tokens,
                temperature=temperature,
                thinking={"type": "enabled"} if enable_thinking else None
            )

            # 获取回复
            ai_response = response.choices[0].message.content

            # 添加AI回复到历史记录
            self.conversation_history[session_id].append({
                "role": "assistant",
                "content": ai_response
            })

            # 限制历史记录长度，保留最近20轮对话
            if len(self.conversation_history[session_id]) > 40:  # 20轮对话 = 40条消息
                self.conversation_history[session_id] = self.conversation_history[session_id][-40:]

            return ai_response

        except Exception as e:
            error_msg = f"GLM API调用失败: {str(e)}"
            print(error_msg)
            return error_msg

    async def chat_stream(self,
                         message: str,
                         session_id: str = "default",
                         system_prompt: str = None,
                         max_tokens: int = 4096,
                         temperature: float = 0.7,
                         enable_thinking: bool = True) -> AsyncGenerator[str, None]:
        """
        流式对话，实时返回AI回复

        Args:
            message: 用户消息
            session_id: 会话ID
            system_prompt: 系统提示词
            max_tokens: 最大输出token数
            temperature: 温度参数
            enable_thinking: 是否启用思考模式

        Yields:
            str: 流式返回的AI回复片段
        """
        # 初始化会话历史
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
            if system_prompt:
                self.conversation_history[session_id].append({
                    "role": "system",
                    "content": system_prompt
                })

        # 添加用户消息
        self.conversation_history[session_id].append({
            "role": "user",
            "content": message
        })

        try:
            # 流式调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history[session_id],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                thinking={"type": "enabled"} if enable_thinking else None
            )

            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            # 添加完整回复到历史记录
            if full_response:
                self.conversation_history[session_id].append({
                    "role": "assistant",
                    "content": full_response
                })

            # 限制历史记录长度
            if len(self.conversation_history[session_id]) > 40:
                self.conversation_history[session_id] = self.conversation_history[session_id][-40:]

        except Exception as e:
            error_msg = f"GLM流式API调用失败: {str(e)}"
            print(error_msg)
            yield error_msg

    def clear_session(self, session_id: str = None):
        """
        清除会话历史

        Args:
            session_id: 要清除的会话ID，如果为None则清除所有会话
        """
        if session_id:
            if session_id in self.conversation_history:
                del self.conversation_history[session_id]
        else:
            self.conversation_history.clear()

    def get_session_history(self, session_id: str) -> List[Dict]:
        """
        获取会话历史

        Args:
            session_id: 会话ID

        Returns:
            List[Dict]: 会话历史记录
        """
        return self.conversation_history.get(session_id, [])

    def set_system_prompt(self, session_id: str, system_prompt: str):
        """
        设置或更新会话的系统提示词

        Args:
            session_id: 会话ID
            system_prompt: 系统提示词
        """
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []

        # 检查是否已有系统提示词
        if (self.conversation_history[session_id] and
            self.conversation_history[session_id][0].get("role") == "system"):
            self.conversation_history[session_id][0]["content"] = system_prompt
        else:
            self.conversation_history[session_id].insert(0, {
                "role": "system",
                "content": system_prompt
            })

    def create_wechat_prompt(self, user_info: Dict = None) -> str:
        """
        创建适用于微信聊天的系统提示词

        Args:
            user_info: 用户信息字典

        Returns:
            str: 系统提示词
        """
        user_name = user_info.get("nickname", "朋友") if user_info else "朋友"
        group_name = user_info.get("group_name", "") if user_info else ""

        if group_name:
            prompt = f"""你是AI助手，正在微信群"{group_name}"中与{user_name}对话。

你的特点：
- 友好、幽默、自然
- 回复简洁，适合聊天场景
- 能记住对话上下文
- 避免过于正式或技术性的语言

请用轻松愉快的方式回复用户的消息。"""
        else:
            prompt = f"""你是AI助手，正在与{user_name}进行私聊。

你的特点：
- 温暖、友好、贴心
- 善于倾听和给出建议
- 保持对话的连贯性
- 适当使用表情符号增加亲和力

请以温暖的方式回复用户的消息。"""

        return prompt