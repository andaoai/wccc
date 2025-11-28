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

def classify_transaction_type(type_str):
    """分类交易类型为'收'或'出'"""
    if not type_str:
        return "其他"

    type_str = type_str.strip()

    # 收类型：包括收、接、招聘、寻
    receive_types = ['收', '接', '招聘', '寻']
    # 出类型：包括出
    send_types = ['出']

    if any(r_type in type_str for r_type in receive_types):
        return "收"
    elif any(s_type in type_str for s_type in send_types):
        return "出"
    else:
        return "其他"

def read_sql_file(filename):
    """读取 SQL 文件"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file_path = os.path.join(current_dir, 'sql', filename)

    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"SQL 文件未找到: {sql_file_path}")
        return None
    except Exception as e:
        st.error(f"读取 SQL 文件时出错: {e}")
        return None

def load_data():
    """加载数据库数据"""
    try:
        # 读取 SQL 文件
        receive_sql = read_sql_file('receive_messages.sql')
        send_sql = read_sql_file('send_messages.sql')
        other_sql = read_sql_file('other_messages.sql')

        if not all([receive_sql, send_sql, other_sql]):
            st.error("无法加载 SQL 查询文件")
            return pd.DataFrame()

        with db_manager.get_cursor(dict_cursor=True) as cursor:
            # 执行收类型查询
            cursor.execute(receive_sql)
            receive_messages = cursor.fetchall()

            # 执行出类型查询
            cursor.execute(send_sql)
            send_messages = cursor.fetchall()

            # 执行其他类型查询
            cursor.execute(other_sql)
            other_messages = cursor.fetchall()

            # 合并所有数据
            all_messages = receive_messages + send_messages + other_messages

            # 添加交易分类字段
            for msg in all_messages:
                msg['transaction_category'] = classify_transaction_type(msg.get('type', ''))

            st.session_state.all_messages = [dict(msg) for msg in all_messages]
            st.session_state.filtered_messages = st.session_state.all_messages.copy()
            st.session_state.data_loaded = True
            return True
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return False



def display_categorized_data():
    """按收/出分类显示数据表格"""
    if not st.session_state.filtered_messages:
        st.info("暂无数据")
        return

    # 转换为DataFrame
    df = pd.DataFrame(st.session_state.filtered_messages)

    # 按交易分类分组
    categories = ['收', '出', '其他']

    for category in categories:
        # 筛选当前分类的数据
        category_data = df[df['transaction_category'] == category]

        if len(category_data) == 0:
            continue

        # 显示分类标题和统计
        st.subheader(f"📊 {category}类型数据 ({len(category_data)}条)")

        # 选择要显示的列
        display_columns = [
            'created_at', 'type', 'certificates', 'location',
            'price', 'group_name', 'member_nick', 'split_certificates', 'duplicate_count'
        ]

        # 确保列存在
        available_columns = [col for col in display_columns if col in category_data.columns]
        df_display = category_data[available_columns].copy()

        # 格式化时间戳
        if 'created_at' in df_display.columns:
            df_display['created_at'] = pd.to_datetime(df_display['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # 格式化价格
        if 'price' in df_display.columns:
            df_display['price'] = df_display['price'].apply(lambda x: f"¥{x:,}" if x is not None and x > 0 else "-")

        # 重命名列标题
        column_names = {
            'created_at': '时间',
            'type': '类型',
            'certificates': '证书',
            'location': '地区',
            'price': '价格',
            'group_name': '群组',
            'member_nick': '成员',
            'split_certificates': '拆分证书',
            'duplicate_count': '重复次数'
        }
        df_display = df_display.rename(columns=column_names)

        # 显示数据表格
        st.dataframe(
            df_display,
            width='stretch',
            hide_index=True
        )

        # 添加分隔线
        st.markdown("---")

def display_data_table():
    """显示数据表格（保留原函数以防兼容性问题）"""
    display_categorized_data()


def sidebar_filters():
    """侧边栏筛选功能"""
    st.sidebar.markdown("## 🔍 数据筛选")

    if not st.session_state.all_messages:
        return

    df = pd.DataFrame(st.session_state.all_messages)

    # 交易分类筛选（收/出/其他）
    if 'transaction_category' in df.columns:
        categories = ['全部'] + list(df['transaction_category'].dropna().unique())
        selected_category = st.sidebar.selectbox("交易分类", categories)

        if selected_category != '全部':
            st.session_state.filtered_messages = [
                msg for msg in st.session_state.all_messages
                if msg.get('transaction_category') == selected_category
            ]
        else:
            st.session_state.filtered_messages = st.session_state.all_messages.copy()

    # 详细交易类型筛选
    if 'type' in df.columns:
        types = ['全部'] + sorted(list(df['type'].dropna().unique()))
        selected_type = st.sidebar.selectbox("详细类型", types)

        # 如果选择了具体类型，进一步筛选
        if selected_type != '全部':
            current_filtered = st.session_state.filtered_messages.copy()
            st.session_state.filtered_messages = [
                msg for msg in current_filtered
                if msg.get('type') == selected_type
            ]

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