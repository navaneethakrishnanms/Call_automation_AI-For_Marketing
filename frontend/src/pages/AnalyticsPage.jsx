import { useState, useEffect } from 'react'
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar,
    PieChart,
    Pie,
    Cell,
    AreaChart,
    Area
} from 'recharts'
import { Calendar, Globe } from 'lucide-react'
import { analyticsAPI, campaignsAPI } from '../api/client'

function AnalyticsPage() {
    const [campaigns, setCampaigns] = useState([])
    const [selectedCampaign, setSelectedCampaign] = useState('')
    const [dateRange, setDateRange] = useState(7)
    const [loading, setLoading] = useState(true)

    const [callMetrics, setCallMetrics] = useState([])
    const [leadTrends, setLeadTrends] = useState([])
    const [languageData, setLanguageData] = useState([])
    const [overviewStats, setOverviewStats] = useState(null)

    useEffect(() => {
        fetchCampaigns()
    }, [])

    useEffect(() => {
        fetchAllData()
    }, [selectedCampaign, dateRange])

    async function fetchCampaigns() {
        try {
            const data = await campaignsAPI.list({ page: 1, page_size: 100 })
            setCampaigns(data.items || [])
        } catch (error) {
            console.error('Failed to fetch campaigns:', error)
        }
    }

    async function fetchAllData() {
        try {
            setLoading(true)
            const campaignId = selectedCampaign || undefined

            const [overview, calls, leads, languages] = await Promise.all([
                analyticsAPI.overview(campaignId),
                analyticsAPI.calls(dateRange, campaignId),
                analyticsAPI.leads(dateRange, campaignId),
                analyticsAPI.languages(campaignId)
            ])

            setOverviewStats(overview)
            setCallMetrics(calls)
            setLeadTrends(leads)
            setLanguageData(languages)
        } catch (error) {
            console.error('Failed to fetch analytics:', error)
        } finally {
            setLoading(false)
        }
    }

    const COLORS = ['#0ea5e9', '#d946ef', '#22c55e', '#f59e0b']
    const LEAD_COLORS = { hot: '#ef4444', warm: '#f59e0b', cold: '#3b82f6' }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Filters */}
            <div className="glass-card p-4">
                <div className="flex flex-wrap gap-4">
                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-sm text-white/50 mb-1">Campaign</label>
                        <select
                            value={selectedCampaign}
                            onChange={(e) => setSelectedCampaign(e.target.value)}
                            className="input-field"
                        >
                            <option value="">All Campaigns</option>
                            {campaigns.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="min-w-[150px]">
                        <label className="block text-sm text-white/50 mb-1">Date Range</label>
                        <select
                            value={dateRange}
                            onChange={(e) => setDateRange(Number(e.target.value))}
                            className="input-field"
                        >
                            <option value={7}>Last 7 Days</option>
                            <option value={14}>Last 14 Days</option>
                            <option value={30}>Last 30 Days</option>
                            <option value={90}>Last 90 Days</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass-card p-4">
                    <p className="text-white/50 text-sm">Total Calls</p>
                    <p className="text-2xl font-bold text-white">{overviewStats?.total_calls || 0}</p>
                </div>
                <div className="glass-card p-4">
                    <p className="text-white/50 text-sm">Conversion Rate</p>
                    <p className="text-2xl font-bold text-emerald-400">
                        {(overviewStats?.conversion_rate || 0).toFixed(1)}%
                    </p>
                </div>
                <div className="glass-card p-4">
                    <p className="text-white/50 text-sm">Avg Duration</p>
                    <p className="text-2xl font-bold text-white">
                        {Math.round(overviewStats?.avg_call_duration || 0)}s
                    </p>
                </div>
                <div className="glass-card p-4">
                    <p className="text-white/50 text-sm">Hot Leads</p>
                    <p className="text-2xl font-bold text-rose-400">{overviewStats?.hot_leads || 0}</p>
                </div>
            </div>

            {/* Charts Row 1 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Call Volume Trend */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Call Volume Trend</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={callMetrics}>
                                <defs>
                                    <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.5)"
                                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', {
                                        month: 'short',
                                        day: 'numeric'
                                    })}
                                />
                                <YAxis stroke="rgba(255,255,255,0.5)" />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: '8px'
                                    }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="total_calls"
                                    stroke="#0ea5e9"
                                    fillOpacity={1}
                                    fill="url(#colorCalls)"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Lead Qualification Trend */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Lead Qualification Trend</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={leadTrends}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.5)"
                                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', {
                                        month: 'short',
                                        day: 'numeric'
                                    })}
                                />
                                <YAxis stroke="rgba(255,255,255,0.5)" />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: '8px'
                                    }}
                                />
                                <Bar dataKey="hot" stackId="a" fill={LEAD_COLORS.hot} />
                                <Bar dataKey="warm" stackId="a" fill={LEAD_COLORS.warm} />
                                <Bar dataKey="cold" stackId="a" fill={LEAD_COLORS.cold} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="flex justify-center gap-6 mt-4">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: LEAD_COLORS.hot }} />
                            <span className="text-sm text-white/70">Hot</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: LEAD_COLORS.warm }} />
                            <span className="text-sm text-white/70">Warm</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: LEAD_COLORS.cold }} />
                            <span className="text-sm text-white/70">Cold</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts Row 2 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Language Distribution */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Globe className="w-5 h-5 text-primary-400" />
                        Language Distribution
                    </h3>
                    <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={languageData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={40}
                                    outerRadius={70}
                                    paddingAngle={5}
                                    dataKey="count"
                                    nameKey="language"
                                >
                                    {languageData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: '8px'
                                    }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="space-y-2 mt-4">
                        {languageData.map((lang, index) => (
                            <div key={lang.language} className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-3 h-3 rounded-full"
                                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                                    />
                                    <span className="text-white/70 capitalize">{lang.language}</span>
                                </div>
                                <span className="text-white/50">{lang.percentage.toFixed(1)}%</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Call Duration Distribution */}
                <div className="lg:col-span-2 glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Average Call Duration Trend</h3>
                    <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={callMetrics}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.5)"
                                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', {
                                        month: 'short',
                                        day: 'numeric'
                                    })}
                                />
                                <YAxis stroke="rgba(255,255,255,0.5)" />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: '8px'
                                    }}
                                    formatter={(value) => [`${value}s`, 'Avg Duration']}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="avg_duration"
                                    stroke="#d946ef"
                                    strokeWidth={2}
                                    dot={{ fill: '#d946ef', strokeWidth: 2 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default AnalyticsPage
