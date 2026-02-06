import { useState, useRef, useEffect } from 'react'
import {
    Mic,
    MicOff,
    Volume2,
    VolumeX,
    Loader2,
    MessageCircle,
    Phone,
    RefreshCw,
    Flame,
    Thermometer,
    Snowflake,
    Send
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

    const mediaRecorderRef = useRef(null)
    const audioChunksRef = useRef([])
    const audioRef = useRef(null)
    const messagesEndRef = useRef(null)

    // Auto-scroll to bottom of messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Initialize audio element
    useEffect(() => {
        audioRef.current = new Audio()
        audioRef.current.onended = () => setIsPlaying(false)
        audioRef.current.onerror = () => {
            console.error('Audio playback error')
            setIsPlaying(false)
        }
    }, [])

    const startRecording = async () => {
        try {
            setError(null)
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
            })

            mediaRecorderRef.current = mediaRecorder
            audioChunksRef.current = []

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data)
                }
            }

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
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop()
            setIsRecording(false)
        }
    }

    const sendAudioToBackend = async (audioBlob) => {
        setIsProcessing(true)
        setError(null)

        try {
            const formData = new FormData()
            formData.append('audio', audioBlob, 'recording.webm')
            if (sessionId) {
                formData.append('session_id', sessionId)
            }

            const response = await fetch(`${API_BASE}/api/voice/chat/audio`, {
                method: 'POST',
                body: formData
            })

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }

            const data = await response.json()
            handleResponse(data)

        } catch (err) {
            console.error('Failed to send audio:', err)
            setError('Failed to process audio. Please try again.')
        } finally {
            setIsProcessing(false)
        }
    }

    const sendTextMessage = async () => {
        if (!textInput.trim()) return

        const userText = textInput.trim()
        setTextInput('')
        setIsProcessing(true)
        setError(null)

        // Add user message immediately
        setMessages(prev => [...prev, {
            role: 'user',
            content: userText,
            timestamp: new Date()
        }])

        try {
            const response = await fetch(`${API_BASE}/api/voice/chat/text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: userText,
                    session_id: sessionId
                })
            })

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }

            const data = await response.json()
            handleResponse(data, true) // Skip adding user message

        } catch (err) {
            console.error('Failed to send text:', err)
            setError('Failed to process message. Please try again.')
        } finally {
            setIsProcessing(false)
        }
    }

    const handleResponse = (data, skipUserMessage = false) => {
        // Update session
        if (data.session_id) {
            setSessionId(data.session_id)
        }

        // Update lead info
        if (data.lead_score !== null) {
            setLeadScore(data.lead_score)
        }
        if (data.lead_status) {
            setLeadStatus(data.lead_status)
        }

        // Add messages
        setMessages(prev => [
            ...prev,
            ...(skipUserMessage ? [] : []),
            {
                role: 'assistant',
                content: data.text_response,
                language: data.detected_language,
                timestamp: new Date()
            }
        ])

        // Play audio response
        if (audioEnabled && data.audio_base64 && audioRef.current) {
            // Sarvam returns WAV audio
            const audioUrl = `data:audio/wav;base64,${data.audio_base64}`
            console.log('Playing audio, length:', data.audio_base64.length)
            audioRef.current.src = audioUrl
            audioRef.current.play().catch(err => {
                console.error('Audio playback failed:', err)
                setIsPlaying(false)
            })
            setIsPlaying(true)
        } else if (!data.audio_base64) {
            console.warn('No audio returned from backend')
        }
    }

    const startNewSession = () => {
        setSessionId(null)
        setMessages([])
        setLeadScore(null)
        setLeadStatus(null)
        setError(null)
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

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col">
            {/* Header */}
            <div className="glass-card p-4 mb-4 flex items-center justify-between">
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
                    {/* Lead Score Badge */}
                    {leadStatus && (
                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${getLeadColor()}`}>
                            {getLeadIcon()}
                            <span className="font-medium capitalize">{leadStatus}</span>
                            {leadScore !== null && (
                                <span className="text-xs opacity-70">({(leadScore * 100).toFixed(0)}%)</span>
                            )}
                        </div>
                    )}

                    {/* Audio Toggle */}
                    <button
                        onClick={() => setAudioEnabled(!audioEnabled)}
                        className={`p-2 rounded-lg transition-colors ${audioEnabled
                            ? 'bg-primary-500/20 text-primary-400 hover:bg-primary-500/30'
                            : 'bg-white/5 text-white/50 hover:bg-white/10'
                            }`}
                        title={audioEnabled ? 'Mute audio' : 'Enable audio'}
                    >
                        {audioEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                    </button>

                    {/* New Session Button */}
                    <button
                        onClick={startNewSession}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 text-white/70 hover:bg-white/10 hover:text-white transition-colors"
                    >
                        <RefreshCw className="w-4 h-4" />
                        New Session
                    </button>
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 glass-card p-4 overflow-y-auto mb-4">
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center">
                        <div className="p-4 rounded-full bg-gradient-to-br from-primary-500/20 to-accent-500/20 mb-4">
                            <Mic className="w-12 h-12 text-primary-400" />
                        </div>
                        <h2 className="text-xl font-semibold text-white mb-2">Start a Conversation</h2>
                        <p className="text-white/50 max-w-md">
                            Click the microphone button and speak, or type a message below.
                            The AI will respond in your language (English, Tamil, or Tanglish).
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`max-w-[80%] px-4 py-3 rounded-2xl ${msg.role === 'user'
                                        ? 'bg-primary-500/30 text-white rounded-br-sm'
                                        : 'bg-white/10 text-white rounded-bl-sm'
                                        }`}
                                >
                                    <p>{msg.content}</p>
                                    {msg.language && msg.role === 'assistant' && (
                                        <p className="text-xs text-white/40 mt-1 capitalize">
                                            {msg.language}
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Error Display */}
            {error && (
                <div className="mb-4 p-3 rounded-lg bg-rose-500/20 text-rose-400 text-sm">
                    {error}
                </div>
            )}

            {/* Input Area */}
            <div className="glass-card p-4">
                <div className="flex items-center gap-3">
                    {/* Text Input */}
                    <div className="flex-1 flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 focus-within:border-primary-500/50">
                        <input
                            type="text"
                            value={textInput}
                            onChange={(e) => setTextInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && sendTextMessage()}
                            placeholder="Type a message..."
                            className="flex-1 bg-transparent text-white placeholder-white/30 outline-none"
                            disabled={isProcessing}
                        />
                        <button
                            onClick={sendTextMessage}
                            disabled={isProcessing || !textInput.trim()}
                            className="p-2 rounded-lg text-white/50 hover:text-primary-400 hover:bg-white/5 disabled:opacity-30 transition-colors"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Voice Recording Button */}
                    <button
                        onClick={isRecording ? stopRecording : startRecording}
                        disabled={isProcessing}
                        className={`relative p-4 rounded-full transition-all ${isRecording
                            ? 'bg-rose-500 text-white animate-pulse'
                            : isProcessing
                                ? 'bg-white/10 text-white/30'
                                : 'bg-gradient-to-br from-primary-500 to-accent-500 text-white hover:shadow-lg hover:shadow-primary-500/30'
                            }`}
                    >
                        {isProcessing ? (
                            <Loader2 className="w-6 h-6 animate-spin" />
                        ) : isRecording ? (
                            <MicOff className="w-6 h-6" />
                        ) : (
                            <Mic className="w-6 h-6" />
                        )}

                        {/* Recording indicator ring */}
                        {isRecording && (
                            <span className="absolute inset-0 rounded-full border-4 border-rose-500/50 animate-ping" />
                        )}
                    </button>
                </div>

                {/* Status Text */}
                <div className="mt-2 text-center text-sm text-white/40">
                    {isRecording ? (
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
