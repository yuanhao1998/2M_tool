import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import AccountForm from '@/components/AccountForm'
import { getAccounts, createAccount, updateAccount, deleteAccount, batchDeleteAccounts, importAccountsExcel, getRecords, sellDiamonds, syncDiamonds } from '@/api'
import type { Account, DiamondRecord } from '@/types'
import { Plus, Pencil, Trash2, X, Filter, ChevronDown, ChevronUp, Gem, RefreshCw } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import * as XLSX from 'xlsx'

const FIELDS: { key: string; label: string }[] = [
  { key: 'account_name', label: '账号名' },
  { key: 'email', label: '邮箱' },
  { key: 'server', label: '区服' },
  { key: 'region', label: '大区' },
  { key: 'class_name', label: '职业' },
  { key: 'pin_code', label: 'PIN 码' },
  { key: 'phone', label: '手机号' },
  { key: 'cloud_device', label: '云机名称' },
  { key: 'location', label: '地点' },
  { key: 'verify_code_url', label: '验证码 URL' },
  { key: 'recovery_code', label: '修复码' },
]

const HEADER_TO_KEY: Record<string, string> = {
  '账号名': 'account_name', '账号': 'account_name',
  '邮箱': 'email',
  '区服': 'server',
  '大区': 'region',
  '职业': 'class_name',
  'pin码': 'pin_code', 'PIN码': 'pin_code', 'PIN 码': 'pin_code',
  '手机号': 'phone', '手机': 'phone',
  '云机名称': 'cloud_device', '云机': 'cloud_device',
  '地点': 'location',
  '验证码url': 'verify_code_url', '验证码URL': 'verify_code_url', '验证码 URL': 'verify_code_url', '验证码': 'verify_code_url',
  '修复码': 'recovery_code',
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [search, setSearch] = useState('')
  const [server, setServer] = useState('all')
  const [region, setRegion] = useState('all')
  const [showMore, setShowMore] = useState(false)
  const [emailFilter, setEmailFilter] = useState('')
  const [classFilter, setClassFilter] = useState('')
  const [deviceFilter, setDeviceFilter] = useState('')
  const [serverOptions, setServerOptions] = useState<string[]>([])
  const [regionOptions, setRegionOptions] = useState<string[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Account | null>(null)
  const [excelRows, setExcelRows] = useState<Record<string, string>[]>([])
  const [excelFile, setExcelFile] = useState<File | null>(null)
  const [viewRecords, setViewRecords] = useState<DiamondRecord[]>([])
  const [viewAccountName, setViewAccountName] = useState('')
  const [recordsOpen, setRecordsOpen] = useState(false)
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncInput, setSyncInput] = useState('')
  const [syncPreview, setSyncPreview] = useState<{ cloud_device: string; diamonds: number; account?: Account; current_diamonds: number; change: number; warn: string | null }[]>([])

  const load = useCallback(() => {
    getAccounts({
      search,
      server: server === 'all' ? '' : server,
      region: region === 'all' ? '' : region,
      email: emailFilter,
      class_name: classFilter,
      cloud_device: deviceFilter,
    }).then(setAccounts).catch(console.error)
  }, [search, server, region, emailFilter, classFilter, deviceFilter])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    getAccounts().then((all) => {
      const servers = [...new Set(all.map((a) => a.server).filter(Boolean))].sort()
      const regions = [...new Set(all.map((a) => a.region).filter(Boolean))].sort()
      setServerOptions(servers)
      setRegionOptions(regions)
    }).catch(console.error)
  }, [])

  const handleSave = async (data: Partial<Account>) => {
    if (editing) {
      await updateAccount(editing.id, data)
    } else {
      await createAccount(data)
    }
    setEditing(null)
    load()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('删除账号将同时删除其所有收益记录，确认？')) return
    await deleteAccount(id)
    setSelected((prev) => { prev.delete(id); return new Set(prev) })
    load()
  }

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === accounts.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(accounts.map((a) => a.id)))
    }
  }

  const handleViewRecords = async (a: Account) => {
    setViewAccountName(a.account_name || a.phone)
    setRecordsOpen(true)
    try {
      const records = await getRecords({ account_id: a.id })
      setViewRecords(records)
    } catch {
      setViewRecords([])
    }
  }

  const handleBatchDelete = async () => {
    if (selected.size === 0) return
    if (!confirm(`确认删除选中的 ${selected.size} 个账号及其所有收益记录？`)) return
    await batchDeleteAccounts([...selected])
    setSelected(new Set())
    load()
  }

  const handleBatchSell = async () => {
    if (selected.size === 0) return
    if (!confirm(`确认将选中 ${selected.size} 个账户的钻石卖出并清零？此操作不可撤销。`)) return
    try {
      const result = await sellDiamonds([...selected])
      alert(`成功卖出 ${result.sold_count} 个账户，共 ${result.total_diamonds_sold.toLocaleString()} 钻石`)
      setSelected(new Set())
      load()
    } catch (err: any) {
      alert(err.message || '卖出失败')
    }
  }

  const existingPhones = new Set(accounts.map((a) => a.phone).filter(Boolean))

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setExcelFile(file)
    const buf = await file.arrayBuffer()
    const wb = XLSX.read(buf, { type: 'array' })
    const sheet = wb.Sheets[wb.SheetNames[0]]
    const data = XLSX.utils.sheet_to_json<Record<string, string>>(sheet)
    const rows = data.map((row) => {
      const mapped: Record<string, string> = {}
      for (const [header, val] of Object.entries(row)) {
        const key = HEADER_TO_KEY[header.trim()] || header.trim()
        mapped[key] = (val || '').toString().trim()
      }
      return mapped
    })
    setExcelRows(rows)
  }

  const downloadTemplate = () => {
    const headerRow = FIELDS.map((f) => f.label)
    const ws = XLSX.utils.aoa_to_sheet([headerRow])
    // set column widths for readability
    ws['!cols'] = headerRow.map(() => ({ wch: 14 }))
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '账号模板')
    XLSX.writeFile(wb, '账号导入模板.xlsx')
  }

  const handleExcelImport = async () => {
    if (!excelFile) return
    await importAccountsExcel(excelFile)
    setExcelRows([])
    setExcelFile(null)
    const input = document.getElementById('excel-account-input') as HTMLInputElement
    if (input) input.value = ''
    load()
    alert('导入成功')
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">账号管理</h2>
      </div>

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">账号列表</TabsTrigger>
          <TabsTrigger value="excel">Excel 批量导入</TabsTrigger>
        </TabsList>

        <TabsContent value="list" className="mt-4">
          <div className="flex items-center justify-between mb-4">
            <div className="space-y-3 flex-1">
              <div className="flex items-center gap-3 flex-wrap">
              <Input
                placeholder="搜索手机号、账号名..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="max-w-xs"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowMore(!showMore)}
              >
                <Filter size={14} className="mr-1" />
                更多筛选
                {showMore ? <ChevronUp size={14} className="ml-1" /> : <ChevronDown size={14} className="ml-1" />}
              </Button>
              {(search || server !== 'all' || region !== 'all' || emailFilter || classFilter || deviceFilter) && (
                <Button variant="ghost" size="sm" onClick={() => {
                  setSearch(''); setServer('all'); setRegion('all')
                  setEmailFilter(''); setClassFilter(''); setDeviceFilter('')
                }}>
                  <X size={14} className="mr-1" />清除
                </Button>
              )}
            </div>
            {showMore && (
              <div className="flex items-center gap-3 flex-wrap p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-gray-500 w-8">区服</span>
                  <Select value={server} onValueChange={(v) => setServer(v ?? 'all')}>
                    <SelectTrigger className="w-32 h-7 text-xs">
                      <SelectValue placeholder="全部" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部区服</SelectItem>
                      {serverOptions.map((s) => (
                        <SelectItem key={s} value={s}>{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-gray-500 w-8">大区</span>
                  <Select value={region} onValueChange={(v) => setRegion(v ?? 'all')}>
                    <SelectTrigger className="w-32 h-7 text-xs">
                      <SelectValue placeholder="全部" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部大区</SelectItem>
                      {regionOptions.map((r) => (
                        <SelectItem key={r} value={r}>{r}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-gray-500 w-8">邮箱</span>
                  <Input
                    placeholder="模糊匹配"
                    value={emailFilter}
                    onChange={(e) => setEmailFilter(e.target.value)}
                    className="w-32 h-7 text-xs"
                  />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-gray-500 w-8">职业</span>
                  <Input
                    placeholder="模糊匹配"
                    value={classFilter}
                    onChange={(e) => setClassFilter(e.target.value)}
                    className="w-32 h-7 text-xs"
                  />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-gray-500 w-8">云机</span>
                  <Input
                    placeholder="模糊匹配"
                    value={deviceFilter}
                    onChange={(e) => setDeviceFilter(e.target.value)}
                    className="w-32 h-7 text-xs"
                  />
                </div>
              </div>
            )}
            </div>
            <div className="flex items-center gap-2">
              {selected.size > 0 && (
                <>
                  <Button variant="default" size="sm" className="bg-amber-600 hover:bg-amber-700" onClick={handleBatchSell}>
                    <Gem size={14} className="mr-1" />卖出钻石 ({selected.size})
                  </Button>
                  <Button variant="destructive" size="sm" onClick={handleBatchDelete}>
                    <Trash2 size={14} className="mr-1" />删除 ({selected.size})
                  </Button>
                </>
              )}
              <Button variant="outline" size="sm" onClick={() => setSyncDialogOpen(true)}>
                <RefreshCw size={14} className="mr-1" />同步钻石
              </Button>
              <Button onClick={() => { setEditing(null); setFormOpen(true) }}>
                <Plus size={16} className="mr-1" />新增账号
              </Button>
            </div>
          </div>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input type="checkbox" checked={selected.size === accounts.length && accounts.length > 0} onChange={toggleAll} />
                  </TableHead>
                  <TableHead>手机号</TableHead>
                  <TableHead>当前钻石</TableHead>
                  <TableHead>云机名</TableHead>
                  <TableHead>账户名</TableHead>
                  <TableHead>区服</TableHead>
                  <TableHead>职业</TableHead>
                  <TableHead className="w-24">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>
                      <input type="checkbox" checked={selected.has(a.id)} onChange={() => toggleSelect(a.id)} />
                    </TableCell>
                    <TableCell className="font-medium text-blue-600 cursor-pointer hover:underline" onClick={() => handleViewRecords(a)}>{a.phone || '—'}</TableCell>
                    <TableCell className="font-medium">{a.current_diamonds?.toLocaleString() ?? '0'}</TableCell>
                    <TableCell>{a.cloud_device}</TableCell>
                    <TableCell>{a.account_name}</TableCell>
                    <TableCell>{a.server}</TableCell>
                    <TableCell>{a.class}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" onClick={() => { setEditing(a); setFormOpen(true) }}>
                          <Pencil size={14} />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(a.id)}>
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {accounts.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-gray-400 py-8">
                      暂无账号，点击右上角"新增账号"或"Excel 批量导入"添加
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="excel" className="space-y-4 mt-4">
          <div className="flex gap-4 items-start">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center flex-1">
              <input
                id="excel-account-input"
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFile}
                className="hidden"
              />
              <label htmlFor="excel-account-input" className="cursor-pointer">
                <div className="text-2xl mb-2">📁</div>
                <div>拖拽或点击上传 Excel 文件</div>
                <div className="text-xs text-gray-400 mt-1">.xlsx / .xls</div>
              </label>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-xs min-w-[240px]">
              <div className="font-bold mb-2">模板格式（第一行为表头）：</div>
              <table className="border-collapse w-full">
                <thead>
                  <tr className="bg-gray-200">
                    {FIELDS.slice(0, 5).map((f) => (
                      <td key={f.key} className="border px-1 py-1">{f.label}</td>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    {FIELDS.slice(0, 5).map((f) => (
                      <td key={f.key} className="border px-1 py-1 text-gray-400">...</td>
                    ))}
                  </tr>
                </tbody>
              </table>
              <div className="mt-2 text-gray-500">支持中文或英文列名，手机号必填</div>
              <Button variant="outline" size="sm" className="mt-2 w-full" onClick={downloadTemplate}>
                下载模板
              </Button>
            </div>
          </div>

          {excelRows.length > 0 && (
            <>
              <div className="font-medium text-sm">
                预览 ({excelRows.filter((r) => r.phone).length} 条有效数据，{excelRows.filter((r) => r.phone && existingPhones.has(r.phone)).length} 条覆盖更新)：
              </div>
              <div className="border rounded-lg max-h-64 overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>账号名</TableHead>
                      <TableHead>区服</TableHead>
                      <TableHead>大区</TableHead>
                      <TableHead>职业</TableHead>
                      <TableHead>云机名称</TableHead>
                      <TableHead>手机号</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {excelRows.map((row, i) => {
                      const isUpdate = row.phone && existingPhones.has(row.phone)
                      return (
                        <TableRow key={i} className={row.phone ? (isUpdate ? 'bg-yellow-50' : '') : 'text-red-300'}>
                          <TableCell>{row.account_name || row.phone || '—'}</TableCell>
                          <TableCell>{row.server || '—'}</TableCell>
                          <TableCell>{row.region || '—'}</TableCell>
                          <TableCell>{row.class_name || '—'}</TableCell>
                          <TableCell>{row.cloud_device || '—'}</TableCell>
                          <TableCell>{row.phone || '—'}</TableCell>
                          <TableCell>
                            {row.phone ? (
                              isUpdate ? <span className="text-xs text-yellow-600 font-medium">覆盖更新</span> : <span className="text-xs text-green-600 font-medium">新增</span>
                            ) : '—'}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
              <div className="text-right">
                <Button onClick={handleExcelImport} disabled={excelRows.filter((r) => r.phone).length === 0}>
                  确认导入
                </Button>
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>

      <AccountForm open={formOpen} onClose={() => setFormOpen(false)} onSave={handleSave} account={editing} />

      <Dialog open={syncDialogOpen} onOpenChange={(open) => { setSyncDialogOpen(open); if (!open) { setSyncPreview([]); setSyncInput('') } }}>
        <DialogContent className={syncPreview.length > 0 ? 'sm:max-w-[50vw]' : 'max-w-xl'}>
          <DialogHeader><DialogTitle>同步钻石</DialogTitle></DialogHeader>

          {syncPreview.length > 0 ? (
            <div className="space-y-4">
              <div className="text-sm text-gray-500">
                共 {syncPreview.length} 条数据，匹配 {syncPreview.filter((p) => p.account).length} 个账户
                {syncPreview.filter((p) => !p.account).length > 0 && (
                  <span className="text-red-500">，{syncPreview.filter((p) => !p.account).length} 条未匹配</span>
                )}
                {syncPreview.filter((p) => p.warn).length > 0 && (
                  <span className="text-amber-600">，{syncPreview.filter((p) => p.warn).length} 条需注意</span>
                )}
              </div>
              <div className="border rounded-lg max-h-[60vh] overflow-auto">
                <Table className="table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs w-[14%]">云机名称</TableHead>
                      <TableHead className="text-xs w-[30%]">匹配账户</TableHead>
                      <TableHead className="text-xs text-right w-[14%]">当前钻石</TableHead>
                      <TableHead className="text-xs text-right w-[14%]">更新为</TableHead>
                      <TableHead className="text-xs text-right w-[14%]">变化</TableHead>
                      <TableHead className="text-xs w-[14%]">提醒</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {syncPreview.map((p, i) => (
                      <TableRow key={i} className={p.warn ? 'bg-amber-50' : ''}>
                        <TableCell className="font-mono text-xs">{p.cloud_device}</TableCell>
                        <TableCell className="truncate" title={p.account ? `${p.account.account_name} (${p.account.phone || '—'})` : ''}>
                          {p.account ? `${p.account.account_name} (${p.account.phone || '—'})` : <span className="text-red-500">未匹配</span>}
                        </TableCell>
                        <TableCell className="text-right">{p.current_diamonds.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-medium">{p.diamonds.toLocaleString()}</TableCell>
                        <TableCell className={`text-right ${p.change >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                          {p.change >= 0 ? '+' : ''}{p.change.toLocaleString()}
                        </TableCell>
                        <TableCell>{p.warn ? <span className="text-amber-600 text-xs">{p.warn}</span> : '—'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="flex justify-between items-center">
                <Button variant="outline" onClick={() => { setSyncPreview([]); setSyncInput('') }}>返回编辑</Button>
                <Button onClick={async () => {
                  try {
                    const data = syncPreview
                      .filter((p) => p.account)
                      .map((p) => ({ cloud_device: p.cloud_device, diamonds: p.diamonds }))
                    if (data.length === 0) { alert('没有可同步的匹配数据'); return }
                    const result = await syncDiamonds(data)
                    alert(`同步完成：更新 ${result.updated_count} 个账户，新建 ${result.snapshot_count} 条快照`)
                    setSyncDialogOpen(false)
                    setSyncInput('')
                    setSyncPreview([])
                    load()
                  } catch (err: any) {
                    alert('同步失败：' + (err.message || '未知错误'))
                  }
                }} disabled={syncPreview.filter((p) => p.account).length === 0}>
                  确认同步 ({syncPreview.filter((p) => p.account).length} 项)
                </Button>
              </div>
            </div>
          ) : (
            <>
              <p className="text-sm text-gray-500 mb-2">
                输入 JSON 数组，通过云机名称匹配账户：{'[{ "cloud_device": "云机-01", "diamonds": 120 }]'}
              </p>
              <textarea
                className="w-full h-48 p-2 border rounded font-mono text-sm"
                value={syncInput}
                onChange={(e) => setSyncInput(e.target.value)}
                placeholder='[{"cloud_device": "云机-01", "diamonds": 150}]'
              />
              <DialogFooter>
                <Button variant="outline" onClick={() => { setSyncDialogOpen(false); setSyncInput('') }}>取消</Button>
                <Button onClick={() => {
                  try {
                    const data = JSON.parse(syncInput)
                    if (!Array.isArray(data)) throw new Error('请输入 JSON 数组')
                    const accountMap = new Map(accounts.map((a) => [a.cloud_device, a]))
                    const preview = data.map((item: any) => {
                      const device = (item.cloud_device || '').trim()
                      const diamonds = parseInt(item.diamonds) || 0
                      const account = accountMap.get(device)
                      const current = account?.current_diamonds || 0
                      const change = diamonds - current
                      let warn: string | null = null
                      if (account && diamonds < current) warn = `减少 ${(current - diamonds).toLocaleString()}`
                      if (diamonds > 2000) warn = (warn ? warn + '；' : '') + `超过 2000（${diamonds.toLocaleString()}）`
                      return { cloud_device: device, diamonds, account, current_diamonds: current, change, warn }
                    })
                    setSyncPreview(preview)
                  } catch (err: any) {
                    alert('解析失败：' + (err.message || '输入格式错误'))
                  }
                }}>校验并预览</Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {recordsOpen && <div className="fixed inset-0 bg-black/30 z-40" onClick={() => setRecordsOpen(false)} />}
      <div className={`fixed top-0 right-0 h-full w-96 bg-white shadow-xl z-50 transform transition-transform duration-300 ${recordsOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">{viewAccountName} — 收益记录</h3>
          <Button variant="ghost" size="icon" onClick={() => setRecordsOpen(false)}>
            <X size={16} />
          </Button>
        </div>
        <div className="p-4 overflow-y-auto h-[calc(100%-60px)]">
          {viewRecords.length > 0 ? (
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
                  {viewRecords.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>{r.recorded_at}</TableCell>
                      <TableCell>{r.location || '—'}</TableCell>
                      <TableCell className="text-right font-medium">{r.amount}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="bg-gray-50 font-bold">
                    <TableCell>合计</TableCell>
                    <TableCell />
                    <TableCell className="text-right">{viewRecords.reduce((s, r) => s + r.amount, 0)}</TableCell>
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
