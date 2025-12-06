import CertificateList from '@/components/CertificateList'

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">证书交易平台</h1>
            <div className="text-sm text-gray-500">
              基于Next.js + TypeScript + Prisma构建
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <CertificateList />
      </main>
    </div>
  )
}
