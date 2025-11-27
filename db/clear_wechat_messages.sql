-- 清除 public.wechat_messages 表中的所有数据
-- This script deletes all records from the wechat_messages table

-- 确认操作：先查看表中的记录数量
SELECT COUNT(*) as total_messages_to_delete FROM public.wechat_messages;

-- 清除所有数据
DELETE FROM public.wechat_messages;

-- 验证清除结果
SELECT COUNT(*) as messages_after_clear FROM public.wechat_messages;

-- 可选：重置自增ID序列（如果表有自增主键）
-- TRUNCATE TABLE public.wechat_messages RESTART IDENTITY;

-- 注意事项：
-- 1. DELETE 操作会保留表结构，只删除数据
-- 2. 如果需要重置自增ID，请取消上面 TRUNCATE 命令的注释
-- 3. 请确保在执行前已备份重要数据
-- 4. 此操作不可撤销，请谨慎执行