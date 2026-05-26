import { Users, FileText, BarChart3, TrendingUp, Gem } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { key: 'accounts', label: '账号管理', icon: Users },
  { key: 'records', label: '收益录入', icon: FileText },
  { key: 'analytics', label: '收益看板', icon: BarChart3 },
  { key: 'diamond', label: '钻石流水', icon: Gem },
  { key: 'analysis', label: '分析看板', icon: TrendingUp },
]

interface LayoutProps {
  active: string
  onNavigate: (key: string) => void
  children: React.ReactNode
}

export default function Layout({ active, onNavigate, children }: LayoutProps) {
  return (
    <div className="flex h-screen">
      <aside className="w-56 bg-gray-50 border-r flex flex-col">
        <div className="p-4 font-bold text-lg border-b">游戏账号管理</div>
        <nav className="flex-1 p-2">
          {navItems.map((item) => (
            <button
              key={item.key}
              onClick={() => onNavigate(item.key)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm mb-1 transition-colors',
                active === item.key
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              <item.icon size={18} />
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
