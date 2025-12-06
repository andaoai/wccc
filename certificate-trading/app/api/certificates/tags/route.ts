import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const search = searchParams.get('search')
    const limit = parseInt(searchParams.get('limit') || '50')

    // 如果有搜索参数，返回匹配的证书
    if (search) {
      const sql = `
        SELECT certificate, COUNT(*)::integer as count
        FROM (
          SELECT unnest(split_certificates) as certificate
          FROM wechat_messages
          WHERE split_certificates IS NOT NULL
            AND array_length(split_certificates, 1) > 0
        ) all_certs
        WHERE certificate ILIKE $1
        GROUP BY certificate
        ORDER BY count DESC, certificate ASC
        LIMIT $2
      `
      const results = await prisma.$queryRawUnsafe(sql, `%${search}%`, limit)

      // 处理 BigInt 错误
      const processedResults = (results as any[]).map((item: any) => ({
        certificate: item.certificate,
        count: Number(item.count)
      }))

      return NextResponse.json(processedResults)
    }

    // 否则返回热门证书统计
    const sql = `
      SELECT
        unnest(split_certificates) as certificate,
        COUNT(*)::integer as count
      FROM wechat_messages
      WHERE split_certificates IS NOT NULL
        AND array_length(split_certificates, 1) > 0
      GROUP BY certificate
      HAVING COUNT(*) >= 5
      ORDER BY count DESC, certificate ASC
      LIMIT 100
    `

    const results = await prisma.$queryRawUnsafe(sql)

    // 处理 BigInt 错误
    const processedResults = (results as any[]).map((item: any) => ({
      certificate: item.certificate,
      count: Number(item.count)
    }))

    return NextResponse.json(processedResults)
  } catch (error) {
    console.error('Error fetching certificate tags:', error)
    return NextResponse.json(
      { error: 'Failed to fetch certificate tags' },
      { status: 500 }
    )
  }
}