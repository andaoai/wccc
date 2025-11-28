-- 查询出类型数据（包括出），使用窗口函数去重并保留重复计数
WITH ranked_messages AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn,
           COUNT(*) OVER (PARTITION BY original_info, member_wxid) as duplicate_count,
           '出' as transaction_category
    FROM wechat_messages
    WHERE type LIKE '%出%'
)
SELECT * FROM ranked_messages WHERE rn = 1
ORDER BY created_at DESC
LIMIT 5000