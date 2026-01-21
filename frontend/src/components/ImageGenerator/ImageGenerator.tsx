/**
 * ImageGenerator Component
 * Reusable component for testing AI image generation
 * Follows semantic design system with modular architecture
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Button, Card, CardHeader, CardBody, CardTitle } from '@/components/ui'
import { 
  Wand2, 
  Download, 
  Loader2, 
  CheckCircle2, 
  XCircle,
  Image as ImageIcon 
} from 'lucide-react'
import type { 
  ImageGenerationRequest, 
  ImageType, 
  AspectRatio, 
  BrandArchetype 
} from '@/types'
import './ImageGenerator.css'

interface ImageGeneratorProps {
  /** Pre-filled business name */
  businessName?: string
  /** Pre-filled category */
  category?: string
  /** Callback when image is generated */
  onImageGenerated?: (imageData: Blob, metadata: any) => void
  /** Show compact version */
  compact?: boolean
}

export const ImageGenerator = ({
  businessName = '',
  category = '',
  onImageGenerated,
  compact = false,
}: ImageGeneratorProps) => {
  // Form state
  const [formData, setFormData] = useState<ImageGenerationRequest>({
    business_name: businessName,
    category: category,
    brand_archetype: 'Regular Guy',
    color_primary: '#2563eb',
    color_secondary: '#7c3aed',
    color_accent: '#f59e0b',
    image_type: 'hero',
    aspect_ratio: '16:9',
  })

  // Generated image state
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null)
  const [generatedMetadata, setGeneratedMetadata] = useState<any>(null)

  // Test generation (metadata only)
  const testMutation = useMutation({
    mutationFn: (data: ImageGenerationRequest) => api.testImageGeneration(data),
    onSuccess: (response) => {
      setGeneratedMetadata(response)
    },
  })

  // Download generation (actual image)
  const downloadMutation = useMutation({
    mutationFn: (data: ImageGenerationRequest) => api.downloadGeneratedImage(data),
    onSuccess: (blob) => {
      // Create URL for preview
      const url = URL.createObjectURL(blob)
      setGeneratedImageUrl(url)
      
      // Call callback if provided
      if (onImageGenerated) {
        onImageGenerated(blob, generatedMetadata)
      }
    },
  })

  const handleGenerate = () => {
    setGeneratedImageUrl(null)
    setGeneratedMetadata(null)
    downloadMutation.mutate(formData)
  }

  const handleDownload = () => {
    if (!generatedImageUrl) return
    
    const link = document.createElement('a')
    link.href = generatedImageUrl
    link.download = `${formData.image_type}-${formData.business_name.replace(/\s+/g, '-').toLowerCase()}.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const updateFormData = (updates: Partial<ImageGenerationRequest>) => {
    setFormData((prev) => ({ ...prev, ...updates }))
  }

  const isLoading = testMutation.isPending || downloadMutation.isPending
  const hasError = testMutation.isError || downloadMutation.isError

  return (
    <Card className={`image-generator ${compact ? 'image-generator--compact' : ''}`}>
      <CardHeader>
        <div className="image-generator__header">
          <div className="image-generator__header-icon">
            <Wand2 className="w-5 h-5" />
          </div>
          <CardTitle>AI Image Generator</CardTitle>
        </div>
      </CardHeader>

      <CardBody>
        <div className="image-generator__content">
          {/* Form Section */}
          <div className="image-generator__form">
            <FormSection title="Business Information">
              <FormField label="Business Name" required>
                <input
                  type="text"
                  className="form-input"
                  value={formData.business_name}
                  onChange={(e) => updateFormData({ business_name: e.target.value })}
                  placeholder="e.g., Sunset Spa & Wellness"
                />
              </FormField>

              <FormField label="Category" required>
                <input
                  type="text"
                  className="form-input"
                  value={formData.category}
                  onChange={(e) => updateFormData({ category: e.target.value })}
                  placeholder="e.g., spa, restaurant, cafe"
                />
              </FormField>
            </FormSection>

            <FormSection title="Brand Identity">
              <FormField label="Brand Archetype">
                <select
                  className="form-select"
                  value={formData.brand_archetype}
                  onChange={(e) => updateFormData({ brand_archetype: e.target.value as BrandArchetype })}
                >
                  <option value="Regular Guy">Regular Guy (Friendly)</option>
                  <option value="Explorer">Explorer (Adventurous)</option>
                  <option value="Creator">Creator (Innovative)</option>
                  <option value="Caregiver">Caregiver (Nurturing)</option>
                  <option value="Ruler">Ruler (Leadership)</option>
                  <option value="Sage">Sage (Wisdom)</option>
                  <option value="Innocent">Innocent (Pure)</option>
                  <option value="Hero">Hero (Courageous)</option>
                  <option value="Magician">Magician (Transformative)</option>
                  <option value="Outlaw">Outlaw (Revolutionary)</option>
                  <option value="Lover">Lover (Intimate)</option>
                  <option value="Jester">Jester (Fun)</option>
                </select>
              </FormField>

              <div className="form-field-group">
                <FormField label="Primary Color">
                  <ColorInput
                    value={formData.color_primary || '#2563eb'}
                    onChange={(color) => updateFormData({ color_primary: color })}
                  />
                </FormField>

                <FormField label="Secondary Color">
                  <ColorInput
                    value={formData.color_secondary || '#7c3aed'}
                    onChange={(color) => updateFormData({ color_secondary: color })}
                  />
                </FormField>

                <FormField label="Accent Color">
                  <ColorInput
                    value={formData.color_accent || '#f59e0b'}
                    onChange={(color) => updateFormData({ color_accent: color })}
                  />
                </FormField>
              </div>
            </FormSection>

            <FormSection title="Image Settings">
              <FormField label="Image Type">
                <div className="image-type-grid">
                  {(['hero', 'background', 'product', 'icon'] as ImageType[]).map((type) => (
                    <ImageTypeButton
                      key={type}
                      type={type}
                      selected={formData.image_type === type}
                      onClick={() => updateFormData({ image_type: type })}
                    />
                  ))}
                </div>
              </FormField>

              <FormField label="Aspect Ratio">
                <select
                  className="form-select"
                  value={formData.aspect_ratio}
                  onChange={(e) => updateFormData({ aspect_ratio: e.target.value as AspectRatio })}
                >
                  <option value="16:9">16:9 (Landscape)</option>
                  <option value="1:1">1:1 (Square)</option>
                  <option value="4:3">4:3 (Standard)</option>
                  <option value="3:2">3:2 (Photo)</option>
                  <option value="21:9">21:9 (Ultrawide)</option>
                </select>
              </FormField>
            </FormSection>

            <div className="image-generator__actions">
              <Button
                onClick={handleGenerate}
                disabled={isLoading || !formData.business_name || !formData.category}
                className="image-generator__generate-btn"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4" />
                    Generate Image
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Preview Section */}
          <div className="image-generator__preview">
            <div className="image-preview-container">
              {isLoading && (
                <div className="image-preview-loading">
                  <Loader2 className="w-12 h-12 animate-spin text-primary-600" />
                  <p className="image-preview-loading__text">
                    Generating your image...
                  </p>
                  <p className="image-preview-loading__subtext">
                    This usually takes 10-30 seconds
                  </p>
                </div>
              )}

              {hasError && (
                <div className="image-preview-error">
                  <XCircle className="w-12 h-12 text-error" />
                  <p className="image-preview-error__text">
                    Generation failed
                  </p>
                  <p className="image-preview-error__subtext">
                    Please try again or adjust parameters
                  </p>
                </div>
              )}

              {generatedImageUrl && !isLoading && (
                <div className="image-preview-success">
                  <img
                    src={generatedImageUrl}
                    alt={`Generated ${formData.image_type}`}
                    className="image-preview-success__img"
                  />
                  <div className="image-preview-success__overlay">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleDownload}
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </Button>
                  </div>
                </div>
              )}

              {!generatedImageUrl && !isLoading && !hasError && (
                <div className="image-preview-empty">
                  <ImageIcon className="w-16 h-16 text-text-tertiary" />
                  <p className="image-preview-empty__text">
                    No image generated yet
                  </p>
                  <p className="image-preview-empty__subtext">
                    Fill in the form and click "Generate Image"
                  </p>
                </div>
              )}
            </div>

            {/* Metadata Display */}
            {generatedMetadata && (
              <div className="image-metadata">
                <div className="image-metadata__item">
                  <CheckCircle2 className="w-4 h-4 text-success" />
                  <span>Success</span>
                </div>
                {generatedMetadata.size_bytes && (
                  <div className="image-metadata__item">
                    <span className="image-metadata__label">Size:</span>
                    <span className="image-metadata__value">
                      {(generatedMetadata.size_bytes / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                )}
                <div className="image-metadata__item">
                  <span className="image-metadata__label">Type:</span>
                  <span className="image-metadata__value">{formData.image_type}</span>
                </div>
                <div className="image-metadata__item">
                  <span className="image-metadata__label">Ratio:</span>
                  <span className="image-metadata__value">{formData.aspect_ratio}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

// ============================================
// SUB-COMPONENTS (Modular & Reusable)
// ============================================

interface FormSectionProps {
  title: string
  children: React.ReactNode
}

const FormSection = ({ title, children }: FormSectionProps) => (
  <div className="form-section">
    <h3 className="form-section__title">{title}</h3>
    <div className="form-section__content">{children}</div>
  </div>
)

interface FormFieldProps {
  label: string
  required?: boolean
  children: React.ReactNode
}

const FormField = ({ label, required, children }: FormFieldProps) => (
  <div className="form-field">
    <label className="form-field__label">
      {label}
      {required && <span className="form-field__required">*</span>}
    </label>
    {children}
  </div>
)

interface ColorInputProps {
  value: string
  onChange: (color: string) => void
}

const ColorInput = ({ value, onChange }: ColorInputProps) => (
  <div className="color-input">
    <input
      type="color"
      className="color-input__picker"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
    <input
      type="text"
      className="color-input__text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="#000000"
      pattern="^#[0-9A-Fa-f]{6}$"
    />
  </div>
)

interface ImageTypeButtonProps {
  type: ImageType
  selected: boolean
  onClick: () => void
}

const ImageTypeButton = ({ type, selected, onClick }: ImageTypeButtonProps) => {
  const icons: Record<ImageType, React.ReactNode> = {
    hero: '🖼️',
    background: '🎨',
    product: '📦',
    icon: '⭐',
  }

  return (
    <button
      type="button"
      className={`image-type-btn ${selected ? 'image-type-btn--selected' : ''}`}
      onClick={onClick}
      data-type={type}
    >
      <span className="image-type-btn__icon">{icons[type]}</span>
      <span className="image-type-btn__label">{type}</span>
    </button>
  )
}
