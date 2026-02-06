import { useState, useEffect } from 'react'
import {
    Search,
    Filter,
    Phone,
    Play,
    Clock,
    Globe,
    ChevronLeft,
    ChevronRight,
    X,
    MessageSquare
} from 'lucide-react'
import { callsAPI, campaignsAPI } from '../api/client'
import { formatDuration, formatDate, formatPhoneNumber, getQualificationBadge, getStatusBadge, getLanguageDisplay } from '../utils/formatters'

function CallsPage() {
    const [calls, setCalls] = useState([])
    const [campaigns, setCampaigns] = useState([])
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [filters, setFilters] = useState({
        campaign_id: '',
        status: '',
        language: '',
    })
    const [selectedCall, setSelectedCall] = useState(null)

    useEffect(() => {
        fetchCampaigns()
    }, [])

    useEffect(() => {
        fetchCalls()
    }, [page, filters])

    async function fetchCampaigns() {
        try {
            const data = await campaignsAPI.list({ page: 1, page_size: 100 })
            setCampaigns(data.items || [])
        } catch (error) {
            console.error('Failed to fetch campaigns:', error)
        }
    }

    async function fetchCalls() {
        try {
            setLoading(true)
            const params = {
                page,
                page_size: 15,
                ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v))
            }
            const data = await callsAPI.list(params)
            setCalls(data.items || [])
            setTotalPages(data.total_pages || 1)
        } catch (error) {
            console.error('Failed to fetch calls:', error)
        } finally {
            setLoading(false)
        }
    }

    function handleFilterChange(key, value) {
        setFilters(prev => ({ ...prev, [key]: value }))
        setPage(1)
    }

    return (
        <div className="space-y-6">
            {/* Filters */}
            <div className="glass-card p-4">
                <div className="flex flex-wrap gap-4">
                    <div className="flex-1 min-w-[200px]">
                        <label className="block text-sm text-white/50 mb-1">Campaign</label>
                        <select
                            value={filters.campaign_id}
                            onChange={(e) => handleFilterChange('campaign_id', e.target.value)}
                            className="input-field"
                        >
                            <option value="">All Campaigns</option>
                            {campaigns.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="min-w-[150px]">
                        <label className="block text-sm text-white/50 mb-1">Status</label>
                        <select
                            value={filters.status}
                            onChange={(e) => handleFilterChange('status', e.target.value)}
                            className="input-field"
                        >
                            <option value="">All Status</option>
                            <option value="completed">Completed</option>
                            <option value="in_progress">In Progress</option>
                            <option value="failed">Failed</option>
                            <option value="no_answer">No Answer</option>
                        </select>
                    </div>
                    <div className="min-w-[150px]">
                        <label className="block text-sm text-white/50 mb-1">Language</label>
                        <select
                            value={filters.language}
                            onChange={(e) => handleFilterChange('language', e.target.value)}
                            className="input-field"
                        >
                            <option value="">All Languages</option>
                            <option value="english">English</option>
                            <option value="tamil">Tamil</option>
                            <option value="tanglish">Tanglish</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Calls Table */}
            <div className="glass-card overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : (
                    <>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-white/5">
                                    <tr className="text-left text-white/50 text-sm">
                                        <th className="p-4 font-medium">Phone Number</th>
                                        <th className="p-4 font-medium">Campaign</th>
                                        <th className="p-4 font-medium">Duration</th>
                                        <th className="p-4 font-medium">Language</th>
                                        <th className="p-4 font-medium">Lead</th>
                                        <th className="p-4 font-medium">Status</th>
                                        <th className="p-4 font-medium">Date</th>
                                        <th className="p-4 font-medium">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {calls.length === 0 ? (
                                        <tr>
                                            <td colSpan={8} className="p-8 text-center text-white/50">
                                                No calls found
                                            </td>
                                        </tr>
                                    ) : (
                                        calls.map((call) => (
                                            <tr key={call.id} className="table-row">
                                                <td className="p-4">
                                                    <div className="flex items-center gap-2">
                                                        <Phone className="w-4 h-4 text-primary-400" />
                                                        <span className="text-white">{formatPhoneNumber(call.phone_number)}</span>
                                                    </div>
                                                </td>
                                                <td className="p-4 text-white/70">
                                                    {campaigns.find(c => c.id === call.campaign_id)?.name || '-'}
                                                </td>
                                                <td className="p-4">
                                                    <div className="flex items-center gap-2 text-white/70">
                                                        <Clock className="w-4 h-4" />
                                                        {formatDuration(call.duration_seconds)}
                                                    </div>
                                                </td>
                                                <td className="p-4">
                                                    <div className="flex items-center gap-2">
                                                        <Globe className="w-4 h-4 text-white/50" />
                                                        <span className="text-white/70">{getLanguageDisplay(call.language_detected)}</span>
                                                    </div>
                                                </td>
                                                <td className="p-4">
                                                    <span className={getQualificationBadge(call.lead_qualification)}>
                                                        {call.lead_qualification || 'N/A'}
                                                    </span>
                                                </td>
                                                <td className="p-4">
                                                    <span className={getStatusBadge(call.status)}>
                                                        {call.status}
                                                    </span>
                                                </td>
                                                <td className="p-4 text-white/50 text-sm">
                                                    {formatDate(call.started_at)}
                                                </td>
                                                <td className="p-4">
                                                    <button
                                                        onClick={() => setSelectedCall(call)}
                                                        className="btn-icon"
                                                        title="View Details"
                                                    >
                                                        <MessageSquare className="w-4 h-4" />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        <div className="flex items-center justify-between p-4 border-t border-white/10">
                            <p className="text-sm text-white/50">
                                Page {page} of {totalPages}
                            </p>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="btn-icon disabled:opacity-50"
                                >
                                    <ChevronLeft className="w-5 h-5" />
                                </button>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page === totalPages}
                                    className="btn-icon disabled:opacity-50"
                                >
                                    <ChevronRight className="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* Call Detail Modal */}
            {selectedCall && (
                <CallDetailModal
                    call={selectedCall}
                    campaign={campaigns.find(c => c.id === selectedCall.campaign_id)}
                    onClose={() => setSelectedCall(null)}
                />
            )}
        </div>
    )
}

function CallDetailModal({ call, campaign, onClose }) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70" onClick={onClose} />
            <div className="relative glass-card w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-white">Call Details</h2>
                    <button onClick={onClose} className="btn-icon">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="space-y-6">
                    {/* Call Info */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <p className="text-sm text-white/50">Phone Number</p>
                            <p className="text-white font-medium">{formatPhoneNumber(call.phone_number)}</p>
                        </div>
                        <div>
                            <p className="text-sm text-white/50">Campaign</p>
                            <p className="text-white font-medium">{campaign?.name || '-'}</p>
                        </div>
                        <div>
                            <p className="text-sm text-white/50">Duration</p>
                            <p className="text-white font-medium">{formatDuration(call.duration_seconds)}</p>
                        </div>
                        <div>
                            <p className="text-sm text-white/50">Language</p>
                            <p className="text-white font-medium">{getLanguageDisplay(call.language_detected)}</p>
                        </div>
                        <div>
                            <p className="text-sm text-white/50">Lead Qualification</p>
                            <span className={getQualificationBadge(call.lead_qualification)}>
                                {call.lead_qualification || 'N/A'}
                            </span>
                        </div>
                        <div>
                            <p className="text-sm text-white/50">Lead Score</p>
                            <p className="text-white font-medium">
                                {call.lead_score ? `${(call.lead_score * 100).toFixed(0)}%` : 'N/A'}
                            </p>
                        </div>
                    </div>

                    {/* Transcript */}
                    <div>
                        <p className="text-sm text-white/50 mb-2">Transcript</p>
                        <div className="p-4 bg-white/5 rounded-lg max-h-64 overflow-y-auto">
                            {call.transcript ? (
                                <pre className="text-white/80 text-sm whitespace-pre-wrap font-sans">
                                    {call.transcript}
                                </pre>
                            ) : (
                                <p className="text-white/40 text-center py-4">No transcript available</p>
                            )}
                        </div>
                    </div>

                    {/* Timestamps */}
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/10">
                        <div>
                            <p className="text-sm text-white/50">Started At</p>
                            <p className="text-white/70 text-sm">{formatDate(call.started_at)}</p>
                        </div>
                        <div>
                            <p className="text-sm text-white/50">Ended At</p>
                            <p className="text-white/70 text-sm">{call.ended_at ? formatDate(call.ended_at) : '-'}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default CallsPage
