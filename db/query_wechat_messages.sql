-- 查询wechat_messages表中的部分字段，限制返回1000条记录。

SELECT type,
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
       msg_id
FROM public.wechat_messages
LIMIT 1000;