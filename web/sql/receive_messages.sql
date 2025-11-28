-- 查询收类型数据（包括收、接、招聘、寻），使用窗口函数去重并保留重复计数
WITH ranked_messages AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn,
           COUNT(*) OVER (PARTITION BY original_info, member_wxid) as duplicate_count,
           '收' as transaction_category
    FROM wechat_messages
    WHERE type LIKE '%收%'
       OR type LIKE '%接%'
       OR type LIKE '%招聘%'
       OR type LIKE '%寻%'
)
SELECT * FROM ranked_messages WHERE rn = 1
ORDER BY created_at DESC
LIMIT 5000000