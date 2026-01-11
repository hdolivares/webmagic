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

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me')
    return response.data
  }

  logout() {
    this.clearAuth()
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
    const response = await this.client.get<BusinessListResponse>('/businesses', {
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
    const response = await this.client.get('/coverage', { params })
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
  }): Promise<{ sites: GeneratedSite[]; total: number }> {
    const response = await this.client.get('/sites', { params })
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

  async getPromptSettings(templateId: string): Promise<PromptSetting[]> {
    const response = await this.client.get<PromptSetting[]>(
      `/settings/templates/${templateId}/settings`
    )
    return response.data
  }

  async updatePromptSetting(
    settingId: string,
    data: PromptSettingUpdate
  ): Promise<PromptSetting> {
    const response = await this.client.patch<PromptSetting>(
      `/settings/settings/${settingId}`,
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
    const response = await this.client.get<CampaignListResponse>('/campaigns', {
      params,
    })
    return response.data
  }

  async getCampaign(id: string): Promise<Campaign> {
    const response = await this.client.get<Campaign>(`/campaigns/${id}`)
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
}

// Export singleton instance
export const api = new ApiClient()
