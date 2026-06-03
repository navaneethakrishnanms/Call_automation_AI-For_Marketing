import { useState } from 'react';
import { Mic, PhoneCall, Send, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

// Get API base URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function UserDashboardPage() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        name: '',
        phone_number: '',
        preferred_time: '',
        message: ''
    });
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await axios.post(`${API_URL}/call-requests`, formData);
            setSuccess(true);
            setFormData({ name: '', phone_number: '', preferred_time: '', message: '' });
            setTimeout(() => setSuccess(false), 5000);
        } catch (error) {
            console.error('Failed to submit call request:', error);
            alert('Failed to submit request. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8 p-4">
            <div className="text-center mb-12 animate-slide-up">
                <h1 className="text-3xl font-bold text-white mb-4">How can we help you today?</h1>
                <p className="text-white/60">Choose an option below to connect with our team</p>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
                {/* Voice Chat Option */}
                <div className="glass-card p-8 animate-slide-up" style={{ animationDelay: '100ms' }}>
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mb-6 shadow-lg shadow-primary-500/30">
                        <Mic className="w-8 h-8 text-white" />
                    </div>
                    <h2 className="text-2xl font-semibold text-white mb-4">Talk to AI Assistant</h2>
                    <p className="text-white/60 mb-8 min-h-[60px]">
                        Start an immediate voice conversation with our intelligent AI assistant to get answers to your questions right away.
                    </p>
                    <button 
                        onClick={() => navigate('/user/voice-chat')}
                        className="w-full btn-primary flex items-center justify-center gap-2"
                    >
                        <Mic className="w-5 h-5" />
                        Start Voice Chat
                    </button>
                </div>

                {/* Request a Call Option */}
                <div className="glass-card p-8 animate-slide-up" style={{ animationDelay: '200ms' }}>
                    <div className="flex items-center gap-4 mb-6">
                        <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center">
                            <PhoneCall className="w-6 h-6 text-accent-400" />
                        </div>
                        <h2 className="text-2xl font-semibold text-white">Request a Call</h2>
                    </div>
                    
                    {success ? (
                        <div className="flex flex-col items-center justify-center h-[300px] text-center space-y-4">
                            <CheckCircle2 className="w-16 h-16 text-emerald-400 animate-pulse" />
                            <h3 className="text-xl font-semibold text-white">Request Sent!</h3>
                            <p className="text-white/60">We'll get back to you shortly.</p>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <input
                                    type="text"
                                    placeholder="Your Name"
                                    required
                                    className="input-field"
                                    value={formData.name}
                                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                                />
                            </div>
                            <div>
                                <input
                                    type="tel"
                                    placeholder="Phone Number"
                                    required
                                    className="input-field"
                                    value={formData.phone_number}
                                    onChange={(e) => setFormData({...formData, phone_number: e.target.value})}
                                />
                            </div>
                            <div>
                                <input
                                    type="text"
                                    placeholder="Preferred Time (e.g. Tomorrow 2 PM)"
                                    className="input-field"
                                    value={formData.preferred_time}
                                    onChange={(e) => setFormData({...formData, preferred_time: e.target.value})}
                                />
                            </div>
                            <div>
                                <textarea
                                    placeholder="What would you like to discuss? (Optional)"
                                    className="input-field min-h-[100px] resize-y"
                                    value={formData.message}
                                    onChange={(e) => setFormData({...formData, message: e.target.value})}
                                />
                            </div>
                            <button 
                                type="submit" 
                                disabled={submitting}
                                className="w-full btn-secondary flex items-center justify-center gap-2"
                            >
                                {submitting ? (
                                    <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <>
                                        <Send className="w-5 h-5" />
                                        Submit Request
                                    </>
                                )}
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
}

