'use client'

import useSWR from 'swr'
import { useState, useEffect } from 'react'

interface WechatMessage {
  id: number
  type: string
  certificates: string
  social_security?: string
  location?: string
  price?: number
  other_info?: string
  original_info: string
  split_certificates: string[]
  group_name: string
  member_nick: string
  timestamp: string
  created_at: string
}

interface CertificateTag {
  certificate: string
  count: number
}

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function CertificateTrading() {
  const [locationInput, setLocationInput] = useState('')
  const [certificateInput, setCertificateInput] = useState('')
  const [selectedCertificates, setSelectedCertificates] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [searchParams, setSearchParams] = useState({
    location: '',
    certificate: ''
  })

  // 获取热门证书
  const { data: popularCertificates } = useSWR<CertificateTag[]>(
    '/api/certificates/tags',
    fetcher
  )

  // 获取搜索建议
  const { data: suggestions } = useSWR<CertificateTag[]>(
    certificateInput.trim() ? `/api/certificates/tags?search=${certificateInput}&limit=20` : null,
    fetcher
  )

  const { data, error, isLoading } = useSWR(
    `/api/certificates?location=${searchParams.location}&certificate=${searchParams.certificate}`,
    fetcher
  )

  const handleSearch = () => {
    setSearchParams({
      location: locationInput.trim(),
      certificate: selectedCertificates.join(' ')
    })
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const addCertificate = (certificate: string) => {
    if (!selectedCertificates.includes(certificate)) {
      setSelectedCertificates([...selectedCertificates, certificate])
    }
    setCertificateInput('')
    setShowSuggestions(false)
  }

  const removeCertificate = (certificate: string) => {
    setSelectedCertificates(selectedCertificates.filter(cert => cert !== certificate))
  }

  const handleCertificateInputChange = (value: string) => {
    setCertificateInput(value)
    setShowSuggestions(value.trim().length > 0)
  }

  // 点击外部关闭建议框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      if (!target.closest('.certificate-input-container')) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('click', handleClickOutside)
    return () => {
      document.removeEventListener('click', handleClickOutside)
    }
  }, [])

  const receiveMessages: WechatMessage[] = data?.receive || []
  const sendMessages: WechatMessage[] = data?.send || []

  const formatPrice = (price?: number) => {
    return price && price > 0 ? `¥${price.toLocaleString()}` : '面议'
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-CN')
  }

  if (error) return <div className="text-red-500 text-center py-8">加载失败: {error.message}</div>
  if (isLoading) return <div className="text-center py-8">加载中...</div>

  return (
    <div className="flex gap-6 h-[calc(100vh-2rem)]">
      {/* 左侧：固定宽度搜索栏 */}
      <div className="w-80 flex-shrink-0 space-y-6 overflow-y-auto">
        {/* 搜索筛选 */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">搜索筛选</h2>
          <div className="space-y-4">
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

            <div className="certificate-input-container relative">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                证书名称
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={certificateInput}
                  onChange={(e) => handleCertificateInputChange(e.target.value)}
                  onFocus={() => setShowSuggestions(certificateInput.trim().length > 0)}
                  onKeyPress={handleKeyPress}
                  placeholder="输入搜索证书"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />

                {/* 搜索建议 */}
                {showSuggestions && suggestions && suggestions.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                    {suggestions.map((suggestion, index) => (
                      <div
                        key={index}
                        onClick={() => addCertificate(suggestion.certificate)}
                        className="px-3 py-2 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                      >
                        <div className="font-medium text-gray-900">{suggestion.certificate}</div>
                        <div className="text-xs text-gray-500">{suggestion.count} 条记录</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 已选择的证书标签 */}
              {selectedCertificates.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {selectedCertificates.map((cert, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-full border border-blue-200"
                    >
                      {cert}
                      <button
                        onClick={() => removeCertificate(cert)}
                        className="ml-2 text-blue-500 hover:text-blue-700"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {/* 热门证书 */}
              {popularCertificates && popularCertificates.length > 0 && (
                <div className="mt-3">
                  <div className="text-xs text-gray-500 mb-2">热门证书：</div>
                  <div className="flex flex-wrap gap-1">
                    {popularCertificates.slice(0, 8).map((tag, index) => (
                      <button
                        key={index}
                        onClick={() => addCertificate(tag.certificate)}
                        className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full hover:bg-gray-200 transition-colors"
                      >
                        {tag.certificate}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div>
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
            <div className="grid grid-cols-2 gap-4">
              {data.stats.map((stat: any) => (
                <div key={stat.type} className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{stat._count.id}</div>
                  <div className="text-sm text-gray-600">{stat.type}类</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 右侧：自适应全屏收出类型分栏 */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
        {/* 左侧：收类型 */}
        <div className="bg-white rounded-lg shadow-sm border flex flex-col min-h-0">
          <div className="p-6 border-b bg-green-50 flex-shrink-0">
            <h2 className="text-lg font-semibold text-green-800">
              收类型 ({receiveMessages.length} 条)
            </h2>
            <p className="text-sm text-green-600 mt-1">收、接、招聘、寻、要、需、找</p>
          </div>

          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="divide-y">
              {receiveMessages.map((message) => (
                <div key={message.id} className="p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                        {message.type}
                      </span>
                      <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full">
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
                              className="px-2 py-1 bg-green-50 text-green-700 text-xs rounded-md border border-green-200 font-medium"
                            >
                              {cert}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-900 font-medium mb-1 text-sm">{message.certificates}</p>
                    )}
                    <p className="text-xs text-gray-600">{message.original_info}</p>
                  </div>

                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      {message.social_security && (
                        <span>
                          社保: {message.social_security}
                        </span>
                      )}
                      {message.member_nick && (
                        <span>
                          发布者: {message.member_nick}
                        </span>
                      )}
                    </div>
                    <div className="text-sm font-semibold text-green-600">
                      {formatPrice(message.price)}
                    </div>
                  </div>
                </div>
              ))}

              {receiveMessages.length === 0 && (
                <div className="p-12 text-center text-gray-500">
                  暂无收类型数据
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 右侧：出类型 */}
        <div className="bg-white rounded-lg shadow-sm border flex flex-col min-h-0">
          <div className="p-6 border-b bg-orange-50 flex-shrink-0">
            <h2 className="text-lg font-semibold text-orange-800">
              出类型 ({sendMessages.length} 条)
            </h2>
            <p className="text-sm text-orange-600 mt-1">出、供</p>
          </div>

          <div className="flex-1 overflow-y-auto min-h-0">
            <div className="divide-y">
              {sendMessages.map((message) => (
                <div key={message.id} className="p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full">
                        {message.type}
                      </span>
                      <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full">
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
                              className="px-2 py-1 bg-orange-50 text-orange-700 text-xs rounded-md border border-orange-200 font-medium"
                            >
                              {cert}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-900 font-medium mb-1 text-sm">{message.certificates}</p>
                    )}
                    <p className="text-xs text-gray-600">{message.original_info}</p>
                  </div>

                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      {message.social_security && (
                        <span>
                          社保: {message.social_security}
                        </span>
                      )}
                      {message.member_nick && (
                        <span>
                          发布者: {message.member_nick}
                        </span>
                      )}
                    </div>
                    <div className="text-sm font-semibold text-green-600">
                      {formatPrice(message.price)}
                    </div>
                  </div>
                </div>
              ))}

              {sendMessages.length === 0 && (
                <div className="p-12 text-center text-gray-500">
                  暂无出类型数据
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}