import axios from 'axios'

// Create axios instance
const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000,
})

// Request interceptor
api.interceptors.request.use(
    (config) => {
        // Add any auth headers here if needed
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor
api.interceptors.response.use(
    (response) => response.data,
    (error) => {
        console.error('API Error:', error.response?.data || error.message)
        return Promise.reject(error)
    }
)

// Campaign APIs
export const campaignsAPI = {
    list: (params = {}) => api.get('/campaigns', { params }),
    get: (id) => api.get(`/campaigns/${id}`),
    create: (data) => api.post('/campaigns', data),
    update: (id, data) => api.put(`/campaigns/${id}`, data),
    delete: (id) => api.delete(`/campaigns/${id}`),
    uploadFaqs: (id, faqs) => api.post(`/campaigns/${id}/faqs`, faqs),
}

// Call APIs
export const callsAPI = {
    list: (params = {}) => api.get('/calls', { params }),
    get: (id) => api.get(`/calls/${id}`),
    initiate: (data) => api.post('/calls/initiate', data),
    end: (id) => api.post(`/calls/${id}/end`),
    processText: (id, text) => api.post(`/calls/${id}/process-text`, null, { params: { text } }),
    retellCall: (data) => api.post('/calls/retell-call', typeof data === 'string' ? { phone_number: data } : data),
}

// Lead APIs
export const leadsAPI = {
    list: (params = {}) => api.get('/leads', { params }),
    get: (id) => api.get(`/leads/${id}`),
    create: (data) => api.post('/leads', data),
    update: (id, data) => api.put(`/leads/${id}`, data),
    delete: (id) => api.delete(`/leads/${id}`),
    stats: (campaignId) => api.get('/leads/stats', { params: { campaign_id: campaignId } }),
}

// Analytics APIs
export const analyticsAPI = {
    overview: (campaignId) => api.get('/analytics/overview', { params: { campaign_id: campaignId } }),
    calls: (days = 7, campaignId) => api.get('/analytics/calls', { params: { days, campaign_id: campaignId } }),
    languages: (campaignId) => api.get('/analytics/languages', { params: { campaign_id: campaignId } }),
    leads: (days = 7, campaignId) => api.get('/analytics/leads', { params: { days, campaign_id: campaignId } }),
}

// Test APIs (work without database)
export const testAPI = {
    status: () => api.get('/test/'),
    healthServices: () => api.get('/test/health-services'),
    call: (phone_number, message) => api.post('/test/call', { phone_number, message }),
    llm: (text, campaign_context) => api.post('/test/llm', { text, campaign_context }),
    tts: (text, language) => api.post('/test/tts', { text, language }),
}

// Bulk Call APIs (Retell AI — proxied to bulk-call-service on port 3001)
export const bulkCallAPI = {
    upload: (formData) =>
        api.post('/bulk-call/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 300000,
            baseURL: '/bulk-api',
        }),
    intentHistory: () => api.get('/intent-history', { baseURL: '/bulk-api' }),
    classifyIntent: (callId, phone, name) =>
        api.get(`/intent/${callId}`, { baseURL: '/bulk-api', params: { phone, name }, timeout: 360000 }),
    downloadCSVUrl: '/bulk-api/download-intent-csv',
}

// Feedback APIs
export const feedbackAPI = {
    list: (params = {}) => api.get('/feedback', { params }),
    create: (data) => api.post('/feedback', data),
}

export default api
