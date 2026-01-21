/**
 * Sites gallery page
 */
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/services/api'
import { Card, CardHeader, CardBody, CardTitle, Badge, Button } from '@/components/ui'
import { Globe, ExternalLink, Wand2 } from 'lucide-react'

export const SitesPage = () => {
  const navigate = useNavigate()
  
  const { data, isLoading } = useQuery({
    queryKey: ['sites'],
    queryFn: () => api.getSites({ limit: 50 }),
  })

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      completed: 'success',
      generating: 'info',
      failed: 'error',
      published: 'primary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  return (
    <div className="p-xl">
      <div className="flex items-center justify-between mb-xl">
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Generated Sites</h1>
          <p className="text-text-secondary">View all AI-generated websites</p>
        </div>
        
        <Button
          onClick={() => navigate('/sites/image-generator')}
          variant="primary"
          className="flex items-center gap-2"
        >
          <Wand2 className="w-4 h-4" />
          Test Image Generator
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-xl">
          <div className="spinner-lg" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-md">
          {data?.sites.map((site) => (
            <Card key={site.id} hover>
              <CardHeader className="flex items-center gap-md">
                <Globe className="w-5 h-5 text-primary-600" />
                <div className="flex-1">
                  <CardTitle>{site.subdomain}.webmagic.com</CardTitle>
                </div>
                {getStatusBadge(site.status)}
              </CardHeader>
              <CardBody>
                <div className="space-y-sm text-sm">
                  <div>
                    <span className="text-text-secondary">Business ID:</span>
                    <p className="font-mono text-xs text-text-primary truncate">
                      {site.business_id}
                    </p>
                  </div>
                  <div className="flex items-center justify-between text-text-tertiary text-xs">
                    <span>Created {new Date(site.created_at).toLocaleDateString()}</span>
                    {site.status === 'published' && (
                      <a
                        href={`https://${site.subdomain}.webmagic.com`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-primary-600 hover:underline"
                      >
                        <ExternalLink className="w-3 h-3" />
                        View
                      </a>
                    )}
                  </div>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
