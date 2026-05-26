import { useState, useEffect, useCallback } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getAccounts, createRecords } from '@/api'
import type { Account } from '@/types'
import { X, Plus } from 'lucide-react'
import * as XLSX from 'xlsx'

interface ExcelRow {
  cloud_device: string
  amount: number
  location: string
  matchAccount?: Account
  matched: boolean
}

export default function RecordsPage() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [accounts, setAccounts] = useState<Account[]>([])
  const [manualMode, setManualMode] = useState<'all' | 'single'>('single')
  const [entrySearches, setEntrySearches] = useState<Record<number, { search: string; show: boolean }>>({})
  const [manualAmounts, setManualAmounts] = useState<Record<number, string>>({})
  const [manualLocations, setManualLocations] = useState<Record<number, string>>({})
  const [singleEntries, setSingleEntries] = useState<{ id: number; account_id: number | null; location: string; amount: string }[]>([
    { id: 1, account_id: null, location: '', amount: '' },
  ])
  const [excelRows, setExcelRows] = useState<ExcelRow[]>([])
  const [excelLocation, setExcelLocation] = useState('')

  const loadAccounts = useCallback(() => {
    getAccounts().then(setAccounts).catch(console.error)
  }, [])

  useEffect(() => { loadAccounts() }, [loadAccounts])

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const buf = await file.arrayBuffer()
    const wb = XLSX.read(buf, { type: 'array' })
    const sheet = wb.Sheets[wb.SheetNames[0]]
    const data = XLSX.utils.sheet_to_json<Record<string, string>>(sheet)

    const accountMap = new Map(accounts.map((a) => [a.cloud_device, a]))
    const rows: ExcelRow[] = data.map((row) => {
      const keys = Object.keys(row)
      const device = (row[keys[0]] || '').toString().trim()
      const amount = parseInt(row[keys[1]]) || 0
      const location = (row[keys[2]] || '').toString().trim()
      const match = accountMap.get(device)
      return { cloud_device: device, amount, location, matchAccount: match, matched: !!match }
    })
    setExcelRows(rows)
  }

  const downloadTemplate = () => {
    const header = ['云机名称', '收益', '地点']
    const sorted = accounts
      .filter((a) => a.cloud_device)
      .sort((a, b) => a.cloud_device.localeCompare(b.cloud_device))
    const rows = sorted.map((a) => [a.cloud_device, '', a.location || ''])
    const ws = XLSX.utils.aoa_to_sheet([header, ...rows])
    ws['!cols'] = [{ wch: 14 }, { wch: 10 }, { wch: 14 }]
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '收益模板')
    XLSX.writeFile(wb, '收益录入模板.xlsx')
  }

  const handleExcelImport = async () => {
    const matched = excelRows.filter((r) => r.matched && r.amount > 0)
    if (matched.length === 0) return
    await createRecords(
      matched.map((r) => ({
        account_id: r.matchAccount!.id,
        amount: r.amount,
        location: r.location || excelLocation,
        recorded_at: date,
      }))
    )
    setExcelRows([])
    const input = document.getElementById('excel-input') as HTMLInputElement
    if (input) input.value = ''
    alert('导入成功')
  }

  const handleManualSubmit = async () => {
    if (manualMode === 'single') {
      const entries = singleEntries
        .filter((e) => e.account_id && e.amount && parseInt(e.amount) > 0)
        .map((e) => ({
          account_id: e.account_id!,
          amount: parseInt(e.amount),
          location: e.location,
          recorded_at: date,
        }))
      if (entries.length === 0) return
      await createRecords(entries)
      setSingleEntries([{ id: 1, account_id: null, location: '', amount: '' }])
      alert('提交成功')
      return
    }
    const entries = Object.entries(manualAmounts)
      .filter(([, v]) => v && parseInt(v) > 0)
      .map(([accountId, amount]) => ({
        account_id: parseInt(accountId),
        amount: parseInt(amount),
        location: manualLocations[parseInt(accountId)] || '',
        recorded_at: date,
      }))
    if (entries.length === 0) return
    await createRecords(entries)
    setManualAmounts({})
    setManualLocations({})
    alert('提交成功')
  }

  const displayedAccounts = accounts

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">收益录入</h2>

      <div className="flex items-center gap-4 mb-4 p-3 bg-blue-50 rounded-lg">
        <span className="font-medium">录入日期：</span>
        <Input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="w-40"
        />
      </div>

      <Tabs defaultValue="excel">
        <TabsList>
          <TabsTrigger value="excel">Excel 批量导入</TabsTrigger>
          <TabsTrigger value="manual">手动录入</TabsTrigger>
        </TabsList>

        <TabsContent value="excel" className="space-y-4 mt-4">
          <div className="flex gap-4 items-start">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center flex-1">
              <input
                id="excel-input"
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFile}
                className="hidden"
              />
              <label htmlFor="excel-input" className="cursor-pointer">
                <div className="text-2xl mb-2">📁</div>
                <div>拖拽或点击上传 Excel 文件</div>
                <div className="text-xs text-gray-400 mt-1">.xlsx / .xls</div>
              </label>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-xs">
              <div className="font-bold mb-2">模板格式：</div>
              <table className="border-collapse">
                <thead>
                  <tr className="bg-gray-200">
                    <td className="border px-2 py-1">云机名称</td>
                    <td className="border px-2 py-1">收益</td>
                    <td className="border px-2 py-1">地点（选填）</td>
                  </tr>
                </thead>
                <tbody>
                  <tr><td className="border px-2 py-1">云机-01</td><td className="border px-2 py-1">120</td><td className="border px-2 py-1">深渊副本</td></tr>
                  <tr><td className="border px-2 py-1">云机-02</td><td className="border px-2 py-1">95</td><td className="border px-2 py-1"></td></tr>
                </tbody>
              </table>
              <Button variant="outline" size="sm" className="mt-2 w-full" onClick={downloadTemplate}>
                下载模板
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm">缺省地点：</span>
            <Input
              placeholder="选填，Excel 中地点为空时使用此值"
              value={excelLocation}
              onChange={(e) => setExcelLocation(e.target.value)}
              className="w-48"
            />
          </div>

          {excelRows.length > 0 && (
            <>
              <div className="font-medium text-sm">匹配预览：</div>
              <div className="border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>云机名称</TableHead>
                      <TableHead>匹配账号</TableHead>
                      <TableHead>收益</TableHead>
                      <TableHead>地点</TableHead>
                      <TableHead>状态</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {excelRows.map((row, i) => (
                      <TableRow key={i} className={row.matched ? '' : 'text-red-500'}>
                        <TableCell>{row.cloud_device}</TableCell>
                        <TableCell>{row.matchAccount?.account_name || '—'}</TableCell>
                        <TableCell>{row.amount}</TableCell>
                        <TableCell>{row.location || excelLocation || '—'}</TableCell>
                        <TableCell>{row.matched ? '✓ 匹配' : '未匹配'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-red-500">
                  {excelRows.filter((r) => !r.matched).length > 0 &&
                    `${excelRows.filter((r) => !r.matched).length} 条未匹配`}
                </span>
                <Button onClick={handleExcelImport} disabled={excelRows.filter((r) => r.matched).length === 0}>
                  确认导入
                </Button>
              </div>
            </>
          )}
        </TabsContent>

        <TabsContent value="manual" className="space-y-4 mt-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
              <button
                className={`px-3 py-1 rounded-md text-sm ${manualMode === 'single' ? 'bg-white shadow font-medium' : 'text-gray-500'}`}
                onClick={() => setManualMode('single')}
              >单账户录入</button>
              <button
                className={`px-3 py-1 rounded-md text-sm ${manualMode === 'all' ? 'bg-white shadow font-medium' : 'text-gray-500'}`}
                onClick={() => setManualMode('all')}
              >整体录入</button>
            </div>
          </div>
          {manualMode === 'single' ? (
            <div className="space-y-2">
              <div className="grid grid-cols-[160px_100px_100px_100px_40px] gap-2 text-xs font-medium text-gray-500 px-2">
                <div>账户名</div>
                <div>云机名</div>
                <div>地点（选填）</div>
                <div>收益</div>
                <div />
              </div>
              {singleEntries.map((entry) => {
                const acc = entry.account_id ? accounts.find((a) => a.id === entry.account_id) : null
                const es = entrySearches[entry.id] || { search: '', show: false }
                return (
                  <div key={entry.id} className="grid grid-cols-[160px_100px_100px_100px_40px] gap-2 items-center px-2 py-1 border rounded-lg">
                    <div className="relative">
                      <Input
                        placeholder="搜索账户..."
                        value={acc ? acc.account_name : es.search}
                        onChange={(e) => {
                          setEntrySearches((s) => ({ ...s, [entry.id]: { search: e.target.value, show: true } }))
                          setSingleEntries((prev) => prev.map((en) => en.id === entry.id ? { ...en, account_id: null } : en))
                        }}
                        onFocus={() => setEntrySearches((s) => ({ ...s, [entry.id]: { ...(s[entry.id] || { search: '' }), show: true } }))}
                        onBlur={() => setTimeout(() => setEntrySearches((s) => ({ ...s, [entry.id]: { ...(s[entry.id] || { search: '' }), show: false } })), 200)}
                        className="h-7 text-xs"
                      />
                      {es.show && (
                        <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-36 overflow-auto">
                          {accounts
                            .filter((a) => {
                              if (!es.search) return true
                              const s = es.search.toLowerCase()
                              return a.account_name.toLowerCase().includes(s) || a.cloud_device.toLowerCase().includes(s) || a.phone.includes(s)
                            })
                            .map((a) => (
                              <div key={a.id} className="px-2 py-1.5 text-xs hover:bg-blue-50 cursor-pointer flex justify-between" onMouseDown={() => {
                                setSingleEntries((prev) => prev.map((en) => en.id === entry.id ? { ...en, account_id: a.id } : en))
                                setEntrySearches((s) => ({ ...s, [entry.id]: { search: a.account_name, show: false } }))
                              }}>
                                <span className="font-medium">{a.account_name}</span>
                                <span className="text-gray-400">{a.cloud_device}</span>
                              </div>
                            ))
                          }
                        </div>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">{acc?.cloud_device || '—'}</div>
                    <Input
                      placeholder="选填"
                      value={entry.location}
                      onChange={(e) => setSingleEntries((prev) => prev.map((en) => en.id === entry.id ? { ...en, location: e.target.value } : en))}
                      className="h-7 text-xs"
                    />
                    <Input
                      type="number"
                      placeholder="0"
                      value={entry.amount}
                      onChange={(e) => setSingleEntries((prev) => prev.map((en) => en.id === entry.id ? { ...en, amount: e.target.value } : en))}
                      className="h-7 text-xs"
                    />
                    <div>
                      {singleEntries.length > 1 && (
                        <Button variant="ghost" size="icon" onClick={() => setSingleEntries((prev) => prev.filter((en) => en.id !== entry.id))}>
                          <X size={14} />
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
              <Button variant="outline" size="sm" onClick={() => setSingleEntries((prev) => [...prev, { id: Date.now(), account_id: null, location: '', amount: '' }])}>
                <Plus size={14} className="mr-1" />添加一条
              </Button>
            </div>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>账号</TableHead>
                    <TableHead>云机</TableHead>
                    <TableHead>地点</TableHead>
                    <TableHead>本次钻石</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedAccounts.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="font-medium">{a.account_name}</TableCell>
                      <TableCell>{a.cloud_device}</TableCell>
                      <TableCell>
                        <Input
                          placeholder="选填"
                          value={manualLocations[a.id] || ''}
                          onChange={(e) => setManualLocations((s) => ({ ...s, [a.id]: e.target.value }))}
                          className="w-32 h-7 text-xs"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          placeholder="0"
                          value={manualAmounts[a.id] || ''}
                          onChange={(e) => setManualAmounts((s) => ({ ...s, [a.id]: e.target.value }))}
                          className="w-24"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <div className="text-right">
            <Button onClick={handleManualSubmit}>提交收益</Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
