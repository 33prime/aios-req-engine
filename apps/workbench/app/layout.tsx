import type { Metadata } from 'next'
import { Inter, JetBrains_Mono, DM_Sans } from 'next/font/google'
import './globals.css'
import { ToastProvider } from '@/components/ui'
import { AuthProvider } from '@/components/auth/AuthProvider'
import { PostHogProvider } from '@/components/PostHogProvider'
import { LayoutWrapper } from '@/components/LayoutWrapper'

const inter = Inter({ subsets: ['latin'] })
const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-expedition'
})
const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-body'
})

export const metadata: Metadata = {
  title: 'Readytogo.ai',
  description: 'AI-powered requirements management workbench',
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
    apple: '/favicon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} ${jetbrainsMono.variable} ${dmSans.variable}`}>
        <AuthProvider>
          <PostHogProvider>
            <ToastProvider>
              <LayoutWrapper>
                {children}
              </LayoutWrapper>
            </ToastProvider>
          </PostHogProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
