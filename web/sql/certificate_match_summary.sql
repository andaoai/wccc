-- 证书匹配汇总统计
-- 简洁版本，专注于统计信息而不是详细消息

WITH
-- 1. 收证书数据（去重后）
receive_certificates AS (
    SELECT split_certificates
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn
        FROM wechat_messages
        WHERE (type LIKE '%收%'
               OR type LIKE '%接%'
               OR type LIKE '%招聘%'
               OR type LIKE '%寻%')
          AND split_certificates IS NOT NULL
          AND split_certificates != '{}'::text[]
    ) ranked_receive
    WHERE rn = 1
),

-- 2. 出证书数据（去重后）
send_certificates AS (
    SELECT split_certificates
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn
        FROM wechat_messages
        WHERE type LIKE '%出%'
          AND split_certificates IS NOT NULL
          AND split_certificates != '{}'::text[]
    ) ranked_send
    WHERE rn = 1
),

-- 3. 收证书统计
receive_certificate_stats AS (
    SELECT
        single_cert.cert,
        COUNT(*) as receive_message_count
    FROM receive_certificates
    CROSS JOIN unnest(split_certificates) as single_cert(cert)
    GROUP BY single_cert.cert
),

-- 4. 出证书统计
send_certificate_stats AS (
    SELECT
        single_cert.cert,
        COUNT(*) as send_message_count
    FROM send_certificates
    CROSS JOIN unnest(split_certificates) as single_cert(cert)
    GROUP BY single_cert.cert
),

-- 5. 证书匹配统计
certificate_match_stats AS (
    SELECT
        COALESCE(rcs.cert, scs.cert) as certificate_name,
        COALESCE(rcs.receive_message_count, 0) as receive_count,
        COALESCE(scs.send_message_count, 0) as send_count,
        CASE
            WHEN COALESCE(scs.send_message_count, 0) > 0 THEN '有出证书匹配'
            ELSE '无出证书匹配'
        END as match_status,
        -- 匹配强度评分（收证书数量 * 出证书数量）
        COALESCE(rcs.receive_message_count, 0) * COALESCE(scs.send_message_count, 0) as match_strength_score,
        -- 出证书与收证书的比例
        CASE
            WHEN COALESCE(rcs.receive_message_count, 0) > 0 THEN
                ROUND(COALESCE(scs.send_message_count, 0) * 100.0 / COALESCE(rcs.receive_message_count, 1), 2)
            ELSE 0
        END as send_receive_ratio_percent
    FROM receive_certificate_stats rcs
    FULL OUTER JOIN send_certificate_stats scs ON rcs.cert = scs.cert
)

-- 6. 最终统计结果
SELECT
    *,
    CASE
        WHEN send_count >= receive_count * 2 THEN '高匹配度'
        WHEN send_count >= receive_count THEN '中匹配度'
        WHEN send_count > 0 THEN '低匹配度'
        ELSE '无匹配'
    END as match_level,
    RANK() OVER (ORDER BY
        CASE
            WHEN send_count > 0 THEN 1
            ELSE 2
        END,
        match_strength_score DESC
    ) as popularity_rank
FROM certificate_match_stats
ORDER BY
    CASE
        WHEN send_count > 0 THEN 1
        ELSE 2
    END,
    match_strength_score DESC,
    certificate_name;