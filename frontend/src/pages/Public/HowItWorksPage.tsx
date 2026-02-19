/**
 * How It Works / FAQ Page
 *
 * Public marketing page explaining the WebMagic post-purchase experience.
 * Includes: feature overview, visual editor demo, ticket system flow, FAQ accordion,
 * and JSON-LD FAQPage schema for SEO.
 */
import { useState, useEffect } from 'react'
import {
  Server,
  Shield,
  Smartphone,
  Sparkles,
  MessageSquare,
  Clock,
  MousePointer,
  Activity,
  Check,
  ChevronDown,
  Palette,
  Type,
  Image,
  Layout,
  Link,
  Phone,
  Calendar,
  DollarSign,
  ArrowRight,
  Zap,
} from 'lucide-react'
import './HowItWorksPage.css'

// ─── Types ───────────────────────────────────────────────────────────────────

interface FaqItem {
  question: string
  answer: string
}

interface FaqGroup {
  label: string
  items: FaqItem[]
}

// ─── FAQ Data ────────────────────────────────────────────────────────────────

const FAQ_GROUPS: FaqGroup[] = [
  {
    label: 'Getting Started',
    items: [
      {
        question: 'What do I get when I claim the site?',
        answer:
          'You get full ownership of a professionally designed, AI-built website tailored to your business. Immediately after purchase you receive login credentials to your customer portal where you can manage your site, request changes, and track the status of every update.',
      },
      {
        question: 'Do I need any technical skills?',
        answer:
          'None at all. You describe what you want in plain English — "make the hero background navy blue" or "update the phone number in the footer" — and our AI handles the rest. You can even click directly on any part of your website to pin exactly what you want changed.',
      },
      {
        question: 'What happens right after I purchase?',
        answer:
          'You\'ll receive a welcome email within minutes with your portal login. Your site is already live and hosted. Log in, head to "My Sites," and open a ticket whenever you\'re ready to make your first change.',
      },
    ],
  },
  {
    label: 'Changes & Customization',
    items: [
      {
        question: 'What can be changed on my site?',
        answer:
          'Almost everything: colors and gradients, fonts and typography, all written content, images and logos, navigation links, call-to-action buttons, contact details, business hours, service descriptions, pricing tables, and entire page sections (add or remove). If you can describe it, we can change it.',
      },
      {
        question: 'How do I request a change?',
        answer:
          'Open a "Site Edit" ticket from your portal. Describe what you want changed — one to three specific changes per ticket. Optionally, use the built-in visual selector to click on the exact element on your live website so there\'s zero ambiguity about what you\'re referring to.',
      },
      {
        question: 'What is the visual element selector?',
        answer:
          'It\'s a built-in inspector tool (similar to browser developer tools, but designed for non-technical users). When you open a Site Edit ticket, your website loads on the left side of the screen. Click "Pin element" for any change slot, then hover over and click any part of your site — the AI receives the exact element details, its CSS selector, and surrounding context. This eliminates guesswork entirely.',
      },
      {
        question: 'How many changes can I include in one ticket?',
        answer:
          'Up to three changes per ticket, each with its own description and optional pinned element. This keeps requests focused and ensures every change is applied correctly. Need more? Just open a second ticket — there\'s no limit on how many tickets you can submit.',
      },
      {
        question: 'How long until I see my changes?',
        answer:
          'Within 24 hours. Our AI pipeline processes your request automatically, generates a preview, and a team member reviews and deploys it. You\'ll receive an email notification the moment your update goes live.',
      },
      {
        question: "What if I'm not happy with a result?",
        answer:
          'Reply to the ticket or open a new one describing what needs adjusting. We iterate until it\'s right. There\'s no extra charge for revisions — updates are included in your monthly subscription.',
      },
    ],
  },
  {
    label: 'Billing & Hosting',
    items: [
      {
        question: "What's included in the $97/month?",
        answer:
          'Managed cloud hosting, SSL certificate, uptime monitoring, ongoing maintenance, unlimited support tickets, AI-powered site edits (within 24 hours), and access to the customer portal with the visual editor. No hidden fees.',
      },
      {
        question: 'Who hosts my website?',
        answer:
          'We do. Your site runs on our cloud infrastructure with 99.9% uptime SLA, automatic backups, and a free SSL certificate. You don\'t need to deal with servers, DNS (beyond your domain), or any hosting setup.',
      },
      {
        question: 'Can I cancel anytime?',
        answer:
          'Yes. You own the $497 one-time purchase — that\'s yours permanently. The $97/month covers hosting and the update service. Cancel the monthly plan at any time and we\'ll provide your site files so you can host elsewhere.',
      },
      {
        question: 'Do I get a custom domain?',
        answer:
          'Your site is immediately live on our servers. Connecting your own domain (e.g. www.yourbusiness.com) is included — open a ticket and we\'ll walk you through pointing your DNS records, or handle it for you entirely.',
      },
    ],
  },
  {
    label: 'Technical',
    items: [
      {
        question: 'Will my site work on mobile?',
        answer:
          'Yes. Every site we build is fully responsive — it adapts automatically to phones, tablets, and desktops. All updates we apply maintain mobile compatibility.',
      },
      {
        question: 'What if something breaks on my site?',
        answer:
          'Open a "Technical Support" ticket and our team responds within 24 hours. Critical outages are prioritized. We maintain version history for every site, so we can roll back any change instantly if needed.',
      },
      {
        question: 'Is my content secure?',
        answer:
          'Yes. All sites are served over HTTPS with a valid SSL certificate. Your portal access is protected by email/password authentication. We never share your data with third parties.',
      },
    ],
  },
]

// ─── JSON-LD Schema ───────────────────────────────────────────────────────────

function buildJsonLd(): string {
  const allItems = FAQ_GROUPS.flatMap((g) => g.items)
  return JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: allItems.map((item) => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.answer,
      },
    })),
  })
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function IncludedCard({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) {
  return (
    <div className="hiw-included-card">
      <div className="hiw-included-icon">
        <Icon size={22} />
      </div>
      <h3 className="hiw-included-title">{title}</h3>
      <p className="hiw-included-desc">{description}</p>
    </div>
  )
}

function FaqAccordionItem({ item, isOpen, onToggle }: { item: FaqItem; isOpen: boolean; onToggle: () => void }) {
  return (
    <div className={`hiw-faq-item ${isOpen ? 'hiw-faq-item--open' : ''}`}>
      <button className="hiw-faq-question" onClick={onToggle} aria-expanded={isOpen}>
        <span>{item.question}</span>
        <ChevronDown size={18} className="hiw-faq-chevron" />
      </button>
      <div className="hiw-faq-answer">
        <p>{item.answer}</p>
      </div>
    </div>
  )
}

function EditorDemo() {
  return (
    <div className="hiw-demo-wrapper" aria-label="Visual editor demonstration">
      <div className="hiw-demo-browser">
        {/* Browser chrome */}
        <div className="hiw-demo-chrome">
          <div className="hiw-demo-dots">
            <span /><span /><span />
          </div>
          <div className="hiw-demo-address">yoursite.com</div>
        </div>

        {/* Simulated site content */}
        <div className="hiw-demo-site">
          <div className="hiw-demo-nav">
            <div className="hiw-demo-logo" />
            <div className="hiw-demo-nav-links">
              <div className="hiw-demo-link" /><div className="hiw-demo-link" /><div className="hiw-demo-link" />
            </div>
          </div>
          <div className="hiw-demo-hero">
            <div className="hiw-demo-headline hiw-demo-highlight" />
            <div className="hiw-demo-subline" />
            <div className="hiw-demo-cta" />
          </div>
        </div>

        {/* Animated cursor */}
        <div className="hiw-demo-cursor" aria-hidden="true">
          <MousePointer size={20} />
        </div>

        {/* Highlight ring over headline */}
        <div className="hiw-demo-ring" aria-hidden="true" />
      </div>

      {/* Slide-in change panel */}
      <div className="hiw-demo-panel">
        <div className="hiw-demo-panel-header">
          <span className="hiw-demo-panel-badge">Change 1</span>
          <span className="hiw-demo-panel-status">Active</span>
        </div>
        <div className="hiw-demo-pinned">
          <div className="hiw-demo-pin-icon"><MousePointer size={12} /></div>
          <div className="hiw-demo-pin-info">
            <span className="hiw-demo-pin-tag">h1.site-headline</span>
            <span className="hiw-demo-pin-text">Hero headline · pinned</span>
          </div>
        </div>
        <div className="hiw-demo-textarea">
          <div className="hiw-demo-text-line" />
          <div className="hiw-demo-text-line hiw-demo-text-line--short" />
        </div>
        <div className="hiw-demo-submit">
          <span>Submit changes</span>
          <ArrowRight size={14} />
        </div>
      </div>
    </div>
  )
}

function TicketStep({ step, title, description }: { step: number; title: string; description: string }) {
  return (
    <div className="hiw-step">
      <div className="hiw-step-number">{step}</div>
      <div className="hiw-step-content">
        <h3 className="hiw-step-title">{title}</h3>
        <p className="hiw-step-desc">{description}</p>
      </div>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HowItWorksPage() {
  const [openFaqKey, setOpenFaqKey] = useState<string | null>(null)

  // Inject JSON-LD FAQPage schema into <head>
  useEffect(() => {
    const script = document.createElement('script')
    script.type = 'application/ld+json'
    script.textContent = buildJsonLd()
    script.id = 'faq-jsonld'
    document.head.appendChild(script)

    // Update page meta
    document.title = 'How It Works — WebMagic by Lavish Solutions'
    const metaDesc = document.querySelector('meta[name="description"]')
    const descContent =
      'Claim your AI-built website for $497. Get 24-hour AI-powered edits, a visual element selector, and full hosting included at $97/month. No technical skills needed.'
    if (metaDesc) {
      metaDesc.setAttribute('content', descContent)
    } else {
      const m = document.createElement('meta')
      m.name = 'description'
      m.content = descContent
      document.head.appendChild(m)
    }

    return () => {
      document.getElementById('faq-jsonld')?.remove()
    }
  }, [])

  const toggleFaq = (key: string) => {
    setOpenFaqKey((prev) => (prev === key ? null : key))
  }

  const handleClaimClick = () => {
    // Navigate to the site preview / purchase flow — users arrive from the claim bar
    // which already has their slug. From here they can go to a general contact page.
    window.location.href = 'mailto:hello@lavish.solutions?subject=I want to claim my website'
  }

  return (
    <div className="hiw-page">
      {/* ── 1. Hero ──────────────────────────────────────────────────────── */}
      <section className="hiw-hero">
        <div className="hiw-hero-inner">
          <div className="hiw-hero-badge">
            <Zap size={14} />
            <span>AI-Powered Website Ownership</span>
          </div>
          <h1 className="hiw-hero-headline">
            Your website. Your rules.<br />Zero technical skills needed.
          </h1>
          <p className="hiw-hero-sub">
            Claim your professionally built website for a one-time fee of <strong>$497</strong>, then <strong>$97/month</strong> for hosting, maintenance, and unlimited AI-powered updates — all delivered within 24 hours.
          </p>
          <div className="hiw-hero-actions">
            <button className="hiw-btn hiw-btn--primary" onClick={handleClaimClick}>
              Claim Your Site
              <ArrowRight size={16} />
            </button>
            <a href="#faq" className="hiw-btn hiw-btn--ghost">
              Skip to FAQ
            </a>
          </div>
          <div className="hiw-hero-trust">
            {['24-hour updates', 'No coding required', 'Cancel anytime', 'SSL included'].map((t) => (
              <span key={t} className="hiw-hero-trust-item">
                <Check size={13} />
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── 2. How It Works — 3 Steps ─────────────────────────────────── */}
      <section className="hiw-section hiw-section--alt">
        <div className="hiw-container">
          <div className="hiw-section-label">The process</div>
          <h2 className="hiw-section-title">From claim to live update in 3 steps</h2>
          <div className="hiw-steps-row">
            <div className="hiw-how-step">
              <div className="hiw-how-step-num">1</div>
              <h3>Claim</h3>
              <p>Pay once and get instant access to your customer portal. Your site is already live and ready.</p>
            </div>
            <div className="hiw-steps-arrow"><ArrowRight size={24} /></div>
            <div className="hiw-how-step">
              <div className="hiw-how-step-num">2</div>
              <h3>Request</h3>
              <p>Describe a change in plain English, or click directly on the part of your site you want updated.</p>
            </div>
            <div className="hiw-steps-arrow"><ArrowRight size={24} /></div>
            <div className="hiw-how-step">
              <div className="hiw-how-step-num">3</div>
              <h3>Done</h3>
              <p>Our AI processes your request, a team member reviews it, and the update goes live within 24 hours.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. What's Included ────────────────────────────────────────── */}
      <section className="hiw-section">
        <div className="hiw-container">
          <div className="hiw-section-label">Everything included</div>
          <h2 className="hiw-section-title">One subscription. Everything you need.</h2>
          <div className="hiw-included-grid">
            <IncludedCard icon={Server} title="Managed Hosting" description="Cloud infrastructure with 99.9% uptime SLA. No servers to manage, ever." />
            <IncludedCard icon={Shield} title="SSL Certificate" description="Your site is served over HTTPS from day one. Free, automatic, and always renewed." />
            <IncludedCard icon={Smartphone} title="Mobile-Ready Design" description="Every site adapts automatically to phones, tablets, and desktops." />
            <IncludedCard icon={Sparkles} title="AI-Powered Edits" description="Describe any change in plain English. Our AI understands non-technical language perfectly." />
            <IncludedCard icon={MessageSquare} title="Support Ticket System" description="A dedicated portal for every request — tracked, acknowledged, and resolved." />
            <IncludedCard icon={Clock} title="24-Hour Response SLA" description="Every site edit request is processed and live within 24 hours, guaranteed." />
            <IncludedCard icon={MousePointer} title="Visual Change Editor" description="Click on any element of your site to pin it to a change request — zero ambiguity." />
            <IncludedCard icon={Activity} title="Uptime Monitoring" description="We watch your site around the clock so you never have to worry about downtime." />
          </div>
        </div>
      </section>

      {/* ── 4. What Can Be Customized ────────────────────────────────── */}
      <section className="hiw-section hiw-section--alt">
        <div className="hiw-container hiw-container--narrow">
          <div className="hiw-section-label">Customization</div>
          <h2 className="hiw-section-title">If you can describe it, we can change it</h2>
          <p className="hiw-section-sub">
            There's no lock-in on content. Every part of your site can be updated on request.
          </p>
          <div className="hiw-custom-grid">
            {[
              { icon: Palette, label: 'Colors & gradients' },
              { icon: Type, label: 'Fonts & typography' },
              { icon: MessageSquare, label: 'All text & copy' },
              { icon: Image, label: 'Images & logos' },
              { icon: Layout, label: 'Page sections (add/remove)' },
              { icon: Link, label: 'Navigation links' },
              { icon: Zap, label: 'CTAs & buttons' },
              { icon: Phone, label: 'Contact details' },
              { icon: Calendar, label: 'Business hours' },
              { icon: DollarSign, label: 'Pricing & service info' },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="hiw-custom-item">
                <Icon size={16} />
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. Visual Editor Demo ────────────────────────────────────── */}
      <section className="hiw-section">
        <div className="hiw-container">
          <div className="hiw-section-label">The visual selector</div>
          <h2 className="hiw-section-title">Point. Click. Change.</h2>
          <p className="hiw-section-sub">
            When you open a Site Edit ticket, your live website loads right there. Hover over any element, click to pin it, then describe your change. Our AI knows exactly what you mean — no CSS knowledge required.
          </p>
          <EditorDemo />
          <p className="hiw-demo-caption">
            Simulated walkthrough — your actual site loads inside the editor panel
          </p>
        </div>
      </section>

      {/* ── 6. Ticket System Flow ────────────────────────────────────── */}
      <section className="hiw-section hiw-section--alt">
        <div className="hiw-container hiw-container--narrow">
          <div className="hiw-section-label">How updates work</div>
          <h2 className="hiw-section-title">From request to live in under 24 hours</h2>
          <div className="hiw-steps-vertical">
            <TicketStep
              step={1}
              title="Open a ticket"
              description={'Log in to your portal, choose "Site Edit," and describe what you want changed. Add up to 3 specific changes per ticket.'}
            />
            <TicketStep
              step={2}
              title="Pin elements (optional)"
              description="Use the visual selector to click on the exact part of your site you mean. The AI receives the element's full context — no guessing."
            />
            <TicketStep
              step={3}
              title="AI processes your request"
              description="Our AI pipeline reads your site's code, interprets your plain-English request, and generates the precise CSS or HTML changes needed."
            />
            <TicketStep
              step={4}
              title="Human review & deploy"
              description="A team member reviews the AI-generated preview for quality, then deploys the change to your live site."
            />
            <TicketStep
              step={5}
              title="You're notified"
              description="You receive an email confirmation and a message in your ticket thread the moment the update goes live — typically within 24 hours."
            />
          </div>
        </div>
      </section>

      {/* ── 7. FAQ ───────────────────────────────────────────────────── */}
      <section className="hiw-section" id="faq">
        <div className="hiw-container hiw-container--narrow">
          <div className="hiw-section-label">Frequently asked questions</div>
          <h2 className="hiw-section-title">Everything you wanted to ask</h2>

          {FAQ_GROUPS.map((group) => (
            <div key={group.label} className="hiw-faq-group">
              <h3 className="hiw-faq-group-label">{group.label}</h3>
              {group.items.map((item) => {
                const key = `${group.label}__${item.question}`
                return (
                  <FaqAccordionItem
                    key={key}
                    item={item}
                    isOpen={openFaqKey === key}
                    onToggle={() => toggleFaq(key)}
                  />
                )
              })}
            </div>
          ))}
        </div>
      </section>

      {/* ── 8. Final CTA ─────────────────────────────────────────────── */}
      <section className="hiw-cta-section">
        <div className="hiw-container hiw-container--narrow hiw-cta-inner">
          <h2 className="hiw-cta-headline">Ready to own your site?</h2>
          <p className="hiw-cta-sub">
            One-time <strong>$497</strong> to claim, then <strong>$97/month</strong> for hosting, maintenance, and unlimited updates. Cancel anytime.
          </p>
          <button className="hiw-btn hiw-btn--primary hiw-btn--large" onClick={handleClaimClick}>
            Claim Your Site Now
            <ArrowRight size={18} />
          </button>
          <p className="hiw-cta-note">Questions? Email us at <a href="mailto:hello@lavish.solutions">hello@lavish.solutions</a></p>
        </div>
      </section>
    </div>
  )
}
