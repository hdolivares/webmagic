/**
 * TypeScript type definitions for WebMagic Admin
 */

// ============================================
// AUTH TYPES
// ============================================

export interface User {
  id: string
  email: string
  full_name?: string
  is_active: boolean
  created_at: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface AuthTokens {
  access_token: string
  token_type: string
}

// ============================================
// BUSINESS TYPES
// ============================================

export interface Business {
  id: string
  name: string
  category?: string
  phone?: string
  address?: string
  city?: string
  state?: string
  country?: string
  postal_code?: string
  lat?: number
  lng?: number
  rating?: number
  reviews_count?: number
  website?: string
  status: 'scraped' | 'qualified' | 'disqualified' | 'contacted' | 'converted'
  has_website: boolean
  disqualified_reason?: string
  created_at: string
  updated_at: string
}

export interface BusinessListResponse {
  businesses: Business[]
  total: number
  skip: number
  limit: number
}

// ============================================
// COVERAGE TYPES
// ============================================

export interface CoverageGrid {
  id: string
  center_lat: number
  center_lng: number
  location_query: string
  category: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  scraped_at?: string
  cooldown_until?: string
  created_at: string
}

// Re-export geo-grid types
export * from './geoGrid'
export * from './draftCampaign'

// ============================================
// SITE TYPES
// ============================================

export interface GeneratedSiteBusiness {
  id: string
  name: string
  category?: string
  phone?: string
  address?: string
  city?: string
  state?: string
  rating?: number | null
  review_count?: number
  website_url?: string
  gmb_place_id?: string
}

export interface GeneratedSite {
  id: string
  business_id: string
  subdomain: string
  html_content?: string | null
  css_content?: string | null
  js_content?: string | null
  brand_analysis?: Record<string, any>
  brand_concept?: Record<string, any>
  design_brief?: Record<string, any>
  status: 'generating' | 'completed' | 'failed' | 'published' | 'draft'
  version?: number
  deployed_at?: string | null
  sold_at?: string | null
  lighthouse_score?: number | null
  load_time_ms?: number | null
  screenshot_desktop_url?: string | null
  screenshot_mobile_url?: string | null
  short_url?: string | null
  custom_domain?: string | null
  full_url?: string
  is_live?: boolean
  assets_urls?: string[]
  generation_started_at?: string
  generation_completed_at?: string
  error_message?: string
  created_at: string
  updated_at: string
  business?: GeneratedSiteBusiness | null
}

export interface GenerateSiteRequest {
  business_id: string
  force_regenerate?: boolean
}

export interface ManualGenerationRequest {
  /** Free-form business description — the primary input */
  description: string
  /** Hard facts — used verbatim on the generated site */
  name?: string
  phone?: string
  email?: string
  address?: string
  city?: string
  state?: string
  /** Layout style */
  website_type?: 'informational' | 'ecommerce'
  /** Free-text color/style description */
  branding_notes?: string
  /** Base64 data URIs of logo/brand images */
  branding_images?: string[]
}

// ============================================
// PROMPT TYPES
// ============================================

export interface PromptTemplate {
  id: string
  agent_name: string
  system_prompt: string
  output_format?: string
  placeholder_sections?: string[]
  created_at: string
  updated_at: string
}

export interface PromptSetting {
  id: string
  agent_name: string
  section_name: string
  content: string
  description?: string
  version: number
  is_active: boolean
  usage_count?: number
  success_count?: number
  success_rate?: number
  created_at: string
  updated_at: string
}

export interface PromptSettingUpdate {
  content?: string
  description?: string
  is_active?: boolean
}

// ============================================
// CAMPAIGN TYPES
// ============================================

export interface Campaign {
  id: string
  business_id?: string
  site_id?: string
  channel: string
  // Email-only (null for SMS)
  subject_line?: string
  email_body?: string
  preview_text?: string
  recipient_email?: string
  // SMS-only (null for email)
  recipient_phone?: string
  sms_body?: string
  sms_cost?: number
  // Common
  business_name?: string
  recipient_name?: string
  status: string
  variant?: string
  sent_at?: string
  delivered_at?: string
  opened_at?: string
  opened_count: number
  clicked_at?: string
  clicked_count: number
  replied_at?: string
  converted_at?: string
  email_provider?: string
  error_message?: string
  retry_count: number
  is_delivered: boolean
  is_engaged: boolean
  created_at: string
  updated_at: string
}

export interface CreateCampaignRequest {
  site_id: string
  recipient_email: string
  recipient_name?: string
  custom_subject?: string
  send_immediately?: boolean
}

export interface CampaignListResponse {
  campaigns: Campaign[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface CampaignStats {
  total_campaigns: number
  by_status: Record<string, number>
  sent_24h: number
  total_sent: number
  total_opened: number
  total_clicked: number
  total_replied: number
  open_rate: number
  click_rate: number
  reply_rate: number
}

// ============================================
// NEW: SMS CAMPAIGN TYPES
// ============================================

export interface ReadyBusiness {
  id: string
  name: string
  category?: string
  city?: string
  state?: string
  country?: string
  phone?: string
  email?: string
  rating?: number
  review_count?: number
  qualification_score?: number
  site_id: string
  site_subdomain: string
  site_url: string
  site_created_at: string
  available_channels: string[]
  recommended_channel: string
  /** null = not yet validated, 'sms' | 'call_later' | 'email' */
  outreach_channel?: string | null
  /** e.g. 'mobile' | 'landline' | 'voip' | 'fixed_voip' | 'unknown' */
  phone_line_type?: string | null
  // Campaign history (null if never contacted)
  last_campaign_status?: string | null
  last_campaign_at?: string | null
  last_campaign_channel?: string | null
}

export interface ReadyBusinessesResponse {
  businesses: ReadyBusiness[]
  total: number
  with_email: number
  with_phone: number
  sms_only: number
  email_only: number
  call_later: number
  already_contacted: number
}

export interface SMSPreviewRequest {
  business_id: string
  variant: 'friendly' | 'professional' | 'urgent'
}

export interface SMSPreviewResponse {
  business_id: string
  business_name: string
  sms_body: string
  character_count: number
  segment_count: number
  estimated_cost: number
  site_url: string
  variant: string
}

export interface BulkCampaignCreateRequest {
  business_ids: string[]
  channel: 'auto' | 'email' | 'sms'
  variant: 'friendly' | 'professional' | 'urgent'
  send_immediately: boolean
  scheduled_for?: string
}

export interface BulkCampaignCreateResponse {
  status: string
  message: string
  total_queued: number
  by_channel: Record<string, number>
  estimated_sms_cost: number
  campaigns_created: string[]
}

// ============================================
// PAYMENT TYPES
// ============================================

export interface Customer {
  id: string
  business_id?: string
  site_id?: string
  recurrente_user_id?: string
  email: string
  full_name?: string
  phone?: string
  status: string
  lifetime_value: number
  created_at: string
}

export interface Subscription {
  id: string
  customer_id: string
  site_id?: string
  recurrente_subscription_id?: string
  amount: number
  currency: string
  status: string
  started_at?: string
  cancelled_at?: string
  current_period_start?: string
  current_period_end?: string
  created_at: string
}

export interface Payment {
  id: string
  customer_id: string
  subscription_id?: string
  recurrente_payment_id?: string
  amount: number
  currency: string
  payment_type: string
  status: string
  paid_at?: string
  created_at: string
}

export interface CustomerListResponse {
  customers: Customer[]
  total: number
  skip: number
  limit: number
}

export interface CustomerStats {
  total_customers: number
  active_customers: number
  total_lifetime_value: number
  average_lifetime_value: number
}

// ============================================
// STATS TYPES
// ============================================

export interface DashboardStats {
  total_businesses: number
  qualified_leads: number
  sites_generated: number
  campaigns_sent: number
  total_customers: number
  total_revenue: number
  conversion_rate: number
}

// ============================================
// IMAGE GENERATION TYPES
// ============================================

export type ImageType = 'hero' | 'background' | 'product' | 'icon'
export type AspectRatio = '1:1' | '16:9' | '4:3' | '3:2' | '21:9'
export type BrandArchetype = 
  | 'Explorer' 
  | 'Creator' 
  | 'Caregiver' 
  | 'Ruler' 
  | 'Sage' 
  | 'Innocent' 
  | 'Hero' 
  | 'Magician' 
  | 'Outlaw' 
  | 'Lover' 
  | 'Jester' 
  | 'Regular Guy'

export interface ImageGenerationRequest {
  business_name: string
  category: string
  brand_archetype?: BrandArchetype
  color_primary?: string
  color_secondary?: string
  color_accent?: string
  image_type: ImageType
  aspect_ratio?: AspectRatio
}

export interface ImageGenerationResponse {
  success: boolean
  message: string
  size_bytes?: number
  aspect_ratio?: string
  image_type: ImageType
}

export interface GeneratedImage {
  id: string
  type: ImageType
  url: string
  size_bytes: number
  aspect_ratio: string
  created_at: string
}
