export interface Account {
  id: number
  account_name: string
  password: string
  email: string
  server: string
  region: string
  class: string
  pin_code: string
  phone: string
  cloud_device: string
  location: string
  current_diamonds: number
  verify_code_url: string
  recovery_code: string
  created_at: string
}

export interface DiamondRecord {
  id: number
  account_id: number
  amount: number
  location: string
  recorded_at: string
  account?: Account
}

export interface Overview {
  total_diamonds: number
  total_records: number
  entry_count: number
  top_location: string | null
}

export interface Comparison {
  current_amount: number
  previous_amount: number
  change: number
  change_rate: number
}

export interface TrendPoint {
  date: string
  amount: number
  change_rate: number | null
}

export interface AccountTrend {
  account_id: number
  account_name: string
  trend: TrendPoint[]
}

export interface LocationDist {
  location: string
  total_amount: number
}

export interface GroupStat {
  name: string
  total_amount: number
}

export interface AccountRanking {
  account_id: number
  account_name: string
  cloud_device: string
  total_amount: number
  record_count: number
}

export interface CalendarEntry {
  date: string
  amount: number
}

export interface CrossStat {
  server: string
  region: string
  total_amount: number
}

export interface TrendComparePoint {
  date: string
  amount: number
  change_rate: number | null
  average: number
}

export interface AccountTrendCompare {
  account_id: number
  account_name: string
  trend: TrendComparePoint[]
}

export interface LowPerformer {
  account_id: number
  account_name: string
  cloud_device: string
  total_amount: number
  average: number
  ratio: number
}

export interface DiamondSnapshot {
  id: number
  account_id: number
  date: string
  diamonds: number
  change: number
}

export interface DiamondSale {
  id: number
  account_id: number
  account_name: string
  cloud_device: string
  phone: string
  diamonds_sold: number
  sale_date: string
  created_at: string
}

export interface DiamondSyncResponse {
  updated_count: number
  snapshot_count: number
}

export interface DiamondSellResponse {
  sold_count: number
  total_diamonds_sold: number
}
