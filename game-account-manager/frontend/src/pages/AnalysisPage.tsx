import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { X } from 'lucide-react'
import { getAccounts, getRecordDates, getLowPerformers, getAccountTrendCompare, getRecords } from '@/api'
import type { Account, LowPerformer, AccountTrendCompare, DiamondRecord } from '@/types'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export default function AnalysisPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [rankingDates, setRankingDates] = useState<string[]>([])
  const [lowPerformerDate, setLowPerformerDate] = useState('all')
  const [lowThreshold, setLowThreshold] = useState(50)
  const [lowPerformers, setLowPerformers] = useState<LowPerformer[]>([])
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [accountSearch, setAccountSearch] = useState('')
  const [showAccountDropdown, setShowAccountDropdown] = useState(false)
  const [accountTrendCompare, setAccountTrendCompare] = useState<AccountTrendCompare | null>(null)
  const [drawerAccount, setDrawerAccount] = useState('')
  const [drawerRecords, setDrawerRecords] = useState<DiamondRecord[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)

  const openRecordDrawer = async (a: { account_id: number; account_name: string }) => {
    setDrawerAccount(a.account_name)
    setDrawerOpen(true)
    try {
      setDrawerRecords(await getRecords({ account_id: a.account_id }))
    } catch {
      setDrawerRecords([])
    }
  }

  useEffect(() => {
    getAccounts().then(setAccounts)
    getRecordDates().then(setRankingDates)
  }, [])

  useEffect(() => {
    getLowPerformers(lowPerformerDate === 'all' ? undefined : lowPerformerDate, lowThreshold / 100).then(setLowPerformers)
  }, [lowPerformerDate, lowThreshold])

  useEffect(() => {
    if (selectedAccount) {
      getAccountTrendCompare(parseInt(selectedAccount)).then(setAccountTrendCompare)
    } else {
      setAccountTrendCompare(null)
    }
  }, [selectedAccount])

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">分析看板</h2>

      {/* Low performers */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>⚠️ 需关注账户（收益低于均值）</CardTitle>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">批次</span>
              <Select value={lowPerformerDate} onValueChange={(v) => setLowPerformerDate(v ?? 'all')}>
                <SelectTrigger className="w-32 h-7 text-xs">
                  <SelectValue placeholder="全部批次" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部批次</SelectItem>
                  {rankingDates.map((d) => (
                    <SelectItem key={d} value={d}>{d}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-xs text-gray-500">低于均值</span>
              <Select value={String(lowThreshold)} onValueChange={(v) => setLowThreshold(Number(v))}>
                <SelectTrigger className="w-20 h-7 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[10, 20, 30, 40, 50, 60, 70, 80, 90].map((p) => (
                    <SelectItem key={p} value={String(p)}>{p}%</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {lowPerformers.length > 0 ? (
            <div className="border rounded-lg max-h-80 overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="text-left p-2">账号名</th>
                    <th className="text-left p-2">云机</th>
                    <th className="text-right p-2">收益</th>
                    <th className="text-right p-2">均值</th>
                    <th className="text-right p-2">占比</th>
                  </tr>
                </thead>
                <tbody>
                  {lowPerformers.map((a) => (
                    <tr key={a.account_id} className="border-b hover:bg-gray-50">
                      <td className="p-2 font-medium text-blue-600 cursor-pointer hover:underline" onClick={() => openRecordDrawer(a)}>{a.account_name}</td>
                      <td className="p-2 text-gray-500">{a.cloud_device || '—'}</td>
                      <td className="text-right p-2">{a.total_amount}</td>
                      <td className="text-right p-2 text-gray-500">{a.average}</td>
                      <td className="text-right p-2 text-red-500">{a.ratio}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">暂无低于均值{lowThreshold}%的账户</div>
          )}
        </CardContent>
      </Card>

      {/* Single account with average comparison */}
      <Card className="overflow-visible">
        <CardHeader><CardTitle>📈 单账户 vs 全体均值</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="relative w-64">
            <Input
              placeholder="搜索账号名、云机、手机号..."
              value={selectedAccount ? (accounts.find(a => a.id === parseInt(selectedAccount))?.account_name || accountSearch) : accountSearch}
              onChange={(e) => {
                setAccountSearch(e.target.value)
                setSelectedAccount('')
                setShowAccountDropdown(true)
              }}
              onFocus={() => setShowAccountDropdown(true)}
              onBlur={() => setTimeout(() => setShowAccountDropdown(false), 200)}
            />
            {showAccountDropdown && (
              <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-48 overflow-auto">
                {accounts
                  .filter((a) => {
                    if (!accountSearch) return true
                    const s = accountSearch.toLowerCase()
                    return a.account_name.toLowerCase().includes(s)
                      || a.phone.includes(s)
                      || a.cloud_device.toLowerCase().includes(s)
                  })
                  .map((a) => (
                    <div
                      key={a.id}
                      className="px-3 py-2 text-sm hover:bg-blue-50 cursor-pointer flex justify-between"
                      onMouseDown={() => {
                        setSelectedAccount(String(a.id))
                        setAccountSearch(a.account_name)
                        setShowAccountDropdown(false)
                      }}
                    >
                      <span className="font-medium">{a.account_name}</span>
                      <span className="text-gray-400 text-xs">{a.phone} | {a.cloud_device}</span>
                    </div>
                  ))
                }
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="font-medium mb-2">
                {accountTrendCompare ? `${accountTrendCompare.account_name} — 收益 vs 均值` : '请选择账户查看对比'}
              </div>
              {accountTrendCompare && accountTrendCompare.trend.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={accountTrendCompare.trend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="amount" stroke="#3b82f6" name="账号收益" />
                    <Line type="monotone" dataKey="average" stroke="#f59e0b" name="全体均值" strokeDasharray="5 5" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="border rounded-lg h-[280px] flex items-center justify-center text-gray-400">暂无数据</div>
              )}
            </div>
            <div>
              <div className="font-medium mb-2">收益明细</div>
              {accountTrendCompare && accountTrendCompare.trend.length > 0 ? (
                <div className="border rounded-lg max-h-72 overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="text-left p-2">日期</th>
                        <th className="text-right p-2">收益</th>
                        <th className="text-right p-2">均值</th>
                        <th className="text-right p-2">环比</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...accountTrendCompare.trend].reverse().map((p, i) => (
                        <tr key={i} className="border-b">
                          <td className="p-2">{p.date}</td>
                          <td className="text-right p-2">{p.amount}</td>
                          <td className="text-right p-2 text-gray-500">{p.average}</td>
                          <td className={`text-right p-2 ${(p.change_rate ?? 0) >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                            {p.change_rate != null ? `${p.change_rate > 0 ? '+' : ''}${p.change_rate}%` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="border rounded-lg h-[280px] flex items-center justify-center text-gray-400">暂无数据</div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
      {drawerOpen && <div className="fixed inset-0 bg-black/30 z-40" onClick={() => setDrawerOpen(false)} />}
      <div className={`fixed top-0 right-0 h-full w-96 bg-white shadow-xl z-50 transform transition-transform duration-300 ${drawerOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">{drawerAccount} — 收益记录</h3>
          <Button variant="ghost" size="icon" onClick={() => setDrawerOpen(false)}>
            <X size={16} />
          </Button>
        </div>
        <div className="p-4 overflow-y-auto h-[calc(100%-60px)]">
          {drawerRecords.length > 0 ? (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>日期</TableHead>
                    <TableHead>地点</TableHead>
                    <TableHead className="text-right">数量</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {drawerRecords.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>{r.recorded_at}</TableCell>
                      <TableCell>{r.location || '—'}</TableCell>
                      <TableCell className="text-right font-medium">{r.amount}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="bg-gray-50 font-bold">
                    <TableCell>合计</TableCell>
                    <TableCell />
                    <TableCell className="text-right">{drawerRecords.reduce((s, r) => s + r.amount, 0)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">暂无收益记录</div>
          )}
        </div>
      </div>
    </div>
  )
}
