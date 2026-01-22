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

// ============================================
// SITE TYPES
// ============================================

export interface GeneratedSite {
  id: string
  business_id: string
  subdomain: string
  html_content: string
  css_content?: string
  js_content?: string
  brand_analysis?: Record<string, any>
  brand_concept?: Record<string, any>
  design_brief?: Record<string, any>
  status: 'generating' | 'completed' | 'failed' | 'published'
  generation_started_at?: string
  generation_completed_at?: string
  error_message?: string
  created_at: string
  updated_at: string
}

export interface GenerateSiteRequest {
  business_id: string
  force_regenerate?: boolean
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
  site_id: string
  business_id?: string
  subject_line: string
  email_body: string
  recipient_email: string
  recipient_name?: string
  status: 'draft' | 'scheduled' | 'sending' | 'sent' | 'failed' | 'opened' | 'clicked'
  sent_at?: string
  opened_at?: string
  clicked_at?: string
  error_message?: string
  tracking_pixel_id?: string
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
  skip: number
  limit: number
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
