import type {
  Account, DiamondRecord, Overview, Comparison, TrendPoint, AccountTrend,
  LocationDist, GroupStat, AccountRanking, CalendarEntry, CrossStat, AccountTrendCompare, LowPerformer,
  DiamondSnapshot, DiamondSale, DiamondSyncResponse, DiamondSellResponse,
} from './types'

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// Accounts
export const getAccounts = (params?: {
  search?: string; server?: string; region?: string
  email?: string; class_name?: string; cloud_device?: string
}) => {
  const sp = new URLSearchParams()
  if (params?.search) sp.set('search', params.search)
  if (params?.server) sp.set('server', params.server)
  if (params?.region) sp.set('region', params.region)
  if (params?.email) sp.set('email', params.email)
  if (params?.class_name) sp.set('class_name', params.class_name)
  if (params?.cloud_device) sp.set('cloud_device', params.cloud_device)
  const qs = sp.toString()
  return request<Account[]>(`/accounts${qs ? `?${qs}` : ''}`)
}

export const getAccountFilters = () =>
  request<{ servers: string[]; regions: string[] }>('/accounts/filters')

export const createAccount = (data: Partial<Account>) =>
  request<Account>('/accounts', { method: 'POST', body: JSON.stringify(data) })

export const updateAccount = (id: number, data: Partial<Account>) =>
  request<Account>(`/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) })

export const deleteAccount = (id: number) =>
  request<void>(`/accounts/${id}`, { method: 'DELETE' })

export const batchDeleteAccounts = (ids: number[]) =>
  request<void>('/accounts/batch-delete', { method: 'POST', body: JSON.stringify({ ids }) })

export const importAccountsExcel = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request<Account[]>('/accounts/import-excel', {
    method: 'POST',
    headers: {},  // let browser set Content-Type with boundary
    body: formData,
  })
}

// Records
export const getRecords = (params?: { date?: string; account_id?: number; location?: string }) => {
  const sp = new URLSearchParams()
  if (params?.date) sp.set('date', params.date)
  if (params?.account_id) sp.set('account_id', String(params.account_id))
  if (params?.location) sp.set('location', params.location)
  const qs = sp.toString()
  return request<DiamondRecord[]>(`/records${qs ? `?${qs}` : ''}`)
}

export const createRecords = (records: { account_id: number; amount: number; location: string; recorded_at: string }[]) =>
  request<DiamondRecord[]>('/records', { method: 'POST', body: JSON.stringify({ records }) })

export const deleteRecord = (id: number) =>
  request<void>(`/records/${id}`, { method: 'DELETE' })

export const getRecordDates = () =>
  request<string[]>('/records/dates')

// Analytics
export const getOverview = () =>
  request<Overview>('/analytics/overview')

export const getOverviewComparison = () =>
  request<Comparison>('/analytics/overview/comparison')

export const getOverviewYoY = () =>
  request<Comparison>('/analytics/overview/yoy')

export const getByLocation = () =>
  request<LocationDist[]>('/analytics/by-location')

export const getByServer = (date?: string) =>
  request<GroupStat[]>(`/analytics/by-server${date ? `?recorded_at=${date}` : ''}`)

export const getByClass = (date?: string) =>
  request<GroupStat[]>(`/analytics/by-class${date ? `?recorded_at=${date}` : ''}`)

export const getByRegion = () =>
  request<GroupStat[]>('/analytics/by-region')

export const getAccountRanking = (limit = 20, startDate?: string, endDate?: string) => {
  const sp = new URLSearchParams()
  sp.set('limit', String(limit))
  if (startDate) sp.set('start_date', startDate)
  if (endDate) sp.set('end_date', endDate)
  return request<AccountRanking[]>(`/analytics/account-ranking?${sp}`)
}

export const getDailyTrend = () =>
  request<TrendPoint[]>('/analytics/daily-trend')

export const getWeeklyTrend = () =>
  request<TrendPoint[]>('/analytics/weekly-trend')

export const getCalendarData = (year?: number) =>
  request<CalendarEntry[]>(`/analytics/calendar?year=${year || new Date().getFullYear()}`)

export const getAccountTrendCompare = (id: number) =>
  request<AccountTrendCompare>(`/analytics/accounts/${id}/trend-compare`)

export const getServerRegionCross = () =>
  request<CrossStat[]>('/analytics/server-region-cross')

export const getLowPerformers = (date?: string, threshold = 0.5) => {
  const sp = new URLSearchParams()
  sp.set('threshold', String(threshold))
  if (date) sp.set('recorded_at', date)
  return request<LowPerformer[]>(`/analytics/low-performers?${sp}`)
}

export const getLocationTrend = (location: string) =>
  request<TrendPoint[]>(`/analytics/by-location/${encodeURIComponent(location)}/trend`)

export const getAccountTrend = (id: number) =>
  request<AccountTrend>(`/analytics/accounts/${id}/trend`)

// Diamonds
export const syncDiamonds = (updates: { cloud_device: string; diamonds: number }[]) =>
  request<DiamondSyncResponse>('/diamonds/sync', {
    method: 'POST',
    body: JSON.stringify({ updates }),
  })

export const sellDiamonds = (accountIds: number[]) =>
  request<DiamondSellResponse>('/diamonds/sell', {
    method: 'POST',
    body: JSON.stringify({ account_ids: accountIds }),
  })

export const getDiamondSales = (params?: {
  start_date?: string; end_date?: string; account_id?: number
}) => {
  const sp = new URLSearchParams()
  if (params?.start_date) sp.set('start_date', params.start_date)
  if (params?.end_date) sp.set('end_date', params.end_date)
  if (params?.account_id) sp.set('account_id', String(params.account_id))
  const qs = sp.toString()
  return request<DiamondSale[]>(`/diamonds/sales${qs ? `?${qs}` : ''}`)
}

export const getAccountDiamondSnapshots = (accountId: number) =>
  request<DiamondSnapshot[]>(`/accounts/${accountId}/diamond-snapshots`)

export const getDiamondTrend = () =>
  request<TrendPoint[]>('/analytics/diamond-trend')
