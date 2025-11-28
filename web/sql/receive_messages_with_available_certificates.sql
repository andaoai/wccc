-- 查询收类型数据，并计算每个消息中split_certificates在出表中的可用证书数量
WITH
-- 收消息数据（去重后）
receive_data AS (
    SELECT *,
           '收' as transaction_category
    FROM wechat_messages
    WHERE type LIKE '%收%'
       OR type LIKE '%接%'
       OR type LIKE '%招聘%'
       OR type LIKE '%寻%'
),

-- 出消息数据（去重后，用于证书匹配）
send_data AS (
    SELECT *,
           '出' as transaction_category
    FROM wechat_messages
    WHERE type LIKE '%出%'
),

-- 为收消息去重并保留重复计数
ranked_receive AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn,
           COUNT(*) OVER (PARTITION BY original_info, member_wxid) as duplicate_count
    FROM receive_data
),

-- 为出消息去重
ranked_send AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn
    FROM send_data
),

-- 收消息最终数据
final_receive AS (
    SELECT * FROM ranked_receive WHERE rn = 1
),

-- 出消息最终数据
final_send AS (
    SELECT * FROM ranked_send WHERE rn = 1
)

-- 最终查询结果
SELECT
    fr.*,
    -- 计算可用证书数量
    (
        SELECT COUNT(DISTINCT unnested_cert)
        FROM unnest(fr.split_certificates) as unnested_cert
        WHERE fr.split_certificates IS NOT NULL
          AND fr.split_certificates != '{}'::text[]
          AND EXISTS (
              SELECT 1
              FROM final_send fs
              WHERE fs.split_certificates IS NOT NULL
                AND fs.split_certificates != '{}'::text[]
                AND unnested_cert = ANY(fs.split_certificates)
          )
    ) as available_certificates_count,

    -- 计算总证书数量
    CASE
        WHEN fr.split_certificates IS NULL OR fr.split_certificates = '{}'::text[]
        THEN 0
        ELSE array_length(fr.split_certificates, 1)
    END as total_certificates_count,

    -- 计算可用证书列表（可选）
    (
        SELECT array_agg(DISTINCT unnested_cert)
        FROM unnest(fr.split_certificates) as unnested_cert
        WHERE fr.split_certificates IS NOT NULL
          AND fr.split_certificates != '{}'::text[]
          AND EXISTS (
              SELECT 1
              FROM final_send fs
              WHERE fs.split_certificates IS NOT NULL
                AND fs.split_certificates != '{}'::text[]
                AND unnested_cert = ANY(fs.split_certificates)
          )
    ) as available_certificates_list
FROM final_receive fr
ORDER BY fr.created_at DESC
LIMIT 5000000;