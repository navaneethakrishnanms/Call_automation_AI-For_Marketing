import { useState, useEffect } from 'react';
import { PhoneCall, Clock, MessageSquare, CheckCircle, Trash2, Loader2, Phone } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function CallRequestsPage() {
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchRequests = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`${API_URL}/call-requests`);
            setRequests(response.data.items || []);
        } catch (error) {
            console.error('Failed to fetch call requests:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
    }, []);

    const handleUpdateStatus = async (id, status) => {
        try {
            await axios.put(`${API_URL}/call-requests/${id}`, { status });
            fetchRequests();
        } catch (error) {
            console.error('Failed to update status:', error);
        }
    };

    const handleDelete = async (id) => {
        try {
            await axios.delete(`${API_URL}/call-requests/${id}`);
            fetchRequests();
        } catch (error) {
            console.error('Failed to delete request:', error);
        }
    };

    const handleCallUser = async (req) => {
        try {
            await axios.post(`${API_URL}/calls/retell-call`, { phone_number: req.phone_number });
            await handleUpdateStatus(req.id, 'done');
        } catch (error) {
            console.error('Failed to trigger call:', error);
            alert('Failed to initiate call. Check console for details.');
        }
    };


    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between animate-slide-up">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Call Requests</h1>
                    <p className="text-white/60">Manage incoming call requests from users.</p>
                </div>
            </div>

            <div className="glass-card p-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
                {requests.length === 0 ? (
                    <div className="py-12 text-center">
                        <PhoneCall className="w-12 h-12 text-white/20 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-white mb-1">No Call Requests</h3>
                        <p className="text-white/50">There are no pending call requests right now.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="text-left text-white/50 text-sm border-b border-white/10">
                                    <th className="pb-4 font-medium">Contact Details</th>
                                    <th className="pb-4 font-medium">Preferred Time</th>
                                    <th className="pb-4 font-medium">Message</th>
                                    <th className="pb-4 font-medium">Status</th>
                                    <th className="pb-4 font-medium text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {requests.map((req) => (
                                    <tr key={req.id} className="table-row">
                                        <td className="py-4">
                                            <div className="font-medium text-white">{req.name}</div>
                                            <div className="text-sm text-white/60 flex items-center gap-1 mt-1">
                                                <PhoneCall className="w-3 h-3" />
                                                {req.phone_number}
                                            </div>
                                        </td>
                                        <td className="py-4">
                                            <div className="flex items-center gap-1.5 text-white/80">
                                                <Clock className="w-4 h-4 text-primary-400" />
                                                {req.preferred_time || 'Not specified'}
                                            </div>
                                            <div className="text-xs text-white/40 mt-1">
                                                Requested: {new Date(req.created_at).toLocaleDateString()}
                                            </div>
                                        </td>
                                        <td className="py-4">
                                            {req.message ? (
                                                <div className="flex items-start gap-1.5 max-w-xs">
                                                    <MessageSquare className="w-4 h-4 text-white/40 mt-0.5 flex-shrink-0" />
                                                    <span className="text-sm text-white/70 truncate" title={req.message}>
                                                        {req.message}
                                                    </span>
                                                </div>
                                            ) : (
                                                <span className="text-sm text-white/30 italic">No message</span>
                                            )}
                                        </td>
                                        <td className="py-4">
                                            <span className={`badge ${req.status === 'done' ? 'badge-active' : 'badge-warm'}`}>
                                                {req.status === 'done' ? 'Done' : 'Pending'}
                                            </span>
                                        </td>
                                        <td className="py-4">
                                            <div className="flex items-center justify-end gap-2">
                                                {req.status !== 'done' && (
                                                    <>
                                                        <button 
                                                            onClick={() => handleCallUser(req)}
                                                            className="p-2 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors"
                                                            title="Initiate Call"
                                                        >
                                                            <Phone className="w-4 h-4" />
                                                        </button>
                                                        <button 
                                                            onClick={() => handleUpdateStatus(req.id, 'done')}
                                                            className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                                                            title="Mark as Done"
                                                        >
                                                            <CheckCircle className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                )}
                                                <button 
                                                    onClick={() => handleDelete(req.id)}
                                                    className="p-2 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors"
                                                    title="Delete Request"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

