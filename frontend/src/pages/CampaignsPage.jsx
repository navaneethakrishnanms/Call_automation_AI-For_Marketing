import { useState, useEffect } from 'react'
import {
    Plus,
    Search,
    Edit2,
    Trash2,
    MoreVertical,
    Phone,
    Users,
    FileText,
    X,
    Check,
    Upload
} from 'lucide-react'
import { campaignsAPI } from '../api/client'
import { formatDate, formatNumber } from '../utils/formatters'

function CampaignsPage() {
    const [campaigns, setCampaigns] = useState([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [editingCampaign, setEditingCampaign] = useState(null)
    const [searchQuery, setSearchQuery] = useState('')

    useEffect(() => {
        fetchCampaigns()
    }, [])

    async function fetchCampaigns() {
        try {
            const data = await campaignsAPI.list({ page: 1, page_size: 50 })
            setCampaigns(data.items || [])
        } catch (error) {
            console.error('Failed to fetch campaigns:', error)
        } finally {
            setLoading(false)
        }
    }

    const filteredCampaigns = campaigns.filter(c =>
        c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.description?.toLowerCase().includes(searchQuery.toLowerCase())
    )

    function handleCreate() {
        setEditingCampaign(null)
        setShowModal(true)
    }

    function handleEdit(campaign) {
        setEditingCampaign(campaign)
        setShowModal(true)
    }

    async function handleDelete(id) {
        if (!confirm('Are you sure you want to delete this campaign?')) return
        try {
            await campaignsAPI.delete(id)
            fetchCampaigns()
        } catch (error) {
            console.error('Failed to delete campaign:', error)
        }
    }

    async function handleSave(formData) {
        try {
            if (editingCampaign) {
                await campaignsAPI.update(editingCampaign.id, formData)
            } else {
                await campaignsAPI.create(formData)
            }
            setShowModal(false)
            fetchCampaigns()
        } catch (error) {
            console.error('Failed to save campaign:', error)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                    <input
                        type="text"
                        placeholder="Search campaigns..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="input-field pl-10"
                    />
                </div>
                <button onClick={handleCreate} className="btn-primary flex items-center gap-2">
                    <Plus className="w-5 h-5" />
                    <span>New Campaign</span>
                </button>
            </div>

            {/* Campaigns Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredCampaigns.length === 0 ? (
                    <div className="col-span-full glass-card p-12 text-center">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                            <FileText className="w-8 h-8 text-white/30" />
                        </div>
                        <h3 className="text-xl font-semibold text-white mb-2">No campaigns yet</h3>
                        <p className="text-white/50 mb-6">Create your first campaign to get started</p>
                        <button onClick={handleCreate} className="btn-primary">
                            Create Campaign
                        </button>
                    </div>
                ) : (
                    filteredCampaigns.map((campaign) => (
                        <div key={campaign.id} className="glass-card glass-card-hover p-6">
                            <div className="flex items-start justify-between mb-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-white">{campaign.name}</h3>
                                    <p className="text-sm text-white/50 mt-1 line-clamp-2">
                                        {campaign.description || 'No description'}
                                    </p>
                                </div>
                                <span className={`badge ${campaign.is_active ? 'badge-active' : 'badge-inactive'}`}>
                                    {campaign.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div className="flex items-center gap-2 text-white/60">
                                    <Phone className="w-4 h-4" />
                                    <span className="text-sm">{formatNumber(campaign.total_calls)} calls</span>
                                </div>
                                <div className="flex items-center gap-2 text-white/60">
                                    <Users className="w-4 h-4" />
                                    <span className="text-sm">{formatNumber(campaign.total_leads)} leads</span>
                                </div>
                            </div>

                            <div className="flex items-center gap-2 text-sm text-white/40 mb-4">
                                <FileText className="w-4 h-4" />
                                <span>{campaign.faqs?.length || 0} FAQs loaded</span>
                            </div>

                            <div className="flex gap-2 pt-4 border-t border-white/10">
                                <button
                                    onClick={() => handleEdit(campaign)}
                                    className="btn-secondary flex-1 flex items-center justify-center gap-2 py-2"
                                >
                                    <Edit2 className="w-4 h-4" />
                                    Edit
                                </button>
                                <button
                                    onClick={() => handleDelete(campaign.id)}
                                    className="btn-icon text-rose-400 hover:bg-rose-500/20"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <CampaignModal
                    campaign={editingCampaign}
                    onClose={() => setShowModal(false)}
                    onSave={handleSave}
                />
            )}
        </div>
    )
}

function CampaignModal({ campaign, onClose, onSave }) {
    const [formData, setFormData] = useState({
        name: campaign?.name || '',
        description: campaign?.description || '',
        greeting_message: campaign?.greeting_message || "Hello! Thank you for your interest. How can I help you today?",
        farewell_message: campaign?.farewell_message || "Thank you for calling! Have a wonderful day!",
        is_active: campaign?.is_active ?? true,
        faqs: campaign?.faqs || [],
    })
    const [newFaq, setNewFaq] = useState({ question: '', answer: '', keywords: [] })
    const [keywordInput, setKeywordInput] = useState('')

    function handleChange(e) {
        const { name, value, type, checked } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }))
    }

    function handleAddFaq() {
        if (!newFaq.question || !newFaq.answer) return
        setFormData(prev => ({
            ...prev,
            faqs: [...prev.faqs, { ...newFaq }]
        }))
        setNewFaq({ question: '', answer: '', keywords: [] })
    }

    function handleRemoveFaq(index) {
        setFormData(prev => ({
            ...prev,
            faqs: prev.faqs.filter((_, i) => i !== index)
        }))
    }

    function handleAddKeyword(e) {
        if (e.key === 'Enter' && keywordInput.trim()) {
            setNewFaq(prev => ({
                ...prev,
                keywords: [...prev.keywords, keywordInput.trim()]
            }))
            setKeywordInput('')
        }
    }

    function handleSubmit(e) {
        e.preventDefault()
        onSave(formData)
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70" onClick={onClose} />
            <div className="relative glass-card w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-white">
                        {campaign ? 'Edit Campaign' : 'Create Campaign'}
                    </h2>
                    <button onClick={onClose} className="btn-icon">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm text-white/70 mb-2">Campaign Name *</label>
                        <input
                            type="text"
                            name="name"
                            value={formData.name}
                            onChange={handleChange}
                            className="input-field"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Description</label>
                        <textarea
                            name="description"
                            value={formData.description}
                            onChange={handleChange}
                            rows={3}
                            className="input-field resize-none"
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Greeting Message</label>
                        <textarea
                            name="greeting_message"
                            value={formData.greeting_message}
                            onChange={handleChange}
                            rows={2}
                            className="input-field resize-none"
                        />
                    </div>

                    <div>
                        <label className="block text-sm text-white/70 mb-2">Farewell Message</label>
                        <textarea
                            name="farewell_message"
                            value={formData.farewell_message}
                            onChange={handleChange}
                            rows={2}
                            className="input-field resize-none"
                        />
                    </div>

                    <div className="flex items-center gap-3">
                        <input
                            type="checkbox"
                            name="is_active"
                            checked={formData.is_active}
                            onChange={handleChange}
                            className="w-4 h-4 rounded"
                        />
                        <label className="text-white/70">Campaign Active</label>
                    </div>

                    {/* FAQs Section */}
                    <div className="border-t border-white/10 pt-6">
                        <h3 className="text-lg font-semibold text-white mb-4">FAQs ({formData.faqs.length})</h3>

                        {/* Existing FAQs */}
                        <div className="space-y-3 mb-4">
                            {formData.faqs.map((faq, index) => (
                                <div key={index} className="p-3 bg-white/5 rounded-lg">
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <p className="text-white font-medium">{faq.question}</p>
                                            <p className="text-white/50 text-sm mt-1">{faq.answer}</p>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => handleRemoveFaq(index)}
                                            className="text-rose-400 hover:text-rose-300"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Add New FAQ */}
                        <div className="space-y-3 p-4 bg-white/5 rounded-lg">
                            <input
                                type="text"
                                placeholder="Question"
                                value={newFaq.question}
                                onChange={(e) => setNewFaq(prev => ({ ...prev, question: e.target.value }))}
                                className="input-field"
                            />
                            <textarea
                                placeholder="Answer"
                                value={newFaq.answer}
                                onChange={(e) => setNewFaq(prev => ({ ...prev, answer: e.target.value }))}
                                rows={2}
                                className="input-field resize-none"
                            />
                            <input
                                type="text"
                                placeholder="Keywords (press Enter to add)"
                                value={keywordInput}
                                onChange={(e) => setKeywordInput(e.target.value)}
                                onKeyDown={handleAddKeyword}
                                className="input-field"
                            />
                            {newFaq.keywords.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {newFaq.keywords.map((kw, i) => (
                                        <span key={i} className="badge badge-active">{kw}</span>
                                    ))}
                                </div>
                            )}
                            <button
                                type="button"
                                onClick={handleAddFaq}
                                className="btn-secondary w-full"
                            >
                                Add FAQ
                            </button>
                        </div>
                    </div>

                    <div className="flex gap-3 pt-4">
                        <button type="button" onClick={onClose} className="btn-secondary flex-1">
                            Cancel
                        </button>
                        <button type="submit" className="btn-primary flex-1">
                            {campaign ? 'Save Changes' : 'Create Campaign'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

export default CampaignsPage
