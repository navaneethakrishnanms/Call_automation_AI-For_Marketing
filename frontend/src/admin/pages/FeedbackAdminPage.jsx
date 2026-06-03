import { useState, useEffect } from 'react'
import { MessageSquare, Star, Calendar, User } from 'lucide-react'
import { feedbackAPI } from '../../shared/services/client'
import { formatDate } from '../../shared/utils/formatters'

function FeedbackAdminPage() {
    const [feedbacks, setFeedbacks] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetchFeedbacks()
    }, [])

    async function fetchFeedbacks() {
        try {
            setLoading(true)
            const data = await feedbackAPI.list()
            setFeedbacks(data || [])
        } catch (err) {
            console.error('Failed to fetch feedbacks:', err)
            setError('Failed to load feedback entries.')
        } finally {
            setLoading(false)
        }
    }

    const renderStars = (rating) => {
        if (!rating) return <span className="text-white/30 text-sm">No rating</span>
        return (
            <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                    <Star 
                        key={star} 
                        className={`w-4 h-4 ${star <= rating ? 'text-amber-400 fill-amber-400' : 'text-white/20'}`} 
                    />
                ))}
            </div>
        )
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
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white mb-2">User Feedback</h2>
                    <p className="text-white/60">Review feedback submitted by users.</p>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 glass-card rounded-xl">
                    <MessageSquare className="w-5 h-5 text-primary-400" />
                    <span className="text-white font-medium">{feedbacks.length} Total</span>
                </div>
            </div>

            {error ? (
                <div className="p-4 bg-rose-500/20 border border-rose-500/30 text-rose-300 rounded-xl">
                    {error}
                </div>
            ) : feedbacks.length === 0 ? (
                <div className="glass-card p-12 text-center">
                    <MessageSquare className="w-12 h-12 text-white/20 mx-auto mb-4" />
                    <p className="text-white/50 text-lg">No feedback entries found.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {feedbacks.map((fb) => (
                        <div key={fb.id} className="glass-card p-6 relative overflow-hidden flex flex-col h-full hover:-translate-y-1 transition-transform">
                            {/* Decorative gradient for highly rated feedback */}
                            {fb.rating >= 4 && (
                                <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-full blur-2xl pointer-events-none -mt-10 -mr-10" />
                            )}
                            
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
                                        <User className="w-5 h-5 text-primary-400" />
                                    </div>
                                    <div>
                                        <p className="text-white font-medium">{fb.user_name || 'Anonymous'}</p>
                                        <div className="flex items-center gap-1 text-white/40 text-xs mt-1">
                                            <Calendar className="w-3 h-3" />
                                            <span>{formatDate(fb.created_at)}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="mb-4">
                                {renderStars(fb.rating)}
                            </div>
                            
                            <div className="bg-white/5 rounded-xl p-4 flex-grow border border-white/5">
                                <p className="text-white/80 whitespace-pre-wrap text-sm leading-relaxed">
                                    {fb.message}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

export default FeedbackAdminPage
