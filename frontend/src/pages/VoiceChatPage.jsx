import { useState, useRef, useEffect } from 'react'
import {
    Mic,
    MicOff,
    Volume2,
    VolumeX,
    Loader2,
    MessageCircle,
    RefreshCw,
    Flame,
    Thermometer,
    Snowflake,
    Send,
    AlertCircle,
    Building2,
    PanelRightOpen,
    PanelRightClose,
    Brain,
    Globe,
    AudioLines,
    FileQuestion,
    Activity,
    Zap,
    Eye,
    MessagesSquare,
    User,
    Bot
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function VoiceChatPage() {
    const [isRecording, setIsRecording] = useState(false)
    const [isProcessing, setIsProcessing] = useState(false)
    const [isPlaying, setIsPlaying] = useState(false)
    const [sessionId, setSessionId] = useState(null)
    const [messages, setMessages] = useState([])
    const [leadScore, setLeadScore] = useState(null)
    const [leadStatus, setLeadStatus] = useState(null)
    const [error, setError] = useState(null)
    const [textInput, setTextInput] = useState('')
    const [audioEnabled, setAudioEnabled] = useState(true)

    // Campaign selection state
    const [campaigns, setCampaigns] = useState([])
    const [selectedCampaign, setSelectedCampaign] = useState(null)
    const [loadingCampaigns, setLoadingCampaigns] = useState(true)

    // Context window state
    const [showContext, setShowContext] = useState(true)
    const [pipelineInfo, setPipelineInfo] = useState(null)
    const [contextTab, setContextTab] = useState('pipeline') // 'pipeline' | 'chat'

    const mediaRecorderRef = useRef(null)
    const audioChunksRef = useRef([])
    const audioRef = useRef(null)
    const messagesEndRef = useRef(null)

    useEffect(() => { fetchCampaigns() }, [])
    useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
    useEffect(() => {
        audioRef.current = new Audio()
        audioRef.current.onended = () => setIsPlaying(false)
        audioRef.current.onerror = () => { console.error('Audio playback error'); setIsPlaying(false) }
    }, [])

    const fetchCampaigns = async () => {
        try {
            setLoadingCampaigns(true)
            const response = await fetch(`${API_BASE}/api/campaigns?page=1&page_size=100`)
            if (response.ok) { const data = await response.json(); setCampaigns(data.items || []) }
        } catch (err) { console.error('Failed to fetch campaigns:', err) }
        finally { setLoadingCampaigns(false) }
    }

    const startRecording = async () => {
        if (!selectedCampaign) { setError('Please select a campaign first'); return }
        try {
            setError(null)
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
            })
            mediaRecorderRef.current = mediaRecorder
            audioChunksRef.current = []
            mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data) }
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
                stream.getTracks().forEach(track => track.stop())
                await sendAudioToBackend(audioBlob)
            }
            mediaRecorder.start()
            setIsRecording(true)
        } catch (err) {
            console.error('Failed to start recording:', err)
            setError('Microphone access denied. Please enable microphone permissions.')
        }
    }

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) { mediaRecorderRef.current.stop(); setIsRecording(false) }
    }

    const sendAudioToBackend = async (audioBlob) => {
        setIsProcessing(true); setError(null)
        try {
            const formData = new FormData()
            formData.append('audio', audioBlob, 'recording.webm')
            formData.append('campaign_id', selectedCampaign.id)
            if (sessionId) formData.append('session_id', sessionId)
            const startTime = Date.now()
            const response = await fetch(`${API_BASE}/api/voice/chat/audio`, { method: 'POST', body: formData })
            const latency = Date.now() - startTime
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
            }
            const data = await response.json()
            handleResponse(data, false, latency)
        } catch (err) {
            console.error('Failed to send audio:', err)
            setError(err.message || 'Failed to process audio. Please try again.')
        } finally { setIsProcessing(false) }
    }

    const sendTextMessage = async () => {
        if (!textInput.trim()) return
        if (!selectedCampaign) { setError('Please select a campaign first'); return }
        const userText = textInput.trim()
        setTextInput(''); setIsProcessing(true); setError(null)
        setMessages(prev => [...prev, { role: 'user', content: userText, timestamp: new Date() }])
        try {
            const startTime = Date.now()
            const response = await fetch(`${API_BASE}/api/voice/chat/text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: userText, session_id: sessionId, campaign_id: selectedCampaign.id })
            })
            const latency = Date.now() - startTime
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
            }
            const data = await response.json()
            handleResponse(data, true, latency)
        } catch (err) {
            console.error('Failed to send text:', err)
            setError(err.message || 'Failed to process message. Please try again.')
        } finally { setIsProcessing(false) }
    }

    const handleResponse = (data, skipUserMessage = false, latency = 0) => {
        if (data.session_id) setSessionId(data.session_id)
        if (data.lead_score !== null) setLeadScore(data.lead_score)
        if (data.lead_status) setLeadStatus(data.lead_status)

        if (data.pipeline_info) {
            const info = { ...data.pipeline_info, latency_ms: latency, timestamp: new Date().toLocaleTimeString() }
            setPipelineInfo(info)
        }

        setMessages(prev => [
            ...prev,
            ...(skipUserMessage ? [] : []),
            { role: 'assistant', content: data.text_response, language: data.detected_language, timestamp: new Date() }
        ])

        if (audioEnabled && data.audio_base64 && audioRef.current) {
            const audioUrl = `data:audio/wav;base64,${data.audio_base64}`
            audioRef.current.src = audioUrl
            audioRef.current.play().catch(err => { console.error('Audio playback failed:', err); setIsPlaying(false) })
            setIsPlaying(true)
        }
    }

    const startNewSession = () => {
        setSessionId(null); setMessages([]); setLeadScore(null)
        setLeadStatus(null); setError(null); setPipelineInfo(null)
    }

    const getLeadIcon = () => {
        if (!leadStatus) return null
        switch (leadStatus.toLowerCase()) {
            case 'hot': return <Flame className="w-5 h-5 text-rose-500" />
            case 'warm': return <Thermometer className="w-5 h-5 text-amber-500" />
            case 'cold': return <Snowflake className="w-5 h-5 text-sky-500" />
            default: return null
        }
    }

    const getLeadColor = () => {
        if (!leadStatus) return 'bg-gray-500/20 text-gray-400'
        switch (leadStatus.toLowerCase()) {
            case 'hot': return 'bg-rose-500/20 text-rose-400'
            case 'warm': return 'bg-amber-500/20 text-amber-400'
            case 'cold': return 'bg-sky-500/20 text-sky-400'
            default: return 'bg-gray-500/20 text-gray-400'
        }
    }

    const getLangLabel = (lang) => {
        switch (lang) {
            case 'tamil': return '🇮🇳 Tamil'
            case 'tanglish': return '🔀 Tanglish'
            case 'english': return '🇬🇧 English'
            default: return lang
        }
    }

    // ---- RENDER ----
    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col">
            {/* Header */}
            <div className="glass-card p-4 mb-4">
                <div className="flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-gradient-to-br from-primary-500/20 to-accent-500/20">
                            <MessageCircle className="w-6 h-6 text-primary-400" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white">Voice AI Chatbot</h1>
                            <p className="text-white/50 text-sm">Speak or type to interact</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Building2 className="w-5 h-5 text-white/50" />
                            <select
                                value={selectedCampaign?.id || ''}
                                onChange={(e) => {
                                    const campaign = campaigns.find(c => c.id === parseInt(e.target.value))
                                    setSelectedCampaign(campaign)
                                    startNewSession()
                                }}
                                className="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white min-w-[200px] focus:outline-none focus:border-primary-500"
                                disabled={loadingCampaigns}
                            >
                                <option value="">Select Campaign</option>
                                {campaigns.map(c => (<option key={c.id} value={c.id}>{c.name}</option>))}
                            </select>
                        </div>

                        {leadStatus && (
                            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${getLeadColor()}`}>
                                {getLeadIcon()}
                                <span className="font-medium capitalize">{leadStatus}</span>
                                {leadScore !== null && (
                                    <span className="text-xs opacity-70">({(leadScore * 100).toFixed(0)}%)</span>
                                )}
                            </div>
                        )}

                        <button onClick={() => setAudioEnabled(!audioEnabled)}
                            className={`p-2 rounded-lg transition-colors ${audioEnabled ? 'bg-primary-500/20 text-primary-400 hover:bg-primary-500/30' : 'bg-white/5 text-white/50 hover:bg-white/10'}`}
                            title={audioEnabled ? 'Mute audio' : 'Enable audio'}>
                            {audioEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                        </button>

                        <button onClick={() => setShowContext(!showContext)}
                            className={`p-2 rounded-lg transition-colors ${showContext ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30' : 'bg-white/5 text-white/50 hover:bg-white/10'}`}
                            title={showContext ? 'Hide context' : 'Show context'}>
                            {showContext ? <PanelRightClose className="w-5 h-5" /> : <PanelRightOpen className="w-5 h-5" />}
                        </button>

                        <button onClick={startNewSession}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 text-white/70 hover:bg-white/10 hover:text-white transition-colors">
                            <RefreshCw className="w-4 h-4" /> New
                        </button>
                    </div>
                </div>
            </div>

            {!selectedCampaign && !loadingCampaigns && (
                <div className="mb-4 p-4 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                    <div>
                        <p className="text-amber-400 font-medium">Select a Campaign to Start</p>
                        <p className="text-amber-400/70 text-sm">Choose a campaign from the dropdown above to enable voice chat.</p>
                    </div>
                </div>
            )}

            {/* Main Content — Chat + Context Panel */}
            <div className="flex-1 flex gap-4 overflow-hidden mb-4">
                {/* Messages Area */}
                <div className="flex-1 glass-card p-4 overflow-y-auto">
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center">
                            <div className="p-4 rounded-full bg-gradient-to-br from-primary-500/20 to-accent-500/20 mb-4">
                                <Mic className="w-12 h-12 text-primary-400" />
                            </div>
                            <h2 className="text-xl font-semibold text-white mb-2">
                                {selectedCampaign ? `Chat: ${selectedCampaign.name}` : 'Start a Conversation'}
                            </h2>
                            <p className="text-white/50 max-w-md">
                                {selectedCampaign
                                    ? 'Click the microphone and speak, or type a message below.'
                                    : 'Select a campaign to begin chatting with the AI assistant.'}
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {messages.map((msg, idx) => (
                                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[80%] px-4 py-3 rounded-2xl ${msg.role === 'user'
                                        ? 'bg-primary-500/30 text-white rounded-br-sm'
                                        : 'bg-white/10 text-white rounded-bl-sm'}`}>
                                        <p>{msg.content}</p>
                                        {msg.language && msg.role === 'assistant' && (
                                            <p className="text-xs text-white/40 mt-1 capitalize">{msg.language}</p>
                                        )}
                                    </div>
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* Context Window Panel */}
                {showContext && (
                    <div className="w-80 flex-shrink-0 glass-card overflow-hidden flex flex-col" style={{
                        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(6, 182, 212, 0.05) 100%)',
                        borderColor: 'rgba(16, 185, 129, 0.2)'
                    }}>
                        {/* Tab Header */}
                        <div className="flex border-b border-white/10">
                            <button
                                onClick={() => setContextTab('pipeline')}
                                className={`flex-1 px-3 py-3 text-xs font-bold uppercase tracking-wider transition-colors
                                    ${contextTab === 'pipeline'
                                        ? 'text-emerald-400 border-b-2 border-emerald-400 bg-emerald-500/10'
                                        : 'text-white/40 hover:text-white/60'}`}
                            >
                                <div className="flex items-center justify-center gap-1.5">
                                    <Activity className="w-3.5 h-3.5" /> Pipeline
                                </div>
                            </button>
                            <button
                                onClick={() => setContextTab('chat')}
                                className={`flex-1 px-3 py-3 text-xs font-bold uppercase tracking-wider transition-colors
                                    ${contextTab === 'chat'
                                        ? 'text-cyan-400 border-b-2 border-cyan-400 bg-cyan-500/10'
                                        : 'text-white/40 hover:text-white/60'}`}
                            >
                                <div className="flex items-center justify-center gap-1.5">
                                    <MessagesSquare className="w-3.5 h-3.5" /> Chat Analysis
                                </div>
                            </button>
                        </div>

                        {/* Tab Content */}
                        <div className="flex-1 overflow-y-auto p-4">
                            {/* PIPELINE TAB */}
                            {contextTab === 'pipeline' && (
                                pipelineInfo ? (
                                    <div className="space-y-3">
                                        {/* Latency */}
                                        <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                            <div className="flex items-center gap-2 mb-1">
                                                <Zap className="w-4 h-4 text-yellow-400" />
                                                <span className="text-xs font-semibold text-white/70 uppercase">Latency</span>
                                            </div>
                                            <p className={`text-lg font-bold ${pipelineInfo.latency_ms < 3000 ? 'text-emerald-400' : pipelineInfo.latency_ms < 6000 ? 'text-amber-400' : 'text-rose-400'}`}>
                                                {(pipelineInfo.latency_ms / 1000).toFixed(1)}s
                                            </p>
                                        </div>

                                        {/* Language */}
                                        <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                            <div className="flex items-center gap-2 mb-1">
                                                <Globe className="w-4 h-4 text-cyan-400" />
                                                <span className="text-xs font-semibold text-white/70 uppercase">Language</span>
                                            </div>
                                            <p className="text-sm font-semibold text-white">{getLangLabel(pipelineInfo.detected_language)}</p>
                                        </div>

                                        {/* STT */}
                                        <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                            <div className="flex items-center gap-2 mb-1">
                                                <AudioLines className="w-4 h-4 text-violet-400" />
                                                <span className="text-xs font-semibold text-white/70 uppercase">STT</span>
                                            </div>
                                            <p className="text-sm font-medium text-white/90">{pipelineInfo.stt_engine}</p>
                                        </div>

                                        {/* LLM */}
                                        <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                            <div className="flex items-center gap-2 mb-1">
                                                <Brain className="w-4 h-4 text-pink-400" />
                                                <span className="text-xs font-semibold text-white/70 uppercase">LLM</span>
                                            </div>
                                            <p className="text-sm font-medium text-white/90">{pipelineInfo.llm_model}</p>
                                        </div>

                                        {/* TTS */}
                                        <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                            <div className="flex items-center gap-2 mb-1">
                                                <Volume2 className="w-4 h-4 text-emerald-400" />
                                                <span className="text-xs font-semibold text-white/70 uppercase">TTS</span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <p className="text-sm font-medium text-white/90">{pipelineInfo.tts_engine}</p>
                                                <span className={`text-xs px-2 py-0.5 rounded-full ${pipelineInfo.tts_status === 'success' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                                                    {pipelineInfo.tts_status}
                                                </span>
                                            </div>
                                        </div>

                                        {/* FAQ / RAG */}
                                        <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                            <div className="flex items-center gap-2 mb-1">
                                                <FileQuestion className="w-4 h-4 text-amber-400" />
                                                <span className="text-xs font-semibold text-white/70 uppercase">RAG Retrieval</span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <p className="text-sm font-medium text-white/90">ChromaDB</p>
                                                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                                                    {pipelineInfo.faq_matches} matches
                                                </span>
                                            </div>
                                        </div>

                                        {/* Campaign */}
                                        <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                                            <div className="flex items-center gap-2 mb-1">
                                                <Building2 className="w-4 h-4 text-blue-400" />
                                                <span className="text-xs font-semibold text-white/70 uppercase">Campaign</span>
                                            </div>
                                            <p className="text-sm font-medium text-white/90">{pipelineInfo.campaign_name}</p>
                                            {pipelineInfo.tone && (
                                                <span className={`inline-block mt-1.5 text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${pipelineInfo.tone === 'professional'
                                                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                                                    : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                                                    }`}>
                                                    {pipelineInfo.tone === 'professional' ? '🎓 Professional' : '🛍️ Casual'}
                                                </span>
                                            )}
                                        </div>

                                        <div className="text-center text-xs text-white/30 pt-1">
                                            Updated: {pipelineInfo.timestamp}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="h-full flex flex-col items-center justify-center text-center py-8">
                                        <div className="p-3 rounded-full bg-emerald-500/10 mb-3">
                                            <Brain className="w-8 h-8 text-emerald-400/50" />
                                        </div>
                                        <p className="text-white/40 text-sm">Pipeline info appears after first message</p>
                                    </div>
                                )
                            )}

                            {/* CHAT ANALYSIS TAB */}
                            {contextTab === 'chat' && (
                                pipelineInfo && pipelineInfo.chat_history ? (
                                    <div className="space-y-4">
                                        {/* Turn Count */}
                                        <div className="flex items-center justify-between p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                                            <span className="text-xs font-bold text-cyan-400 uppercase">Turns</span>
                                            <span className="text-lg font-bold text-cyan-300">{pipelineInfo.turn_count}</span>
                                        </div>

                                        {/* User Topics */}
                                        {pipelineInfo.user_topics && pipelineInfo.user_topics.length > 0 && (
                                            <div>
                                                <h4 className="text-xs font-bold text-white/60 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                                    <Eye className="w-3.5 h-3.5" /> User Topics
                                                </h4>
                                                <div className="space-y-1.5">
                                                    {pipelineInfo.user_topics.map((topic, i) => (
                                                        <div key={i} className="p-2 rounded-lg bg-white/5 border border-white/10">
                                                            <p className="text-xs text-white/80 line-clamp-2">"{topic}"</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Chat History */}
                                        <div>
                                            <h4 className="text-xs font-bold text-white/60 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                                <MessagesSquare className="w-3.5 h-3.5" /> Chat Log
                                            </h4>
                                            <div className="space-y-2">
                                                {pipelineInfo.chat_history.map((msg, i) => (
                                                    <div key={i} className={`p-2.5 rounded-lg border ${msg.role === 'user'
                                                        ? 'bg-primary-500/10 border-primary-500/20'
                                                        : 'bg-white/5 border-white/10'
                                                        }`}>
                                                        <div className="flex items-center gap-1.5 mb-1">
                                                            {msg.role === 'user'
                                                                ? <User className="w-3 h-3 text-primary-400" />
                                                                : <Bot className="w-3 h-3 text-emerald-400" />
                                                            }
                                                            <span className={`text-[10px] font-bold uppercase ${msg.role === 'user' ? 'text-primary-400' : 'text-emerald-400'}`}>
                                                                {msg.role}
                                                            </span>
                                                        </div>
                                                        <p className="text-xs text-white/70 line-clamp-3">{msg.content}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Lead Signals */}
                                        {pipelineInfo.lead_signals && pipelineInfo.lead_signals.length > 0 && (
                                            <div>
                                                <h4 className="text-xs font-bold text-white/60 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                                    <Flame className="w-3.5 h-3.5" /> Lead Signals
                                                </h4>
                                                <div className="space-y-1">
                                                    {pipelineInfo.lead_signals.map((signal, i) => (
                                                        <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                                                            <span className="text-xs text-rose-300">
                                                                {typeof signal === 'string' ? signal : signal.type || JSON.stringify(signal)}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="h-full flex flex-col items-center justify-center text-center py-8">
                                        <div className="p-3 rounded-full bg-cyan-500/10 mb-3">
                                            <MessagesSquare className="w-8 h-8 text-cyan-400/50" />
                                        </div>
                                        <p className="text-white/40 text-sm">Chat analysis appears after first message</p>
                                    </div>
                                )
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Error Display */}
            {error && (
                <div className="mb-4 p-3 rounded-lg bg-rose-500/20 text-rose-400 text-sm">{error}</div>
            )}

            {/* Input Area */}
            <div className="glass-card p-4">
                <div className="flex items-center gap-3">
                    <div className="flex-1 flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 focus-within:border-primary-500/50">
                        <input
                            type="text" value={textInput}
                            onChange={(e) => setTextInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && sendTextMessage()}
                            placeholder={selectedCampaign ? "Type a message..." : "Select a campaign first"}
                            className="flex-1 bg-transparent text-white placeholder-white/30 outline-none"
                            disabled={isProcessing || !selectedCampaign}
                        />
                        <button onClick={sendTextMessage}
                            disabled={isProcessing || !textInput.trim() || !selectedCampaign}
                            className="p-2 rounded-lg text-white/50 hover:text-primary-400 hover:bg-white/5 disabled:opacity-30 transition-colors">
                            <Send className="w-5 h-5" />
                        </button>
                    </div>

                    <button
                        onClick={isRecording ? stopRecording : startRecording}
                        disabled={isProcessing || !selectedCampaign}
                        className={`relative p-4 rounded-full transition-all ${isRecording
                            ? 'bg-rose-500 text-white animate-pulse'
                            : isProcessing || !selectedCampaign
                                ? 'bg-white/10 text-white/30'
                                : 'bg-gradient-to-br from-primary-500 to-accent-500 text-white hover:shadow-lg hover:shadow-primary-500/30'
                            }`}>
                        {isProcessing ? <Loader2 className="w-6 h-6 animate-spin" /> : isRecording ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
                        {isRecording && <span className="absolute inset-0 rounded-full border-4 border-rose-500/50 animate-ping" />}
                    </button>
                </div>

                <div className="mt-2 text-center text-sm text-white/40">
                    {!selectedCampaign ? (
                        <span className="text-amber-400">Please select a campaign to start</span>
                    ) : isRecording ? (
                        <span className="text-rose-400">Recording... Click to stop</span>
                    ) : isProcessing ? (
                        <span className="text-primary-400">Processing...</span>
                    ) : isPlaying ? (
                        <span className="text-accent-400">Playing response...</span>
                    ) : (
                        <span>Click the mic and speak, or type below</span>
                    )}
                </div>
            </div>
        </div>
    )
}

export default VoiceChatPage
