import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'FinSight — Financial research, made clear',
  description: 'Source-linked Indian company research, fund NAV comparisons, portfolio exposure and RBI economic context.',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>
}
