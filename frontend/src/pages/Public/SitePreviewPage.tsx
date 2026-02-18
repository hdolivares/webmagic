/**
 * Public Site Preview Page
 * 
 * Allows potential customers to view a site preview and purchase it.
 * This is a PUBLIC page (no auth required).
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ExternalLink, Check, Sparkles, Zap, Shield, ArrowRight } from 'lucide-react'

interface SitePreview {
  id: string
  slug: string
  site_title: string
  site_description: string
  purchase_amount: number
  monthly_amount: number
  status: string
  business_name?: string
  preview_url: string
}

interface CheckoutResponse {
  checkout_id: string
  checkout_url: string
  site_slug: string
  site_title: string
  amount: number
  currency: string
}

export default function SitePreviewPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [site, setSite] = useState<SitePreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [purchaseLoading, setPurchaseLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [showForm, setShowForm] = useState(false)

  // Fetch site details
  useEffect(() => {
    const fetchSite = async () => {
      try {
        setLoading(true)
        const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
        const response = await fetch(`${API_BASE}/sites/public/${slug}`)
        
        if (!response.ok) {
          throw new Error('Site not found')
        }
        
        const data = await response.json()
        setSite({
          ...data,
          preview_url: `https://sites.lavish.solutions/${slug}`
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load site')
      } finally {
        setLoading(false)
      }
    }

    if (slug) {
      fetchSite()
    }
  }, [slug])

  // Handle purchase/claim
  const handleClaim = async () => {
    // Validate required fields
    if (!name || name.trim().length === 0) {
      alert('Please enter your full name')
      return
    }
    
    if (!email || email.trim().length === 0) {
      alert('Please enter your email address')
      return
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      alert('Please enter a valid email address')
      return
    }

    try {
      setPurchaseLoading(true)
      const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
      
      const response = await fetch(`${API_BASE}/sites/${slug}/purchase`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          customer_email: email,
          customer_name: name,
          success_url: `${window.location.origin}/purchase-success?slug=${slug}`,
          cancel_url: `${window.location.origin}/site-preview/${slug}`
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create checkout')
      }

      const data: CheckoutResponse = await response.json()
      
      // Redirect to payment page
      window.location.href = data.checkout_url
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start purchase')
      setPurchaseLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-600 to-secondary-600 flex items-center justify-center">
        <div className="text-center text-white">
          <div className="w-16 h-16 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-lg">Loading site preview...</p>
        </div>
      </div>
    )
  }

  if (error || !site) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-600 to-secondary-600 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-md text-center">
          <div className="text-6xl mb-4">😕</div>
          <h2 className="text-2xl font-bold text-text-primary mb-2">Site Not Found</h2>
          <p className="text-text-secondary mb-4">{error || 'This site does not exist or is not available.'}</p>
          <button
            onClick={() => navigate('/')}
            className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700"
          >
            Go Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-600 via-secondary-600 to-accent-600">
      {/* Header */}
      <div className="bg-white/10 backdrop-blur-sm border-b border-white/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Sparkles className="w-8 h-8 text-white" />
              <span className="text-2xl font-bold text-white">WebMagic</span>
            </div>
            <a
              href={site.preview_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              <span>View Live Site</span>
            </a>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left Column - Site Info */}
          <div className="text-white space-y-8">
            <div>
              <div className="inline-block bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-semibold mb-4">
                ✨ AI-Generated Website
              </div>
              <h1 className="text-5xl font-bold mb-4 leading-tight">
                {site.site_title}
              </h1>
              <p className="text-xl text-white/80">
                {site.site_description}
              </p>
            </div>

            {/* Features */}
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <div className="bg-white/20 p-2 rounded-lg">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Lightning Fast</h3>
                  <p className="text-white/80">Optimized for speed and performance</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="bg-white/20 p-2 rounded-lg">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Secure & Reliable</h3>
                  <p className="text-white/80">SSL certificate and hosting included</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="bg-white/20 p-2 rounded-lg">
                  <Check className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Fully Customizable</h3>
                  <p className="text-white/80">Request unlimited AI-powered edits</p>
                </div>
              </div>
            </div>

            {/* Pricing Badge */}
            <div className="bg-white/20 backdrop-blur-sm p-6 rounded-xl">
              <div className="flex items-baseline space-x-2 mb-2">
                <span className="text-5xl font-bold">${site.purchase_amount}</span>
                <span className="text-xl text-white/80">one-time</span>
              </div>
              <div className="text-white/80 mb-4">
                + ${site.monthly_amount}/month hosting
              </div>
              <div className="text-sm text-white/70 border-t border-white/20 pt-4">
                <p className="mb-2"><strong>What you pay today:</strong> ${site.purchase_amount}</p>
                <p><strong>Starting next month:</strong> ${site.monthly_amount}/month</p>
              </div>
            </div>
          </div>

          {/* Right Column - CTA Card */}
          <div className="bg-white rounded-2xl shadow-2xl p-8 space-y-6">
            {!showForm ? (
              <>
                <div className="text-center">
                  <h2 className="text-3xl font-bold text-text-primary mb-2">
                    Claim This Website
                  </h2>
                  <p className="text-text-secondary">
                    Get started in minutes with your own professional website
                  </p>
                </div>

                {/* What's Included */}
                <div className="space-y-3 py-4">
                  <div className="flex items-center space-x-3">
                    <Check className="w-5 h-5 text-success-600 flex-shrink-0" />
                    <span className="text-text-secondary">AI-generated design & content</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Check className="w-5 h-5 text-success-600 flex-shrink-0" />
                    <span className="text-text-secondary">Custom domain support</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Check className="w-5 h-5 text-success-600 flex-shrink-0" />
                    <span className="text-text-secondary">Unlimited AI-powered edits</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Check className="w-5 h-5 text-success-600 flex-shrink-0" />
                    <span className="text-text-secondary">SSL certificate included</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Check className="w-5 h-5 text-success-600 flex-shrink-0" />
                    <span className="text-text-secondary">24/7 hosting & support</span>
                  </div>
                </div>

                <button
                  onClick={() => setShowForm(true)}
                  className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-4 px-6 rounded-xl transition-all transform hover:scale-105 flex items-center justify-center space-x-2 shadow-lg"
                >
                  <span>Claim This Site</span>
                  <ArrowRight className="w-5 h-5" />
                </button>

                <p className="text-center text-sm text-text-tertiary">
                  Secure payment powered by Recurrente
                </p>
              </>
            ) : (
              <>
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-text-primary mb-2">
                    Enter Your Details
                  </h2>
                  <p className="text-text-secondary text-sm">
                    We'll create your account and send you login details
                  </p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Full Name <span className="text-error-600">*</span>
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="John Doe"
                      className="w-full px-4 py-3 border border-border-default rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      disabled={purchaseLoading}
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Email Address <span className="text-error-600">*</span>
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="john@example.com"
                      className="w-full px-4 py-3 border border-border-default rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      disabled={purchaseLoading}
                      required
                    />
                  </div>

                  {/* Pricing Breakdown */}
                  <div className="bg-bg-secondary p-4 rounded-lg space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-text-secondary">Today's Payment:</span>
                      <span className="font-bold text-text-primary text-lg">
                        ${site.purchase_amount}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm pb-3 border-b border-border-default">
                      <span className="text-text-secondary">Then Monthly:</span>
                      <span className="font-semibold text-text-primary">
                        ${site.monthly_amount}/mo
                      </span>
                    </div>
                    <div className="text-xs text-text-tertiary leading-relaxed">
                      <p className="mb-1">✓ Includes first month hosting</p>
                      <p>✓ Monthly billing starts in 30 days</p>
                      <p>✓ Cancel anytime, no commitment</p>
                    </div>
                  </div>

                  {/* Legal Disclaimer */}
                  <div className="bg-warning-50 border border-warning-200 rounded-lg p-3">
                    <p className="text-xs text-warning-800 leading-relaxed">
                      <strong>Payment Authorization:</strong> By completing this purchase, you authorize Lavish Solutions to charge your payment method <strong>${site.purchase_amount} today</strong> for website setup and first month hosting, and <strong>${site.monthly_amount} per month</strong> starting 30 days from today for continued hosting and maintenance. You may cancel your subscription anytime.
                    </p>
                  </div>

                  <button
                    onClick={handleClaim}
                    disabled={purchaseLoading || !email || !name}
                    className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-border-default disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-xl transition-all flex items-center justify-center space-x-2"
                  >
                    {purchaseLoading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Processing...</span>
                      </>
                    ) : (
                      <>
                        <span>Continue to Payment</span>
                        <ArrowRight className="w-5 h-5" />
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => setShowForm(false)}
                    disabled={purchaseLoading}
                    className="w-full text-text-secondary hover:text-text-primary py-2 transition-colors"
                  >
                    ← Back
                  </button>
                </div>

                <p className="text-center text-xs text-text-tertiary">
                  By continuing, you agree to our Terms of Service and Privacy Policy
                </p>
              </>
            )}
          </div>
        </div>

        {/* Preview Frame */}
        <div className="mt-16">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6">
            <h3 className="text-2xl font-bold text-white mb-4 text-center">
              Site Preview
            </h3>
            <div className="bg-white rounded-lg shadow-2xl overflow-hidden" style={{ height: '600px' }}>
              <iframe
                src={site.preview_url}
                className="w-full h-full border-0"
                title="Site Preview"
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
