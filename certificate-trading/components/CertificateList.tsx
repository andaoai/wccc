'use client'

import useSWR from 'swr'
import { useState, useEffect, useMemo } from 'react'

interface WechatMessage {
  id: number
  type: string
  certificates: string
  socialSecurity: string
  location: string
  price: number
  otherInfo: string
  originalInfo: string
  splitCertificates: string[]
  groupName: string
  memberNick: string
  timestamp: string
  createdAt: string
}

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function CertificateList() {
  const [type, setType] = useState('收')
  const [locationInput, setLocationInput] = useState('')
  const [certificateInput, setCertificateInput] = useState('')
  const [searchParams, setSearchParams] = useState({
    type: '收',
    location: '',
    certificate: ''
  })

  const { data, error, isLoading } = useSWR(
    `/api/certificates?type=${searchParams.type}&location=${searchParams.location}&certificate=${searchParams.certificate}`,
    fetcher
  )

  const handleSearch = () => {
    setSearchParams({
      type,
      location: locationInput.trim(),
      certificate: certificateInput.trim()
    })
  }

  const handleTypeChange = (newType: string) => {
    setType(newType)
    setSearchParams({
      type: newType,
      location: locationInput.trim(),
      certificate: certificateInput.trim()
    })
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const messages: WechatMessage[] = data?.messages || []

  const formatPrice = (price: number) => {
    return price > 0 ? `¥${price.toLocaleString()}` : '面议'
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-CN')
  }

  if (error) return <div className="text-red-500 text-center py-8">加载失败: {error.message}</div>
  if (isLoading) return <div className="text-center py-8">加载中...</div>

  return (
    <div className="space-y-6">
      {/* 搜索筛选 */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h2 className="text-lg font-semibold mb-4">搜索筛选</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              交易类型
            </label>
            <select
              value={type}
              onChange={(e) => handleTypeChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="收">收类型</option>
              <option value="出">出类型</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              地区
            </label>
            <input
              type="text"
              value={locationInput}
              onChange={(e) => setLocationInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="如：浙江、杭州"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              证书名称
            </label>
            <input
              type="text"
              value={certificateInput}
              onChange={(e) => setCertificateInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="如：一级建造师"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleSearch}
              disabled={isLoading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? '搜索中...' : '搜索'}
            </button>
          </div>
        </div>
      </div>

      {/* 统计信息 */}
      {data?.stats && (
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold mb-4">统计信息</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {data.stats.map((stat: any) => (
              <div key={stat.type} className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stat._count.id}</div>
                <div className="text-sm text-gray-600">{stat.type}类</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 消息列表 */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="p-6 border-b">
          <h2 className="text-lg font-semibold">
            消息列表 ({messages.length} 条)
          </h2>
        </div>

        <div className="divide-y">
          {messages.map((message) => (
            <div key={message.id} className="p-6 hover:bg-gray-50">
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                    {message.type}
                  </span>
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                    {message.location || '未指定地区'}
                  </span>
                </div>
                <div className="text-sm text-gray-500">
                  {formatTime(message.timestamp)}
                </div>
              </div>

              <div className="mb-3">
                {/* 优先显示分割后的证书 */}
                {message.split_certificates && message.split_certificates.length > 0 ? (
                  <div className="mb-2">
                    <div className="flex flex-wrap gap-1 mb-2">
                      {message.split_certificates.map((cert, index) => (
                        <span
                          key={index}
                          className="px-3 py-1 bg-blue-50 text-blue-700 text-sm rounded-md border border-blue-200 font-medium"
                        >
                          {cert}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-900 font-medium mb-1">{message.certificates}</p>
                )}
                <p className="text-sm text-gray-600">{message.originalInfo}</p>
              </div>

              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-4 text-sm">
                  {message.socialSecurity && (
                    <span className="text-gray-500">
                      社保: {message.socialSecurity}
                    </span>
                  )}
                  {message.memberNick && (
                    <span className="text-gray-500">
                      发布者: {message.memberNick}
                    </span>
                  )}
                </div>
                <div className="text-lg font-semibold text-green-600">
                  {formatPrice(message.price)}
                </div>
              </div>

              </div>
          ))}
        </div>

        {messages.length === 0 && (
          <div className="p-12 text-center text-gray-500">
            暂无匹配的数据
          </div>
        )}
      </div>
    </div>
  )
}