import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import DashboardPage from './pages/DashboardPage'
import CampaignsPage from './pages/CampaignsPage'
import CallsPage from './pages/CallsPage'
import LeadsPage from './pages/LeadsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import VoiceChatPage from './pages/VoiceChatPage'

function App() {
    return (
        <Layout>
            <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/voice-chat" element={<VoiceChatPage />} />
                <Route path="/campaigns" element={<CampaignsPage />} />
                <Route path="/calls" element={<CallsPage />} />
                <Route path="/leads" element={<LeadsPage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
            </Routes>
        </Layout>
    )
}

export default App
