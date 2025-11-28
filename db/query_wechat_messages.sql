-- 查询wechat_messages表中的所有消息，按时间倒序显示，并在每条消息前显示重复计数
-- 这样可以看到最新消息，同时了解该消息的重复情况

SELECT
       type,
       certificates,
       split_certificates,
       social_security,
       location,
       price,
       original_info,
       other_info,
       group_name,
       member_nick,
       group_wxid,
       member_wxid,
       msg_id,
       created_at,
       COUNT(*) OVER (PARTITION BY original_info, member_wxid) as duplicate_count
FROM public.wechat_messages
ORDER BY created_at DESC
LIMIT 1000;