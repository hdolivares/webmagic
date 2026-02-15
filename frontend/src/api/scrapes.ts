/**
 * Scrapes API Client.
 * 
 * Purpose:
 *   Type-safe API client for scraping operations.
 *   Handles requests to /api/v1/scrapes endpoints.
 * 
 * Best Practices:
 *   - Type-safe request/response models
 *   - Error handling with typed errors
 *   - Consistent API interface
 *   - Separation from UI logic
 *   - Uses authenticated API client
 */

import { api } from '@/services/api';

// =============================================================================
// TYPES
// =============================================================================

export interface StartScrapeRequest {
  zone_id: string;
  city: string;
  state: string;
  category: string;
  country?: string;
  limit_per_zone?: number;
  strategy_id?: string;
}

export interface StartScrapeResponse {
  session_id: string;
  status: string;
  message: string;
  progress_url: string;
  status_url: string;
}

export interface ScrapeProgress {
  total: number;
  scraped: number;
  validated: number;
  discovered: number;
  scrape_percentage: number;
  validation_percentage: number;
}

export interface ScrapeTimestamps {
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface ScrapeStatusResponse {
  session_id: string;
  zone_id: string;
  status: string;
  progress: ScrapeProgress;
  timestamps: ScrapeTimestamps;
  error: string | null;
}

// =============================================================================
// API CLIENT
// =============================================================================

export const scrapesAPI = {
  /**
   * Start a new scraping operation.
   * 
   * Returns immediately with session_id for progress tracking.
   * Use the returned progress_url for SSE updates.
   * 
   * @param request - Scrape parameters
   * @returns Session details with URLs for tracking
   */
  async startScrape(request: StartScrapeRequest): Promise<StartScrapeResponse> {
    try {
      const response = await api.post<StartScrapeResponse>(
        '/scrapes/start',
        {
          zone_id: request.zone_id,
          city: request.city,
          state: request.state,
          category: request.category,
          country: request.country || 'US',
          limit_per_zone: request.limit_per_zone || 50,
          strategy_id: request.strategy_id
        }
      );
      
      return response.data;
    } catch (error: any) {
      console.error('Failed to start scrape:', error);
      
      throw new Error(
        error.response?.data?.detail || 
        'Failed to start scraping operation'
      );
    }
  },
  
  /**
   * Get current status of a scrape session (polling).
   * 
   * For real-time updates, use SSE via useScrapeProgress hook instead.
   * 
   * @param sessionId - Scrape session UUID
   * @returns Current status and progress
   */
  async getScrapeStatus(sessionId: string): Promise<ScrapeStatusResponse> {
    try {
      const response = await api.get<ScrapeStatusResponse>(
        `/scrapes/${sessionId}/status`
      );
      
      return response.data;
    } catch (error: any) {
      console.error('Failed to get scrape status:', error);
      
      if (error.response?.status === 404) {
        throw new Error('Scrape session not found');
      }
      
      throw new Error(
        error.response?.data?.detail || 
        'Failed to fetch scrape status'
      );
    }
  },
  
  /**
   * List recent scrape sessions.
   * 
   * @param options - Filtering and pagination options
   * @returns List of scrape sessions
   */
  async listScrapes(options?: {
    limit?: number;
    status?: string;
  }): Promise<ScrapeStatusResponse[]> {
    try {
      const params = new URLSearchParams();
      
      if (options?.limit) {
        params.append('limit', options.limit.toString());
      }
      
      if (options?.status) {
        params.append('status_filter', options.status);
      }
      
      const response = await api.get<ScrapeStatusResponse[]>(
        `/scrapes?${params.toString()}`
      );
      
      return response.data;
    } catch (error: any) {
      console.error('Failed to list scrapes:', error);
      
      throw new Error(
        error.response?.data?.detail || 
        'Failed to fetch scrape list'
      );
    }
  }
};
