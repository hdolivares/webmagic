/**
 * React Hook for Scrape Progress via SSE.
 * 
 * Purpose:
 *   Subscribe to real-time scraping progress using Server-Sent Events.
 *   Provides type-safe access to progress data with automatic cleanup.
 * 
 * Best Practices:
 *   - Clean up EventSource on unmount
 *   - Type-safe event handling
 *   - Automatic reconnection
 *   - Error state management
 * 
 * Usage:
 *   const { progress, lastBusiness, status, error } = useScrapeProgress(sessionId);
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// =============================================================================
// TYPES
// =============================================================================

export interface ScrapeProgress {
  current: number;
  total: number;
  percentage: number;
}

export interface BusinessScraped {
  id: string;
  name: string;
}

export interface ScrapeEvent {
  session_id: string;
  event: string;
  data: any;
  timestamp: string;
}

export type ScrapeStatus = 
  | 'connecting' 
  | 'connected' 
  | 'scraping' 
  | 'validating' 
  | 'completed' 
  | 'error' 
  | 'disconnected';

export interface UseScrapeProgressReturn {
  /** Current scraping progress (null if not started) */
  progress: ScrapeProgress | null;
  
  /** Last business that was scraped */
  lastBusiness: BusinessScraped | null;
  
  /** Current status of the scrape */
  status: ScrapeStatus;
  
  /** Error message if status is 'error' */
  error: string | null;
  
  /** All events received (for debugging) */
  events: ScrapeEvent[];
  
  /** Summary data when completed */
  summary: Record<string, number> | null;
  
  /** Manually reconnect if disconnected */
  reconnect: () => void;
}

// =============================================================================
// HOOK
// =============================================================================

export function useScrapeProgress(
  sessionId: string | null,
  options?: {
    /** Auto-reconnect on error (default: true) */
    autoReconnect?: boolean;
    /** Maximum reconnection attempts (default: 3) */
    maxReconnects?: number;
  }
): UseScrapeProgressReturn {
  const { autoReconnect = true, maxReconnects = 3 } = options || {};
  
  // State
  const [progress, setProgress] = useState<ScrapeProgress | null>(null);
  const [lastBusiness, setLastBusiness] = useState<BusinessScraped | null>(null);
  const [status, setStatus] = useState<ScrapeStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<ScrapeEvent[]>([]);
  const [summary, setSummary] = useState<Record<string, number> | null>(null);
  
  // Refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  
  // Reconnect function
  const reconnect = useCallback(() => {
    if (!sessionId) return;
    
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    setStatus('connecting');
    setError(null);
    
    // Will be reconnected by useEffect
  }, [sessionId]);
  
  // Main effect
  useEffect(() => {
    if (!sessionId) {
      setStatus('disconnected');
      return;
    }
    
    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // Create EventSource
    const url = `/api/v1/scrapes/${sessionId}/progress`;
    const eventSource = new EventSource(url, {
      withCredentials: true  // Include cookies for auth
    });
    
    eventSourceRef.current = eventSource;
    
    console.log('📡 SSE: Connecting to', url);
    
    // Connection opened
    eventSource.onopen = () => {
      console.log('✅ SSE: Connection opened');
      setStatus('connected');
      setError(null);
      reconnectAttemptsRef.current = 0;  // Reset on successful connect
    };
    
    // Generic message handler (catches all events without specific handler)
    eventSource.onmessage = (event) => {
      try {
        const data: ScrapeEvent = JSON.parse(event.data);
        console.log('📨 SSE: Message received', data.event);
        
        // Store event
        setEvents(prev => [...prev, data]);
        
        // Handle event
        handleEvent(data);
      } catch (err) {
        console.error('❌ SSE: Failed to parse message', err);
      }
    };
    
    // Specific event handlers
    eventSource.addEventListener('connected', (event) => {
      console.log('🔗 SSE: Connected event');
      setStatus('connected');
    });
    
    eventSource.addEventListener('scraping_started', (event) => {
      console.log('🚀 SSE: Scraping started');
      setStatus('scraping');
    });
    
    eventSource.addEventListener('business_scraped', (event) => {
      try {
        const data = JSON.parse(event.data);
        setProgress(data.data.progress);
        setLastBusiness({
          id: data.data.business_id,
          name: data.data.business_name
        });
      } catch (err) {
        console.error('Failed to parse business_scraped event', err);
      }
    });
    
    eventSource.addEventListener('validation_started', (event) => {
      console.log('🔍 SSE: Validation started');
      setStatus('validating');
    });
    
    eventSource.addEventListener('scrape_complete', (event) => {
      console.log('🎉 SSE: Scrape completed');
      setStatus('completed');
      
      try {
        const data = JSON.parse(event.data);
        setSummary(data.data.summary);
      } catch (err) {
        console.error('Failed to parse scrape_complete event', err);
      }
      
      // Close connection
      eventSource.close();
    });
    
    eventSource.addEventListener('error', (event) => {
      try {
        const data = JSON.parse((event as any).data);
        const errorMessage = data.error || 'Unknown error occurred';
        console.error('❌ SSE: Error event', errorMessage);
        setError(errorMessage);
        setStatus('error');
      } catch (err) {
        console.error('Failed to parse error event', err);
      }
      
      // Close connection
      eventSource.close();
    });
    
    // Connection error
    eventSource.onerror = (event) => {
      console.error('❌ SSE: Connection error', event);
      
      if (eventSource.readyState === EventSource.CLOSED) {
        setStatus('disconnected');
        
        // Auto-reconnect logic
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnects) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current - 1), 10000);
          
          console.log(`🔄 SSE: Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnects})`);
          setError(`Connection lost. Reconnecting... (attempt ${reconnectAttemptsRef.current}/${maxReconnects})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnect();
          }, delay);
        } else {
          setError('Connection lost. Please refresh the page.');
        }
      }
    };
    
    // Cleanup
    return () => {
      console.log('📴 SSE: Closing connection');
      eventSource.close();
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
    
  }, [sessionId, autoReconnect, maxReconnects, reconnect]);
  
  // Helper to handle events
  const handleEvent = (event: ScrapeEvent) => {
    // Already handled by specific event listeners
    // This is a catch-all for unhandled events
  };
  
  return {
    progress,
    lastBusiness,
    status,
    error,
    events,
    summary,
    reconnect
  };
}
