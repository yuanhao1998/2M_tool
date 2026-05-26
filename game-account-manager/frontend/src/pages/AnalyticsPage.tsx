import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { X } from 'lucide-react'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  BarChart, Bar,
} from 'recharts'
import {
  getOverview, getOverviewComparison, getOverviewYoY,
  getByLocation, getByServer, getByClass,
  getAccountRanking, getWeeklyTrend,
  getCalendarData,
  getLocationTrend, getRecordDates,
} from '@/api'
import OverallTrend from '@/components/OverallTrend'
import type {
  Overview, Comparison, TrendPoint, LocationDist,
  GroupStat, AccountRanking, CalendarEntry,
} from '@/types'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316']

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [yoy, setYoy] = useState<Comparison | null>(null)
  const [locationDist, setLocationDist] = useState<LocationDist[]>([])
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)
  const [locationTrend, setLocationTrend] = useState<TrendPoint[]>([])
  const [serverData, setServerData] = useState<GroupStat[]>([])
  const [classData, setClassData] = useState<GroupStat[]>([])
  const [ranking, setRanking] = useState<AccountRanking[]>([])
  const [rankingDate, setRankingDate] = useState('all')
  const [serverChartDate, setServerChartDate] = useState('all')
  const [classChartDate, setClassChartDate] = useState('all')
  const [rankingDates, setRankingDates] = useState<string[]>([])
  const [rankingDrawerOpen, setRankingDrawerOpen] = useState(false)
  const [allRanking, setAllRanking] = useState<AccountRanking[]>([])
  const [rankSortDesc, setRankSortDesc] = useState(true)
  const [weeklyTrend, setWeeklyTrend] = useState<TrendPoint[]>([])
  const [calendarData, setCalendarData] = useState<CalendarEntry[]>([])
  useEffect(() => {
    getOverview().then(setOverview)
    getOverviewComparison().then(setComparison)
    getOverviewYoY().then(setYoy)
    getByLocation().then(setLocationDist)
    getByServer().then(setServerData)
    getByClass().then(setClassData)
    getWeeklyTrend().then(setWeeklyTrend)
    getCalendarData().then(setCalendarData)
  }, [])

  useEffect(() => {
    if (selectedLocation) {
      getLocationTrend(selectedLocation).then(setLocationTrend)
    }
  }, [selectedLocation])

  useEffect(() => {
    getRecordDates().then(setRankingDates)
  }, [])

  useEffect(() => {
    getAccountRanking(15, rankingDate === 'all' ? undefined : rankingDate, rankingDate === 'all' ? undefined : rankingDate).then(setRanking)
  }, [rankingDate])

  const openAllRanking = () => {
    getAccountRanking(9999, rankingDate === 'all' ? undefined : rankingDate, rankingDate === 'all' ? undefined : rankingDate).then((data) => {
      setAllRanking(data)
      setRankingDrawerOpen(true)
    })
  }

  const pieData = locationDist.map((d) => ({ name: d.location, value: d.total_amount }))

  const calendarMap = new Map(calendarData.map((e) => [e.date, e.amount]))
  const maxCal = Math.max(1, ...calendarData.map((e) => e.amount))

  const year = new Date().getFullYear()
  const months = Array.from({ length: 12 }, (_, m) => {
    const daysInMonth = new Date(year, m + 1, 0).getDate()
    const firstDow = new Date(year, m, 1).getDay()
    const weeks: (number | null)[] = Array(firstDow).fill(null)
    for (let d = 1; d <= daysInMonth; d++) {
      weeks.push(d)
    }
    return { month: m, weeks }
  })

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">收益看板</h2>

      {/* Overview cards */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs text-gray-500">总收益</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">💎 {overview?.total_diamonds ?? '—'}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs text-gray-500">环比变化</CardTitle></CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(comparison?.change_rate ?? 0) >= 0 ? 'text-green-600' : 'text-red-500'}`}>
              📈 {comparison?.change_rate != null ? `${comparison.change_rate > 0 ? '+' : ''}${comparison.change_rate}%` : '—'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs text-gray-500">同比变化</CardTitle></CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${(yoy?.change_rate ?? 0) >= 0 ? 'text-green-600' : 'text-red-500'}`}>
              📊 {yoy?.change_rate != null ? `${yoy.change_rate > 0 ? '+' : ''}${yoy.change_rate}%` : '—'}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs text-gray-500">最高产出地</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">📍 {overview?.top_location || '—'}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs text-gray-500">录入次数</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">📋 {overview?.entry_count ?? 0} 次</div></CardContent>
        </Card>
      </div>

      {/* Row 1: Overall trend + Location pie */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle>📈 钻石日变化趋势</CardTitle></CardHeader>
          <CardContent><OverallTrend /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>🥧 按地点收益分布</CardTitle></CardHeader>
          <CardContent>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" outerRadius={100} label
                    onClick={(e) => setSelectedLocation(e.name ?? null)}
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : <div className="text-center text-gray-400 h-64 flex items-center justify-center">暂无数据</div>}
          </CardContent>
        </Card>
      </div>

      {/* Location trend */}
      {selectedLocation && locationTrend.length > 0 && (
        <Card>
          <CardHeader><CardTitle>📍 {selectedLocation} — 收益趋势</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={locationTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="amount" stroke="#3b82f6" name="收益" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Row 3: Weekly trend */}
      <Card>
        <CardHeader><CardTitle>📊 每周收益趋势</CardTitle></CardHeader>
        <CardContent>
          {weeklyTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={weeklyTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="amount" fill="#8b5cf6" name="收益" />
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="text-center text-gray-400 h-56 flex items-center justify-center">暂无数据</div>}
        </CardContent>
      </Card>

      {/* Calendar heatmap */}
      <Card>
        <CardHeader><CardTitle>🔥 收益日历（{year}）</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-1">
            {months.map((m) => (
              <div key={m.month} className="flex flex-col gap-0.5">
                <div className="text-[10px] text-gray-400 text-center">{m.month + 1}月</div>
                <div className="grid grid-cols-7 gap-px">
                  {m.weeks.map((day, i) => {
                    if (day === null) return <div key={`e-${i}`} className="w-3 h-3" />
                    const ds = `${year}-${String(m.month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                    const amt = calendarMap.get(ds) || 0
                    const intensity = amt === 0 ? 0.05 : 0.15 + (amt / maxCal) * 0.85
                    return (
                      <div
                        key={ds}
                        className="w-3 h-3 rounded-sm"
                        style={{ backgroundColor: `rgba(59,130,246,${intensity})` }}
                        title={`${ds}: ${amt}`}
                      />
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
          {calendarData.length === 0 && (
            <div className="text-center text-gray-400 py-4">暂无数据</div>
          )}
        </CardContent>
      </Card>

      {/* Account ranking */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>🏆 账号收益排行 Top 15</CardTitle>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">批次</span>
              <Select value={rankingDate} onValueChange={(v) => setRankingDate(v ?? 'all')}>
                <SelectTrigger className="w-36 h-7 text-xs">
                  <SelectValue placeholder="全部批次" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部批次</SelectItem>
                  {rankingDates.map((d) => (
                    <SelectItem key={d} value={d}>{d}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" onClick={openAllRanking}>查看全部</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {ranking.length > 0 ? (
            <div className="border rounded-lg">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="text-left p-2 w-10">#</th>
                    <th className="text-left p-2">账号名</th>
                    <th className="text-left p-2">云机</th>
                    <th className="text-right p-2">累计收益</th>
                    <th className="text-right p-2">录入次数</th>
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((r, i) => (
                    <tr key={r.account_id} className="border-b hover:bg-gray-50">
                      <td className="p-2 text-gray-400">{i + 1}</td>
                      <td className="p-2 font-medium">{r.account_name}</td>
                      <td className="p-2 text-gray-500">{r.cloud_device || '—'}</td>
                      <td className="text-right p-2">{r.total_amount}</td>
                      <td className="text-right p-2 text-gray-500">{r.record_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="text-center text-gray-400 py-8">暂无数据</div>}
        </CardContent>
      </Card>

      {/* All ranking drawer */}
      {rankingDrawerOpen && <div className="fixed inset-0 bg-black/30 z-40" onClick={() => setRankingDrawerOpen(false)} />}
      <div className={`fixed top-0 right-0 h-full w-96 bg-white shadow-xl z-50 transform transition-transform duration-300 ${rankingDrawerOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">全部账户排行</h3>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={() => setRankSortDesc(!rankSortDesc)}>
              {rankSortDesc ? '↓ 从高到低' : '↑ 从低到高'}
            </Button>
            <Button variant="ghost" size="icon" onClick={() => setRankingDrawerOpen(false)}>
              <X size={16} />
            </Button>
          </div>
        </div>
        <div className="p-4 overflow-y-auto h-[calc(100%-60px)]">
          {allRanking.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>账号名</TableHead>
                  <TableHead>云机名称</TableHead>
                  <TableHead className="text-right">收益</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(rankSortDesc ? allRanking : [...allRanking].reverse()).map((r) => (
                  <TableRow key={r.account_id}>
                    <TableCell className="font-medium">{r.account_name}</TableCell>
                    <TableCell className="text-gray-500">{r.cloud_device || '—'}</TableCell>
                    <TableCell className="text-right">{r.total_amount}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <div className="text-center text-gray-400 py-8">暂无数据</div>}
        </div>
      </div>

      {/* Server / Class bar charts */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>🗺️ 按区服收益</CardTitle>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-500">批次</span>
                <Select value={serverChartDate} onValueChange={(v) => { const val = v ?? 'all'; setServerChartDate(val); getByServer(val === 'all' ? undefined : val).then(setServerData) }}>
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
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {serverData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={serverData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="total_amount" fill="#3b82f6" name="收益" />
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="text-center text-gray-400 h-56 flex items-center justify-center">暂无数据</div>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>⚔️ 按职业收益</CardTitle>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-500">批次</span>
                <Select value={classChartDate} onValueChange={(v) => { const val = v ?? 'all'; setClassChartDate(val); getByClass(val === 'all' ? undefined : val).then(setClassData) }}>
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
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {classData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={classData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="total_amount" fill="#10b981" name="收益" />
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="text-center text-gray-400 h-56 flex items-center justify-center">暂无数据</div>}
          </CardContent>
        </Card>
      </div>

    </div>
  )
}
