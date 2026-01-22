/**
 * Draft Campaign Types
 * 
 * Types for the draft mode campaign review workflow.
 */

export interface DraftCampaign {
  id: string
  strategy_id: string
  city: string
  state: string
  category: string
  zone_id: string
  zone_location: {
    lat: string
    lon: string
    radius_km: string
  } | null
  total_businesses_found: number
  qualified_leads_count: number
  qualification_rate: number | null
  business_ids: string[]
  status: 'pending_review' | 'approved' | 'rejected' | 'sent'
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  messages_sent: number
  messages_failed: number
  sent_at: string | null
  created_at: string
  updated_at: string
}

export interface DraftCampaignBusiness {
  id: string
  name: string
  website_url: string | null
  website_status: string | null
  phone: string | null
  email: string | null
  address: string | null
  rating: number | null
  review_count: number | null
  category: string | null
  qualification_score: number | null
}

export interface DraftCampaignListResponse {
  campaigns: DraftCampaign[]
  total: number
}

export interface DraftCampaignDetailResponse {
  campaign: DraftCampaign
  businesses: DraftCampaignBusiness[]
}

export interface DraftCampaignStats {
  pending_campaigns: number
  approved_campaigns: number
  sent_campaigns: number
  rejected_campaigns: number
  total_campaigns: number
  total_pending_leads: number
  total_approved_leads: number
  total_sent_messages: number
}

