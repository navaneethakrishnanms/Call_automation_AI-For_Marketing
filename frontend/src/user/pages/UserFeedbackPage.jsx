import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { MessageSquare, Star, Send, Sparkles, ArrowLeft } from 'lucide-react'
import { feedbackAPI } from '../../shared/services/client'

function UserFeedbackPage() {
    const navigate = useNavigate()
    const [formData, setFormData] = useState({
        user_name: '',
        message: '',
        rating: 5,
    })
    const [submitting, setSubmitting] = useState(false)
    const [success, setSuccess] = useState(false)
    const [error, setError] = useState(null)

    const handleChange = (e) => {
        const { name, value } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: value
        }))
    }

    const handleRatingClick = (rating) => {
        setFormData(prev => ({ ...prev, rating }))
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!formData.message.trim()) {
            setError("Feedback message is required.")
            return
        }

        setSubmitting(true)
        setError(null)
        try {
            await feedbackAPI.create(formData)
            setSuccess(true)
            setFormData({ user_name: '', message: '', rating: 5 })
            setTimeout(() => setSuccess(false), 5000)
        } catch (err) {
            console.error("Feedback submission error:", err)
            setError("Failed to submit feedback. Please try again later.")
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="max-w-2xl mx-auto py-8">
            <button 
                onClick={() => navigate('/request-call')} 
                className="mb-4 flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 text-white/60 hover:text-white hover:bg-white/10 transition-colors"
            >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Home</span>
            </button>

            <div className="glass-card p-8 relative overflow-hidden">
                {/* Decorative background elements */}
                <div className="absolute top-0 right-0 -mr-20 -mt-20 w-64 h-64 bg-primary-500/20 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-64 h-64 bg-accent-500/20 rounded-full blur-3xl pointer-events-none" />

                <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
                            <MessageSquare className="w-6 h-6 text-primary-400" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white">We Value Your Feedback</h2>
                            <p className="text-white/60">Help us improve your experience.</p>
                        </div>
                    </div>

                    {success ? (
                        <div className="p-6 text-center glass-card bg-emerald-500/10 border-emerald-500/30 mb-6 rounded-xl animate-fade-in">
                            <Sparkles className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                            <h3 className="text-xl font-semibold text-emerald-300 mb-2">Thank You!</h3>
                            <p className="text-emerald-400/80">Your feedback has been submitted successfully.</p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {error && (
                                <div className="p-4 bg-rose-500/20 border border-rose-500/30 text-rose-300 rounded-xl">
                                    {error}
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-white/70 mb-2">Your Name (Optional)</label>
                                <input
                                    type="text"
                                    name="user_name"
                                    value={formData.user_name}
                                    onChange={handleChange}
                                    placeholder="John Doe"
                                    className="input-field"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-white/70 mb-2">Rating</label>
                                <div className="flex items-center gap-2">
                                    {[1, 2, 3, 4, 5].map((star) => (
                                        <button
                                            key={star}
                                            type="button"
                                            onClick={() => handleRatingClick(star)}
                                            className="focus:outline-none transition-transform hover:scale-110"
                                        >
                                            <Star 
                                                className={`w-8 h-8 ${star <= formData.rating ? 'text-amber-400 fill-amber-400' : 'text-white/20'}`} 
                                            />
                                        </button>
                                    ))}
                                    <span className="ml-3 text-white/50 text-sm">{formData.rating} out of 5</span>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-white/70 mb-2">Your Feedback *</label>
                                <textarea
                                    name="message"
                                    value={formData.message}
                                    onChange={handleChange}
                                    required
                                    rows="5"
                                    placeholder="Tell us what you love or what we can do better..."
                                    className="input-field resize-none"
                                />
                            </div>

                            <button 
                                type="submit" 
                                disabled={submitting || !formData.message.trim()}
                                className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {submitting ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        <span>Submitting...</span>
                                    </>
                                ) : (
                                    <>
                                        <Send className="w-5 h-5" />
                                        <span>Submit Feedback</span>
                                    </>
                                )}
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </div>
    )
}

export default UserFeedbackPage
