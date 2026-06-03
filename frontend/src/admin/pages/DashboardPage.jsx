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

    Snowflake,
    Globe
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
import { analyticsAPI, callsAPI } from '../../shared/services/client'
import { formatDuration, formatRelativeTime, formatPercentage } from '../../shared/utils/formatters'

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6']
const CHART_COLORS = ['#0ea5e9', '#d946ef', '#22c55e', '#f59e0b']

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

    const [languageData, setLanguageData] = useState([])
    const [dateRange, setDateRange] = useState(7)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true)
                const [overviewData, callsData, langData] = await Promise.all([
                    analyticsAPI.overview(),
                    analyticsAPI.calls(dateRange),
                    analyticsAPI.languages()
                ])
                setStats(overviewData)
                setCallMetrics(callsData)
                setLanguageData(langData || [])
            } catch (error) {
                console.error('Failed to fetch dashboard data:', error)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [dateRange])

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
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-slide-up" style={{ animationDelay: '100ms' }}>
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
                    title="Avg. Duration"
                    value={formatDuration(stats?.avg_call_duration || 0)}
                    subtitle="Per call"
                    icon={Clock}
                />
            </div>

            {/* Charts Row */}
            <div className="flex justify-end animate-slide-up" style={{ animationDelay: '150ms' }}>
                <select
                    value={dateRange}
                    onChange={(e) => setDateRange(Number(e.target.value))}
                    className="input-field max-w-[200px]"
                >
                    <option value={7}>Last 7 Days</option>
                    <option value={15}>Last 15 Days</option>
                    <option value={30}>Last 30 Days</option>
                    <option value={90}>All Days</option>
                </select>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '200ms', opacity: 0, animationFillMode: 'forwards' }}>
                {/* Call Volume Chart */}
                <div className="lg:col-span-2 glass-card p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">
                        Call Volume ({dateRange === 90 ? 'All Days' : `Last ${dateRange} Days`})
                    </h3>
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
                                    itemStyle={{ color: '#fff' }}
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
                                    itemStyle={{ color: '#fff' }}
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

            {/* Charts Row 2 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '250ms', opacity: 0, animationFillMode: 'forwards' }}>
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
                                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: '8px'
                                    }}
                                    itemStyle={{ color: '#fff' }}
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
                                        style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
                                    />
                                    <span className="text-white/70 capitalize">{lang.language}</span>
                                </div>
                                <span className="text-white/50">{(lang.percentage || 0).toFixed(1)}%</span>
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
                                    itemStyle={{ color: '#fff' }}
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

export default DashboardPage

