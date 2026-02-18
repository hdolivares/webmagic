/**
 * Purchase Success Page
 * 
 * Shown after successful site purchase via Recurrente
 */
import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { CheckCircle, Mail, Lock, ExternalLink, ArrowRight } from 'lucide-react'

export default function PurchaseSuccessPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const slug = searchParams.get('slug')

  // No auto-redirect - user controls when to proceed

  return (
    <div className="min-h-screen bg-gradient-to-br from-success-500 to-success-700 flex items-center justify-center px-4">
      <div className="max-w-2xl w-full">
        {/* Success Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8 md:p-12 text-center">
          {/* Success Icon */}
          <div className="mb-6">
            <div className="w-24 h-24 bg-success-100 rounded-full flex items-center justify-center mx-auto mb-4 animate-bounce">
              <CheckCircle className="w-16 h-16 text-success-600" />
            </div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">
              🎉 Congratulations!
            </h1>
            <p className="text-xl text-text-secondary">
              Your website purchase was successful
            </p>
          </div>

          {/* Site Info */}
          {slug && (
            <div className="bg-bg-secondary rounded-lg p-6 mb-8">
              <p className="text-text-secondary text-sm mb-2">Your new website:</p>
              <p className="text-lg font-semibold text-text-primary break-all">
                {slug}
              </p>
              <a
                href={`https://sites.lavish.solutions/${slug}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 text-primary-600 hover:text-primary-700 mt-3 text-sm"
              >
                <span>View your site</span>
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          )}

          {/* Next Steps */}
          <div className="space-y-4 mb-8 text-left">
            <h2 className="text-xl font-semibold text-text-primary text-center mb-6">
              What happens next?
            </h2>

            <div className="flex items-start space-x-4 p-4 bg-primary-50 rounded-lg">
              <div className="bg-primary-100 p-2 rounded-lg flex-shrink-0">
                <Mail className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <h3 className="font-semibold text-text-primary mb-1">
                  1. Check your email
                </h3>
                <p className="text-sm text-text-secondary">
                  We've sent you an email with your account credentials and next steps.
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-4 p-4 bg-secondary-50 rounded-lg">
              <div className="bg-secondary-100 p-2 rounded-lg flex-shrink-0">
                <Lock className="w-6 h-6 text-secondary-600" />
              </div>
              <div>
                <h3 className="font-semibold text-text-primary mb-1">
                  2. Log in to your dashboard
                </h3>
                <p className="text-sm text-text-secondary">
                  Access your customer dashboard to manage your site, request edits, and more.
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-4 p-4 bg-accent-50 rounded-lg">
              <div className="bg-accent-100 p-2 rounded-lg flex-shrink-0">
                <ExternalLink className="w-6 h-6 text-accent-600" />
              </div>
              <div>
                <h3 className="font-semibold text-text-primary mb-1">
                  3. Customize your site
                </h3>
                <p className="text-sm text-text-secondary">
                  Request unlimited AI-powered edits, add a custom domain, and make it yours!
                </p>
              </div>
            </div>
          </div>

          {/* CTA */}
          <div className="space-y-4">
            <button
              onClick={() => window.location.href = 'https://web.lavish.solutions/customer/login'}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-4 px-6 rounded-xl transition-all flex items-center justify-center space-x-2"
            >
              <span>Go to Customer Dashboard</span>
              <ArrowRight className="w-5 h-5" />
            </button>

            <p className="text-sm text-text-secondary italic">
              Click the button above when you're ready to access your dashboard
            </p>
          </div>

          {/* Support */}
          <div className="mt-8 pt-8 border-t border-border-default">
            <p className="text-sm text-text-secondary">
              Need help? Contact us at{' '}
              <a href="mailto:support@lavish.solutions" className="text-primary-600 hover:text-primary-700">
                support@lavish.solutions
              </a>
            </p>
          </div>
        </div>

        {/* Footer Note */}
        <p className="text-center text-white/80 mt-6 text-sm">
          Thank you for choosing WebMagic! 🚀
        </p>
      </div>
    </div>
  )
}
