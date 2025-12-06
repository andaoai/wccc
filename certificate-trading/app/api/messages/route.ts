import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const type = searchParams.get('type')
    const location = searchParams.get('location')
    const limit = searchParams.get('limit')
    const offset = searchParams.get('offset')

    const whereClause: any = {}

    if (type) {
      whereClause.type = {
        contains: type
      }
    }

    if (location) {
      whereClause.location = {
        contains: location
      }
    }

    const messages = await prisma.wechatMessage.findMany({
      where: whereClause,
      orderBy: {
        timestamp: 'desc'
      },
      take: limit ? parseInt(limit) : 100,
      skip: offset ? parseInt(offset) : 0
    })

    return NextResponse.json(messages)
  } catch (error) {
    console.error('Error fetching messages:', error)
    return NextResponse.json(
      { error: 'Failed to fetch messages' },
      { status: 500 }
    )
  }
}