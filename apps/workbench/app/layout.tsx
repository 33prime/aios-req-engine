import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ToastProvider } from '@/components/ui'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Consultant Workbench',
  description: 'AI-powered requirements management workbench',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ToastProvider>
          <div className="min-h-screen bg-gray-50">
            <header className="bg-white shadow-sm border-b">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center py-4">
                  <h1 className="text-2xl font-bold text-gray-900">
                    Consultant Workbench
                  </h1>
                  <div className="text-sm text-gray-500">
                    AIOS Req Engine
                  </div>
                </div>
              </div>
            </header>
            <main>{children}</main>
          </div>
        </ToastProvider>
      </body>
    </html>
  )
}
