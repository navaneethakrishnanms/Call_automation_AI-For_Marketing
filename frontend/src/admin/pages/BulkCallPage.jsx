import { useState, useCallback, useEffect } from 'react'
import {
    Upload,
    FileSpreadsheet,
    Phone,
    CheckCircle2,
    XCircle,
    Loader2,
    Download,
    AlertTriangle,
    Users,
    Zap,
    ArrowRight,
    X,
    History,
    ChevronDown,
    ChevronRight
} from 'lucide-react'
import api, { bulkCallAPI } from '../../shared/services/client'

function BulkCallPage() {
    const [file, setFile] = useState(null)
    const [dragActive, setDragActive] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)
    const [intentHistory, setIntentHistory] = useState([])
    const [historyLoading, setHistoryLoading] = useState(false)
    const [downloadUrl, setDownloadUrl] = useState(null)
    const [intentResults, setIntentResults] = useState([])
    const [intentProgress, setIntentProgress] = useState(null) // { done: N, total: M }

    // Load intent history on mount
    useEffect(() => {
        fetchIntentHistory()
    }, [])

    async function fetchIntentHistory() {
        try {
            setHistoryLoading(true)
            const data = await bulkCallAPI.intentHistory()
            setIntentHistory(data.intents || [])
            setDownloadUrl(data.downloadUrl || null)
        } catch (err) {
            console.error('Failed to load intent history:', err)
        } finally {
            setHistoryLoading(false)
        }
    }

    // ── Drag & drop ──────────────────────────────────────────────────────
    const handleDrag = useCallback((e) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true)
        else if (e.type === 'dragleave') setDragActive(false)
    }, [])

    const handleDrop = useCallback((e) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)
        if (e.dataTransfer.files?.[0]) handleFileSelect(e.dataTransfer.files[0])
    }, [])

    const handleFileSelect = (f) => {
        const ext = f.name.split('.').pop().toLowerCase()
        if (!['xlsx', 'xls', 'csv'].includes(ext)) {
            setError('Please upload an .xlsx, .xls, or .csv file.')
            return
        }
        setFile(f)
        setError(null)
        setResult(null)
        setIntentResults([])
        setIntentProgress(null)
    }

    const clearFile = () => {
        setFile(null)
        setResult(null)
        setError(null)
        setIntentResults([])
        setIntentProgress(null)
    }

    // ── Upload ───────────────────────────────────────────────────────────
    const handleUpload = async () => {
        if (!file) return
        setUploading(true)
        setError(null)
        setResult(null)
        setIntentResults([])
        setIntentProgress(null)

        const formData = new FormData()
        formData.append('file', file)

        try {
            const response = await api.post('/bulk-call/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                timeout: 300000,
                baseURL: '/bulk-api',
            })
            setResult(response)
            setUploading(false)

            // Now classify intent for each successful call individually
            const calls = response.successful_calls || []
            if (calls.length > 0) {
                setIntentProgress({ done: 0, total: calls.length })
                const results = []

                for (const call of calls) {
                    try {
                        const intent = await bulkCallAPI.classifyIntent(
                            call.call_id,
                            call.phone,
                            call.name
                        )
                        results.push({ name: call.name, phone: call.phone, call_id: call.call_id, ...intent })
                    } catch (err) {
                        results.push({
                            name: call.name, phone: call.phone, call_id: call.call_id,
                            intent: 'Needs Follow-up', confidence_score: 0,
                            description: err.message || 'Classification failed',
                        })
                    }
                    setIntentResults([...results])
                    setIntentProgress({ done: results.length, total: calls.length })
                }

                // Refresh history after all intents are classified
                fetchIntentHistory()
            }
        } catch (err) {
            setError(
                err.response?.data?.error ||
                err.response?.data?.details ||
                err.message ||
                'Something went wrong.'
            )
            setUploading(false)
        }
    }

    const summary = result?.summary

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center">
                        <Zap className="w-5 h-5 text-white" />
                    </div>
                    Bulk Calls
                </h1>
                <p className="text-white/50 mt-1 ml-[52px]">
                    Upload an Excel or CSV file to trigger Retell AI outbound calls in parallel
                </p>
            </div>

            {/* ── Upload zone ───────────────────────────────────────────── */}
            <div
                className={`glass-card p-8 border-2 border-dashed transition-all duration-300 cursor-pointer
                    ${dragActive ? 'border-primary-400 bg-primary-500/10' : 'border-white/10 hover:border-white/25'}
                    ${file ? 'border-emerald-400/50' : ''}
                `}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => { if (!file) document.getElementById('bulk-file-input').click() }}
            >
                <input
                    id="bulk-file-input"
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    className="hidden"
                    onChange={(e) => { if (e.target.files?.[0]) handleFileSelect(e.target.files[0]) }}
                />

                {!file ? (
                    <div className="flex flex-col items-center gap-4 py-4">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
                            <Upload className="w-8 h-8 text-primary-400" />
                        </div>
                        <div className="text-center">
                            <p className="text-white font-medium text-lg">Drop your file here or click to browse</p>
                            <p className="text-white/40 text-sm mt-1">Supports .xlsx, .xls, and .csv — Max 10 MB</p>
                        </div>
                        <div className="flex gap-2 text-xs text-white/30">
                            <span className="px-2 py-1 rounded bg-white/5">Name</span>
                            <span className="px-2 py-1 rounded bg-white/5">Phone</span>
                            <span className="px-2 py-1 rounded bg-white/5">Agent_ID</span>
                            <span className="px-2 py-1 rounded bg-white/5">Status</span>
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                                <FileSpreadsheet className="w-6 h-6 text-emerald-400" />
                            </div>
                            <div>
                                <p className="text-white font-medium">{file.name}</p>
                                <p className="text-white/40 text-sm">
                                    {(file.size / 1024).toFixed(1)} KB · {file.name.split('.').pop().toUpperCase()}
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={(e) => { e.stopPropagation(); clearFile() }}
                            className="btn-icon hover:bg-red-500/20"
                        >
                            <X className="w-5 h-5 text-white/60 hover:text-red-400" />
                        </button>
                    </div>
                )}
            </div>

            {/* Error */}
            {error && (
                <div className="glass-card p-4 border border-red-500/30 bg-red-500/5 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                        <p className="text-red-300 font-medium">Error</p>
                        <p className="text-red-200/70 text-sm mt-0.5">{error}</p>
                    </div>
                </div>
            )}

            {/* Start button */}
            {file && !result && (
                <button
                    onClick={handleUpload}
                    disabled={uploading}
                    className={`w-full py-4 rounded-xl font-semibold text-lg flex items-center justify-center gap-3 transition-all duration-300
                        ${uploading
                            ? 'bg-white/10 text-white/50 cursor-not-allowed'
                            : 'bg-gradient-to-r from-primary-500 to-accent-500 text-white hover:shadow-lg hover:shadow-primary-500/25 hover:scale-[1.01]'
                        }
                    `}
                >
                    {uploading ? (
                        <>
                            <Loader2 className="w-6 h-6 animate-spin" />
                            Processing calls… This may take a moment
                        </>
                    ) : (
                        <>
                            <Phone className="w-5 h-5" />
                            Start Bulk Calls
                            <ArrowRight className="w-5 h-5" />
                        </>
                    )}
                </button>
            )}

            {/* Loading */}
            {uploading && (
                <div className="glass-card p-6">
                    <div className="flex items-center gap-4 mb-4">
                        <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
                        <p className="text-white font-medium">Triggering outbound calls…</p>
                    </div>
                    <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full animate-pulse" style={{ width: '70%' }} />
                    </div>
                    <p className="text-white/40 text-sm mt-3">
                        Calls are triggered in parallel batches, then each call is monitored for intent classification. This may take several minutes.
                    </p>
                </div>
            )}

            {/* ── Results ───────────────────────────────────────────────── */}
            {summary && (
                <div className="space-y-4">
                    <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                        Results Summary
                    </h2>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <StatCard label="Total Rows" value={summary.total_rows}
                            icon={<Users className="w-5 h-5" />} color="from-blue-500/20 to-blue-600/20" iconColor="text-blue-400" />
                        <StatCard label="Pending" value={summary.total_pending}
                            icon={<Phone className="w-5 h-5" />} color="from-amber-500/20 to-amber-600/20" iconColor="text-amber-400" />
                        <StatCard label="Success" value={summary.successfully_triggered}
                            icon={<CheckCircle2 className="w-5 h-5" />} color="from-emerald-500/20 to-emerald-600/20" iconColor="text-emerald-400" />
                        <StatCard label="Failed" value={summary.failed}
                            icon={<XCircle className="w-5 h-5" />} color="from-red-500/20 to-red-600/20" iconColor="text-red-400" />
                    </div>

                    {summary.duration_seconds && (
                        <p className="text-white/40 text-sm">Completed in {summary.duration_seconds}s</p>
                    )}

                    {/* Errors table */}
                    {summary.errors?.length > 0 && (
                        <div className="glass-card overflow-hidden">
                            <div className="p-4 border-b border-white/10">
                                <p className="text-red-300 font-medium flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4" />
                                    Failed Calls ({summary.errors.length})
                                </p>
                            </div>
                            <div className="overflow-x-auto max-h-64 overflow-y-auto">
                                <table className="w-full">
                                    <thead className="bg-white/5 sticky top-0">
                                        <tr className="text-left text-white/50 text-sm">
                                            <th className="p-3 font-medium">Name</th>
                                            <th className="p-3 font-medium">Phone</th>
                                            <th className="p-3 font-medium">Error</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {summary.errors.map((e, i) => (
                                            <tr key={i} className="border-t border-white/5">
                                                <td className="p-3 text-white/80">{e.name}</td>
                                                <td className="p-3 text-white/60">{e.phone}</td>
                                                <td className="p-3 text-red-300/70 text-sm">{e.error}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Intent Classification Progress */}
                    {intentProgress && intentProgress.done < intentProgress.total && (
                        <div className="glass-card p-6">
                            <div className="flex items-center gap-4 mb-4">
                                <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
                                <p className="text-white font-medium">
                                    Classifying intent… {intentProgress.done}/{intentProgress.total} calls
                                </p>
                            </div>
                            <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-500"
                                    style={{ width: `${(intentProgress.done / intentProgress.total) * 100}%` }}
                                />
                            </div>
                            <p className="text-white/40 text-sm mt-3">
                                Waiting for calls to finish and analyzing transcripts. This may take several minutes per call.
                            </p>
                        </div>
                    )}

                    {/* Intent Classification Results */}
                    {intentResults.length > 0 && (
                        <div className="glass-card overflow-hidden">
                            <div className="p-4 border-b border-white/10">
                                <p className="text-white font-medium flex items-center gap-2">
                                    🎯 Customer Intent Classification ({intentResults.length})
                                    {intentProgress && intentProgress.done < intentProgress.total && (
                                        <span className="text-white/40 text-sm ml-2">
                                            ({intentProgress.done}/{intentProgress.total} complete)
                                        </span>
                                    )}
                                </p>
                            </div>
                            <div className="overflow-x-auto max-h-96 overflow-y-auto">
                                <table className="w-full">
                                    <thead className="bg-white/5 sticky top-0">
                                        <tr className="text-left text-white/50 text-sm">
                                            <th className="p-3 font-medium">Name</th>
                                            <th className="p-3 font-medium">Phone</th>
                                            <th className="p-3 font-medium">Intent</th>
                                            <th className="p-3 font-medium">Description</th>
                                            <th className="p-3 font-medium">Confidence</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {intentResults.map((r, i) => (
                                            <tr key={i} className="border-t border-white/5">
                                                <td className="p-3 text-white/80">{r.name}</td>
                                                <td className="p-3 text-white/60">{r.phone_number || r.phone}</td>
                                                <td className="p-3">
                                                    <IntentBadge intent={r.intent} />
                                                </td>
                                                <td className="p-3 text-white/60 text-sm max-w-xs">{r.description || '-'}</td>
                                                <td className="p-3">
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-16 h-2 bg-white/10 rounded-full overflow-hidden">
                                                            <div
                                                                className={`h-full rounded-full ${getConfidenceColor(r.confidence_score)}`}
                                                                style={{ width: `${r.confidence_score}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-white/50 text-sm">{r.confidence_score}%</span>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Download buttons */}
                    <div className="flex flex-wrap gap-3">
                        {result?.updated_file && (
                            <a href={result.updated_file} download
                                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30 transition-all font-medium">
                                <Download className="w-5 h-5" />
                                Download Updated File
                            </a>
                        )}

                        <a href={bulkCallAPI.downloadCSVUrl} download
                            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30 transition-all font-medium">
                            <Download className="w-5 h-5" />
                            Download Intent CSV
                        </a>
                    </div>

                    <button onClick={clearFile}
                        className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white/5 border border-white/10 text-white/60 hover:text-white hover:bg-white/10 transition-all font-medium">
                        <Upload className="w-4 h-4" />
                        Upload Another File
                    </button>
                </div>
            )}

            {/* ── File format guide ─────────────────────────────────────── */}
            {!result && (
                <div className="glass-card p-6">
                    <h3 className="text-white/70 font-medium mb-3 text-sm uppercase tracking-wider">
                        Expected File Format
                    </h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left text-white/40 border-b border-white/10">
                                    <th className="p-2 font-medium">Name</th>
                                    <th className="p-2 font-medium">Phone</th>
                                    <th className="p-2 font-medium">Agent_ID</th>
                                    <th className="p-2 font-medium">Status</th>
                                </tr>
                            </thead>
                            <tbody className="text-white/60">
                                <tr className="border-b border-white/5">
                                    <td className="p-2">John Doe</td>
                                    <td className="p-2">9876543210</td>
                                    <td className="p-2">agent_abc123</td>
                                    <td className="p-2"><span className="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-300">Pending</span></td>
                                </tr>
                                <tr className="border-b border-white/5">
                                    <td className="p-2">Jane Smith</td>
                                    <td className="p-2">9123456789</td>
                                    <td className="p-2">agent_abc123</td>
                                    <td className="p-2"><span className="px-2 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-300">Called</span></td>
                                </tr>
                                <tr>
                                    <td className="p-2">Ravi Kumar</td>
                                    <td className="p-2">8012345678</td>
                                    <td className="p-2">agent_xyz456</td>
                                    <td className="p-2"><span className="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-300">Pending</span></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <p className="text-white/30 text-xs mt-3">
                        Phone numbers should NOT contain country code — <span className="text-white/50">+91</span> is added automatically.
                        Only rows with <span className="text-amber-300/70">Pending</span> status will be called.
                    </p>
                </div>
            )}

            {/* ── Intent History ────────────────────────────────────────── */}
            <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <History className="w-5 h-5 text-primary-400" />
                        Saved Intent Results
                    </h3>
                    <div className="flex items-center gap-2">
                        {(intentHistory.length > 0) && (
                            <a href={bulkCallAPI.downloadCSVUrl} download
                                className="btn-secondary text-sm flex items-center gap-1 bg-violet-500/20 hover:bg-violet-500/30 text-violet-300 border-violet-500/30">
                                <Download className="w-4 h-4" />
                                Download Intent CSV
                            </a>
                        )}
                        <button onClick={fetchIntentHistory} className="btn-secondary text-sm flex items-center gap-1">
                            Refresh
                        </button>
                    </div>
                </div>

                {historyLoading ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
                    </div>
                ) : intentHistory.length === 0 ? (
                    <p className="text-white/40 text-sm text-center py-6">No saved intent results yet. Run a bulk call to generate them.</p>
                ) : (
                    <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                        <table className="w-full">
                            <thead className="bg-white/5 sticky top-0">
                                <tr className="text-left text-white/50 text-sm">
                                    <th className="p-3 font-medium">Name</th>
                                    <th className="p-3 font-medium">Phone</th>
                                    <th className="p-3 font-medium">Intent</th>
                                    <th className="p-3 font-medium">Description</th>
                                    <th className="p-3 font-medium">Confidence</th>
                                    <th className="p-3 font-medium">Timestamp</th>
                                </tr>
                            </thead>
                            <tbody>
                                {intentHistory.map((r, i) => (
                                    <tr key={i} className="border-t border-white/5">
                                        <td className="p-3 text-white/80">{r.Name}</td>
                                        <td className="p-3 text-white/60">{r.Phone}</td>
                                        <td className="p-3">
                                            <IntentBadge intent={r.Intent} />
                                        </td>
                                        <td className="p-3 text-white/60 text-sm max-w-xs">{r.Description || '-'}</td>
                                        <td className="p-3">
                                            <div className="flex items-center gap-2">
                                                <div className="w-16 h-2 bg-white/10 rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full ${getConfidenceColor(Number(r.Confidence))}`}
                                                        style={{ width: `${r.Confidence}%` }}
                                                    />
                                                </div>
                                                <span className="text-white/50 text-sm">{r.Confidence}%</span>
                                            </div>
                                        </td>
                                        <td className="p-3 text-white/40 text-xs">{r.Timestamp}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}

const INTENT_STYLES = {
    'Highly Interested': 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    'Interested': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    'Needs Follow-up': 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    'Just Exploring': 'bg-slate-500/20 text-slate-300 border-slate-500/30',
    'Not Interested': 'bg-red-500/20 text-red-300 border-red-500/30',
}

function IntentBadge({ intent }) {
    const style = INTENT_STYLES[intent] || INTENT_STYLES['Needs Follow-up']
    return (
        <span className={`px-2.5 py-1 rounded-lg text-xs font-medium border ${style}`}>
            {intent}
        </span>
    )
}

function getConfidenceColor(score) {
    if (score >= 80) return 'bg-gradient-to-r from-emerald-400 to-emerald-500'
    if (score >= 60) return 'bg-gradient-to-r from-blue-400 to-blue-500'
    if (score >= 40) return 'bg-gradient-to-r from-amber-400 to-amber-500'
    return 'bg-gradient-to-r from-red-400 to-red-500'
}

function StatCard({ label, value, icon, color, iconColor }) {
    return (
        <div className={`glass-card p-4 bg-gradient-to-br ${color}`}>
            <div className="flex items-center justify-between mb-2">
                <span className={iconColor}>{icon}</span>
            </div>
            <p className="text-3xl font-bold text-white">{value}</p>
            <p className="text-white/50 text-sm mt-1">{label}</p>
        </div>
    )
}

export default BulkCallPage

