#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit主应用
微信消息数据展示和分析界面
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import wechat_message_dao, init_database, db_manager
from db.models import WeChatMessageData

# 页面配置
st.set_page_config(
    page_title="微信消息数据",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """初始化session state"""
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'all_messages' not in st.session_state:
        st.session_state.all_messages = []
    if 'filtered_messages' not in st.session_state:
        st.session_state.filtered_messages = []

def load_data():
    """加载数据库数据"""
    try:
        with db_manager.get_cursor(dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT * FROM wechat_messages
                ORDER BY created_at DESC
                LIMIT 10000
            """)
            messages = cursor.fetchall()
            st.session_state.all_messages = [dict(msg) for msg in messages]
            st.session_state.filtered_messages = st.session_state.all_messages.copy()
            st.session_state.data_loaded = True
            return True
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return False



def display_data_table():
    """显示数据表格"""
    if not st.session_state.filtered_messages:
        st.info("暂无数据")
        return

    # 转换为DataFrame
    df = pd.DataFrame(st.session_state.filtered_messages)

    # 选择要显示的列
    display_columns = [
        'created_at', 'type', 'certificates', 'location',
        'price', 'group_name', 'member_nick', 'split_certificates'
    ]

    # 确保列存在
    available_columns = [col for col in display_columns if col in df.columns]
    df_display = df[available_columns].copy()

    # 格式化时间戳
    if 'created_at' in df_display.columns:
        df_display['created_at'] = pd.to_datetime(df_display['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # 格式化价格
    if 'price' in df_display.columns:
        df_display['price'] = df_display['price'].apply(lambda x: f"¥{x:,}" if x > 0 else "-")

    # 重命名列标题
    column_names = {
        'created_at': '时间',
        'type': '类型',
        'certificates': '证书',
        'location': '地区',
        'price': '价格',
        'group_name': '群组',
        'member_nick': '成员',
        'split_certificates': '拆分证书'
    }
    df_display = df_display.rename(columns=column_names)

    # 显示数据表格
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True
    )


def sidebar_filters():
    """侧边栏筛选功能"""
    st.sidebar.markdown("## 🔍 数据筛选")

    if not st.session_state.all_messages:
        return

    df = pd.DataFrame(st.session_state.all_messages)

    # 交易类型筛选
    if 'type' in df.columns:
        types = ['全部'] + list(df['type'].dropna().unique())
        selected_type = st.sidebar.selectbox("交易类型", types)
        if selected_type != '全部':
            st.session_state.filtered_messages = [
                msg for msg in st.session_state.all_messages
                if msg.get('type') == selected_type
            ]
        else:
            st.session_state.filtered_messages = st.session_state.all_messages.copy()

def main():
    """主函数"""
    init_session_state()

    # 侧边栏
    with st.sidebar:
        st.markdown("## ⚙️ 设置")

        # 数据加载按钮
        if st.button("🔄 重新加载数据"):
            st.session_state.data_loaded = False
            st.rerun()

        # 初始化数据库按钮
        if st.button("🔧 初始化数据库"):
            try:
                init_database()
                st.success("数据库初始化成功！")
            except Exception as e:
                st.error(f"数据库初始化失败: {e}")

    # 加载数据
    if not st.session_state.data_loaded:
        with st.spinner("正在加载数据..."):
            load_data()

    # 如果数据加载成功，显示内容
    if st.session_state.data_loaded and st.session_state.all_messages:
        # 筛选功能
        sidebar_filters()

        # 直接显示数据列表
        display_data_table()

    else:
        st.warning("暂无数据，请检查数据库连接。")

if __name__ == "__main__":
    main()