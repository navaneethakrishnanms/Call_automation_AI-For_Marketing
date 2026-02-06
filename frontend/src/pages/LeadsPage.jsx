import { useState, useEffect } from 'react'
import {
    Search,
    Filter,
    Flame,
    Thermometer,
    Snowflake,
    Phone,
    PhoneOutgoing,
    Mail,
    User,
    Calendar,
    Edit2,
    X,
    ChevronLeft,
    ChevronRight,
    Download,
    Plus
} from 'lucide-react'
import { leadsAPI, campaignsAPI, callsAPI, testAPI } from '../api/client'
import { formatDate, formatPhoneNumber, getQualificationBadge } from '../utils/formatters'

function LeadsPage() {
    const [leads, setLeads] = useState([])
    const [campaigns, setCampaigns] = useState([])
    const [stats, setStats] = useState({ hot: 0, warm: 0, cold: 0, total: 0 })
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [activeTab, setActiveTab] = useState('')
    const [selectedLead, setSelectedLead] = useState(null)
    const [showCreateModal, setShowCreateModal] = useState(false)

    useEffect(() => {
        fetchCampaigns()
        fetchStats()
    }, [])

    useEffect(() => {
        fetchLeads()
    }, [page, activeTab])

    async function fetchCampaigns() {
        try {
            const data = await campaignsAPI.list({ page: 1, page_size: 100 })
            setCampaigns(data.items || [])
        } catch (error) {
            console.error('Failed to fetch campaigns:', error)
        }
    }

    async function fetchStats() {
        try {
            const data = await leadsAPI.stats()
            setStats(data)
        } catch (error) {
            console.error('Failed to fetch stats:', error)
        }
    }

    async function fetchLeads() {
        try {
            setLoading(true)
            const params = {
                page,
                page_size: 15,
                ...(activeTab && { qualification: activeTab })
            }
            const data = await leadsAPI.list(params)
            setLeads(data.items || [])
            setTotalPages(data.total_pages || 1)
        } catch (error) {
            console.error('Failed to fetch leads:', error)
        } finally {
            setLoading(false)
        }
    }

    async function handleUpdateLead(id, data) {
        try {
            await leadsAPI.update(id, data)
            fetchLeads()
            fetchStats()
            setSelectedLead(null)
        } catch (error) {
            console.error('Failed to update lead:', error)
        }
    }

    async function handleCreateLead(data) {
        try {
            await leadsAPI.create(data)
            fetchLeads()
            fetchStats()
            setShowCreateModal(false)
        } catch (error) {
            console.error('Failed to create lead:', error)
        }
    }

    async function initiateCall(lead) {
        if (!lead.phone) {
            alert('Lead has no phone number')
            return
        }

        const campaign = campaigns.find(c => c.id === lead.campaign_id)

        if (!confirm(`Call ${lead.name || lead.phone}?`)) {
            return
        }

        try {
            // Use test API for database-free calling
            const message = `Hello! This is a call from ${campaign?.name || 'Marketing AI'}. We are reaching out regarding our services.`
            const result = await testAPI.call(lead.phone, message)

            if (result.status === 'success') {
                alert(`Call initiated! Call SID: ${result.call_sid}`)
            } else {
                alert(`Call failed: ${result.message}`)
            }
        } catch (error) {
            console.error('Failed to initiate call:', error)
            alert('Failed to initiate call. Check console for details.')
        }
    }

    function exportToCSV() {
        const headers = ['Name', 'Phone', 'Email', 'Qualification', 'Interest Level', 'Created At']
        const rows = leads.map(lead => [
            lead.name || '',
            lead.phone,
            lead.email || '',
            lead.qualification,
            lead.interest_level || '',
            formatDate(lead.created_at)
        ])

        const csv = [headers, ...rows].map(row => row.join(',')).join('\n')
        const blob = new Blob([csv], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `leads-${new Date().toISOString().split('T')[0]}.csv`
        a.click()
    }

    const tabs = [
        { key: '', label: 'All', count: stats.total, icon: null },
        { key: 'hot', label: 'Hot', count: stats.hot, icon: Flame, color: 'text-rose-400' },
        { key: 'warm', label: 'Warm', count: stats.warm, icon: Thermometer, color: 'text-amber-400' },
        { key: 'cold', label: 'Cold', count: stats.cold, icon: Snowflake, color: 'text-sky-400' },
    ]

    return (
        <div className="space-y-6">
            {/* Tabs */}
            <div className="flex flex-wrap gap-2">
                {tabs.map(tab => (
                    <button
                        key={tab.key}
                        onClick={() => { setActiveTab(tab.key); setPage(1); }}
                        className={`
              flex items-center gap-2 px-4 py-2 rounded-xl transition-all
              ${activeTab === tab.key
                                ? 'bg-gradient-to-r from-primary-500/20 to-accent-500/20 text-white border border-primary-500/30'
                                : 'bg-white/5 text-white/60 hover:bg-white/10'
                            }
            `}
                    >
                        {tab.icon && <tab.icon className={`w-4 h-4 ${tab.color}`} />}
                        <span>{tab.label}</span>
                        <span className="px-2 py-0.5 rounded-full bg-white/10 text-xs">{tab.count}</span>
                    </button>
                ))}

                <button onClick={exportToCSV} className="ml-auto btn-secondary flex items-center gap-2">
                    <Download className="w-4 h-4" />
                    Export CSV
                </button>
                <button onClick={() => setShowCreateModal(true)} className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    New Lead
                </button>
            </div>

            {/* Leads Table */}
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
                                        <th className="p-4 font-medium">Contact</th>
                                        <th className="p-4 font-medium">Phone</th>
                                        <th className="p-4 font-medium">Campaign</th>
                                        <th className="p-4 font-medium">Qualification</th>
                                        <th className="p-4 font-medium">Interest</th>
                                        <th className="p-4 font-medium">Callback</th>
                                        <th className="p-4 font-medium">Created</th>
                                        <th className="p-4 font-medium">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {leads.length === 0 ? (
                                        <tr>
                                            <td colSpan={8} className="p-8 text-center text-white/50">
                                                No leads found
                                            </td>
                                        </tr>
                                    ) : (
                                        leads.map((lead) => (
                                            <tr key={lead.id} className="table-row">
                                                <td className="p-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500/30 to-accent-500/30 flex items-center justify-center">
                                                            <User className="w-5 h-5 text-white/70" />
                                                        </div>
                                                        <div>
                                                            <p className="text-white font-medium">{lead.name || 'Unknown'}</p>
                                                            {lead.email && (
                                                                <p className="text-white/50 text-sm">{lead.email}</p>
                                                            )}
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="p-4">
                                                    <div className="flex items-center gap-2 text-white/70">
                                                        <Phone className="w-4 h-4" />
                                                        {formatPhoneNumber(lead.phone)}
                                                    </div>
                                                </td>
                                                <td className="p-4 text-white/70">
                                                    {campaigns.find(c => c.id === lead.campaign_id)?.name || '-'}
                                                </td>
                                                <td className="p-4">
                                                    <span className={getQualificationBadge(lead.qualification)}>
                                                        {lead.qualification}
                                                    </span>
                                                </td>
                                                <td className="p-4">
                                                    {lead.interest_level ? (
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-16 h-2 bg-white/10 rounded-full overflow-hidden">
                                                                <div
                                                                    className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                                                                    style={{ width: `${lead.interest_level * 10}%` }}
                                                                />
                                                            </div>
                                                            <span className="text-white/50 text-sm">{lead.interest_level}/10</span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-white/30">-</span>
                                                    )}
                                                </td>
                                                <td className="p-4">
                                                    {lead.requires_callback ? (
                                                        <span className="badge badge-warm">Required</span>
                                                    ) : (
                                                        <span className="text-white/30">-</span>
                                                    )}
                                                </td>
                                                <td className="p-4 text-white/50 text-sm">
                                                    {formatDate(lead.created_at)}
                                                </td>
                                                <td className="p-4">
                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={() => initiateCall(lead)}
                                                            className="btn-icon bg-green-500/20 hover:bg-green-500/30 text-green-400"
                                                            title="Call Lead"
                                                        >
                                                            <PhoneOutgoing className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => setSelectedLead(lead)}
                                                            className="btn-icon"
                                                            title="Edit Lead"
                                                        >
                                                            <Edit2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
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

            {/* Edit Lead Modal */}
            {selectedLead && (
                <LeadEditModal
                    lead={selectedLead}
                    onClose={() => setSelectedLead(null)}
                    onSave={(data) => handleUpdateLead(selectedLead.id, data)}
                />
            )}

            {/* Create Lead Modal */}
            {showCreateModal && (
                <LeadCreateModal
                    campaigns={campaigns}
                    onClose={() => setShowCreateModal(false)}
                    onSave={handleCreateLead}
                />
            )}
        </div>
    )
}

function LeadEditModal({ lead, onClose, onSave }) {
    const [formData, setFormData] = useState({
        name: lead.name || '',
        email: lead.email || '',
        qualification: lead.qualification,
        interest_level: lead.interest_level || 5,
        notes: lead.notes || '',
        requires_callback: lead.requires_callback || false,
    })

    function handleChange(e) {
        const { name, value, type, checked } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }))
    }

    function handleSubmit(e) {
        e.preventDefault()
        onSave(formData)
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70" onClick={onClose} />
            <div className="relative glass-card w-full max-w-md p-6">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-white">Edit Lead</h2>
                    <button onClick={onClose} className="btn-icon">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm text-white/70 mb-2">Name</label>
                        <input
                            type="text"
                            name="name"
                            value={formData.name}
                            onChange={handleChange}
                            className="input-field"
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Email</label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            className="input-field"
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Qualification</label>
                        <select
                            name="qualification"
                            value={formData.qualification}
                            onChange={handleChange}
                            className="input-field"
                        >
                            <option value="hot">Hot</option>
                            <option value="warm">Warm</option>
                            <option value="cold">Cold</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">
                            Interest Level: {formData.interest_level}/10
                        </label>
                        <input
                            type="range"
                            name="interest_level"
                            min="1"
                            max="10"
                            value={formData.interest_level}
                            onChange={handleChange}
                            className="w-full"
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Notes</label>
                        <textarea
                            name="notes"
                            value={formData.notes}
                            onChange={handleChange}
                            rows={3}
                            className="input-field resize-none"
                        />
                    </div>

                    <div className="flex items-center gap-3">
                        <input
                            type="checkbox"
                            name="requires_callback"
                            checked={formData.requires_callback}
                            onChange={handleChange}
                            className="w-4 h-4 rounded"
                        />
                        <label className="text-white/70">Requires Callback</label>
                    </div>

                    <div className="flex gap-3 pt-4">
                        <button type="button" onClick={onClose} className="btn-secondary flex-1">
                            Cancel
                        </button>
                        <button type="submit" className="btn-primary flex-1">
                            Save Changes
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

function LeadCreateModal({ campaigns, onClose, onSave }) {
    const [formData, setFormData] = useState({
        name: '',
        phone: '',
        email: '',
        campaign_id: campaigns[0]?.id || '',
        qualification: 'warm',
        interest_level: 5,
        notes: '',
    })

    function handleChange(e) {
        const { name, value, type } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: type === 'number' ? parseInt(value) : value
        }))
    }

    function handleSubmit(e) {
        e.preventDefault()
        if (!formData.phone) {
            alert('Phone number is required')
            return
        }
        onSave(formData)
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70" onClick={onClose} />
            <div className="relative glass-card w-full max-w-md p-6">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-white">New Lead</h2>
                    <button onClick={onClose} className="btn-icon">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm text-white/70 mb-2">Name</label>
                        <input
                            type="text"
                            name="name"
                            value={formData.name}
                            onChange={handleChange}
                            className="input-field"
                            placeholder="John Doe"
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Phone *</label>
                        <input
                            type="tel"
                            name="phone"
                            value={formData.phone}
                            onChange={handleChange}
                            className="input-field"
                            placeholder="+1234567890"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Email</label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            className="input-field"
                            placeholder="john@example.com"
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Campaign</label>
                        <select
                            name="campaign_id"
                            value={formData.campaign_id}
                            onChange={handleChange}
                            className="input-field"
                        >
                            {campaigns.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Qualification</label>
                        <select
                            name="qualification"
                            value={formData.qualification}
                            onChange={handleChange}
                            className="input-field"
                        >
                            <option value="hot">Hot</option>
                            <option value="warm">Warm</option>
                            <option value="cold">Cold</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Notes</label>
                        <textarea
                            name="notes"
                            value={formData.notes}
                            onChange={handleChange}
                            rows={2}
                            className="input-field resize-none"
                            placeholder="Additional notes..."
                        />
                    </div>

                    <div className="flex gap-3 pt-4">
                        <button type="button" onClick={onClose} className="btn-secondary flex-1">
                            Cancel
                        </button>
                        <button type="submit" className="btn-primary flex-1">
                            Create Lead
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

export default LeadsPage
