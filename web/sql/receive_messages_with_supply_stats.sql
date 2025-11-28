-- 查询收类型数据，并统计对应证书在供（出）市场的信息条数
WITH supply_messages AS (
    -- 获取所有供（出）类型消息，进行去重处理
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY original_info, member_wxid ORDER BY created_at DESC) as rn
    FROM wechat_messages
    WHERE type LIKE '%出%'
      AND split_certificates IS NOT NULL
      AND split_certificates != '{}'::text[]
),

-- 获取去重后的供应消息
deduplicated_supply AS (
    SELECT * FROM supply_messages WHERE rn = 1
),

-- 统计每个证书在供应市场的消息数量
supply_counts AS (
    SELECT
        cert,
        COUNT(*) as supply_count
    FROM deduplicated_supply,
         unnest(split_certificates) as cert
    GROUP BY cert
),

-- 收类型数据处理（去重）
ranked_messages AS (
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

-- 最终查询：收类型数据 + 供应统计
SELECT
    rm.*,

    -- 统计逻辑说明：
    -- 1. rm.split_certificates 是当前收类型消息中的证书数组（例如：['二级建造师', '一级建造师']）
    -- 2. sc.supply_count 是每个证书在供应市场（去重后的出类型消息）中出现的消息条数
    -- 3. sc.cert = ANY(rm.split_certificates) 检查供应市场中的证书是否在当前需求的证书列表中
    -- 4. SUM(sc.supply_count) 将所有匹配证书的供应消息条数相加
    -- 结果：当前需求消息中所有证书在供应市场的总消息条数
    (
        SELECT COALESCE(SUM(sc.supply_count), 0)
        FROM supply_counts sc
        WHERE sc.cert = ANY(rm.split_certificates)
    ) as total_supply_count,

    -- 统计当前需求的证书中有多少种在供应市场存在
    -- COUNT(DISTINCT sc.cert) 计算匹配到的不同证书种类数量
    (
        SELECT COUNT(DISTINCT sc.cert)
        FROM supply_counts sc
        WHERE sc.cert = ANY(rm.split_certificates)
    ) as available_certificates_count,

    -- 列出当前需求中在供应市场可用的具体证书
    -- array_agg(DISTINCT sc.cert ORDER BY sc.cert) 将匹配的证书聚合成有序数组
    (
        SELECT array_agg(DISTINCT sc.cert ORDER BY sc.cert)
        FROM supply_counts sc
        WHERE sc.cert = ANY(rm.split_certificates)
    ) as available_certificates

FROM ranked_messages rm
WHERE rm.rn = 1
ORDER BY rm.created_at DESC
LIMIT 5000000;