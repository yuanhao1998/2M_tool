import { useState } from 'react'
import Layout from './components/Layout'
import AccountsPage from './pages/AccountsPage'
import RecordsPage from './pages/RecordsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import AnalysisPage from './pages/AnalysisPage'
import DiamondPage from './pages/DiamondPage'

export default function App() {
  const [page, setPage] = useState('accounts')

  return (
    <Layout active={page} onNavigate={setPage}>
      {page === 'accounts' && <AccountsPage />}
      {page === 'records' && <RecordsPage />}
      {page === 'analytics' && <AnalyticsPage />}
      {page === 'diamond' && <DiamondPage />}
      {page === 'analysis' && <AnalysisPage />}
    </Layout>
  )
}
