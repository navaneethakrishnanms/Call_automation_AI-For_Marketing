import { useState, useEffect } from 'react'
import {
    Phone,
    Users,
    TrendingUp,
    Clock,
    ArrowUpRight,
    ArrowDownRight,
    Flame,
    Thermometer,
    Snowflake
} from 'lucide-react'
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell
} from 'recharts'
import { analyticsAPI, callsAPI } from '../api/client'
import { formatDuration, formatRelativeTime, formatPercentage } from '../utils/formatters'

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6']

function StatCard({ title, value, subtitle, icon: Icon, trend, trendUp }) {
    return (
        <div className="stat-card glass-card-hover">
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-white/60 text-sm mb-1">{title}</p>
                    <p className="text-3xl font-bold text-white">{value}</p>
                    {subtitle && (
                        <p className="text-white/50 text-sm mt-1">{subtitle}</p>
                    )}
                </div>
                <div className="p-3 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-500/20">
                    <Icon className="w-6 h-6 text-primary-400" />
                </div>
            </div>
            {trend !== undefined && (
                <div className={`flex items-center gap-1 mt-3 text-sm ${trendUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {trendUp ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                    <span>{trend}% from last week</span>
                </div>
            )}
        </div>
    )
}

function DashboardPage() {
    const [stats, setStats] = useState(null)
    const [callMetrics, setCallMetrics] = useState([])
    const [recentCalls, setRecentCalls] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function fetchData() {
            try {
                const [overviewData, callsData, recentCallsData] = await Promise.all([
                    analyticsAPI.overview(),
                    analyticsAPI.calls(7),
                    callsAPI.list({ page: 1, page_size: 5 })
                ])
                setStats(overviewData)
                setCallMetrics(callsData)
                setRecentCalls(recentCallsData.items || [])
            } catch (error) {
                console.error('Failed to fetch dashboard data:', error)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [])

    const leadPieData = stats ? [
        { name: 'Hot', value: stats.hot_leads, color: '#ef4444' },
        { name: 'Warm', value: stats.warm_leads, color: '#f59e0b' },
        { name: 'Cold', value: stats.cold_leads, color: '#3b82f6' },
    ] : []

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    title="Total Calls"
                    value={stats?.total_calls || 0}
                    subtitle="This month"
                    icon={Phone}
                    trend={12}
                    trendUp={true}
                />
                <StatCard
                    title="Total Leads"
                    value={stats?.total_leads || 0}
                    subtitle={`${stats?.hot_leads || 0} hot leads`}
                    icon={Users}
                    trend={8}
                    trendUp={true}
                />
                <StatCard
                    title="Conversion Rate"
                    value={formatPercentage(stats?.conversion_rate || 0)}
                    subtitle="Hot leads / Total calls"
                    icon={TrendingUp}
                    trend={5}
                    trendUp={true}
                />
                <StatCard
                    title="Avg. Duration"
                    value={formatDuration(stats?.avg_call_duration || 0)}
                    subtitle="Per call"
                    icon={Clock}
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Call Volume Chart */}
                <div className="lg:col-span-2 glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Call Volume (Last 7 Days)</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={callMetrics}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis
                                    dataKey="date"
                                    stroke="rgba(255,255,255,0.5)"
                                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { weekday: 'short' })}
                                />
                                <YAxis stroke="rgba(255,255,255,0.5)" />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: '8px'
                                    }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="total_calls"
                                    stroke="#0ea5e9"
                                    strokeWidth={2}
                                    dot={{ fill: '#0ea5e9', strokeWidth: 2 }}
                                    activeDot={{ r: 6, fill: '#0ea5e9' }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="completed_calls"
                                    stroke="#d946ef"
                                    strokeWidth={2}
                                    dot={{ fill: '#d946ef', strokeWidth: 2 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Lead Distribution Pie */}
                <div className="glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Lead Distribution</h3>
                    <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={leadPieData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={50}
                                    outerRadius={70}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {leadPieData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
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
                    {/* Legend */}
                    <div className="flex justify-center gap-4 mt-4">
                        <div className="flex items-center gap-2">
                            <Flame className="w-4 h-4 text-rose-500" />
                            <span className="text-sm text-white/70">Hot ({stats?.hot_leads || 0})</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Thermometer className="w-4 h-4 text-amber-500" />
                            <span className="text-sm text-white/70">Warm ({stats?.warm_leads || 0})</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Snowflake className="w-4 h-4 text-sky-500" />
                            <span className="text-sm text-white/70">Cold ({stats?.cold_leads || 0})</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Recent Calls */}
            <div className="glass-card p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Recent Calls</h3>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="text-left text-white/50 text-sm border-b border-white/10">
                                <th className="pb-3 font-medium">Phone</th>
                                <th className="pb-3 font-medium">Duration</th>
                                <th className="pb-3 font-medium">Language</th>
                                <th className="pb-3 font-medium">Lead Score</th>
                                <th className="pb-3 font-medium">Status</th>
                                <th className="pb-3 font-medium">Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recentCalls.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="py-8 text-center text-white/50">
                                        No calls yet. Start a campaign to see data here.
                                    </td>
                                </tr>
                            ) : (
                                recentCalls.map((call) => (
                                    <tr key={call.id} className="table-row">
                                        <td className="py-3 text-white">{call.phone_number}</td>
                                        <td className="py-3 text-white/70">{formatDuration(call.duration_seconds)}</td>
                                        <td className="py-3">
                                            <span className="badge badge-active">{call.language_detected || 'Unknown'}</span>
                                        </td>
                                        <td className="py-3">
                                            <span className={`badge ${call.lead_qualification === 'hot' ? 'badge-hot' :
                                                    call.lead_qualification === 'warm' ? 'badge-warm' : 'badge-cold'
                                                }`}>
                                                {call.lead_qualification || 'N/A'}
                                            </span>
                                        </td>
                                        <td className="py-3">
                                            <span className={`badge ${call.status === 'completed' ? 'badge-active' : 'badge-inactive'
                                                }`}>
                                                {call.status}
                                            </span>
                                        </td>
                                        <td className="py-3 text-white/50">{formatRelativeTime(call.started_at)}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}

export default DashboardPage
