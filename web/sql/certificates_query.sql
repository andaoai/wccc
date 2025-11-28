-- 查询包含指定证书的出类型数据
-- 配置目标证书数组 - 只需在这里修改一次
WITH target_certs AS (
    SELECT ARRAY[
        'B证',          -- 234
        -- '二级市政'  161
        -- '二级建筑'  101
        -- '二级机电'  77
        ]::text[] as certificates
),
ranked_messages AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn,
           COUNT(*) OVER (PARTITION BY original_info, member_wxid) as duplicate_count,
           '出' as transaction_category,

           -- 检查是否包含目标证书
           CASE
               WHEN split_certificates IS NOT NULL
                AND split_certificates != '{}'::text[]
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
                AND split_certificates != '{}'::text[]
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
                AND split_certificates != '{}'::text[]
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
)
SELECT
    *
FROM ranked_messages
WHERE rn = 1
  AND contains_target_certificates = true
ORDER BY target_certificates_count DESC, created_at DESC
LIMIT 5000;