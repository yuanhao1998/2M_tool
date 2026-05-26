import { useState, useEffect } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import type { TrendPoint } from '@/types'

export default function OverallTrend() {
  const [data, setData] = useState<TrendPoint[]>([])

  useEffect(() => {
    fetch('/api/analytics/diamond-trend')
      .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json() })
      .then(setData)
      .catch(console.error)
  }, [])

  if (data.length === 0) {
    return <div className="text-center text-gray-400 h-64 flex items-center justify-center">暂无钻石变化数据</div>
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="amount" stroke="#3b82f6" name="钻石日变化" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
