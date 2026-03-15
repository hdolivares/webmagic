/**
 * Bandwidth Settings
 *
 * Displays traffic (in/out) from vnstat snapshot for the server.
 * When monitoring is not available (vnstat not installed or snapshot missing),
 * shows a clear message so the rest of Settings remains usable.
 */
import { useQuery } from '@tanstack/react-query'
import { Activity, AlertCircle } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui'
import { api } from '@/services/api'

function formatBytes(bytes: number): string {
  if (bytes >= 1e12) return `${(bytes / 1e12).toFixed(2)} TB`
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(2)} MB`
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(2)} KB`
  return `${bytes} B`
}

export const BandwidthSettings = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['bandwidth'],
    queryFn: () => api.getBandwidth(),
  })

  if (isLoading) {
    return (
      <Card>
        <CardBody>
          <div style={{ color: 'var(--color-text-secondary)', padding: '1rem' }}>
            Loading bandwidth data…
          </div>
        </CardBody>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardBody>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: 'var(--color-text-secondary)',
              padding: '1rem',
            }}
          >
            <AlertCircle size={20} style={{ color: 'var(--color-warning)' }} />
            Failed to load bandwidth data. Try again later.
          </div>
        </CardBody>
      </Card>
    )
  }

  if (!data?.available) {
    const reasonMessage =
      data?.reason === 'file_missing'
        ? 'Snapshot file is missing.'
        : data?.reason === 'file_too_old'
          ? 'Snapshot file is too old.'
          : data?.reason === 'parse_error'
            ? 'Snapshot file could not be read.'
            : 'Monitoring is not available.'
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <Card>
          <CardHeader>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity size={20} style={{ color: 'var(--color-text-tertiary)' }} />
              Bandwidth
            </CardTitle>
          </CardHeader>
          <CardBody>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>
              {reasonMessage} Ensure vnstat is installed and the snapshot cron is running on the server.
            </p>
            <p style={{ color: 'var(--color-text-tertiary)', fontSize: '0.875rem' }}>
              See the deployment runbook for vnstat setup and cron: <code>vnstat -i eth0 --json</code> to the configured path.
            </p>
          </CardBody>
        </Card>
      </div>
    )
  }

  const daily = data.daily ?? []
  const monthly = data.monthly
  const total = data.total
  const updatedAt = data.updated_at

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <Card>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={20} />
            Bandwidth
          </CardTitle>
          {updatedAt && (
            <p style={{ color: 'var(--color-text-tertiary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
              Last updated: {new Date(updatedAt).toLocaleString()}
              {data.interface ? ` · Interface: ${data.interface}` : ''}
            </p>
          )}
        </CardHeader>
        <CardBody>
          <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
            Expected: under 10 GB for normal manual use. High values may indicate bot traffic or pipeline activity.
          </p>

          {monthly && (
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text-primary)' }}>
                This month
              </div>
              <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                <span>Received: {formatBytes(monthly.rx_bytes)}</span>
                <span>Sent: {formatBytes(monthly.tx_bytes)}</span>
                <span>Total: {formatBytes(monthly.rx_bytes + monthly.tx_bytes)}</span>
              </div>
            </div>
          )}

          {total && (
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text-primary)' }}>
                All-time (since vnstat reset)
              </div>
              <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                <span>Received: {formatBytes(total.rx_bytes)}</span>
                <span>Sent: {formatBytes(total.tx_bytes)}</span>
              </div>
            </div>
          )}

          {daily.length > 0 && (
            <div>
              <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text-primary)' }}>
                Last 7 days
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--color-border-primary)' }}>
                      <th style={{ textAlign: 'left', padding: '0.5rem 0.75rem' }}>Date</th>
                      <th style={{ textAlign: 'right', padding: '0.5rem 0.75rem' }}>Received</th>
                      <th style={{ textAlign: 'right', padding: '0.5rem 0.75rem' }}>Sent</th>
                      <th style={{ textAlign: 'right', padding: '0.5rem 0.75rem' }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {daily.map((row) => (
                      <tr key={row.date} style={{ borderBottom: '1px solid var(--color-border-secondary)' }}>
                        <td style={{ padding: '0.5rem 0.75rem', color: 'var(--color-text-primary)' }}>{row.date}</td>
                        <td style={{ textAlign: 'right', padding: '0.5rem 0.75rem', color: 'var(--color-text-secondary)' }}>
                          {formatBytes(row.rx_bytes)}
                        </td>
                        <td style={{ textAlign: 'right', padding: '0.5rem 0.75rem', color: 'var(--color-text-secondary)' }}>
                          {formatBytes(row.tx_bytes)}
                        </td>
                        <td style={{ textAlign: 'right', padding: '0.5rem 0.75rem', color: 'var(--color-text-primary)' }}>
                          {formatBytes(row.rx_bytes + row.tx_bytes)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {daily.length === 0 && !monthly && !total && (
            <p style={{ color: 'var(--color-text-tertiary)', fontSize: '0.9rem' }}>
              No traffic data in snapshot yet. Ensure vnstat has been running and cron has written the JSON.
            </p>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
