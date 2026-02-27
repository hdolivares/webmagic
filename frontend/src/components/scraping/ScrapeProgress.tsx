/**
 * Scrape Progress Component.
 * 
 * Purpose:
 *   Display real-time scraping progress with SSE updates.
 *   Shows progress bar, current business, and status indicators.
 * 
 * Best Practices:
 *   - Separation of concerns (hook handles data, component handles UI)
 *   - Semantic CSS variables for theming
 *   - Type-safe props and state
 *   - Accessible UI elements
 *   - Clear visual hierarchy
 */

import React, { useEffect } from 'react';
import { useScrapeProgress, ScrapeStatus } from '../../hooks/useScrapeProgress';
import './ScrapeProgress.css';

// =============================================================================
// TYPES
// =============================================================================

export interface ScrapeProgressProps {
  /** Scrape session UUID */
  sessionId: string;
  
  /** Callback when scraping completes */
  onComplete?: (summary: Record<string, number>) => void;
  
  /** Callback when error occurs */
  onError?: (error: string) => void;
  
  /** Show detailed event log (default: false) */
  showEventLog?: boolean;
  
  /** Custom className for styling */
  className?: string;
}

// =============================================================================
// COMPONENT
// =============================================================================

export function ScrapeProgress({
  sessionId,
  onComplete,
  onError,
  showEventLog = false,
  className = ''
}: ScrapeProgressProps) {
  const {
    progress,
    lastBusiness,
    status,
    error,
    events,
    summary,
    reconnect
  } = useScrapeProgress(sessionId);
  
  // Call callbacks when status changes
  useEffect(() => {
    if (status === 'completed' && summary && onComplete) {
      onComplete(summary);
    }
  }, [status, summary, onComplete]);
  
  useEffect(() => {
    if (status === 'error' && error && onError) {
      onError(error);
    }
  }, [status, error, onError]);
  
  // Render nothing if no session
  if (!sessionId) {
    return null;
  }
  
  return (
    <div className={`scrape-progress ${className}`}>
      {/* Status Header */}
      <div className="scrape-progress__header">
        <h3 className="scrape-progress__title">
          {getStatusIcon(status)} {getStatusText(status)}
        </h3>
        
        {progress && (
          <span className="scrape-progress__count">
            {progress.current} / {progress.total}
          </span>
        )}
      </div>
      
      {/* Progress Bar — indeterminate while waiting for Outscraper, determinate once businesses flow in */}
      {status !== 'completed' && status !== 'error' && status !== 'disconnected' && (
        <div className="scrape-progress__bar-container">
          <div className="scrape-progress__bar">
            {progress ? (
              <div
                className={`scrape-progress__bar-fill scrape-progress__bar-fill--${status}`}
                style={{ width: `${progress.percentage}%` }}
                role="progressbar"
                aria-valuenow={progress.percentage}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            ) : (
              <div
                className="scrape-progress__bar-fill scrape-progress__bar-fill--indeterminate"
                role="progressbar"
                aria-label="Waiting for results…"
              />
            )}
          </div>
          {progress && (
            <span className="scrape-progress__percentage">
              {progress.percentage.toFixed(1)}%
            </span>
          )}
        </div>
      )}
      
      {/* Current Business Being Scraped */}
      {lastBusiness && status === 'scraping' && (
        <div className="scrape-progress__current-business">
          <p className="scrape-progress__current-label">
            Currently scraping:
          </p>
          <p className="scrape-progress__current-name">
            {lastBusiness.name}
          </p>
        </div>
      )}
      
      {/* Completion Summary */}
      {status === 'completed' && summary && (
        <div className="scrape-progress__summary">
          <div className="scrape-progress__summary-item">
            <span className="scrape-progress__summary-label">Businesses saved</span>
            <span className="scrape-progress__summary-value">{summary.total}</span>
          </div>
          <div className="scrape-progress__summary-item">
            <span className="scrape-progress__summary-label">Have a website</span>
            <span className="scrape-progress__summary-value scrape-progress__summary-value--muted">
              {summary.valid}
            </span>
          </div>
          <div className="scrape-progress__summary-item">
            <span className="scrape-progress__summary-label">Need a website ✨</span>
            <span className="scrape-progress__summary-value scrape-progress__summary-value--success">
              {summary.invalid}
            </span>
          </div>
        </div>
      )}
      
      {/* Error Display */}
      {error && (
        <div className="scrape-progress__error">
          <p className="scrape-progress__error-message">{error}</p>
          {status === 'disconnected' && (
            <button 
              onClick={reconnect}
              className="scrape-progress__error-action"
            >
              🔄 Reconnect
            </button>
          )}
        </div>
      )}
      
      {/* Event Log (Development Only) */}
      {showEventLog && events.length > 0 && (
        <details className="scrape-progress__event-log">
          <summary className="scrape-progress__event-log-summary">
            View event log ({events.length} events)
          </summary>
          <div className="scrape-progress__event-log-items">
            {events.map((event, index) => (
              <div key={index} className="scrape-progress__event-log-item">
                <span className="scrape-progress__event-log-type">
                  {event.event}
                </span>
                <span className="scrape-progress__event-log-time">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function getStatusIcon(status: ScrapeStatus): string {
  switch (status) {
    case 'connecting':
      return '🔄';
    case 'connected':
      return '📡';
    case 'scraping':
      return '🔍';
    case 'validating':
      return '✓';
    case 'completed':
      return '✅';
    case 'error':
      return '❌';
    case 'disconnected':
      return '📴';
    default:
      return '⏳';
  }
}

function getStatusText(status: ScrapeStatus): string {
  switch (status) {
    case 'connecting':
      return 'Connecting to scraping service...';
    case 'connected':
      return 'Connected - Waiting for scrape to start';
    case 'scraping':
      return 'Scraping businesses...';
    case 'validating':
      return 'Validating websites...';
    case 'completed':
      return 'Scraping completed successfully!';
    case 'error':
      return 'Error occurred';
    case 'disconnected':
      return 'Connection lost';
    default:
      return 'Unknown status';
  }
}
