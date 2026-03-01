/**
 * Manual Site Builder Page
 *
 * Lets an admin generate a website from a free-form business description.
 * No scraped data required — Claude interprets and expands the description
 * before the normal 4-stage pipeline runs.
 */
import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, X, Wand2, ChevronRight, Loader2, AlertCircle } from 'lucide-react'
import { api } from '@/services/api'
import { Button, Card, CardBody } from '@/components/ui'
import type { ManualGenerationRequest } from '@/types'
import './ManualSiteBuilderPage.css'

// ─── Generation pipeline step labels ─────────────────────────────────────────

const PIPELINE_STEPS = [
  { key: 'interpreting',   label: 'Understanding your business…'      },
  { key: 'analyzing',      label: 'Analyzing brand personality…'       },
  { key: 'concepting',     label: 'Generating visual concepts…'        },
  { key: 'designing',      label: 'Designing the look and feel…'       },
  { key: 'building',       label: 'Building your site…'                },
  { key: 'completing',     label: 'Wrapping up…'                       },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

interface ImageThumbnailProps {
  dataUri: string
  onRemove: () => void
}

function ImageThumbnail({ dataUri, onRemove }: ImageThumbnailProps) {
  return (
    <div className="manual-builder__thumbnail">
      <img src={dataUri} alt="Branding reference" className="manual-builder__thumbnail-img" />
      <button
        type="button"
        onClick={onRemove}
        className="manual-builder__thumbnail-remove"
        aria-label="Remove image"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  )
}

interface WebsiteTypeSelectorProps {
  value: 'informational' | 'ecommerce'
  onChange: (v: 'informational' | 'ecommerce') => void
}

function WebsiteTypeSelector({ value, onChange }: WebsiteTypeSelectorProps) {
  return (
    <div className="manual-builder__type-grid">
      {(
        [
          {
            id: 'informational' as const,
            title: 'Informational',
            description: 'Hero, about, services, testimonials, contact form — ideal for service businesses.',
          },
          {
            id: 'ecommerce' as const,
            title: 'E-commerce',
            description: 'Product grid, categories, deals, bestsellers, newsletter — ideal for online stores.',
          },
        ] satisfies Array<{ id: 'informational' | 'ecommerce'; title: string; description: string }>
      ).map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onChange(option.id)}
          className={[
            'manual-builder__type-option',
            value === option.id ? 'manual-builder__type-option--active' : '',
          ].join(' ')}
        >
          <span className="manual-builder__type-title">{option.title}</span>
          <span className="manual-builder__type-desc">{option.description}</span>
        </button>
      ))}
    </div>
  )
}

interface GenerationProgressProps {
  currentStep: number
}

function GenerationProgress({ currentStep }: GenerationProgressProps) {
  return (
    <div className="manual-builder__progress">
      <div className="manual-builder__progress-spinner">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
      <ul className="manual-builder__progress-steps">
        {PIPELINE_STEPS.map((step, idx) => {
          const isDone    = idx < currentStep
          const isCurrent = idx === currentStep
          return (
            <li
              key={step.key}
              className={[
                'manual-builder__progress-step',
                isDone    ? 'manual-builder__progress-step--done'    : '',
                isCurrent ? 'manual-builder__progress-step--active'  : '',
              ].join(' ')}
            >
              <span className="manual-builder__progress-step-dot" />
              {step.label}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

// ─── Pricing helpers ──────────────────────────────────────────────────────────

/** Format a number as a price string without trailing zeros. */
function fmtPrice(value: number): string {
  return value % 1 === 0
    ? value.toLocaleString('en-US', { minimumFractionDigits: 0 })
    : value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function ManualSiteBuilderPage() {
  const navigate = useNavigate()

  // ── Form state ──────────────────────────────────────────────────────────────
  const [description, setDescription] = useState('')
  const [websiteType, setWebsiteType]  = useState<'informational' | 'ecommerce'>('informational')
  const [brandingNotes, setBrandingNotes] = useState('')
  const [brandingImages, setBrandingImages] = useState<string[]>([])

  // Hard facts
  const [name,    setName]    = useState('')
  const [phone,   setPhone]   = useState('')
  const [email,   setEmail]   = useState('')
  const [address, setAddress] = useState('')
  const [city,    setCity]    = useState('')
  const [state,   setState]   = useState('')

  // Pricing (optional — defaults applied on the backend)
  const [oneTimePrice, setOneTimePrice] = useState<string>('')
  const [monthlyPrice, setMonthlyPrice] = useState<string>('')
  const [currencySymbol, setCurrencySymbol] = useState<string>('$')

  // ── Generation state ─────────────────────────────────────────────────────────
  const [isGenerating, setIsGenerating]     = useState(false)
  const [currentStep, setCurrentStep]       = useState(0)
  const [error, setError]                   = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Image upload ─────────────────────────────────────────────────────────────
  const handleFileChange = useCallback(
    (files: FileList | null) => {
      if (!files) return
      const remaining = 5 - brandingImages.length
      Array.from(files)
        .slice(0, remaining)
        .forEach((file) => {
          const reader = new FileReader()
          reader.onload = (e) => {
            const result = e.target?.result
            if (typeof result === 'string') {
              setBrandingImages((prev) => [...prev, result])
            }
          }
          reader.readAsDataURL(file)
        })
    },
    [brandingImages.length],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      handleFileChange(e.dataTransfer.files)
    },
    [handleFileChange],
  )

  const removeImage = useCallback((idx: number) => {
    setBrandingImages((prev) => prev.filter((_, i) => i !== idx))
  }, [])

  // ── Submission ────────────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim()) return

    setError(null)
    setIsGenerating(true)
    setCurrentStep(0)

    const parsedOneTime = oneTimePrice !== '' ? parseFloat(oneTimePrice) : undefined
    const parsedMonthly = monthlyPrice !== '' ? parseFloat(monthlyPrice) : undefined

    const payload: ManualGenerationRequest = {
      description: description.trim(),
      website_type: websiteType,
      ...(name.trim()    && { name:    name.trim()    }),
      ...(phone.trim()   && { phone:   phone.trim()   }),
      ...(email.trim()   && { email:   email.trim()   }),
      ...(address.trim() && { address: address.trim() }),
      ...(city.trim()    && { city:    city.trim()    }),
      ...(state.trim()   && { state:   state.trim()   }),
      ...(brandingNotes.trim() && { branding_notes: brandingNotes.trim() }),
      ...(brandingImages.length && { branding_images: brandingImages }),
      ...(parsedOneTime !== undefined && !isNaN(parsedOneTime) && { one_time_price: parsedOneTime }),
      ...(parsedMonthly !== undefined && !isNaN(parsedMonthly) && { monthly_price: parsedMonthly }),
      ...(currencySymbol.trim() && currencySymbol.trim() !== '$' && { currency_symbol: currencySymbol.trim() }),
    }

    try {
      const { site_id } = await api.generateManualSite(payload)

      // Advance the progress indicator while polling
      const stepInterval = setInterval(() => {
        setCurrentStep((prev) =>
          prev < PIPELINE_STEPS.length - 2 ? prev + 1 : prev,
        )
      }, 12_000)

      await api.pollSiteUntilComplete(site_id, (status) => {
        if (status === 'completed') setCurrentStep(PIPELINE_STEPS.length - 1)
      })

      clearInterval(stepInterval)
      navigate(`/sites/generated/${site_id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.')
      setIsGenerating(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  if (isGenerating) {
    return (
      <div className="page-container">
        <div className="manual-builder__generating-shell">
          <h1 className="manual-builder__generating-title">Building your site…</h1>
          <p className="manual-builder__generating-sub">
            The AI pipeline is running — this usually takes 1–3 minutes.
          </p>
          <GenerationProgress currentStep={currentStep} />
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="manual-builder">

        {/* ── Page header ─────────────────────────────────────────────────── */}
        <header className="manual-builder__header">
          <div className="manual-builder__header-icon">
            <Wand2 className="w-6 h-6" />
          </div>
          <div>
            <h1 className="manual-builder__title">Manual Site Builder</h1>
            <p className="manual-builder__subtitle">
              Describe any business and let the AI build a complete website from scratch.
            </p>
          </div>
        </header>

        {error && (
          <div className="manual-builder__error" role="alert">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="manual-builder__form">

          {/* ── Section 1: Description ──────────────────────────────────── */}
          <Card>
            <CardBody>
              <section className="manual-builder__section">
                <h2 className="manual-builder__section-title">
                  <span className="manual-builder__step-badge">1</span>
                  Tell us about the business
                </h2>

                <label htmlFor="description" className="manual-builder__label">
                  Business description <span className="manual-builder__required">*</span>
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  rows={6}
                  placeholder={
                    "Describe the business in your own words — what they sell or offer, " +
                    "who they are, what makes them special, any details you know.\n\n" +
                    "Example: \"A website for a store that sells only cat-related products " +
                    "and home decor. The owner is Maria, a passionate cat lover, and the " +
                    "store also has a podcast about cat care tips...\""
                  }
                  className="manual-builder__textarea"
                />
                <p className="manual-builder__hint">
                  The more you share, the better. Claude will understand it, fill in the gaps,
                  and build the full picture.
                </p>
              </section>
            </CardBody>
          </Card>

          {/* ── Section 2: Key details (hard facts) ────────────────────── */}
          <Card>
            <CardBody>
              <section className="manual-builder__section">
                <h2 className="manual-builder__section-title">
                  <span className="manual-builder__step-badge">2</span>
                  Key details
                  <span className="manual-builder__optional-badge">Optional</span>
                </h2>

                <div className="manual-builder__fields-row">
                  <div className="manual-builder__field">
                    <label htmlFor="biz-name" className="manual-builder__label">Business name</label>
                    <input
                      id="biz-name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Ajoji"
                      className="manual-builder__input"
                    />
                  </div>
                  <div className="manual-builder__field">
                    <label htmlFor="biz-phone" className="manual-builder__label">Phone</label>
                    <input
                      id="biz-phone"
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+1 (555) 000-0000"
                      className="manual-builder__input"
                    />
                  </div>
                  <div className="manual-builder__field">
                    <label htmlFor="biz-email" className="manual-builder__label">Email</label>
                    <input
                      id="biz-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="hello@business.com"
                      className="manual-builder__input"
                    />
                  </div>
                </div>

                <div className="manual-builder__fields-row">
                  <div className="manual-builder__field manual-builder__field--grow">
                    <label htmlFor="biz-address" className="manual-builder__label">Street address</label>
                    <input
                      id="biz-address"
                      type="text"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="123 Main St"
                      className="manual-builder__input"
                    />
                  </div>
                  <div className="manual-builder__field">
                    <label htmlFor="biz-city" className="manual-builder__label">City</label>
                    <input
                      id="biz-city"
                      type="text"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      placeholder="Miami"
                      className="manual-builder__input"
                    />
                  </div>
                  <div className="manual-builder__field manual-builder__field--narrow">
                    <label htmlFor="biz-state" className="manual-builder__label">State</label>
                    <input
                      id="biz-state"
                      type="text"
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      placeholder="FL"
                      className="manual-builder__input"
                    />
                  </div>
                </div>

                <p className="manual-builder__hint">
                  Anything you fill in here will be used verbatim on the website.
                  Leave blank and Claude will work from the description.
                </p>
              </section>
            </CardBody>
          </Card>

          {/* ── Section 3: Website type ──────────────────────────────────── */}
          <Card>
            <CardBody>
              <section className="manual-builder__section">
                <h2 className="manual-builder__section-title">
                  <span className="manual-builder__step-badge">3</span>
                  Website type
                </h2>
                <WebsiteTypeSelector value={websiteType} onChange={setWebsiteType} />
              </section>
            </CardBody>
          </Card>

          {/* ── Section 4: Branding ──────────────────────────────────────── */}
          <Card>
            <CardBody>
              <section className="manual-builder__section">
                <h2 className="manual-builder__section-title">
                  <span className="manual-builder__step-badge">4</span>
                  Branding
                  <span className="manual-builder__optional-badge">All optional</span>
                </h2>

                {/* Image drop zone */}
                <div
                  className="manual-builder__dropzone"
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  onClick={() => fileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
                  aria-label="Upload branding images"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    multiple
                    className="sr-only"
                    onChange={(e) => handleFileChange(e.target.files)}
                  />
                  <Upload className="w-8 h-8 text-text-secondary mb-2" />
                  <p className="manual-builder__dropzone-label">
                    Logo, brand photos, or any visual reference
                  </p>
                  <p className="manual-builder__dropzone-sub">
                    Drag &amp; drop or click to browse — up to 5 images
                  </p>
                </div>

                {brandingImages.length > 0 && (
                  <div className="manual-builder__thumbnails">
                    {brandingImages.map((img, idx) => (
                      <ImageThumbnail
                        key={idx}
                        dataUri={img}
                        onRemove={() => removeImage(idx)}
                      />
                    ))}
                  </div>
                )}

                {/* Style notes */}
                <label htmlFor="branding-notes" className="manual-builder__label mt-md">
                  Style notes
                </label>
                <textarea
                  id="branding-notes"
                  value={brandingNotes}
                  onChange={(e) => setBrandingNotes(e.target.value)}
                  rows={3}
                  placeholder={
                    '"deep navy and gold, luxury and minimal" — or — ' +
                    '"earthy greens, warm, approachable for families"'
                  }
                  className="manual-builder__textarea"
                />
                <p className="manual-builder__hint">
                  Describe colors, vibe, or style — or leave blank and let the AI decide.
                  Claude will derive a complete color system from even a vague description.
                </p>
              </section>
            </CardBody>
          </Card>

          {/* ── Section 5: Pricing ──────────────────────────────────────── */}
          <Card>
            <CardBody>
              <section className="manual-builder__section">
                <h2 className="manual-builder__section-title">
                  <span className="manual-builder__step-badge">5</span>
                  Pricing
                  <span className="manual-builder__optional-badge">Optional</span>
                </h2>

                {/* Currency symbol row */}
                <div className="manual-builder__field" style={{ marginBottom: '1rem' }}>
                  <label htmlFor="currency-symbol" className="manual-builder__label">
                    Currency symbol
                  </label>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input
                      id="currency-symbol"
                      type="text"
                      maxLength={8}
                      value={currencySymbol}
                      onChange={(e) => setCurrencySymbol(e.target.value)}
                      placeholder="$"
                      className="manual-builder__price-input"
                      style={{ maxWidth: '6rem' }}
                    />
                    <span className="manual-builder__pricing-hint" style={{ margin: 0 }}>
                      e.g. <code>$</code>&nbsp;USD · <code>Q</code>&nbsp;Quetzal · <code>€</code>&nbsp;Euro
                    </span>
                  </div>
                </div>

                <div className="manual-builder__pricing-row">
                  <div className="manual-builder__field">
                    <label htmlFor="price-one-time" className="manual-builder__label">
                      One-time claim price
                    </label>
                    <div className="manual-builder__price-input-wrap">
                      <span className="manual-builder__price-symbol">{currencySymbol || '$'}</span>
                      <input
                        id="price-one-time"
                        type="number"
                        min="0"
                        step="1"
                        value={oneTimePrice}
                        onChange={(e) => setOneTimePrice(e.target.value)}
                        placeholder="497"
                        className="manual-builder__price-input"
                      />
                    </div>
                  </div>

                  <div className="manual-builder__field">
                    <label htmlFor="price-monthly" className="manual-builder__label">
                      Monthly subscription
                    </label>
                    <div className="manual-builder__price-input-wrap">
                      <span className="manual-builder__price-symbol">{currencySymbol || '$'}</span>
                      <input
                        id="price-monthly"
                        type="number"
                        min="0"
                        step="1"
                        value={monthlyPrice}
                        onChange={(e) => setMonthlyPrice(e.target.value)}
                        placeholder="97"
                        className="manual-builder__price-input"
                      />
                    </div>
                  </div>
                </div>

                {/* Live pricing breakdown */}
                {(oneTimePrice !== '' || monthlyPrice !== '') && (() => {
                  const cur     = currencySymbol || '$'
                  const total   = parseFloat(oneTimePrice)  || 0
                  const monthly = parseFloat(monthlyPrice)  || 0
                  const setup   = total - monthly
                  return (
                    <div className="manual-builder__pricing-breakdown">
                      <div className="manual-builder__pricing-breakdown-row">
                        <span>Setup fee (one-time)</span>
                        <span className="manual-builder__pricing-breakdown-value">
                          {cur}{fmtPrice(Math.max(0, setup))}
                        </span>
                      </div>
                      <div className="manual-builder__pricing-breakdown-row">
                        <span>+ First month&apos;s subscription</span>
                        <span className="manual-builder__pricing-breakdown-value">
                          {cur}{fmtPrice(monthly)}
                        </span>
                      </div>
                      <div className="manual-builder__pricing-breakdown-row manual-builder__pricing-breakdown-row--total">
                        <span>First charge (shown on claim bar)</span>
                        <span className="manual-builder__pricing-breakdown-value">
                          {cur}{fmtPrice(total)}
                        </span>
                      </div>
                      <p className="manual-builder__pricing-hint">
                        After the first payment, the customer is billed {cur}{fmtPrice(monthly)}/month.
                      </p>
                    </div>
                  )
                })()}

                <p className="manual-builder__hint">
                  Leave blank to use the default pricing ($497 one-time · $97/month).
                  The one-time price is what the customer sees on the claim bar — it
                  includes the setup fee plus the first month&apos;s subscription.
                </p>
              </section>
            </CardBody>
          </Card>

          {/* ── Submit ──────────────────────────────────────────────────── */}
          <div className="manual-builder__submit-row">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={!description.trim() || isGenerating}
              className="manual-builder__submit-btn"
            >
              Build My Site
              <ChevronRight className="w-5 h-5" />
            </Button>
            <p className="manual-builder__submit-hint">
              Takes 1–3 minutes · 5–6 AI steps · fully automated
            </p>
          </div>

        </form>
      </div>
    </div>
  )
}
