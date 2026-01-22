/**
 * API client for WebMagic backend
 * Handles authentication, requests, and error handling
 */
import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  AuthTokens,
  LoginCredentials,
  User,
  Business,
  BusinessListResponse,
  CoverageGrid,
  GeneratedSite,
  GenerateSiteRequest,
  PromptTemplate,
  PromptSetting,
  PromptSettingUpdate,
  Campaign,
  CreateCampaignRequest,
  CampaignListResponse,
  Customer,
  CustomerListResponse,
  CustomerStats,
  Payment,
  Subscription,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

class ApiClient {
  private client: AxiosInstance
  private accessToken: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Load token from localStorage
    this.accessToken = localStorage.getItem('access_token')
    if (this.accessToken) {
      this.setAuthToken(this.accessToken)
    }

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearAuth()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // ============================================
  // AUTH METHODS
  // ============================================

  setAuthToken(token: string) {
    this.accessToken = token
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`
    localStorage.setItem('access_token', token)
  }

  clearAuth() {
    this.accessToken = null
    delete this.client.defaults.headers.common['Authorization']
    localStorage.removeItem('access_token')
  }

  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    const formData = new FormData()
    formData.append('username', credentials.email)
    formData.append('password', credentials.password)

    const response = await this.client.post<AuthTokens>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })

    this.setAuthToken(response.data.access_token)
    return response.data
  }

  async unifiedLogin(credentials: LoginCredentials): Promise<{
    access_token: string
    token_type: string
    user_type: 'admin' | 'customer'
    user: any
    email_verified: boolean
  }> {
    const formData = new FormData()
    formData.append('username', credentials.email)
    formData.append('password', credentials.password)

    const response = await this.client.post('/auth/unified-login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })

    this.setAuthToken(response.data.access_token)
    // Store user type for conditional rendering
    localStorage.setItem('user_type', response.data.user_type)
    localStorage.setItem('user', JSON.stringify(response.data.user))
    return response.data
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me')
    return response.data
  }

  logout() {
    this.clearAuth()
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    const response = await this.client.post('/auth/change-password', null, {
      params: {
        current_password: currentPassword,
        new_password: newPassword,
      },
    })
    return response.data
  }

  // ============================================
  // BUSINESS METHODS
  // ============================================

  async getBusinesses(params?: {
    skip?: number
    limit?: number
    status?: string
    has_website?: boolean
  }): Promise<BusinessListResponse> {
    const response = await this.client.get<BusinessListResponse>('/businesses/', {
      params,
    })
    return response.data
  }

  async getBusiness(id: string): Promise<Business> {
    const response = await this.client.get<Business>(`/businesses/${id}`)
    return response.data
  }

  async updateBusinessStatus(
    id: string,
    status: string,
    reason?: string
  ): Promise<Business> {
    const response = await this.client.patch<Business>(`/businesses/${id}/status`, {
      status,
      disqualified_reason: reason,
    })
    return response.data
  }

  // ============================================
  // COVERAGE METHODS
  // ============================================

  async getCoverageGrids(params?: {
    skip?: number
    limit?: number
  }): Promise<{ grids: CoverageGrid[]; total: number }> {
    const response = await this.client.get('/coverage/', { params })
    return response.data
  }

  async triggerScrape(data: {
    location: string
    category: string
  }): Promise<{ message: string; grid_id: string }> {
    const response = await this.client.post('/coverage/scrape', data)
    return response.data
  }

  // ============================================
  // SITE METHODS
  // ============================================

  async getSites(params?: {
    skip?: number
    limit?: number
    status?: string
  }): Promise<{ sites: any[]; total: number }> {
    // Call the admin endpoint for deployed sites
    const response = await this.client.get('/admin/sites', { params })
    return response.data
  }

  async getSite(id: string): Promise<GeneratedSite> {
    const response = await this.client.get<GeneratedSite>(`/sites/${id}`)
    return response.data
  }

  async generateSite(data: GenerateSiteRequest): Promise<{ site_id: string }> {
    const response = await this.client.post('/sites/generate', data)
    return response.data
  }

  // ============================================
  // PROMPT SETTINGS METHODS
  // ============================================

  async getPromptTemplates(): Promise<PromptTemplate[]> {
    const response = await this.client.get<PromptTemplate[]>('/settings/templates')
    return response.data
  }

  async getPromptSettings(agentName: string): Promise<{ settings: PromptSetting[]; total: number }> {
    const response = await this.client.get<{ settings: PromptSetting[]; total: number }>(
      `/settings/prompts`,
      { params: { agent_name: agentName, active_only: true } }
    )
    return response.data
  }

  async updatePromptSetting(
    settingId: string,
    data: PromptSettingUpdate
  ): Promise<PromptSetting> {
    const response = await this.client.patch<PromptSetting>(
      `/settings/prompts/${settingId}`,
      data
    )
    return response.data
  }

  // ============================================
  // CAMPAIGN METHODS
  // ============================================

  async getCampaigns(params?: {
    skip?: number
    limit?: number
    status?: string
  }): Promise<CampaignListResponse> {
    const response = await this.client.get<CampaignListResponse>('/campaigns/', {
      params,
    })
    return response.data
  }

  async getCampaign(id: string): Promise<Campaign> {
    const response = await this.client.get<Campaign>(`/campaigns/${id}`)
    return response.data
  }

  // ============================================
  // COVERAGE CAMPAIGN METHODS
  // ============================================

  async getCoverageStats(): Promise<any> {
    const response = await this.client.get<any>('/coverage/campaigns/stats')
    return response.data
  }

  async getCoverageLocations(params?: { limit?: number }): Promise<any[]> {
    const response = await this.client.get<any[]>('/coverage/campaigns/locations', {
      params,
    })
    return response.data
  }

  async getCoverageCategories(params?: { limit?: number }): Promise<any[]> {
    const response = await this.client.get<any[]>('/coverage/campaigns/categories', {
      params,
    })
    return response.data
  }

  async createCampaign(data: CreateCampaignRequest): Promise<Campaign> {
    const response = await this.client.post<Campaign>('/campaigns', data)
    return response.data
  }

  async sendCampaign(id: string): Promise<{ status: string }> {
    const response = await this.client.post(`/campaigns/${id}/send`)
    return response.data
  }

  async getCampaignStats(): Promise<{
    total: number
    sent: number
    opened: number
    clicked: number
    open_rate: number
    click_rate: number
  }> {
    const response = await this.client.get('/campaigns/stats')
    return response.data
  }

  // ============================================
  // CUSTOMER & PAYMENT METHODS
  // ============================================

  async getCustomers(params?: {
    skip?: number
    limit?: number
    status?: string
  }): Promise<CustomerListResponse> {
    const response = await this.client.get<CustomerListResponse>('/payments/customers', {
      params,
    })
    return response.data
  }

  async getCustomer(id: string): Promise<Customer> {
    const response = await this.client.get<Customer>(`/payments/customers/${id}`)
    return response.data
  }

  async getCustomerStats(): Promise<CustomerStats> {
    const response = await this.client.get<CustomerStats>('/payments/customers/stats')
    return response.data
  }

  async getCustomerPayments(customerId: string): Promise<{ payments: Payment[]; total: number }> {
    const response = await this.client.get(`/payments/customers/${customerId}/payments`)
    return response.data
  }

  async getCustomerSubscriptions(customerId: string): Promise<Subscription[]> {
    const response = await this.client.get<Subscription[]>(
      `/payments/customers/${customerId}/subscriptions`
    )
    return response.data
  }

  async cancelSubscription(
    subscriptionId: string,
    reason?: string
  ): Promise<{ status: string }> {
    const response = await this.client.post(
      `/payments/subscriptions/${subscriptionId}/cancel`,
      { reason }
    )
    return response.data
  }

  // ============================================
  // IMAGE GENERATION METHODS
  // ============================================

  async testImageGeneration(
    data: import('@/types').ImageGenerationRequest
  ): Promise<import('@/types').ImageGenerationResponse> {
    const response = await this.client.post<import('@/types').ImageGenerationResponse>(
      '/sites/test-image-generation',
      data
    )
    return response.data
  }

  async downloadGeneratedImage(
    data: import('@/types').ImageGenerationRequest
  ): Promise<Blob> {
    const response = await this.client.post(
      '/sites/test-image-generation/download',
      data,
      {
        responseType: 'blob',
      }
    )
    return response.data
  }

  // ============================================
  // SYSTEM SETTINGS METHODS
  // ============================================

  async getAIConfig(): Promise<any> {
    const response = await this.client.get('/system/ai-config')
    return response.data
  }

  async getAIProviders(): Promise<any> {
    const response = await this.client.get('/system/ai-providers')
    return response.data
  }

  async updateSystemSetting(key: string, value: string): Promise<any> {
    const response = await this.client.post('/system/settings', { key, value })
    return response.data
  }

  async getSettingsByCategory(category: string): Promise<any> {
    const response = await this.client.get(`/system/settings/${category}`)
    return response.data
  }

  // ============================================
  // EDIT REQUESTS METHODS (Phase 4)
  // ============================================

  async createEditRequest(
    siteId: string,
    data: {
      request_text: string
      request_type?: string
      target_section?: string
    }
  ): Promise<any> {
    const response = await this.client.post(`/sites/${siteId}/edits`, data)
    return response.data
  }

  async listEditRequests(
    siteId: string,
    params?: {
      status?: string
      page?: number
      page_size?: number
    }
  ): Promise<any> {
    const response = await this.client.get(`/sites/${siteId}/edits`, { params })
    return response.data
  }

  async getEditRequest(siteId: string, editId: string): Promise<any> {
    const response = await this.client.get(`/sites/${siteId}/edits/${editId}`)
    return response.data
  }

  async getEditRequestStats(siteId: string): Promise<any> {
    const response = await this.client.get(`/sites/${siteId}/edits/stats`)
    return response.data
  }

  async approveEditRequest(
    siteId: string,
    editId: string,
    feedback?: string
  ): Promise<any> {
    const response = await this.client.post(`/sites/${siteId}/edits/${editId}/approve`, {
      approved: true,
      feedback,
    })
    return response.data
  }

  async rejectEditRequest(
    siteId: string,
    editId: string,
    reason: string
  ): Promise<any> {
    const response = await this.client.post(`/sites/${siteId}/edits/${editId}/reject`, {
      approved: false,
      feedback: reason,
    })
    return response.data
  }

  async cancelEditRequest(siteId: string, editId: string): Promise<void> {
    await this.client.delete(`/sites/${siteId}/edits/${editId}`)
  }

  // ============================================
  // CUSTOM DOMAINS METHODS (Phase 5)
  // ============================================

  async connectDomain(
    siteId: string,
    data: {
      domain: string
      verification_method?: string
    }
  ): Promise<any> {
    const response = await this.client.post(
      '/domains/connect',
      data,
      { params: { site_id: siteId } }
    )
    return response.data
  }

  async verifyDomain(
    siteId: string,
    domain: string
  ): Promise<any> {
    const response = await this.client.post(
      '/domains/verify',
      { domain },
      { params: { site_id: siteId } }
    )
    return response.data
  }

  async getDomainStatus(siteId: string): Promise<any> {
    const response = await this.client.get('/domains/status', {
      params: { site_id: siteId }
    })
    return response.data
  }

  async disconnectDomain(siteId: string): Promise<any> {
    const response = await this.client.delete('/domains/disconnect', {
      params: { site_id: siteId }
    })
    return response.data
  }

  // ============================================
  // SUPPORT TICKETS METHODS (Phase 6)
  // ============================================

  async getTicketCategories(): Promise<any> {
    const response = await this.client.get('/tickets/categories')
    return response.data
  }

  async createTicket(data: {
    subject: string
    description: string
    category: string
    site_id?: string
  }): Promise<any> {
    const response = await this.client.post('/tickets/', data)
    return response.data
  }

  async listTickets(params?: {
    status?: string
    category?: string
    limit?: number
    offset?: number
  }): Promise<any> {
    const response = await this.client.get('/tickets/', { params })
    return response.data
  }

  async getTicket(ticketId: string): Promise<any> {
    const response = await this.client.get(`/tickets/${ticketId}`)
    return response.data
  }

  async getTicketStats(): Promise<any> {
    const response = await this.client.get('/tickets/stats')
    return response.data
  }

  async addTicketMessage(ticketId: string, message: string): Promise<any> {
    const response = await this.client.post(`/tickets/${ticketId}/messages`, {
      message
    })
    return response.data
  }

  async updateTicketStatus(ticketId: string, status: string): Promise<any> {
    const response = await this.client.patch(`/tickets/${ticketId}/status`, {
      status
    })
    return response.data
  }
}

// Export singleton instance
export const api = new ApiClient()
