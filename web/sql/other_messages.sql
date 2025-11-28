-- 查询其他类型数据，使用窗口函数去重并保留重复计数
WITH ranked_messages AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn,
           COUNT(*) OVER (PARTITION BY original_info, member_wxid) as duplicate_count,
           '其他' as transaction_category
    FROM wechat_messages
    WHERE type NOT LIKE '%收%'
       AND type NOT LIKE '%接%'
       AND type NOT LIKE '%招聘%'
       AND type NOT LIKE '%寻%'
       AND type NOT LIKE '%出%'
)
SELECT * FROM ranked_messages WHERE rn = 1
ORDER BY created_at DESC
LIMIT 1000