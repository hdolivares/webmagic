/**
 * Image Generation Test Page
 * Standalone page for testing AI image generation
 */
import { ImageGenerator } from '@/components/ImageGenerator'
import { Wand2, Info } from 'lucide-react'

export const ImageGenerationPage = () => {
  const handleImageGenerated = (imageData: Blob, metadata: any) => {
    console.log('Image generated:', { 
      size: imageData.size, 
      metadata 
    })
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header__content">
          <div className="page-header__icon">
            <Wand2 className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="page-header__title">
              AI Image Generator
            </h1>
            <p className="page-header__description">
              Generate custom images for websites using Google's Gemini AI (Nano Banana)
            </p>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="info-banner">
        <Info className="w-5 h-5 text-info" />
        <div className="info-banner__content">
          <p className="info-banner__text">
            <strong>How it works:</strong> Enter business details and select image type. 
            The AI will generate a custom image based on the brand archetype and color palette.
          </p>
          <p className="info-banner__subtext">
            Generation typically takes 10-30 seconds. You can download the image once it's ready.
          </p>
        </div>
      </div>

      {/* Image Generator Component */}
      <div className="page-content">
        <ImageGenerator onImageGenerated={handleImageGenerated} />
      </div>
    </div>
  )
}
