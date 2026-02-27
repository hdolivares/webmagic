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
  ReadyBusiness,
  ReadyBusinessesResponse,
  SMSPreviewRequest,
  SMSPreviewResponse,
  BulkCampaignCreateRequest,
  BulkCampaignCreateResponse,
} from '@/types'

// ─── Conversation types ────────────────────────────────────────────────────

export interface ConversationSummary {
  contact_phone: string
  business_id: string | null
  business_name: string | null
  business_category: string | null
  business_city: string | null
  last_message_body: string
  last_message_direction: 'inbound' | 'outbound'
  last_message_at: string
  message_count: number
  inbound_count: number
}

export interface SMSMessageItem {
  id: string
  campaign_id: string | null
  business_id: string | null
  direction: 'inbound' | 'outbound'
  from_phone: string
  to_phone: string
  body: string
  status: string
  telnyx_message_id: string | null
  segments: number | null
  cost: number | null
  error_code: string | null
  error_message: string | null
  received_at: string | null
  sent_at: string | null
  delivered_at: string | null
  created_at: string
  business_name: string | null
  business_city: string | null
  business_state: string | null
}

// ─── Verification Queue types ─────────────────────────────────────────────

export interface VerificationMatchSignals {
  phone_match: boolean
  address_match: boolean
  name_match: boolean
}

export interface VerificationQueueItem {
  id: string
  name: string
  address: string | null
  phone: string | null
  city: string | null
  state: string | null
  category: string | null
  rating: number | null
  review_count: number
  outscraper_website: string | null
  candidate_url: string | null
  candidate_title: string | null
  candidate_phones: string[]
  candidate_emails: string[]
  candidate_content_preview: string | null
  candidate_quality_score: number | null
  llm_reasoning: string | null
  llm_confidence: number | null
  invalid_reason: 'wrong_business' | 'no_contact' | string | null
  match_signals: VerificationMatchSignals | null
  has_generated_site: boolean
  generated_site_subdomain: string | null
  generated_site_url: string | null
  website_validated_at: string | null
}

export interface VerificationQueueResponse {
  items: VerificationQueueItem[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface VerificationDecisionRequest {
  decision: 'valid_website' | 'no_website' | 're_run'
  website_url?: string
  notes?: string
}

// ──────────────────────────────────────────────────────────────────────────

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
          const isLoginEndpoint = error.config?.url?.includes('/auth/login') || 
                                  error.config?.url?.includes('/auth/unified-login')
          // Callers can pass { suppressAuthRedirect: true } in axios config
          // to handle 401 themselves (e.g. background polling) without forcing logout
          const suppress = (error.config as any)?.suppressAuthRedirect === true

          if (!isLoginEndpoint && !suppress) {
            this.clearAuth()
            window.location.href = '/login'
          }
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

  async getCurrentCustomer(): Promise<any> {
    const response = await this.client.get('/customer/me')
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
  // CUSTOMER PASSWORD MANAGEMENT METHODS
  // ============================================

  /**
   * Request password reset email for customer
   * @param email - Customer email address
   * @returns Success message
   */
  async customerForgotPassword(email: string): Promise<{ message: string; success: boolean }> {
    const response = await this.client.post('/customer/forgot-password', { email })
    return response.data
  }

  /**
   * Reset customer password using token from email
   * @param token - Password reset token
   * @param newPassword - New password
   * @returns Success message
   */
  async customerResetPassword(token: string, newPassword: string): Promise<{ message: string; success: boolean }> {
    const response = await this.client.post('/customer/reset-password', {
      token,
      new_password: newPassword,
    })
    return response.data
  }

  /**
   * Change password for authenticated customer
   * @param currentPassword - Current password for verification
   * @param newPassword - New password
   * @returns Success message
   */
  async customerChangePassword(currentPassword: string, newPassword: string): Promise<{ message: string; success: boolean }> {
    const response = await this.client.post('/customer/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
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
    // Call the sites endpoint for deployed CUSTOMER sites (sites table)
    const response = await this.client.get('/sites/', { params })
    return response.data
  }

  async getGeneratedSites(params?: {
    page?: number
    page_size?: number
    limit?: number
    status?: string
  }): Promise<{ sites: any[]; total: number; page?: number; pages?: number }> {
    // Call the sites API for AI-GENERATED sites inventory (generated_sites table)
    const response = await this.client.get('/sites/', { 
      params: {
        page: params?.page || 1,
        page_size: params?.limit || params?.page_size || 100,
        status: params?.status
      }
    })
    return response.data
  }

  async getSite(id: string): Promise<GeneratedSite> {
    const response = await this.client.get<GeneratedSite>(`/sites/detail/${id}`)
    return response.data
  }

  async generateSite(data: GenerateSiteRequest): Promise<{ site_id: string }> {
    const response = await this.client.post('/sites/generate', data)
    return response.data
  }

  // ============================================
  // BUSINESS GENERATION QUEUE METHODS
  // ============================================

  async getBusinessesNeedingGeneration(): Promise<{ 
    total: number
    businesses: Array<{
      id: string
      name: string
      category: string
      city: string
      state: string
      country: string
      phone: string | null
      email: string | null
      rating: number | null
      review_count: number | null
      website_validation_status: string
      created_at: string
    }>
  }> {
    const response = await this.client.get('/businesses/needs-generation')
    return response.data
  }

  async queueBusinessesForGeneration(params?: {
    business_ids?: string[]
    queue_all?: boolean
  }): Promise<{
    queued: number
    already_queued: number
    failed: number
    total: number
    message: string
  }> {
    // Axios serializes arrays as `key[]=val` by default, but FastAPI expects
    // `key=val` repeated (no brackets).  Build the query string manually so
    // FastAPI's List[str] param is populated correctly.
    const parts: string[] = []
    if (params?.business_ids?.length) {
      params.business_ids.forEach(id => parts.push(`business_ids=${encodeURIComponent(id)}`))
    }
    parts.push(`queue_all=${params?.queue_all ? 'true' : 'false'}`)
    const qs = parts.join('&')

    const response = await this.client.post(
      `/businesses/queue-for-generation?${qs}`,
      null,
    )
    return response.data
  }

  async markSiteHasWebsite(siteId: string): Promise<{ success: boolean; message: string }> {
    const response = await this.client.post(`/sites/${siteId}/mark-has-website`)
    return response.data
  }

  async markSiteUnreachable(siteId: string): Promise<{ success: boolean; message: string }> {
    const response = await this.client.post(`/sites/${siteId}/mark-unreachable`)
    return response.data
  }

  async regenerateSiteImages(siteId: string): Promise<{ success: boolean; message: string; saved: number; total: number; failed_slots: string[] }> {
    const response = await this.client.post(`/sites/${siteId}/regenerate-images`)
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

  // ============================================
  // GEO-GRID METHODS
  // ============================================

  /**
   * Scrape a city using geo-grid subdivision
   * Automatically breaks down large cities into zones for comprehensive coverage
   */
  async scrapeWithGeoGrid(data: {
    city: string
    state: string
    industry: string
    population: number
    city_lat: number
    city_lon: number
    limit_per_zone?: number
    priority?: number
  }): Promise<any> {
    const response = await this.client.post('/coverage/geo-grid/scrape', data)
    return response.data
  }

  /**
   * Compare traditional vs geo-grid strategy for a location
   * Returns cost and coverage comparison
   */
  async compareGeoGridStrategy(params: {
    city: string
    state: string
    population: number
  }): Promise<any> {
    const response = await this.client.get('/coverage/geo-grid/compare', { params })
    return response.data
  }

  /**
   * Get geo-grid statistics and metrics
   */
  async getGeoGridStats(): Promise<{
    total_zones: number
    zones_with_data: number
    zones_pending: number
    avg_businesses_per_zone: number
    total_cities_subdivided: number
  }> {
    const response = await this.client.get('/coverage/geo-grid/stats')
    return response.data
  }

  /**
   * Get coverage grids with zone information
   */
  async getGeoGridCoverage(params?: {
    city?: string
    state?: string
    industry?: string
    has_zones?: boolean
    skip?: number
    limit?: number
  }): Promise<{ grids: any[]; total: number }> {
    const response = await this.client.get('/coverage/geo-grid', { params })
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

  async getCampaignStats(): Promise<import('@/types').CampaignStats> {
    const response = await this.client.get('/campaigns/stats')
    return response.data
  }

  // ============================================
  // NEW: SMS CAMPAIGN METHODS
  // ============================================

  /**
   * Get businesses ready for campaigns (with completed sites)
   */
  async getReadyBusinesses(params?: { include_contacted?: boolean }): Promise<ReadyBusinessesResponse> {
    const response = await this.client.get<ReadyBusinessesResponse>('/campaigns/ready-businesses', { params })
    return response.data
  }

  /**
   * Preview SMS message for a business
   */
  async previewSMSMessage(request: SMSPreviewRequest): Promise<SMSPreviewResponse> {
    const response = await this.client.post<SMSPreviewResponse>('/campaigns/preview-sms', request)
    return response.data
  }

  /**
   * Create campaigns for multiple businesses (bulk)
   */
  async createBulkCampaigns(request: BulkCampaignCreateRequest): Promise<BulkCampaignCreateResponse> {
    const response = await this.client.post<BulkCampaignCreateResponse>('/campaigns/bulk', request)
    return response.data
  }

  /**
   * Send a test SMS to verify Telnyx configuration
   */
  async sendTestSms(toPhone: string, message?: string): Promise<{ status: string; message: string; from: string; to: string; message_id: string }> {
    const response = await this.client.post('/campaigns/test-sms', {
      to_phone: toPhone,
      ...(message ? { message } : {})
    })
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

  async getMessagingTemplates(): Promise<{
    friendly: string
    professional: string
    urgent: string
    defaults: { friendly: string; professional: string; urgent: string }
  }> {
    const response = await this.client.get('/system/messaging-templates')
    return response.data
  }

  async getNotificationSettings(): Promise<{ support_admin_email: string; config_default: string }> {
    const response = await this.client.get('/system/notifications')
    return response.data
  }

  async updateNotificationSettings(support_admin_email: string): Promise<{ support_admin_email: string; config_default: string }> {
    const response = await this.client.put('/system/notifications', { support_admin_email })
    return response.data
  }

  async getAutopilotSettings(): Promise<{ enabled: boolean; target_businesses: number }> {
    const response = await this.client.get('/system/autopilot')
    return response.data
  }

  async updateAutopilotSettings(
    enabled: boolean,
    target_businesses: number
  ): Promise<{ enabled: boolean; target_businesses: number }> {
    const response = await this.client.put('/system/autopilot', { enabled, target_businesses })
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
      '/customer/domain/connect',
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
      '/customer/domain/verify',
      { domain },
      { params: { site_id: siteId } }
    )
    return response.data
  }

  async getDomainStatus(siteId: string): Promise<any> {
    const response = await this.client.get('/customer/domain/status', {
      params: { site_id: siteId }
    })
    return response.data
  }

  async disconnectDomain(siteId: string): Promise<any> {
    const response = await this.client.delete('/customer/domain/disconnect', {
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
    /** For site_edit tickets: structured per-change array */
    changes?: Array<{
      description: string
      element_context?: Record<string, any> | null
    }> | null
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

  // ============================================
  // CUSTOMER SITE METHODS (Multi-site support)
  // ============================================

  async getMySites(): Promise<{
    sites: Array<{
      site_id: string
      slug: string
      site_title: string
      site_url: string
      status: string
      subscription_status: string
      is_primary: boolean
      acquired_at: string
      next_billing_date?: string
      custom_domain?: string
    }>
    total: number
    has_multiple_sites: boolean
  }> {
    const response = await this.client.get('/customer/my-sites')
    return response.data
  }

  async getMySite(): Promise<any> {
    const response = await this.client.get('/customer/my-site')
    return response.data
  }

  // Intelligent Campaign Methods
  async createIntelligentStrategy(data: {
    city: string
    state: string
    category: string
    population?: number
    force_regenerate?: boolean
  }): Promise<any> {
    const response = await this.client.post('/intelligent-campaigns/strategies', data)
    return response.data
  }

  async scrapeIntelligentZone(data: {
    strategy_id: string
    zone_id?: string
    force_rescrape?: boolean
    limit_per_zone?: number
    draft_mode?: boolean
  }): Promise<any> {
    const response = await this.client.post('/intelligent-campaigns/scrape-zone', data)
    return response.data
  }

  async batchScrapeIntelligentStrategy(data: {
    strategy_id: string
    limit_per_zone?: number
    max_zones?: number
    draft_mode?: boolean
  }): Promise<any> {
    const response = await this.client.post('/intelligent-campaigns/batch-scrape', data)
    return response.data
  }

  async getIntelligentStrategy(strategyId: string): Promise<any> {
    const response = await this.client.get(`/intelligent-campaigns/strategies/${strategyId}`)
    return response.data
  }

  // Silent variant for background polling — a 401 won't trigger global logout
  async getIntelligentStrategyQuiet(strategyId: string): Promise<any> {
    const response = await this.client.get(
      `/intelligent-campaigns/strategies/${strategyId}`,
      { suppressAuthRedirect: true } as any
    )
    return response.data
  }

  async listIntelligentStrategies(params?: {
    city?: string
    state?: string
    category?: string
    status?: string
  }): Promise<any> {
    const response = await this.client.get('/intelligent-campaigns/strategies', { params })
    return response.data
  }

  async refineIntelligentStrategy(strategyId: string): Promise<any> {
    const response = await this.client.post(`/intelligent-campaigns/strategies/${strategyId}/refine`)
    return response.data
  }

  async getIntelligentCampaignStats(): Promise<any> {
    const response = await this.client.get('/intelligent-campaigns/stats')
    return response.data
  }

  // Business Categories
  async getBusinessCategories(): Promise<any[]> {
    const response = await this.client.get('/business-categories/')
    return response.data
  }

  async getBusinessCategorySearchTerms(): Promise<string[]> {
    const response = await this.client.get('/business-categories/search-terms')
    return response.data
  }

  // Draft Campaigns
  async getDraftCampaigns(params?: {
    city?: string
    state?: string
    category?: string
    limit?: number
  }): Promise<any> {
    const response = await this.client.get('/draft-campaigns/pending', { params })
    return response.data
  }

  async getDraftCampaignDetail(campaignId: string): Promise<any> {
    const response = await this.client.get(`/draft-campaigns/${campaignId}`)
    return response.data
  }

  async approveDraftCampaign(campaignId: string, reviewNotes?: string): Promise<any> {
    const response = await this.client.post('/draft-campaigns/approve', {
      campaign_id: campaignId,
      review_notes: reviewNotes
    })
    return response.data
  }

  async rejectDraftCampaign(campaignId: string, reviewNotes?: string): Promise<any> {
    const response = await this.client.post('/draft-campaigns/reject', {
      campaign_id: campaignId,
      review_notes: reviewNotes
    })
    return response.data
  }

  async getDraftCampaignStats(): Promise<any> {
    const response = await this.client.get('/draft-campaigns/stats')
    return response.data
  }

  // ============================================
  // PHASE 3: COVERAGE REPORTING METHODS
  // ============================================

  /**
   * Get detailed statistics for a specific zone
   */
  async getZoneStatistics(zoneId: string): Promise<any> {
    const response = await this.client.get(`/intelligent-campaigns/zones/${zoneId}/statistics`)
    return response.data
  }

  /**
   * Get comprehensive overview of a geo-strategy with all zones
   */
  async getStrategyOverview(strategyId: string): Promise<any> {
    const response = await this.client.get(`/intelligent-campaigns/strategies/${strategyId}/overview`)
    return response.data
  }

  /**
   * Get coverage breakdown with optional filters
   */
  async getCoverageBreakdown(params?: {
    city?: string
    state?: string
    category?: string
  }): Promise<any> {
    const response = await this.client.get('/intelligent-campaigns/coverage/breakdown', { params })
    return response.data
  }

  // ============================================
  // PHASE 4: BUSINESS FILTERING METHODS
  // ============================================

  /**
   * Apply advanced filters to businesses
   */
  async filterBusinesses(request: {
    filters: any
    sort_by?: string
    sort_desc?: boolean
    page?: number
    page_size?: number
  }): Promise<any> {
    const response = await this.client.post('/businesses/filter', request)
    return response.data
  }

  /**
   * Get predefined quick filter templates
   */
  async getQuickFilters(): Promise<any> {
    const response = await this.client.get('/businesses/filters/quick')
    return response.data
  }

  /**
   * Get filter statistics (counts by website status, etc.)
   */
  async getFilterStats(filters?: any): Promise<any> {
    const params = filters ? { filters: JSON.stringify(filters) } : {}
    const response = await this.client.get('/businesses/filters/stats', { params })
    return response.data
  }

  /**
   * Save a filter preset
   */
  async saveFilterPreset(name: string, filters: any, isPublic: boolean = false): Promise<any> {
    const response = await this.client.post('/businesses/filters/presets', {
      name,
      filters,
      is_public: isPublic
    })
    return response.data
  }

  /**
   * Get all filter presets for current user
   */
  async getFilterPresets(includePublic: boolean = true): Promise<any> {
    const response = await this.client.get('/businesses/filters/presets', {
      params: { include_public: includePublic }
    })
    return response.data
  }

  /**
   * Delete a filter preset
   */
  async deleteFilterPreset(presetId: string): Promise<any> {
    const response = await this.client.delete(`/businesses/filters/presets/${presetId}`)
    return response.data
  }

  // ============================================
  // SMS MESSAGES METHODS (Phase 7)
  // ============================================

  /**
   * Get all SMS messages with pagination and filtering
   */
  async getMessages(params?: {
    page?: number
    page_size?: number
    direction?: 'inbound' | 'outbound'
    status?: string
    business_id?: string
    search?: string
  }): Promise<{
    messages: any[]
    total: number
    page: number
    page_size: number
    pages: number
  }> {
    const response = await this.client.get('/messages/', { params })
    return response.data
  }

  /**
   * Get SMS message statistics
   */
  async getMessageStats(): Promise<{
    total_messages: number
    inbound_count: number
    outbound_count: number
    delivered_count: number
    failed_count: number
    opt_out_count: number
    total_cost: number
    avg_cost_per_message: number
    messages_today: number
    messages_this_week: number
    inbound_today: number
  }> {
    const response = await this.client.get('/messages/stats')
    return response.data
  }

  /**
   * Get a single SMS message by ID
   */
  async getMessage(messageId: string): Promise<any> {
    const response = await this.client.get(`/messages/${messageId}`)
    return response.data
  }

  /**
   * Get all SMS messages for a specific business
   */
  async getBusinessMessages(businessId: string, params?: {
    page?: number
    page_size?: number
  }): Promise<any> {
    const response = await this.client.get(`/messages/business/${businessId}`, { params })
    return response.data
  }

  /**
   * Get conversation list — one summary per unique contact phone, newest first
   */
  async getConversations(params?: {
    search?: string
    limit?: number
  }): Promise<{
    conversations: ConversationSummary[]
    total: number
  }> {
    const response = await this.client.get('/messages/conversations', { params })
    return response.data
  }

  /**
   * Get the full message thread for a single contact phone number
   */
  async getConversationThread(contactPhone: string): Promise<{
    messages: SMSMessageItem[]
    total: number
    page: number
    page_size: number
    pages: number
  }> {
    const encoded = encodeURIComponent(contactPhone)
    const response = await this.client.get(`/messages/conversations/${encoded}`)
    return response.data
  }

  // ============================================
  // SCRAPING METHODS (Phase 2: Async with Progress)
  // ============================================

  /**
   * Start a new scraping operation.
   * Returns immediately with session_id for progress tracking.
   */
  async startScrape(request: {
    zone_id: string
    city: string
    state: string
    category: string
    country?: string
    limit_per_zone?: number
    strategy_id?: string
  }): Promise<{
    session_id: string
    status: string
    message: string
    progress_url: string
    status_url: string
  }> {
    const response = await this.client.post('/scrapes/start', {
      zone_id: request.zone_id,
      city: request.city,
      state: request.state,
      category: request.category,
      country: request.country || 'US',
      limit_per_zone: request.limit_per_zone || 50,
      strategy_id: request.strategy_id
    })
    return response.data
  }

  /**
   * Get current status of a scrape session (polling).
   */
  async getScrapeStatus(sessionId: string): Promise<{
    session_id: string
    zone_id: string
    status: string
    progress: any
    timestamps: any
    error: string | null
  }> {
    const response = await this.client.get(`/scrapes/${sessionId}/status`)
    return response.data
  }

  /**
   * List recent scrape sessions.
   */
  async listScrapes(options?: {
    limit?: number
    status?: string
  }): Promise<any[]> {
    const params = new URLSearchParams()
    
    if (options?.limit) {
      params.append('limit', options.limit.toString())
    }
    
    if (options?.status) {
      params.append('status_filter', options.status)
    }
    
    const response = await this.client.get(`/scrapes?${params.toString()}`)
    return response.data
  }
  // ============================================
  // URL SHORTENER METHODS
  // ============================================

  async getShortenerConfig(): Promise<{
    domain: string
    protocol: string
    slug_length: number
    default_expiry_days: number
    enabled: boolean
  }> {
    const response = await this.client.get('/shortener/config')
    return response.data
  }

  async getShortenerStats(): Promise<{
    total_links: number
    active_links: number
    total_clicks: number
    links_by_type: Record<string, number>
  }> {
    const response = await this.client.get('/shortener/stats')
    return response.data
  }

  async listShortLinks(params?: {
    link_type?: string
    is_active?: boolean
    page?: number
    page_size?: number
  }): Promise<{
    items: any[]
    total: number
    page: number
    page_size: number
  }> {
    const response = await this.client.get('/shortener/links', { params })
    return response.data
  }

  async createShortLink(data: {
    destination_url: string
    link_type?: string
    custom_slug?: string
  }): Promise<{ success: boolean; short_url: string }> {
    const response = await this.client.post('/shortener/links', data)
    return response.data
  }

  async deactivateShortLink(linkId: string): Promise<{ success: boolean }> {
    const response = await this.client.delete(`/shortener/links/${linkId}`)
    return response.data
  }

  // ============================================
  // ADMIN SUPPORT TICKETS
  // ============================================

  async getAdminTickets(params?: {
    status?: string
    category?: string
    priority?: string
    site_slug?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<{ tickets: any[]; total: number; limit: number; offset: number }> {
    const response = await this.client.get('/admin/tickets/', { params })
    return response.data
  }

  async getAdminTicket(ticketId: string): Promise<any> {
    const response = await this.client.get(`/admin/tickets/${ticketId}`)
    return response.data
  }

  async replyToTicket(ticketId: string, message: string): Promise<any> {
    const response = await this.client.post(`/admin/tickets/${ticketId}/messages`, { message })
    return response.data
  }

  async updateAdminTicketStatus(ticketId: string, status: string): Promise<any> {
    const response = await this.client.patch(`/admin/tickets/${ticketId}/status`, { status })
    return response.data
  }

  async assignTicket(ticketId: string, adminUserId: string | null): Promise<any> {
    const response = await this.client.patch(`/admin/tickets/${ticketId}/assign`, {
      admin_user_id: adminUserId,
    })
    return response.data
  }

  async applyTicketSiteEdit(ticketId: string): Promise<any> {
    const response = await this.client.post(`/admin/tickets/${ticketId}/apply-edit`)
    return response.data
  }

  // ============================================
  // VERIFICATION QUEUE
  // ============================================

  async getVerificationQueue(params?: {
    page?: number
    page_size?: number
    has_generated_site?: boolean
  }): Promise<VerificationQueueResponse> {
    const response = await this.client.get('/verification/queue', { params })
    return response.data
  }

  async submitVerificationDecision(
    businessId: string,
    decision: VerificationDecisionRequest
  ): Promise<{ status: string; decision?: string; business_id: string }> {
    const response = await this.client.post(
      `/verification/${businessId}/decide`,
      decision
    )
    return response.data
  }
}

// Export singleton instance
export const api = new ApiClient()
