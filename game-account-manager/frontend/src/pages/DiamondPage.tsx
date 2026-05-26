import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getDiamondSales } from '@/api'
import type { DiamondSale } from '@/types'

export default function DiamondPage() {
  const [sales, setSales] = useState<DiamondSale[]>([])
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const load = () => {
    getDiamondSales({
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }).then(setSales).catch(console.error)
  }

  useEffect(() => { load() }, [])

  const totalSold = sales.reduce((s, r) => s + r.diamonds_sold, 0)

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">钻石流水</h2>

      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500">开始</span>
          <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-36 h-8" />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-500">结束</span>
          <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-36 h-8" />
        </div>
        <Button size="sm" onClick={load}>查询</Button>
        {sales.length > 0 && (
          <span className="text-sm text-gray-500 ml-2">
            共 {sales.length} 条记录，合计卖出 {totalSold.toLocaleString()} 钻石
          </span>
        )}
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>日期</TableHead>
              <TableHead>账号名</TableHead>
              <TableHead>云机</TableHead>
              <TableHead>手机号</TableHead>
              <TableHead className="text-right">卖出数量</TableHead>
              <TableHead>记录时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sales.map((s) => (
              <TableRow key={s.id}>
                <TableCell>{s.sale_date}</TableCell>
                <TableCell className="font-medium">{s.account_name}</TableCell>
                <TableCell>{s.cloud_device}</TableCell>
                <TableCell>{s.phone}</TableCell>
                <TableCell className="text-right text-amber-600 font-medium">
                  {s.diamonds_sold.toLocaleString()}
                </TableCell>
                <TableCell className="text-xs text-gray-400">
                  {new Date(s.created_at).toLocaleString()}
                </TableCell>
              </TableRow>
            ))}
            {sales.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-gray-400 py-8">
                  暂无卖出记录
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
