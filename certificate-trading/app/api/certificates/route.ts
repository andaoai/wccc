import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const queryType = searchParams.get('type') || '收' // 默认查询收类型
    const location = searchParams.get('location')
    const certificate = searchParams.get('certificate')

    // 使用原始SQL查询来避免Prisma字段映射问题
    let sql = `
      SELECT
        id, type, certificates, social_security, location, price,
        other_info, original_info, split_certificates, group_name,
        member_nick, group_wxid, member_wxid, msg_id, timestamp,
        created_at, updated_at
      FROM wechat_messages
      WHERE 1=1
    `

    let params: any[] = []

    if (queryType === '收') {
      // 收类型：收、接、招聘、寻、要、需、找
      sql += ` AND (type ILIKE '%收%' OR type ILIKE '%接%' OR type ILIKE '%招聘%' OR type ILIKE '%寻%' OR type ILIKE '%要%' OR type ILIKE '%需%' OR type ILIKE '%找%')`
    } else if (queryType === '出') {
      // 出类型：出、供
      sql += ` AND (type ILIKE '%出%' OR type ILIKE '%供%')`
    }

    // 添加地区筛选
    if (location && location !== '全部') {
      const paramIndex = params.length + 1
      sql += ` AND location ILIKE $${paramIndex}`
      params.push(`%${location}%`)
    }

    // 添加证书筛选
    if (certificate) {
      const paramIndex = params.length + 1
      sql += ` AND $${paramIndex} = ANY(split_certificates)`
      params.push(certificate)
    }

    sql += ` ORDER BY CASE WHEN split_certificates IS NOT NULL AND array_length(split_certificates, 1) > 0 THEN 0 ELSE 1 END, id DESC LIMIT 50`

    // 执行查询
    const messages = await prisma.$queryRawUnsafe(sql, ...params)

    // 统计两大类别的信息
    const receiveStats = await prisma.$queryRaw`
      SELECT
        '收' as type,
        COUNT(*) as count
      FROM wechat_messages
      WHERE type ILIKE '%收%' OR type ILIKE '%接%' OR type ILIKE '%招聘%' OR type ILIKE '%寻%' OR type ILIKE '%要%' OR type ILIKE '%需%' OR type ILIKE '%找%'
    `

    const sendStats = await prisma.$queryRaw`
      SELECT
        '出' as type,
        COUNT(*) as count
      FROM wechat_messages
      WHERE type ILIKE '%出%' OR type ILIKE '%供%'
    `

    const stats = [
      { type: '收', _count: { id: Number(receiveStats[0].count) } },
      { type: '出', _count: { id: Number(sendStats[0].count) } }
    ]

    return NextResponse.json({
      messages,
      stats,
      queryType // 返回当前查询的类型
    })
  } catch (error) {
    console.error('Error fetching certificates:', error)
    return NextResponse.json(
      { error: 'Failed to fetch certificates' },
      { status: 500 }
    )
  }
}