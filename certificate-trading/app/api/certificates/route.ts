import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const location = searchParams.get('location')
    const certificate = searchParams.get('certificate')

    // 构建基础WHERE条件
    let baseWhereConditions = []
    let params: any[] = []

    // 添加地区筛选
    if (location && location !== '全部') {
      const paramIndex = params.length + 1
      baseWhereConditions.push(`location ILIKE $${paramIndex}`)
      params.push(`%${location}%`)
    }

    // 添加证书筛选 - 支持多个证书查询
    if (certificate && certificate.trim()) {
      const certificates = certificate.trim().split(/\s+/).filter(cert => cert.length > 0)
      if (certificates.length > 0) {
        const certificateConditions = certificates.map(cert => {
          const paramIndex = params.length + 1
          params.push(cert)
          return `$${paramIndex} = ANY(split_certificates)`
        })
        baseWhereConditions.push(`(${certificateConditions.join(' OR ')})`)
      }
    }

    const baseWhereClause = baseWhereConditions.length > 0 ? ` AND ${baseWhereConditions.join(' AND ')}` : ''

    // 查询收类型数据
    let receiveSql = `
      SELECT
        id, type, certificates, social_security, location, price,
        other_info, original_info, split_certificates, group_name,
        member_nick, group_wxid, member_wxid, msg_id, timestamp,
        created_at, updated_at
      FROM wechat_messages
      WHERE (type ILIKE '%收%' OR type ILIKE '%接%' OR type ILIKE '%招聘%' OR type ILIKE '%寻%' OR type ILIKE '%要%' OR type ILIKE '%需%' OR type ILIKE '%找%')
      ${baseWhereClause}
      ORDER BY CASE WHEN split_certificates IS NOT NULL AND array_length(split_certificates, 1) > 0 THEN 0 ELSE 1 END, id DESC LIMIT 30
    `

    // 查询出类型数据
    let sendSql = `
      SELECT
        id, type, certificates, social_security, location, price,
        other_info, original_info, split_certificates, group_name,
        member_nick, group_wxid, member_wxid, msg_id, timestamp,
        created_at, updated_at
      FROM wechat_messages
      WHERE (type ILIKE '%出%' OR type ILIKE '%供%')
      ${baseWhereClause}
      ORDER BY CASE WHEN split_certificates IS NOT NULL AND array_length(split_certificates, 1) > 0 THEN 0 ELSE 1 END, id DESC LIMIT 30
    `

    // 执行查询
    const receiveMessages = await prisma.$queryRawUnsafe(receiveSql, ...params)
    const sendMessages = await prisma.$queryRawUnsafe(sendSql, ...params)

    // 统计两大类别的信息（应用相同的筛选条件）
    let receiveStatsSql = `
      SELECT COUNT(*) as count
      FROM wechat_messages
      WHERE (type ILIKE '%收%' OR type ILIKE '%接%' OR type ILIKE '%招聘%' OR type ILIKE '%寻%' OR type ILIKE '%要%' OR type ILIKE '%需%' OR type ILIKE '%找%')
      ${baseWhereClause}
    `

    let sendStatsSql = `
      SELECT COUNT(*) as count
      FROM wechat_messages
      WHERE (type ILIKE '%出%' OR type ILIKE '%供%')
      ${baseWhereClause}
    `

    const receiveStats = await prisma.$queryRawUnsafe(receiveStatsSql, ...params)
    const sendStats = await prisma.$queryRawUnsafe(sendStatsSql, ...params)

    const stats = [
      { type: '收', _count: { id: Number(receiveStats[0].count) } },
      { type: '出', _count: { id: Number(sendStats[0].count) } }
    ]

    return NextResponse.json({
      receive: receiveMessages,
      send: sendMessages,
      stats
    })
  } catch (error) {
    console.error('Error fetching certificates:', error)
    return NextResponse.json(
      { error: 'Failed to fetch certificates' },
      { status: 500 }
    )
  }
}