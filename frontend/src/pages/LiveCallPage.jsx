import { useState, useRef, useEffect, useCallback } from 'react'
import {
    PhoneCall,
    PhoneOff,
    Mic,
    MicOff,
    Volume2,
    VolumeX,
    Loader2,
    Building2,
    Clock,
    Radio,
    User,
    Bot,
    Flame,
    Thermometer,
    Snowflake,
    AlertCircle,
    CheckCircle2,
    Activity,
    Zap,
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_BASE = API_BASE.replace(/^http/, 'ws')

// Voice Activity Detection thresholds
const VAD_SPEECH_THRESHOLD = 15    // analyser avg above this = speaking
const VAD_SILENCE_DURATION = 1800  // ms of silence to trigger audio_end
const VAD_MIN_SPEECH_DURATION = 400 // ms minimum speech before we accept it

function LiveCallPage() {
    // Call state
    const [callState, setCallState] = useState('idle')
    const [sessionId, setSessionId] = useState(null)
    const [isMuted, setIsMuted] = useState(false)
    const [speakerOn, setSpeakerOn] = useState(true)
    const [isProcessing, setIsProcessing] = useState(false)
    const [callDuration, setCallDuration] = useState(0)
    const [error, setError] = useState(null)

    // Campaign
    const [campaigns, setCampaigns] = useState([])
    const [selectedCampaign, setSelectedCampaign] = useState(null)
    const [loadingCampaigns, setLoadingCampaigns] = useState(true)

    // Transcript and lead
    const [messages, setMessages] = useState([])
    const [leadScore, setLeadScore] = useState(null)
    const [leadStatus, setLeadStatus] = useState(null)
    const [callSummary, setCallSummary] = useState(null)

    // Audio visualization
    const [audioLevel, setAudioLevel] = useState(0)
    const [isSpeaking, setIsSpeaking] = useState(false)

    // Refs
    const wsRef = useRef(null)
    const mediaStreamRef = useRef(null)
    const mediaRecorderRef = useRef(null)
    const audioContextRef = useRef(null)
    const analyserRef = useRef(null)
    const timerRef = useRef(null)
    const animFrameRef = useRef(null)
    const audioQueueRef = useRef([])
    const isPlayingRef = useRef(false)
    const messagesEndRef = useRef(null)
    const isMutedRef = useRef(false)
    const speakerOnRef = useRef(true)
    const handleWsMessageRef = useRef(null)  // avoids stale closure in ws.onmessage

    // VAD (Voice Activity Detection) refs
    const vadTimerRef = useRef(null)
    const speechStartRef = useRef(null)      // timestamp when speech started
    const hasSpeechRef = useRef(false)        // whether we detected speech this segment
    const isListeningRef = useRef(false)      // whether we're actively listening (not during AI playback)
    const recorderActiveRef = useRef(false)   // whether MediaRecorder is running

    useEffect(() => { fetchCampaigns() }, [])
    useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

    // Keep refs in sync with state
    useEffect(() => { isMutedRef.current = isMuted }, [isMuted])
    useEffect(() => { speakerOnRef.current = speakerOn }, [speakerOn])

    // Cleanup on unmount
    useEffect(() => {
        return () => { cleanupCall() }
    }, [])

    const fetchCampaigns = async () => {
        try {
            setLoadingCampaigns(true)
            const response = await fetch(`${API_BASE}/api/campaigns?page=1&page_size=100`)
            if (response.ok) {
                const data = await response.json()
                setCampaigns(data.items || [])
            }
        } catch (err) {
            console.error('Failed to fetch campaigns:', err)
        } finally {
            setLoadingCampaigns(false)
        }
    }

    const cleanupCall = useCallback(() => {
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
        if (animFrameRef.current) { cancelAnimationFrame(animFrameRef.current); animFrameRef.current = null }
        if (vadTimerRef.current) { clearTimeout(vadTimerRef.current); vadTimerRef.current = null }

        isListeningRef.current = false
        recorderActiveRef.current = false

        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            try { mediaRecorderRef.current.stop() } catch (e) { }
        }
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(t => t.stop())
            mediaStreamRef.current = null
        }
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            try { audioContextRef.current.close() } catch (e) { }
            audioContextRef.current = null
        }

        if (wsRef.current) {
            try { wsRef.current.close() } catch (e) { }
            wsRef.current = null
        }

        audioQueueRef.current = []
        isPlayingRef.current = false
    }, [])

    // ========== AUDIO RECORDING ==========

    const startRecording = useCallback(() => {
        if (!mediaStreamRef.current || recorderActiveRef.current) return

        console.log('[LiveCall] Starting MediaRecorder...')
        const mediaRecorder = new MediaRecorder(mediaStreamRef.current, {
            mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : MediaRecorder.isTypeSupported('audio/webm')
                    ? 'audio/webm'
                    : 'audio/mp4',
        })
        mediaRecorderRef.current = mediaRecorder

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN
                && !isMutedRef.current && isListeningRef.current) {
                wsRef.current.send(e.data)
            }
        }

        mediaRecorder.start(250) // send chunks every 250ms
        recorderActiveRef.current = true
        console.log('[LiveCall] MediaRecorder started')
    }, [])

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            try { mediaRecorderRef.current.stop() } catch (e) { }
        }
        recorderActiveRef.current = false
        console.log('[LiveCall] MediaRecorder stopped')
    }, [])

    // ========== VOICE ACTIVITY DETECTION ==========
    // Uses the AudioContext analyser to detect speech vs silence.
    // MediaRecorder.ondataavailable fires every 250ms ALWAYS (even in silence).
    // So we rely on the analyser's frequency data to know if the user is actually speaking.

    const startVAD = useCallback(() => {
        if (!analyserRef.current) return

        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)

        const checkVAD = () => {
            if (!analyserRef.current || !isListeningRef.current) return

            analyserRef.current.getByteFrequencyData(dataArray)
            const avg = dataArray.reduce((sum, val) => sum + val, 0) / dataArray.length
            const normalizedLevel = avg / 255

            setAudioLevel(normalizedLevel)

            const isTalking = avg > VAD_SPEECH_THRESHOLD && !isMutedRef.current

            if (isTalking) {
                setIsSpeaking(true)

                // User started speaking
                if (!speechStartRef.current) {
                    speechStartRef.current = Date.now()
                    hasSpeechRef.current = true
                    console.log('[VAD] Speech started')
                }

                // Clear silence timer — user is still talking
                if (vadTimerRef.current) {
                    clearTimeout(vadTimerRef.current)
                    vadTimerRef.current = null
                }
            } else {
                setIsSpeaking(false)

                // User stopped speaking — start silence countdown
                if (hasSpeechRef.current && !vadTimerRef.current) {
                    const speechDuration = Date.now() - (speechStartRef.current || Date.now())

                    // Only trigger audio_end if speech was long enough (not just a cough/click)
                    if (speechDuration >= VAD_MIN_SPEECH_DURATION) {
                        vadTimerRef.current = setTimeout(() => {
                            console.log(`[VAD] Silence detected after ${speechDuration}ms of speech → sending audio_end`)

                            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && hasSpeechRef.current) {
                                // Stop listening while we process
                                isListeningRef.current = false
                                hasSpeechRef.current = false
                                speechStartRef.current = null

                                wsRef.current.send(JSON.stringify({ type: 'audio_end' }))
                            }

                            vadTimerRef.current = null
                        }, VAD_SILENCE_DURATION)
                    } else {
                        // Too short — reset
                        hasSpeechRef.current = false
                        speechStartRef.current = null
                    }
                }
            }

            animFrameRef.current = requestAnimationFrame(checkVAD)
        }

        checkVAD()
    }, [])

    // Resume listening after AI finishes speaking
    const resumeListening = useCallback(() => {
        // Don't resume listening if the user is muted
        if (isMutedRef.current) {
            console.log('[LiveCall] Skipping resumeListening — muted')
            return
        }

        console.log('[LiveCall] Resuming listening...')
        isListeningRef.current = true
        hasSpeechRef.current = false
        speechStartRef.current = null
        if (vadTimerRef.current) { clearTimeout(vadTimerRef.current); vadTimerRef.current = null }

        // Restart recorder if needed
        if (!recorderActiveRef.current) {
            startRecording()
        }

        // Restart VAD monitoring
        startVAD()
    }, [startRecording, startVAD])

    // ========== AUDIO PLAYBACK ==========

    const playAudio = useCallback(async (base64Audio) => {
        if (!speakerOnRef.current) {
            // Even if speaker is off, resume listening after a small delay
            setTimeout(resumeListening, 300)
            return
        }

        audioQueueRef.current.push(base64Audio)
        if (isPlayingRef.current) return

        isPlayingRef.current = true

        // Pause listening while AI is speaking (prevent echo)
        isListeningRef.current = false
        hasSpeechRef.current = false
        speechStartRef.current = null

        while (audioQueueRef.current.length > 0) {
            const audioB64 = audioQueueRef.current.shift()
            try {
                const audioBytes = Uint8Array.from(atob(audioB64), c => c.charCodeAt(0))
                const audioBlob = new Blob([audioBytes], { type: 'audio/wav' })
                const audioUrl = URL.createObjectURL(audioBlob)
                const audio = new Audio(audioUrl)

                await new Promise((resolve, reject) => {
                    audio.onended = resolve
                    audio.onerror = reject
                    audio.play().catch(reject)
                })

                URL.revokeObjectURL(audioUrl)
            } catch (err) {
                console.error('[LiveCall] Audio playback error:', err)
            }
        }

        isPlayingRef.current = false

        // Resume listening after AI finishes speaking — but only if NOT muted
        if (!isMutedRef.current) {
            setTimeout(resumeListening, 300)
        } else {
            console.log('[LiveCall] Audio playback finished while muted — not resuming listening')
        }
    }, [resumeListening])

    // ========== WEBSOCKET MESSAGE HANDLER ==========

    const handleWsMessage = useCallback((data) => {
        switch (data.type) {
            case 'connected':
                setSessionId(data.session_id)
                break

            case 'greeting':
                setCallState('active')
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: data.ai_text,
                    timestamp: new Date(),
                }])
                // Start call timer
                timerRef.current = setInterval(() => {
                    setCallDuration(prev => prev + 1)
                }, 1000)
                // Play greeting audio, then start listening
                if (data.audio_base64) {
                    playAudio(data.audio_base64)
                } else {
                    // No audio — start listening immediately
                    setTimeout(() => {
                        startRecording()
                        isListeningRef.current = true
                        startVAD()
                    }, 500)
                }
                break

            case 'processing':
                setIsProcessing(true)
                break

            case 'response':
                setIsProcessing(false)
                if (data.user_text) {
                    setMessages(prev => [...prev, {
                        role: 'user',
                        content: data.user_text,
                        timestamp: new Date(),
                    }])
                }
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: data.ai_text,
                    timestamp: new Date(),
                    language: data.detected_language,
                }])
                if (data.lead_score !== null) setLeadScore(data.lead_score)
                if (data.lead_status) setLeadStatus(data.lead_status)
                // Play audio response → then resume listening
                if (data.audio_base64) {
                    playAudio(data.audio_base64)
                } else {
                    // No audio — resume listening immediately
                    setTimeout(resumeListening, 300)
                }
                break

            case 'silence':
                setIsProcessing(false)
                // Resume listening
                setTimeout(resumeListening, 300)
                break


            case 'call_ended':
                setCallState('ended')
                setCallSummary({
                    turnCount: data.turn_count,
                    leadScore: data.lead_score,
                    leadStatus: data.lead_status,
                    transcript: data.transcript,
                })
                cleanupCall()
                break

            case 'error':
                setError(data.message)
                setIsProcessing(false)
                // Resume listening on non-fatal errors
                setTimeout(resumeListening, 500)
                break
        }
    }, [cleanupCall, playAudio, startRecording, startVAD, resumeListening])

    // Keep ref in sync so ws.onmessage always uses latest handler
    useEffect(() => { handleWsMessageRef.current = handleWsMessage }, [handleWsMessage])

    // ========== START CALL ==========

    const startCall = async () => {
        if (!selectedCampaign) { setError('Please select a campaign first'); return }
        setError(null)
        setCallState('connecting')
        setMessages([])
        setLeadScore(null)
        setLeadStatus(null)
        setCallSummary(null)
        setCallDuration(0)

        try {
            // Get microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000,
                }
            })
            mediaStreamRef.current = stream

            // Set up audio analysis for VAD + visualization
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)()
            audioContextRef.current = audioCtx
            const source = audioCtx.createMediaStreamSource(stream)
            const analyser = audioCtx.createAnalyser()
            analyser.fftSize = 256
            analyser.smoothingTimeConstant = 0.8
            source.connect(analyser)
            analyserRef.current = analyser

            // Connect WebSocket
            const wsUrl = `${WS_BASE}/api/ws/live-call?campaign_id=${selectedCampaign.id}`
            const ws = new WebSocket(wsUrl)
            wsRef.current = ws

            ws.onopen = () => {
                console.log('[LiveCall] WebSocket connected')
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    // Use ref to always call the latest handler (avoids stale closure)
                    if (handleWsMessageRef.current) handleWsMessageRef.current(data)
                } catch (e) {
                    console.error('[LiveCall] Failed to parse message:', e)
                }
            }

            ws.onerror = (event) => {
                console.error('[LiveCall] WebSocket error:', event)
                setError('Connection error. Please try again.')
                setCallState('idle')
                cleanupCall()
            }

            ws.onclose = (event) => {
                console.log('[LiveCall] WebSocket closed:', event.code)
            }

        } catch (err) {
            console.error('[LiveCall] Failed to start call:', err)
            setError('Microphone access denied. Please enable microphone permissions.')
            setCallState('idle')
            cleanupCall()
        }
    }

    // ========== CALL CONTROLS ==========

    const toggleMute = () => {
        if (isMuted) {
            // UNMUTE: resume audio capture
            setIsMuted(false)
            isMutedRef.current = false
            resumeListening()
        } else {
            // MUTE: stop capturing audio (purely client-side)
            // If user was speaking, send audio_end so backend processes buffered audio
            if (hasSpeechRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                console.log('[LiveCall] Flushing pending speech before mute')
                wsRef.current.send(JSON.stringify({ type: 'audio_end' }))
                hasSpeechRef.current = false
                speechStartRef.current = null
            }

            setIsMuted(true)
            isMutedRef.current = true
            isListeningRef.current = false

            // Clear VAD timer and stop recording
            if (vadTimerRef.current) { clearTimeout(vadTimerRef.current); vadTimerRef.current = null }
            stopRecording()
        }
    }

    const toggleSpeaker = () => {
        setSpeakerOn(!speakerOn)
    }

    const hangUp = () => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'hangup' }))
        } else {
            setCallState('ended')
            cleanupCall()
        }
    }

    const startNewCall = () => {
        setCallState('idle')
        setSessionId(null)
        setMessages([])
        setLeadScore(null)
        setLeadStatus(null)
        setCallSummary(null)
        setCallDuration(0)
        setError(null)
        setIsProcessing(false)
        setIsMuted(false)
        setSpeakerOn(true)
    }

    const formatDuration = (seconds) => {
        const m = Math.floor(seconds / 60).toString().padStart(2, '0')
        const s = (seconds % 60).toString().padStart(2, '0')
        return `${m}:${s}`
    }

    const getLeadIcon = () => {
        if (!leadStatus) return null
        switch (leadStatus.toLowerCase()) {
            case 'hot': return <Flame className="w-4 h-4" />
            case 'warm': return <Thermometer className="w-4 h-4" />
            case 'cold': return <Snowflake className="w-4 h-4" />
            default: return null
        }
    }

    const getLeadColor = () => {
        if (!leadStatus) return 'text-gray-400'
        switch (leadStatus.toLowerCase()) {
            case 'hot': return 'text-rose-400'
            case 'warm': return 'text-amber-400'
            case 'cold': return 'text-sky-400'
            default: return 'text-gray-400'
        }
    }

    // ========== RENDER ==========

    // PRE-CALL / IDLE
    if (callState === 'idle') {
        return (
            <div className="h-[calc(100vh-8rem)] flex items-center justify-center">
                <div className="glass-card p-10 max-w-lg w-full text-center">
                    <div className="relative mx-auto w-28 h-28 mb-6">
                        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 animate-pulse" />
                        <div className="absolute inset-3 rounded-full bg-gradient-to-br from-emerald-500/30 to-cyan-500/30 flex items-center justify-center">
                            <PhoneCall className="w-12 h-12 text-emerald-400" />
                        </div>
                    </div>

                    <h1 className="text-2xl font-bold text-white mb-2">Start a Live Call</h1>
                    <p className="text-white/50 mb-8">Real-time AI voice conversation — speak naturally, AI responds instantly</p>

                    <div className="mb-6">
                        <label className="block text-sm font-medium text-white/60 mb-2 text-left">
                            <Building2 className="w-4 h-4 inline mr-1.5" />
                            Select Campaign
                        </label>
                        <select
                            value={selectedCampaign?.id || ''}
                            onChange={(e) => {
                                const c = campaigns.find(c => c.id === parseInt(e.target.value))
                                setSelectedCampaign(c)
                            }}
                            className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors"
                            disabled={loadingCampaigns}
                        >
                            <option value="">Choose a campaign...</option>
                            {campaigns.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 rounded-lg bg-rose-500/20 text-rose-400 text-sm flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 flex-shrink-0" />
                            {error}
                        </div>
                    )}

                    <button
                        onClick={startCall}
                        disabled={!selectedCampaign || loadingCampaigns}
                        className="w-full py-4 rounded-xl font-bold text-lg text-white transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed bg-gradient-to-r from-emerald-500 to-cyan-500 hover:shadow-lg hover:shadow-emerald-500/30 hover:scale-[1.02] active:scale-[0.98]"
                    >
                        <PhoneCall className="w-5 h-5 inline mr-2" />
                        Start Call
                    </button>
                </div>
            </div>
        )
    }

    // CONNECTING
    if (callState === 'connecting') {
        return (
            <div className="h-[calc(100vh-8rem)] flex items-center justify-center">
                <div className="text-center">
                    <div className="relative mx-auto w-32 h-32 mb-6">
                        <div className="absolute inset-0 rounded-full border-4 border-emerald-500/30 animate-ping" />
                        <div className="absolute inset-0 rounded-full border-4 border-emerald-500/50 animate-pulse" />
                        <div className="absolute inset-4 rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center">
                            <PhoneCall className="w-10 h-10 text-emerald-400 animate-bounce" />
                        </div>
                    </div>
                    <h2 className="text-xl font-bold text-white mb-2">Connecting...</h2>
                    <p className="text-white/50">Setting up your call with {selectedCampaign?.name}</p>
                </div>
            </div>
        )
    }

    // CALL ENDED
    if (callState === 'ended') {
        return (
            <div className="h-[calc(100vh-8rem)] flex items-center justify-center">
                <div className="glass-card p-10 max-w-lg w-full text-center">
                    <div className="mx-auto w-20 h-20 mb-6 rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center">
                        <CheckCircle2 className="w-10 h-10 text-emerald-400" />
                    </div>

                    <h2 className="text-2xl font-bold text-white mb-2">Call Ended</h2>
                    <p className="text-white/50 mb-6">
                        Duration: {formatDuration(callDuration)} • {callSummary?.turnCount || messages.filter(m => m.role === 'user').length} turns
                    </p>

                    {(callSummary?.leadStatus || leadStatus) && (
                        <div className="mb-6 p-4 rounded-xl bg-white/5 border border-white/10">
                            <p className="text-sm text-white/60 mb-2">Lead Qualification</p>
                            <div className={`flex items-center justify-center gap-2 text-2xl font-bold ${getLeadColor()}`}>
                                {getLeadIcon()}
                                <span className="capitalize">{callSummary?.leadStatus || leadStatus}</span>
                            </div>
                            {(callSummary?.leadScore || leadScore) && (
                                <p className="text-white/40 mt-1">
                                    Score: {((callSummary?.leadScore || leadScore) * 100).toFixed(0)}%
                                </p>
                            )}
                        </div>
                    )}

                    {messages.length > 0 && (
                        <div className="mb-6 max-h-48 overflow-y-auto text-left">
                            <p className="text-xs font-bold text-white/60 uppercase tracking-wider mb-2">Transcript</p>
                            <div className="space-y-2">
                                {messages.map((msg, idx) => (
                                    <div key={idx} className="flex gap-2 text-sm">
                                        <span className={`font-bold flex-shrink-0 ${msg.role === 'user' ? 'text-primary-400' : 'text-emerald-400'}`}>
                                            {msg.role === 'user' ? 'You:' : 'AI:'}
                                        </span>
                                        <span className="text-white/70">{msg.content}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <button
                        onClick={startNewCall}
                        className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-emerald-500 to-cyan-500 hover:shadow-lg hover:shadow-emerald-500/30 transition-all"
                    >
                        <PhoneCall className="w-4 h-4 inline mr-2" />
                        Start New Call
                    </button>
                </div>
            </div>
        )
    }

    // ACTIVE CALL
    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col">
            {/* Header Bar */}
            <div className="glass-card p-4 mb-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-sm font-bold text-emerald-400">LIVE</span>
                        </div>
                        <div>
                            <p className="text-white font-semibold">{selectedCampaign?.name}</p>
                            <p className="text-white/40 text-xs">Session: {sessionId?.slice(0, 8)}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5">
                            <Clock className="w-4 h-4 text-white/50" />
                            <span className="text-white font-mono text-lg">{formatDuration(callDuration)}</span>
                        </div>
                        {leadStatus && (
                            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 ${getLeadColor()}`}>
                                {getLeadIcon()}
                                <span className="text-sm font-bold capitalize">{leadStatus}</span>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Main Area */}
            <div className="flex-1 flex gap-4 overflow-hidden mb-4">
                {/* Center: Waveform + Status */}
                <div className="flex-1 flex flex-col items-center justify-center glass-card p-8 relative overflow-hidden">
                    <div
                        className="absolute inset-0 transition-all duration-500"
                        style={{
                            background: `radial-gradient(circle at center, 
                                ${isPlayingRef.current ? 'rgba(16, 185, 129, 0.2)' :
                                    isSpeaking && !isMuted ? 'rgba(16, 185, 129, 0.15)' :
                                        'rgba(99, 102, 241, 0.05)'} 0%, 
                                transparent 70%)`,
                        }}
                    />

                    {/* Audio Visualizer */}
                    <div className="relative w-48 h-48 mb-8">
                        {[0, 1, 2, 3].map(i => (
                            <div
                                key={i}
                                className="absolute inset-0 rounded-full border-2 transition-all duration-300"
                                style={{
                                    transform: `scale(${1 + i * 0.18 + (isMuted ? 0 : audioLevel * 0.4 * (i + 1))})`,
                                    borderColor: isMuted
                                        ? `rgba(239, 68, 68, ${0.3 - i * 0.06})`
                                        : isSpeaking
                                            ? `rgba(16, 185, 129, ${0.5 - i * 0.1})`
                                            : `rgba(99, 102, 241, ${0.2 - i * 0.04})`,
                                    opacity: 1 - i * 0.2,
                                }}
                            />
                        ))}
                        <div className={`absolute inset-6 rounded-full flex items-center justify-center transition-all duration-300 ${isMuted
                            ? 'bg-rose-500/20 border-2 border-rose-500/40'
                            : isSpeaking
                                ? 'bg-emerald-500/20 border-2 border-emerald-500/40'
                                : 'bg-white/10 border-2 border-white/20'
                            }`}>
                            {isMuted ? (
                                <MicOff className="w-12 h-12 text-rose-400" />
                            ) : isProcessing ? (
                                <Loader2 className="w-12 h-12 text-primary-400 animate-spin" />
                            ) : (
                                <Radio className={`w-12 h-12 ${isSpeaking ? 'text-emerald-400' : 'text-white/40'}`} />
                            )}
                        </div>
                    </div>

                    {/* Status text */}
                    <div className="text-center z-10">
                        {isMuted ? (
                            <p className="text-rose-400 font-semibold text-lg">Muted</p>
                        ) : isProcessing ? (
                            <p className="text-primary-400 font-semibold text-lg flex items-center gap-2">
                                <Activity className="w-5 h-5 animate-pulse" />
                                Thinking...
                            </p>
                        ) : isPlayingRef.current ? (
                            <p className="text-emerald-400 font-semibold text-lg flex items-center gap-2">
                                <Volume2 className="w-5 h-5" />
                                AI Speaking...
                            </p>
                        ) : isSpeaking ? (
                            <p className="text-emerald-400 font-semibold text-lg">Listening...</p>
                        ) : (
                            <p className="text-white/40 text-lg">Speak to the AI</p>
                        )}
                    </div>
                </div>

                {/* Right: Live Transcript */}
                <div className="w-96 flex-shrink-0 glass-card flex flex-col overflow-hidden">
                    <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
                        <Zap className="w-4 h-4 text-amber-400" />
                        <span className="text-sm font-bold text-white/70 uppercase tracking-wider">Live Transcript</span>
                        <span className="ml-auto text-xs text-white/30">{messages.length} messages</span>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {messages.length === 0 ? (
                            <div className="h-full flex items-center justify-center">
                                <p className="text-white/30 text-sm text-center">Transcript will appear here as you speak</p>
                            </div>
                        ) : (
                            messages.map((msg, idx) => (
                                <div key={idx} className={`flex gap-2.5`}>
                                    <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${msg.role === 'user'
                                        ? 'bg-primary-500/20'
                                        : 'bg-emerald-500/20'
                                        }`}>
                                        {msg.role === 'user'
                                            ? <User className="w-3.5 h-3.5 text-primary-400" />
                                            : <Bot className="w-3.5 h-3.5 text-emerald-400" />
                                        }
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className={`text-[10px] font-bold uppercase mb-0.5 ${msg.role === 'user' ? 'text-primary-400' : 'text-emerald-400'
                                            }`}>
                                            {msg.role === 'user' ? 'You' : 'AI'}
                                        </p>
                                        <p className="text-sm text-white/80 leading-relaxed">{msg.content}</p>
                                    </div>
                                </div>
                            ))
                        )}
                        {isProcessing && (
                            <div className="flex gap-2.5">
                                <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-emerald-500/20">
                                    <Bot className="w-3.5 h-3.5 text-emerald-400" />
                                </div>
                                <div className="flex items-center gap-1 pt-2">
                                    <div className="w-2 h-2 bg-emerald-400/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <div className="w-2 h-2 bg-emerald-400/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <div className="w-2 h-2 bg-emerald-400/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                </div>
            </div>

            {/* Call Controls */}
            <div className="glass-card p-6">
                <div className="flex items-center justify-center gap-6">
                    <button
                        onClick={toggleMute}
                        className={`relative p-5 rounded-full transition-all duration-300 ${isMuted
                            ? 'bg-rose-500/20 text-rose-400 border-2 border-rose-500/40 hover:bg-rose-500/30'
                            : 'bg-white/10 text-white border-2 border-white/20 hover:bg-white/20'
                            }`}
                        title={isMuted ? 'Unmute' : 'Mute'}
                    >
                        {isMuted ? <MicOff className="w-7 h-7" /> : <Mic className="w-7 h-7" />}
                        <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-white/40">
                            {isMuted ? 'Unmute' : 'Mute'}
                        </span>
                    </button>

                    <button
                        onClick={hangUp}
                        className="relative p-6 rounded-full bg-gradient-to-br from-rose-500 to-rose-600 text-white shadow-lg shadow-rose-500/30 hover:shadow-xl hover:shadow-rose-500/40 hover:scale-105 active:scale-95 transition-all duration-300"
                        title="Hang Up"
                    >
                        <PhoneOff className="w-8 h-8" />
                        <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-white/40">
                            Hang up
                        </span>
                    </button>

                    <button
                        onClick={toggleSpeaker}
                        className={`relative p-5 rounded-full transition-all duration-300 ${!speakerOn
                            ? 'bg-amber-500/20 text-amber-400 border-2 border-amber-500/40 hover:bg-amber-500/30'
                            : 'bg-white/10 text-white border-2 border-white/20 hover:bg-white/20'
                            }`}
                        title={speakerOn ? 'Mute Speaker' : 'Enable Speaker'}
                    >
                        {speakerOn ? <Volume2 className="w-7 h-7" /> : <VolumeX className="w-7 h-7" />}
                        <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-white/40 whitespace-nowrap">
                            {speakerOn ? 'Speaker' : 'Speaker Off'}
                        </span>
                    </button>
                </div>
            </div>
        </div>
    )
}

export default LiveCallPage
