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
    if 'business_messages' not in st.session_state:
        st.session_state.business_messages = []
    if 'filtered_business' not in st.session_state:
        st.session_state.filtered_business = []

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

def get_all_locations():
    """获取所有可用地区列表（包含无地区信息选项）"""
    try:
        with db_manager.get_cursor(dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT DISTINCT location,
                    CASE
                        WHEN location = '全国' THEN 1
                        WHEN location LIKE '%省%' AND NOT location LIKE '%市%' THEN 2
                        WHEN location LIKE '%省%市%' THEN 3
                        WHEN location LIKE '%市%' AND NOT location LIKE '%省%' THEN 4
                        ELSE 5
                    END as sort_order
                FROM wechat_messages
                WHERE location IS NOT NULL
                  AND location != ''
                  AND location != 'None'
                  AND TRIM(location) != ''
                ORDER BY sort_order, location
            """)
            results = cursor.fetchall()
            locations = [row['location'] for row in results]

            # 在开头添加特殊选项
            return ['无地区信息'] + locations
    except Exception as e:
        st.error(f"获取地区列表失败: {e}")
        return ['无地区信息']

def query_by_location(location, message_types=None, fuzzy_search=False):
    """按地区查询消息（支持模糊查询）"""
    try:
        # 构建类型筛选条件
        type_condition = ""
        if message_types and len(message_types) > 0 and '全部' not in message_types:
            conditions = []
            if '收类型' in message_types:
                conditions.append("(type LIKE '%收%' OR type LIKE '%接%' OR type LIKE '%招聘%' OR type LIKE '%寻%')")
            if '出类型' in message_types:
                conditions.append("type LIKE '%出%'")
            if '其他类型' in message_types:
                conditions.append("NOT (type LIKE '%收%' OR type LIKE '%接%' OR type LIKE '%招聘%' OR type LIKE '%寻%' OR type LIKE '%出%')")

            if conditions:
                type_condition = " AND (" + " OR ".join(conditions) + ")"

        # 构建地区查询条件
        if location == '无地区信息':
            location_condition = "(location IS NULL OR location = '' OR location = 'None' OR TRIM(location) = '')"
        elif fuzzy_search:
            # 模糊查询：支持字符串部分匹配
            location_condition = "location LIKE %s"
            location_param = f"%{location}%"
        else:
            # 精确查询
            location_condition = "location = %s"
            location_param = location

        # 构建动态SQL
        base_sql = f"""
        WITH ranked_messages AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn,
                   COUNT(*) OVER (PARTITION BY original_info, member_wxid) as duplicate_count,
                   CASE
                       WHEN type LIKE '%出%' THEN '出'
                       WHEN type LIKE '%收%' OR type LIKE '%接%' OR type LIKE '%招聘%' OR type LIKE '%寻%' THEN '收'
                       ELSE '其他'
                   END as transaction_category
            FROM wechat_messages
            WHERE {location_condition}
        """ + type_condition + """
        )
        SELECT *
        FROM ranked_messages
        WHERE rn = 1
        ORDER BY created_at DESC
        LIMIT 5000;
        """

        with db_manager.get_cursor(dict_cursor=True) as cursor:
            if location == '无地区信息':
                cursor.execute(base_sql)
            else:
                cursor.execute(base_sql, (location_param,))
            results = cursor.fetchall()
            return [dict(msg) for msg in results]

    except Exception as e:
        st.error(f"地区查询失败: {e}")
        return []

def query_certificates(target_certs, location_filter=None, fuzzy_search=False):
    """动态查询指定证书（支持地区筛选和模糊搜索）"""
    try:
        # 构建动态SQL
        certs_formatted = "', '".join(target_certs)

        # 构建地区筛选条件
        location_condition = ""
        if location_filter and location_filter != "全部":
            if fuzzy_search:
                location_condition = f"AND location LIKE '%{location_filter}%'"
            else:
                location_condition = f"AND location = '{location_filter}'"

        dynamic_sql = f"""
        WITH target_certs AS (
            SELECT ARRAY['{certs_formatted}']::text[] as certificates
        ),
        ranked_messages AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn,
                   COUNT(*) OVER (PARTITION BY original_info, member_wxid) as duplicate_count,
                   '出' as transaction_category,

                   -- 检查是否包含目标证书
                   CASE
                       WHEN split_certificates IS NOT NULL
                        AND split_certificates != '{{}}'::text[]
                        AND EXISTS (
                            SELECT 1
                            FROM target_certs tc,
                                 unnest(split_certificates) sc
                            WHERE sc = ANY(tc.certificates)
                        )
                       THEN true
                       ELSE false
                   END as contains_target_certificates,

                   -- 统计包含的目标证书数量
                   CASE
                       WHEN split_certificates IS NOT NULL
                        AND split_certificates != '{{}}'::text[]
                       THEN (
                           SELECT COUNT(*)
                           FROM target_certs tc,
                                unnest(split_certificates) sc
                           WHERE sc = ANY(tc.certificates)
                       )
                       ELSE 0
                   END as target_certificates_count,

                   -- 列出包含的目标证书
                   CASE
                       WHEN split_certificates IS NOT NULL
                        AND split_certificates != '{{}}'::text[]
                       THEN (
                           SELECT array_agg(DISTINCT sc ORDER BY sc)
                           FROM target_certs tc,
                                unnest(split_certificates) sc
                           WHERE sc = ANY(tc.certificates)
                       )
                       ELSE NULL
                   END as found_target_certificates

            FROM wechat_messages
            WHERE type LIKE '%出%'
              {location_condition}
        )
        SELECT
            *
        FROM ranked_messages
        WHERE rn = 1
          AND contains_target_certificates = true
        ORDER BY target_certificates_count DESC, created_at DESC
        LIMIT 5000;
        """

        with db_manager.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(dynamic_sql)
            results = cursor.fetchall()
            return [dict(msg) for msg in results]

    except Exception as e:
        st.error(f"证书查询失败: {e}")
        return []

def load_business_opportunity_data():
    """加载商机匹配数据"""
    try:
        # 读取商机SQL文件
        business_sql = read_sql_file('receive_messages_with_supply_stats.sql')

        if not business_sql:
            st.error("无法加载商机数据 SQL 查询文件")
            return []

        with db_manager.get_cursor(dict_cursor=True) as cursor:
            cursor.execute(business_sql)
            business_messages = cursor.fetchall()

            # 确保数据为字典列表格式
            return [dict(msg) for msg in business_messages]

    except Exception as e:
        st.error(f"商机数据加载失败: {e}")
        return []

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

            # 同时加载商机数据
            st.session_state.business_messages = load_business_opportunity_data()

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


def sidebar_filters(location_filter=None, fuzzy_location_input=None, use_fuzzy_search=False, time_filter="全部时间"):
    """侧边栏筛选功能（支持多选和模糊搜索同时使用）"""
    st.sidebar.markdown("## 🔍 数据筛选")

    if not st.session_state.all_messages:
        return

    # 移除侧边栏时间筛选，使用全局时间筛选参数

    # 应用地区筛选 - 支持多个地区、"无地区信息"选项和模糊搜索同时使用
    base_messages = st.session_state.all_messages

    # 如果有地区筛选条件（精确匹配或模糊搜索）
    if (location_filter and len(location_filter) > 0) or (use_fuzzy_search and fuzzy_location_input and fuzzy_location_input.strip()):
        base_messages = []
        for msg in st.session_state.all_messages:
            msg_location = msg.get('location')

            # 精确匹配检查
            exact_match = False
            if location_filter and len(location_filter) > 0:
                if msg_location in location_filter:
                    exact_match = True
                elif '无地区信息' in location_filter and (
                    msg_location is None or
                    msg_location == '' or
                    msg_location == 'None' or
                    (isinstance(msg_location, str) and msg_location.strip() == '')
                ):
                    exact_match = True

            # 模糊搜索检查
            fuzzy_match = False
            if use_fuzzy_search and fuzzy_location_input and fuzzy_location_input.strip():
                search_keyword = fuzzy_location_input.strip().lower()
                if msg_location and isinstance(msg_location, str) and search_keyword in msg_location.lower():
                    fuzzy_match = True

            # 匹配逻辑：精确匹配 OR 模糊搜索（只要满足任一条件就包含）
            if (location_filter and len(location_filter) > 0 and exact_match) or (use_fuzzy_search and fuzzy_match):
                base_messages.append(msg)
            elif not location_filter or len(location_filter) == 0:  # 如果没有精确匹配，只考虑模糊搜索
                if use_fuzzy_search and fuzzy_match:
                    base_messages.append(msg)

    # 应用时间筛选（使用全局参数）
    if time_filter and time_filter != "全部时间":
        from datetime import datetime, timedelta
        now = datetime.now()

        if time_filter == "最近3天":
            cutoff_date = now - timedelta(days=3)
        elif time_filter == "最近7天":
            cutoff_date = now - timedelta(days=7)
        elif time_filter == "最近30天":
            cutoff_date = now - timedelta(days=30)
        else:
            cutoff_date = None

        if cutoff_date:
            filtered_by_time = []
            for msg in base_messages:
                created_at = msg.get('created_at')
                if created_at:
                    # 处理不同的时间格式
                    if isinstance(created_at, str):
                        try:
                            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            try:
                                # 尝试其他常见格式
                                created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                            except:
                                continue
                    elif isinstance(created_at, datetime):
                        created_dt = created_at
                    else:
                        continue

                    if created_dt >= cutoff_date:
                        filtered_by_time.append(msg)
            base_messages = filtered_by_time

    df = pd.DataFrame(base_messages)

    # 交易分类筛选（收/出/其他）
    if 'transaction_category' in df.columns:
        categories = ['全部'] + list(df['transaction_category'].dropna().unique())
        selected_category = st.sidebar.selectbox("交易分类", categories)

        if selected_category != '全部':
            st.session_state.filtered_messages = [
                msg for msg in base_messages
                if msg.get('transaction_category') == selected_category
            ]
        else:
            st.session_state.filtered_messages = base_messages.copy()

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

def business_opportunity_filters(location_filter=None, fuzzy_location_input=None, use_fuzzy_search=False):
    """商机数据筛选功能（支持多选和模糊搜索同时使用）"""
    if 'business_messages' not in st.session_state or not st.session_state.business_messages:
        return

    st.sidebar.markdown("## 💼 商机筛选")

    # 移除侧边栏时间筛选，统一使用主界面的时间筛选

    # 应用地区筛选 - 支持多个地区、"无地区信息"选项和模糊搜索同时使用
    base_business_messages = st.session_state.business_messages

    # 如果有地区筛选条件（精确匹配或模糊搜索）
    if (location_filter and len(location_filter) > 0) or (use_fuzzy_search and fuzzy_location_input and fuzzy_location_input.strip()):
        base_business_messages = []
        for msg in st.session_state.business_messages:
            msg_location = msg.get('location')

            # 精确匹配检查
            exact_match = False
            if location_filter and len(location_filter) > 0:
                if msg_location in location_filter:
                    exact_match = True
                elif '无地区信息' in location_filter and (
                    msg_location is None or
                    msg_location == '' or
                    msg_location == 'None' or
                    (isinstance(msg_location, str) and msg_location.strip() == '')
                ):
                    exact_match = True

            # 模糊搜索检查
            fuzzy_match = False
            if use_fuzzy_search and fuzzy_location_input and fuzzy_location_input.strip():
                search_keyword = fuzzy_location_input.strip().lower()
                if msg_location and isinstance(msg_location, str) and search_keyword in msg_location.lower():
                    fuzzy_match = True

            # 匹配逻辑：精确匹配 OR 模糊搜索（只要满足任一条件就包含）
            if (location_filter and len(location_filter) > 0 and exact_match) or (use_fuzzy_search and fuzzy_match):
                base_business_messages.append(msg)
            elif not location_filter or len(location_filter) == 0:  # 如果没有精确匹配，只考虑模糊搜索
                if use_fuzzy_search and fuzzy_match:
                    base_business_messages.append(msg)

    df = pd.DataFrame(base_business_messages)

    # 移除时间筛选逻辑，统一在 display_business_opportunity_dashboard 中处理

    # 供应匹配度筛选
    if 'total_supply_count' in df.columns:
        # 处理Decimal类型数据
        max_supply = int(float(df['total_supply_count'].max()))
        min_supply = 0
        supply_range = st.sidebar.slider(
            "供应匹配数范围",
            min_value=min_supply,
            max_value=max_supply,
            value=(min_supply, max_supply)
        )

        if supply_range != (min_supply, max_supply):
            st.session_state.filtered_business = [
                msg for msg in base_business_messages
                if supply_range[0] <= msg.get('total_supply_count', 0) <= supply_range[1]
            ]
        else:
            st.session_state.filtered_business = base_business_messages.copy()

    # 证书种类筛选
    if 'available_certificates_count' in df.columns:
        cert_options = ['全部'] + sorted(df['available_certificates_count'].dropna().unique().astype(int).tolist())
        selected_cert_count = st.sidebar.selectbox("可用证书种类数", cert_options)

        if selected_cert_count != '全部':
            current_filtered = st.session_state.filtered_business.copy()
            st.session_state.filtered_business = [
                msg for msg in current_filtered
                if msg.get('available_certificates_count') == selected_cert_count
            ]

    # 移除重复的地区筛选，使用主界面传递的地区筛选参数

    # 交易类型筛选
    if 'type' in df.columns:
        types = ['全部'] + sorted(df['type'].dropna().unique())
        selected_type = st.sidebar.selectbox("商机类型", types)

        if selected_type != '全部':
            current_filtered = st.session_state.filtered_business.copy()
            st.session_state.filtered_business = [
                msg for msg in current_filtered
                if msg.get('type') == selected_type
            ]

def display_business_opportunity_dashboard(location_filter=None, fuzzy_location_input=None, use_fuzzy_search=False, time_filter="全部时间"):
    """显示商机匹配仪表板（支持多选和模糊搜索同时使用）"""
    if 'business_messages' not in st.session_state or not st.session_state.business_messages:
        st.info("暂无商机数据")
        return

    # 显示当前地区筛选状态
    if (location_filter and len(location_filter) > 0) or (use_fuzzy_search and fuzzy_location_input and fuzzy_location_input.strip()):
        exact_count = len(location_filter) if location_filter else 0
        fuzzy_status = f"模糊搜索 '{fuzzy_location_input}'" if use_fuzzy_search and fuzzy_location_input.strip() else ""

        if exact_count > 0 and fuzzy_status:
            st.success(f"🌍 地区筛选已激活：精确匹配 {exact_count} 个地区 + {fuzzy_status}")
        elif exact_count > 0:
            st.success(f"🌍 地区筛选已激活：精确匹配 {exact_count} 个地区")
        elif fuzzy_status:
            st.success(f"🌍 地区筛选已激活：{fuzzy_status}")
    else:
        st.info("🌍 未设置地区筛选，显示全部地区数据")

    # 应用地区筛选 - 支持多个地区、"无地区信息"选项和模糊搜索同时使用
    base_business_messages = st.session_state.business_messages

    # 如果有地区筛选条件（精确匹配或模糊搜索）
    if (location_filter and len(location_filter) > 0) or (use_fuzzy_search and fuzzy_location_input and fuzzy_location_input.strip()):
        base_business_messages = []
        for msg in st.session_state.business_messages:
            msg_location = msg.get('location')

            # 精确匹配检查
            exact_match = False
            if location_filter and len(location_filter) > 0:
                if msg_location in location_filter:
                    exact_match = True
                elif isinstance(location_filter, list) and '无地区信息' in location_filter and (
                    msg_location is None or
                    msg_location == '' or
                    msg_location == 'None' or
                    (isinstance(msg_location, str) and msg_location.strip() == '')
                ):
                    exact_match = True

            # 模糊搜索检查
            fuzzy_match = False
            if use_fuzzy_search and fuzzy_location_input and fuzzy_location_input.strip():
                search_keyword = fuzzy_location_input.strip().lower()
                if msg_location and isinstance(msg_location, str) and search_keyword in msg_location.lower():
                    fuzzy_match = True

            # 匹配逻辑：精确匹配 OR 模糊搜索（只要满足任一条件就包含）
            if (location_filter and len(location_filter) > 0 and exact_match) or (use_fuzzy_search and fuzzy_match):
                base_business_messages.append(msg)
            elif not location_filter or len(location_filter) == 0:  # 如果没有精确匹配，只考虑模糊搜索
                if use_fuzzy_search and fuzzy_match:
                    base_business_messages.append(msg)

    # 应用时间筛选（使用从主界面传递的参数）
    if time_filter and time_filter != "全部时间":
        from datetime import datetime, timedelta
        now = datetime.now()

        if time_filter == "最近3天":
            cutoff_date = now - timedelta(days=3)
        elif time_filter == "最近7天":
            cutoff_date = now - timedelta(days=7)
        elif time_filter == "最近30天":
            cutoff_date = now - timedelta(days=30)
        else:
            cutoff_date = None

        if cutoff_date:
            filtered_by_time = []
            for msg in base_business_messages:
                created_at = msg.get('created_at')
                if created_at:
                    # 处理不同的时间格式
                    if isinstance(created_at, str):
                        try:
                            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            try:
                                # 尝试其他常见格式
                                created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                            except:
                                continue
                    elif isinstance(created_at, datetime):
                        created_dt = created_at
                    else:
                        continue

                    if created_dt >= cutoff_date:
                        filtered_by_time.append(msg)
            base_business_messages = filtered_by_time

    # 直接使用已经筛选好的数据，不要重复应用地区筛选
    df = pd.DataFrame(base_business_messages)

    # 显示时间筛选提示
    if time_filter and time_filter != "全部时间":
        st.info(f"📅 当前显示 {time_filter} 内的数据，共 {len(df)} 条商机")

    # 显示总体统计
    st.markdown("## 📊 商机匹配概览")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_opportunities = len(df)
        st.metric("总商机数", total_opportunities)

    with col2:
        matched_opportunities = len(df[df['total_supply_count'] > 0])
        match_rate = matched_opportunities / total_opportunities * 100 if total_opportunities > 0 else 0
        st.metric("匹配商机", f"{matched_opportunities} ({match_rate:.1f}%)")

    with col3:
        avg_supply = float(df['total_supply_count'].mean()) if len(df) > 0 else 0
        st.metric("平均供应匹配", f"{avg_supply:.1f}")

    with col4:
        high_match = len(df[df['total_supply_count'] >= 10])
        st.metric("高匹配商机", high_match)

    # 供应匹配分布图
    st.markdown("### 📈 供应匹配分布")
    col1, col2 = st.columns(2)

    with col1:
        # 供应匹配数直方图
        supply_hist = df['total_supply_count'].value_counts().sort_index()
        st.bar_chart(supply_hist)

    with col2:
        # 证书种类分布
        cert_dist = df['available_certificates_count'].value_counts().sort_index()
        st.bar_chart(cert_dist)

    # 热门证书统计
    st.markdown("### 🔥 热门需求证书")
    if len(df) > 0:
        # 统计所有证书的匹配度
        cert_stats = {}
        for _, row in df.iterrows():
            available_certs = row.get('available_certificates', [])
            supply_count = row.get('total_supply_count', 0)

            # 检查available_certs是否为None或不是列表
            if available_certs is None or not isinstance(available_certs, list):
                continue

            for cert in available_certs:
                if cert not in cert_stats:
                    cert_stats[cert] = {'demand_count': 0, 'total_supply': 0, 'avg_supply': 0}
                cert_stats[cert]['demand_count'] += 1
                cert_stats[cert]['total_supply'] += supply_count

        # 计算平均供应匹配
        for cert in cert_stats:
            if cert_stats[cert]['demand_count'] > 0:
                cert_stats[cert]['avg_supply'] = cert_stats[cert]['total_supply'] / cert_stats[cert]['demand_count']

        # 创建证书统计DataFrame
        cert_df = pd.DataFrame([
            {
                '证书': cert,
                '需求次数': stats['demand_count'],
                '总供应匹配': stats['total_supply'],
                '平均供应匹配': f"{stats['avg_supply']:.1f}"
            }
            for cert, stats in sorted(cert_stats.items(), key=lambda x: x[1]['total_supply'], reverse=True)[:10]
        ])

        st.dataframe(cert_df, use_container_width=True)

    # 商机详情表格
    st.markdown("### 💼 商机详情")

    # 选择显示的列
    display_columns = [
        'created_at', 'type', 'certificates', 'location', 'price',
        'total_supply_count', 'available_certificates_count', 'available_certificates',
        'group_name', 'member_nick', 'duplicate_count'
    ]

    # 确保列存在
    available_columns = [col for col in display_columns if col in df.columns]
    df_display = df[available_columns].copy()

    # 格式化数据
    if 'created_at' in df_display.columns:
        df_display['created_at'] = pd.to_datetime(df_display['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

    if 'price' in df_display.columns:
        df_display['price'] = df_display['price'].apply(lambda x: f"¥{x:,}" if x is not None and x > 0 else "-")

    if 'available_certificates' in df_display.columns:
        def format_certs(x):
            if x is None or not isinstance(x, list) or not x:
                return "-"
            return ", ".join(str(cert) for cert in x)

        df_display['available_certificates'] = df_display['available_certificates'].apply(format_certs)

    # 重命名列标题
    column_names = {
        'created_at': '发布时间',
        'type': '类型',
        'certificates': '需求证书',
        'location': '地区',
        'price': '价格',
        'total_supply_count': '供应匹配数',
        'available_certificates_count': '可用证书数',
        'available_certificates': '可用证书',
        'group_name': '群组',
        'member_nick': '发布者',
        'duplicate_count': '重复次数'
    }
    df_display = df_display.rename(columns=column_names)

    # 按供应匹配数排序
    df_display = df_display.sort_values('供应匹配数', ascending=False)

    st.dataframe(
        df_display,
        width='stretch',
        hide_index=True
    )

def display_certificate_query_page():
    """显示证书查询页面"""
    st.markdown("## 🔍 证书查询")

    # 获取所有可用证书选项
    try:
        with db_manager.get_cursor(dict_cursor=True) as cursor:
            # 查询所有出类型消息中的证书
            cursor.execute("""
                SELECT DISTINCT unnest(split_certificates) as cert
                FROM wechat_messages
                WHERE type LIKE '%出%'
                  AND split_certificates IS NOT NULL
                  AND split_certificates != '{}'::text[]
                ORDER BY cert
            """)
            cert_results = cursor.fetchall()
            all_certificates = [row['cert'] for row in cert_results]
    except Exception as e:
        st.error(f"获取证书列表失败: {e}")
        all_certificates = []

    # 证书输入区域
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📝 选择要查询的证书")

        # 多选证书 - 支持同时查询多个证书
        selected_certs = st.multiselect(
            "选择证书 (可多选 - 查询包含任一证书的记录)",
            options=all_certificates,
            default=['B证'] if 'B证' in all_certificates else [],
            help="选择多个证书，系统将返回包含这些证书中任一个的所有记录"
        )

        # 显示选中证书说明
        if selected_certs:
            st.info(f"📋 将查询包含以下任一证书的记录: {', '.join(selected_certs)}")
        else:
            st.warning("⚠️ 请至少选择一个证书进行查询")

        # 或者手动输入
        st.markdown("**或手动输入证书名称**")
        manual_input = st.text_input(
            "手动输入证书（用逗号分隔）",
            placeholder="例如: B证, 二级市政, 一级建造师",
            help="可以手动输入证书名称，多个证书用逗号分隔"
        )

    # 地区筛选区域
    st.markdown("### 🌍 地区筛选")
    all_locations = get_all_locations()
    if all_locations:
        # 精确匹配区域
        with st.expander("📍 精确匹配地区（可选）", expanded=False):
            selected_location = st.selectbox(
                "选择完整地区名称（可选）",
                options=["全部"] + all_locations,
                index=0,
                help="选择一个完整地区名称来筛选证书查询结果"
            )

        # 模糊搜索区域
        with st.expander("🔍 模糊搜索地区（可选）", expanded=False):
            location_input = st.text_input(
                "输入地区关键词",
                placeholder="例如：北京、广东、华东、华南等",
                help="输入地区关键词，系统会查找包含该关键词的所有地区"
            )

            if location_input.strip():
                st.info(f"🔍 将模糊搜索包含 '{location_input}' 的所有地区")
                use_fuzzy_search = True
                fuzzy_location = location_input.strip()
            else:
                st.info("📋 未输入模糊搜索关键词")
                use_fuzzy_search = False
                fuzzy_location = ""

        # 综合提示
        if selected_location != "全部" or use_fuzzy_search:
            exact_text = f"精确匹配 '{selected_location}'" if selected_location != "全部" else ""
            fuzzy_text = f"模糊搜索 '{fuzzy_location}'" if use_fuzzy_search else ""

            if exact_text and fuzzy_text:
                st.success(f"✅ 地区筛选已激活：{exact_text} + {fuzzy_text}")
            elif exact_text:
                st.success(f"✅ 地区筛选已激活：{exact_text}")
            elif fuzzy_text:
                st.success(f"✅ 地区筛选已激活：{fuzzy_text}")
        else:
            st.info("📋 未设置地区筛选，将查询全部地区")

    else:
        selected_location = "全部"
        use_fuzzy_search = False
        fuzzy_location = ""
        st.warning("未找到地区数据")

    # 时间筛选区域
    st.markdown("### 📅 时间筛选")
    col1, col2 = st.columns([2, 1])
    with col1:
        time_filter_options = ["全部时间", "最近3天", "最近7天", "最近30天"]
        selected_time_filter = st.selectbox(
            "选择时间范围",
            options=time_filter_options,
            index=1,  # 默认选择"最近3天"
            help="筛选指定时间范围内的证书数据"
        )

    with col2:
        st.markdown("**时间统计**")
        st.info("📅 按时间筛选数据")

    # 显示时间筛选提示
    if selected_time_filter != "全部时间":
        st.success(f"📅 将查询 {selected_time_filter} 内的证书数据")
    else:
        st.info("📅 查询全部时间的数据")

    with col2:
        st.markdown("### 🚀 快速操作")

        # 快速选择按钮
        st.markdown("**快速选择**")
        if st.button("选择热门证书", key="popular_certs"):
            popular = ['B证', '二级市政', '二级建筑', '二级机电', '一级建造师']
            selected_certs = [cert for cert in popular if cert in all_certificates]

        if st.button("清空选择", key="clear_certs"):
            selected_certs = []
            manual_input = ""

    # 处理最终选择的证书列表
    target_certs = selected_certs.copy()
    if manual_input.strip():
        manual_certs = [cert.strip() for cert in manual_input.split(',') if cert.strip()]
        target_certs.extend(manual_certs)

    # 去重并过滤
    target_certs = list(set(target_certs))
    target_certs = [cert for cert in target_certs if cert and cert in all_certificates]

    if not target_certs:
        st.info("👆 请选择或输入要查询的证书")
        return

    # 显示选中的证书
    st.success(f"📋 将查询以下证书: {', '.join(target_certs)}")

    # 执行查询
    if st.button("🔍 开始查询", key="execute_query"):
        with st.spinner("正在查询证书数据..."):
            # 传递地区筛选参数 - 支持精确匹配和模糊搜索同时使用
            exact_location = selected_location if selected_location != "全部" else None

            # 如果既有精确匹配又有模糊搜索，需要两次查询并合并结果
            if exact_location and use_fuzzy_search:
                # 精确匹配查询
                exact_results = query_certificates(
                    target_certs,
                    location_filter=exact_location,
                    fuzzy_search=False
                )
                # 模糊搜索查询
                fuzzy_results = query_certificates(
                    target_certs,
                    location_filter=fuzzy_location,
                    fuzzy_search=True
                )
                # 合并结果并去重（基于消息ID）
                all_results = {msg['id']: msg for msg in exact_results}
                for msg in fuzzy_results:
                    all_results[msg['id']] = msg
                query_results = list(all_results.values())
            else:
                # 单一类型查询
                location_filter = exact_location if exact_location else (fuzzy_location if use_fuzzy_search else None)
                query_results = query_certificates(
                    target_certs,
                    location_filter=location_filter,
                    fuzzy_search=use_fuzzy_search
                )

        # 应用时间筛选到查询结果
        if query_results and selected_time_filter != "全部时间":
            from datetime import datetime, timedelta
            now = datetime.now()

            if selected_time_filter == "最近3天":
                cutoff_date = now - timedelta(days=3)
            elif selected_time_filter == "最近7天":
                cutoff_date = now - timedelta(days=7)
            elif selected_time_filter == "最近30天":
                cutoff_date = now - timedelta(days=30)
            else:
                cutoff_date = None

            if cutoff_date:
                filtered_by_time = []
                for msg in query_results:
                    created_at = msg.get('created_at')
                    if created_at:
                        # 处理不同的时间格式
                        if isinstance(created_at, str):
                            try:
                                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            except:
                                try:
                                    # 尝试其他常见格式
                                    created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                                except:
                                    continue
                        elif isinstance(created_at, datetime):
                            created_dt = created_at
                        else:
                            continue

                        if created_dt >= cutoff_date:
                            filtered_by_time.append(msg)
                query_results = filtered_by_time

        if query_results:
            df = pd.DataFrame(query_results)

            # 显示查询结果统计
            st.markdown("### 📊 查询结果统计")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("总记录数", len(df))

            with col2:
                # 按目标证书数量统计
                multi_cert = len(df[df['target_certificates_count'] > 1])
                st.metric("多证书匹配", f"{multi_cert}条")

            with col3:
                # 有价格记录的数量
                price_count = len(df[df['price'].notna() & (df['price'] > 0)])
                st.metric("有价格记录", f"{price_count}条")

            with col4:
                # 平均目标证书数量
                avg_certs = float(df['target_certificates_count'].mean())
                st.metric("平均匹配数", f"{avg_certs:.1f}")

            # 分布图表
            st.markdown("### 📈 数据分布")

            col1, col2 = st.columns(2)

            with col1:
                # 目标证书数量分布
                cert_count_dist = df['target_certificates_count'].value_counts().sort_index()
                st.bar_chart(cert_count_dist)

            with col2:
                # 地区分布（前10）
                if 'location' in df.columns:
                    location_dist = df[df['location'].notna()]['location'].value_counts().head(10)
                    if not location_dist.empty:
                        st.bar_chart(location_dist)

            # 价格统计
            price_data = df[df['price'].notna() & (df['price'] > 0)]
            if not price_data.empty:
                st.markdown("### 💰 价格分析")

                col1, col2, col3 = st.columns(3)

                with col1:
                    avg_price = float(price_data['price'].mean())
                    st.metric("平均价格", f"¥{avg_price:,.0f}")

                with col2:
                    max_price = float(price_data['price'].max())
                    st.metric("最高价格", f"¥{max_price:,.0f}")

                with col3:
                    min_price = float(price_data['price'].min())
                    st.metric("最低价格", f"¥{min_price:,.0f}")

            # 详细结果表格
            st.markdown("### 📋 查询结果详情")

            # 选择显示的列
            display_columns = [
                'created_at', 'type', 'certificates', 'location', 'price',
                'target_certificates_count', 'found_target_certificates',
                'group_name', 'member_nick', 'duplicate_count'
            ]

            # 确保列存在
            available_columns = [col for col in display_columns if col in df.columns]
            df_display = df[available_columns].copy()

            # 格式化数据
            if 'created_at' in df_display.columns:
                df_display['created_at'] = pd.to_datetime(df_display['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

            if 'price' in df_display.columns:
                df_display['price'] = df_display['price'].apply(lambda x: f"¥{x:,}" if x is not None and x > 0 else "-")

            if 'found_target_certificates' in df_display.columns:
                def format_found_certs(x):
                    if x is None or not isinstance(x, list) or not x:
                        return "-"
                    return ", ".join(str(cert) for cert in x)

                df_display['found_target_certificates'] = df_display['found_target_certificates'].apply(format_found_certs)

            # 重命名列标题
            column_names = {
                'created_at': '发布时间',
                'type': '类型',
                'certificates': '证书信息',
                'location': '地区',
                'price': '价格',
                'target_certificates_count': '匹配证书数',
                'found_target_certificates': '匹配的证书',
                'group_name': '群组',
                'member_nick': '发布者',
                'duplicate_count': '重复次数'
            }
            df_display = df_display.rename(columns=column_names)

            # 按匹配证书数量排序
            df_display = df_display.sort_values('匹配证书数', ascending=False)

            st.dataframe(
                df_display,
                width='stretch',
                hide_index=True
            )

        else:
            st.warning("没有找到匹配的记录")

def main():
    """主函数"""
    init_session_state()

    # 侧边栏
    with st.sidebar:
        st.markdown("## ⚙️ 设置")

        # 页面切换
        st.markdown("## 📄 页面选择")
        page_options = ["📊 数据总览", "💼 商机匹配", "🔍 证书查询"]
        selected_page = st.selectbox("选择页面", page_options)

        # 全局地区筛选 - 支持多选和模糊搜索同时使用
        st.markdown("## 🌍 地区筛选")
        all_locations = get_all_locations()
        if all_locations:
            # 精确匹配区域
            with st.expander("📍 精确匹配（可多选）", expanded=True):
                selected_locations = st.multiselect(
                    "选择完整地区名称（可多选）",
                    options=all_locations,
                    default=[],
                    help="选择一个或多个完整地区名称，支持多地区同时查询"
                )

                # 显示选中地区数量
                if selected_locations:
                    st.info(f"📋 已精确选择 {len(selected_locations)} 个地区")
                else:
                    st.info("📋 未精确选择地区")

            # 模糊搜索区域
            with st.expander("🔍 模糊搜索（关键词匹配）", expanded=False):
                fuzzy_location_input = st.text_input(
                    "输入地区关键词",
                    placeholder="例如：北京、广东、华东、华南、东北等",
                    help="输入地区关键词，系统会查找包含该关键词的所有地区"
                )

                if fuzzy_location_input.strip():
                    st.info(f"🔍 将模糊搜索包含 '{fuzzy_location_input}' 的所有地区")
                    use_fuzzy_search = True
                else:
                    st.info("📋 未输入模糊搜索关键词")
                    use_fuzzy_search = False

            # 综合提示
            if selected_locations or use_fuzzy_search:
                st.success(f"✅ 地区筛选已激活：精确匹配 {len(selected_locations)} 个地区 + 模糊搜索 {'"' + fuzzy_location_input + '"' if use_fuzzy_search else '未启用'}")
            else:
                st.info("📋 未设置地区筛选，将显示全部数据")

        else:
            selected_locations = []
            use_fuzzy_search = False
            fuzzy_location_input = ""
            st.warning("未找到地区数据")

        # 时间筛选选项 - 全局时间筛选
        st.markdown("### 📅 时间筛选")
        time_filter_options = ["全部时间", "最近3天", "最近7天", "最近30天"]
        global_time_filter = st.selectbox(
            "选择时间范围",
            options=time_filter_options,
            index=1,  # 默认选择"最近3天"
            help="筛选指定时间范围内的数据"
        )

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

    # 显示页面内容
    if selected_page == "🔍 证书查询":
        # 证书查询页面 - 不需要预先加载数据
        display_certificate_query_page()
    else:
        # 其他页面需要加载数据
        if not st.session_state.data_loaded:
            with st.spinner("正在加载数据..."):
                load_data()

        # 如果数据加载成功，显示内容
        if st.session_state.data_loaded and st.session_state.all_messages:
            if selected_page == "💼 商机匹配":
                # 商机匹配页面 - 同时传递多选和模糊搜索参数
                business_opportunity_filters(
                    location_filter=selected_locations,
                    fuzzy_location_input=fuzzy_location_input,
                    use_fuzzy_search=use_fuzzy_search
                )
                display_business_opportunity_dashboard(
                    location_filter=selected_locations,
                    fuzzy_location_input=fuzzy_location_input,
                    use_fuzzy_search=use_fuzzy_search,
                    time_filter=global_time_filter
                )
            else:
                # 原始数据总览页面 - 同时传递多选和模糊搜索参数
                sidebar_filters(
                    location_filter=selected_locations,
                    fuzzy_location_input=fuzzy_location_input,
                    use_fuzzy_search=use_fuzzy_search,
                    time_filter=global_time_filter
                )
                display_data_table()

        else:
            st.warning("暂无数据，请检查数据库连接。")

if __name__ == "__main__":
    main()