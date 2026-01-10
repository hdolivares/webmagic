# webmagic

Web design and development on autopilot


 I'm thinking about creating a software that scrapes only Google My business listings automatically, and it checks the information of multiple businesses and determines if the business already has a website or not.

If the business doesn't have a website and there is an email to contact the business, we copy the information of the business and request an LLM to expand the information and create a beautiful landing page. If the website needs more pages, we just make the buttons and links on the menu a # as a placeholder and only develop the landing page.

Then we would automate sending the email address a cold email selling the website, a link where they can see the website and screenshots of how their website looks like, and the link for them to pay for the website and have it ready to use within minutes. We would charge $600-$900 depending on the amount of info needed on the website and amount of pages needed, and we would charge $100/mo to keep the website and for maintenance, as a subscription service.

If the user decides to pay, we create a user for them on payment and then we also send an instruction to the LLM to continue building the rest of the website pages needed.

The websites created would use a generic subdomain address. If the users decide to purchase a domain they can redirect their website to their domain while logged in on the backend. If they need changes, they can take screenshots and write changes to a ticket system that would be connected to an LLM, and the LLM would do the needed changes for them.

I'm thinking about simple ,dynamic and beautifully designed websites using html/css/javascript, etc attached an example of a simple website. We would ideally separate also the css/javascript/etc and have files for each.

A server would manage a ton of very simple and fast websites with beautiful designs.

This entire process would need to be automated. Analyze what would be the best way to do this, what is the tech stack (avoid recommending docker) and create a very detailed implementation plan.



This is a sophisticated "Agency-in-a-Box" concept. It aligns perfectly with your "Mapio" outreach project but adds a vertically integrated product fulfillment layer.

The "Magic Trick" here is not just generating a website, but generating a website  **good enough to sell itself via a screenshot** . The example you provided (`secuencia_creative.html`) is high-end, utilizing noise textures, custom cursors, and GSAP-style animations. To achieve *that* level of quality automatically, you cannot simply ask an LLM to "write HTML." You need a **Component-Based Architecture** where the LLM acts as the "Content Director" and "Styler" rather than just a coder.

Here is the detailed implementation plan, avoiding Docker as requested, and focusing on a raw, high-performance Linux architecture.

### **The Tech Stack**

**Core Logic & Backend:**

* **Language:** Python 3.11+ (FastAPI). Python is non-negotiable here because of its dominance in scraping (Playwright/Selenium) and AI integration.
* **Database:** PostgreSQL (via Supabase or local install). You need relational data to track: `Business -> Scrape Status -> Site Version -> Subscription Status`.
* **Task Queue:** **Celery** with  **Redis** . This is crucial. Generating a site, taking a screenshot, and sending an email takes time. You cannot do this in the main API loop.

**Scraping & Outreach:**

* **GMB Data:**  **Outscraper API** . *Do not try to scrape Google Maps raw with Selenium.* Google's anti-bot is world-class. Outscraper handles the IP rotations and captchas for you.
* **Email:** **Amazon SES** (High volume, low cost) or **SendGrid** (easier setup).

**The "Factory" (Site Generation):**

* **LLM:** **Claude 3.5 Sonnet** (via Anthropic API). Currently, this model beats GPT-4o for frontend code generation (HTML/CSS/JS) by a significant margin.
* **Visuals:** **Flux.1** or **Midjourney API** (for generating hero background images specific to the business type if none exist).

**Hosting (The "Server"):**

* **OS:** Ubuntu 22.04 LTS (VPS on Hetzner, DigitalOcean, or Linode).
* **Web Server:**  **Nginx** . The absolute king of serving static files.
* **Storage:** Local NVMe SSD (fastest) + AWS S3 (backup).

---

### **Implementation Plan**

#### **Phase 1: The Hunter (Scraping & Filtering)**

We need to find businesses that *need* you.

1. **Input:** You feed the system a niche and location (e.g., "Landscapers in Nashville").
2. **API Call:** Python script hits Outscraper.
3. **The Filter:**
   * `website` field is empty.
   * `email` field is NOT empty (or use a secondary tool like Hunter.io to find the owner's email).
   * `rating` > 3.5 (Don't waste time on bad businesses).
4. **Storage:** Save valid leads to PostgreSQL with status `PENDING_GENERATION`.

#### **Phase 2: The Architect (Generative Engine)**

This is where we match the quality of your uploaded example.

* **Strategy:** Do not ask the LLM to write one giant HTML file. It will hallucinate closing tags.
* **The "Vibe" System:** Create 3-4 distinct "Master Templates" (HTML/CSS/JS skeletons) that support "Theming" via CSS Variables.
  * *Template A (Luxury):* Serif fonts, dark mode, gold accents (like your example).
  * *Template B (Clean):* Sans-serif, lots of white space, blue/green accents (Medical/Dental).
  * *Template C (Industrial):* Bold fonts, high contrast (Construction/Auto).
* **The Prompt Chain:**
  1. **Analyzer:** "Here is the business info. Pick the best Template (A, B, or C) and define the Color Palette (Hex codes) and Font pairing."
  2. **Copywriter:** "Write the H1 Headline, the 'About Us' paragraph, and 3 Service descriptions based on this business category."
  3. **Coder:** "Output the CSS variables and specific HTML content blocks for the selected template."
* **Assembly:** Python takes the raw HTML skeleton, injects the LLM-generated content and CSS variables, and saves `index.html`, `style.css`, and `script.js` into a folder: `/var/www/sites/{business_slug}/`.

#### **Phase 3: The Pitch (Automated Sales)**

1. **The Paparazzi:**
   * Use  **Playwright (Python)** .
   * Script spins up a headless browser, loads the local file `/var/www/sites/{business_slug}/index.html`.
   * **Crucial:** Set viewport to 1440p (Desktop) and 390p (Mobile). Take *two* screenshots.
   * Save images to a public folder.
2. **The Email:**
   * **Subject:** "I built a new website for {Business_Name} (Preview inside)"
   * **Body:** Keep it short. "I noticed you didn't have a website. I took the liberty of building a concept for you. It's ready to go live."
   * **The Hook:** Embed the screenshot.
   * **The CTA:** A link to a Stripe Checkout page ($600-$900).
   * **The Preview Link:** `https://{business_slug}.your-staging-domain.com`.

#### **Phase 4: The Platform (Nginx Multi-Tenancy)**

You want one server to handle thousands of sites efficiently. You don't need Docker for this; you need  **Nginx Virtual Hosting** .

Nginx Configuration Strategy:

You will use a Wildcard Subdomain setup.

1. **DNS:** Point `*.yourplatform.com` to your Server IP.
2. **Nginx Config (`/etc/nginx/sites-available/platform`):**
   **Nginx**

   ```
   server {
       listen 80;
       server_name ~^(?<subdomain>.+)\.yourplatform\.com$;
       root /var/www/sites/$subdomain;
       index index.html;

       location / {
           try_files $uri $uri/ =404;
       }
   }
   ```

   * **How it works:** If a user visits `plumber-joe.yourplatform.com`, Nginx automatically looks inside `/var/www/sites/plumber-joe/`.
   * **Zero Restart:** You can add new sites by just creating a folder. No need to restart Nginx.

#### **Phase 5: The Concierge (AI Maintenance & Ticket System)**

This is the subscription retention tool.

1. **The Dashboard:** User logs in. They see their live site in an iframe.
2. **The Ticket:** User types: "Change the background to blue and make the phone number bigger."
3. **The "Vision" Agent:**
   * Python reads the current `style.css` and `index.html`.
   * Sends the User Request + Current Code to  **Claude 3.5 Sonnet** .
   * Prompt: "You are a maintenance developer. Apply these changes to the code. Output ONLY the changed CSS/HTML."
4. **The Update:** Python overwrites the file. The change is instant.

### **Monetization & Flow Summary**

| **Stage** | **Action**              | **Tech** | **Cost to You** |
| --------------- | ----------------------------- | -------------- | --------------------- |
| **1**     | Scrape 1,000 leads            | Outscraper     | ~$2.00                |
| **2**     | Filter to 400 valid leads     | Python Script  | $0                    |
| **3**     | Generate 400 Sites            | Claude 3.5 API | ~$8.00                |
| **4**     | Send 400 Emails               | Amazon SES     | ~$0.04                |
| **TOTAL** | **400 Potential Sales** |                | **~$10.04**     |

If **one** person buys at $600, you have a 60x ROI on the campaign cost.

### **Next Steps for You**

1. **Validation:** Do not build the automated payment system yet. First, manually find 10 emails, generate 10 sites using ChatGPT manually, and send the emails. See if people click.
2. **Template Creation:** Build the "Master Template" (like the `secuencia` file you uploaded) but clean it up so variables (Colors, Name, Text) can be easily swapped by Python strings.

Would you like me to generate the **Python logic for the "Generation Module"** that takes a business description and dynamically fills your HTML template?



I also need the system to be running in autopilot mode and since google my business is mostly local seo, we need the system to auto run these campaigns with locations and have a sub system for coverage, so we can tackle all major cities in all the states in the US. The system should be smart enough to remember what industries, types of business, regions and states we have already covered, etc.

Also, we can't use only 3 templates, as that would highly suck and not be hype personalized, so we need a master prompt to handle this.

Since we are going to be scraping the information of a business on google my business, we will already have an idea of the industry and type of business we are coming in contact with. We would need the LLM to first analyze that information to determine the important things about that business, and then based on that, we'll use a master prompt that will take this information, and with that we will guide the llm to create another prompt to request a very specific and personalized website.

I usually try to use the following to create good frontend aesthetics. Additionally we can request the usage of iconography from open source places like https://iconify.design/ and the lucide or solar line of icons. And also we can direct the llm to use bento grids as inspiration. While I usually restrict the usage of generic colors, we could have an exception for this if the company has a logo and we would want to play with the contrast/colors to make sure the identity we are creating makes a lot more sense.

<frontend_aesthetics>

You tend to converge toward generic, "on distribution" outputs. In frontend design,this creates what users call the "AI slop" aesthetic. Avoid this: make creative,distinctive frontends that surprise and delight.

Focus on:

- Typography: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics.
- Color & Theme: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Draw from IDE themes and cultural aesthetics for inspiration.
- Motion: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions.
- Backgrounds: Create atmosphere and depth rather than defaulting to solid colors. Layer CSS gradients, use geometric patterns, or add contextual effects that match the overall aesthetic.

Avoid generic AI-generated aesthetics:

- Overused font families (Inter, Roboto, Arial, system fonts)
- Clichéd color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
- Cookie-cutter design that lacks context-specific character

Interpret creatively and make unexpected choices that feel genuinely designed for the context. Vary between light and dark themes, different fonts, different aesthetics. You still tend to converge on common choices (Space Grotesk, for example) across generations. Avoid this: it is critical that you think outside the box!

</frontend_aesthetics>

So I can imagine we can create a set of steps with different calls and prompts on different processes to achieve personalized designs without having to rely on templates. Analyze what would be the best way to create these things



This is a massive pivot from "simple automation" to "autonomous creative agency." To achieve this without templates and without "AI slop," you need a  **multi-agent cognitive pipeline** .

You are essentially building a digital "Creative Director" and "Frontend Developer" who work together on every single project.

Here is the blueprint for  **Project Autopilot** .

### **I. The Architecture: "The Grid"**

We need a system that systematically "eats" through the US market without getting full or confused.

Database Schema (PostgreSQL):

You need three core tables to manage the autopilot state.

1. **`coverage_grid`** : The map of your conquest.

* `state` (e.g., "Texas")
* `city` (e.g., "Austin")
* `industry` (e.g., "HVAC")
* `status` (Pending, In Progress, Completed, Cooldown)

1. **`businesses`** : The leads.

* `gmb_id` (Unique Google ID to prevent duplicate contacts)
* `website_status` (Must be 'None')
* `contact_status` (Emailed, Clicked, Purchased)

1. **`campaign_logs`** : To prevent spamming.

### **II. The Creative Engine (No Templates)**

To avoid "AI Slop," we split the generation process into three distinct "Agents" (LLM calls). This mimics a real agency workflow.

#### **Phase 1: The Analyst (Context Extraction)**

* **Input:** GMB Data (Reviews, Business Name, Photos, Category).
* **Goal:** Extract the "Vibe" and "Brand DNA."
* **Prompt Strategy:** "Analyze these 50 reviews and the business name. Is this a 'family-owned, trusted, legacy' business or a 'modern, high-tech, fast' business? Extract a color palette based on their uploaded photos (or suggest one if missing) that fits this psychological profile."

#### **Phase 2: The Art Director (The Brief)**

* **Input:** Analyst Output + Your `<frontend_aesthetics>` prompt.
* **Goal:** Write a strict implementation plan.
* **Master Prompt:** "You are an Award-Winning UI Designer. Create a design brief for [Business Name]. Do NOT output code. Define:
  1. **Typography:** Choose a Google Font pairing (e.g., 'Space Grotesk' + 'Inter' is banned. Try 'Syne' + 'Manrope').
  2. **Layout:** Choose a structure (e.g., Bento Grid, Asymmetrical Split, Parallax Scroll).
  3. **Motion:** Define the entrance animations (e.g., 'Hero text staggers in from bottom, images reveal with a clip-path wiping right')."

#### **Phase 3: The Architect (The Code)**

* **Input:** The Art Director's Brief.
* **Goal:** Write the raw HTML/CSS/JS.
* **Constraint:** "Use **TailwindCSS** via CDN for structure, but write **Custom CSS** for the creative effects defined in the brief. Use **Iconify** for icons. Ensure the navigation links are `#` anchors."

---

### **III. Implementation Plan**

#### **1. The Tech Stack (No Docker)**

* **Orchestrator:** Python 3.11 + **Celery** (Task Queue).
* **Browser:** **Playwright** (for screenshots).
* **Database:** PostgreSQL.
* **Server:** Ubuntu 22.04 LTS (Hetzner AX series is great for raw power).
* **Reverse Proxy:** Nginx.

#### **2. The Autopilot Script (`conductor.py`)**

This script runs perpetually. It picks a target, scrapes it, and queues the "Factory" jobs.

**Python**

```
import outscraper
from app.db import get_next_target, save_lead
from app.tasks import generate_site_pipeline

def autopilot_tick():
    # 1. Select next battleground
    target = get_next_target() # Returns e.g., {"city": "Dallas", "state": "TX", "niche": "Roofing"}
  
    # 2. Scrape GMB
    results = outscraper.Api(api_key).google_maps_search(
        query=f"{target['niche']} in {target['city']}, {target['state']}",
        limit=50,
        drop_duplicates=True
    )
  
    # 3. Filter & Queue
    for business in results:
        if not business.get('site') and business.get('email'):
            # Found a lead!
            lead_id = save_lead(business)
            # Trigger the AI Agents asynchronously
            generate_site_pipeline.delay(lead_id)
          
    print(f"Scraped {len(results)} businesses in {target['city']}")

if __name__ == "__main__":
    while True:
        autopilot_tick()
```

#### **3. The "Anti-Slop" Prompt Chain**

This is the core differentiator.

**Agent 1: The Analyst**

**Python**

```
ANALYST_PROMPT = """
Analyze this business: {business_json}.
1. Brand Archetype: (e.g., The Sage, The Hero, The Everyman).
2. Color Psychology: Suggest a primary HEX and accent HEX that matches the archetype.
3. Content Strategy: What is the ONE main pain point their reviews mention? (e.g., "They show up on time").
"""
```

**Agent 2: The Art Director (Incorporating your aesthetics)**

**Python**

```
DIRECTOR_PROMPT = """
Context: {analyst_output}
Aesthetic Guidelines:
{your_frontend_aesthetics_xml}

Task: Create a visual brief for a landing page.
- Typography: Pick 1 Display font (Unique) and 1 Body font from Google Fonts.
- Layout: Describe a unique Hero Section (e.g., "Text on left, massive circular image on right").
- Background: Define a CSS background (gradient mesh, grain, or geometric pattern). NO solid white/black.
- Motion: Define one "Delight" moment (e.g., "The 'Call Now' button pulses when the user scrolls to the reviews").
"""
```

**Agent 3: The Architect**

**Python**

```
ARCHITECT_PROMPT = """
You are a Senior Frontend Dev. Build a single HTML file based on this brief: {director_output}.
- Use TailwindCSS (CDN) for layout.
- Use GSAP (CDN) for the animations defined.
- Use Iconify (CDN) for icons.
- Images: Use "https://source.unsplash.com/random/1600x900/?{industry}" for placeholders.
- OUTPUT ONLY RAW HTML CODE.
"""
```

### **IV. Managing the "Server Farm"**

You will have thousands of folders. Nginx can handle this with a  **dynamic wildcard configuration** .

File Structure:

/var/www/sites/us/tx/dallas/plumber-joe/index.html

Nginx Config (Dynamic Mapping):

This allows you to serve thousands of sites without reloading Nginx.

**Nginx**

```
map $host $site_path {
    # Extract subdomain to map to folder
    ~^(?<subdomain>.+)\.youragency\.com$ $subdomain;
}

server {
    server_name *.youragency.com;
    root /var/www/sites/$site_path;
    index index.html;
}
```

*Note: You'll need a small Python script to "flatten" the folder structure or map the subdomain to the complex path in a Redis key-value store for Nginx (using Lua module) if you want high-speed lookup, but a flat folder structure like `/var/www/sites/{uuid}/` is easier.*

### **V. Next Steps**

1. **Seed the Grid:** Download a CSV of "US Cities by Population." Import the top 500 cities into your `coverage_grid` table.
2. **Test the "Art Director":** Run the prompt manually in Claude 3.5 Sonnet with a fake business. Adjust the `<frontend_aesthetics>` block until it stops giving you "Corporate Memphis" designs.
3. **Build the Scraper:** Set up the `conductor.py` script to just print valid leads without emailing them yet.

Would you like the **SQL Schema** code to set up the tracking database, or the **Art Director Prompt** refined for a specific test industry?



I'm thinking that somewhere on our prompt, we should also pass a definition of what the page is for and what we are aiming to build.

The llm that will act as a world class senior frontend developer will steer away from building something generic and without style if it has enough information.

If we just pass the current info, we'll lack some of the direction. For example, if you request a website for a branding agency, it will be very generic.

However if you say something like "we need to create a website for a branding agency in mexico. They are known for thinking outside the box and being very genuine and unapologetic. We need to match that vibe. Think of an unusual loader, then a scroll stopping message as the hero and dynamics where the user can interact with the content" etc. The output will be very different. This is how I approached creating the example website with an LLM for the secuencia branding agency.

So we need to be able to capture that. You being an LLM should understand how you would create the information based on the those prompts, and what would be the outputs. Think of how we can create great things. Not just basic websites.

we should direct the LLM to creating different loaders and trying new things. I like that your director prompt uses typography, layout and describing sections, backgrounds, and motion. What else can we do?

Also, we should be saving the information being used to generate these websites, because these will direct the future of the development of the website. Also based on this information, we can start learning ourselves what works best and seeing what produces the best results



This creates a distinct challenge: **Most businesses you scrape (like a local HVAC tech) won't have a "vibe" yet.** They are blank slates.

If you feed the LLM "Bob's AC Repair" and ask for a website, you get a generic blue site. To get the "Secuencia" result (unapologetic, distinctive), the system must **invent a brand personality** for them before writing a single line of code.

We need to inject a **"Creative Concept" Agent** between the data scraping and the design phase. This agent's sole job is to hallucinate a distinct "Angle" or "Hook" so the designer has something specific to visualize.

Here is the enhanced pipeline to achieve "Award-Winning" output automatically.

### **1. The New Data Structure: "Creative DNA"**

We stop treating the website as just code and start treating it as a  **Brand Profile** . We save this object in your database (`business_profiles` table). This is the "Truth" the LLM refers to for every future edit or new page.

**The JSON Schema (Saved to DB):**

**JSON**

```
{
  "business_id": "12345",
  "generated_identity": {
    "archetype": "The Magician", // e.g., The Outlaw, The Caregiver, The Sage
    "angle": "Scientific precision in cleaning",
    "visual_theme": "Cyber-Medical",
    "tone_of_voice": "Clinical, abrupt, confident"
  },
  "design_system": {
    "primary_color": "#00FF41", // Neon Green
    "background_style": "Dark mode with technical grid overlay",
    "typography": {
      "heading": "Space Mono",
      "body": "Inter"
    },
    "signature_interaction": "Custom crosshair cursor",
    "loader_type": "Data decryption typing effect"
  }
}
```

### **2. Step 1: The "Concept" Agent (The Inventor)**

Before we design, we must define *what* we are building. This agent takes the boring GMB data and spins it into a "Concept."

**Prompt Strategy:**

> "You are a Creative Director at a world-class branding agency.
>
> Input: 'Miller Roofing', Dallas TX. Reviews say 'honest, showed up in a storm'.
>
> Task: Invent 3 distinct 'Brand Concepts' for this business to make them stand out.
>
> * **Concept A (The Heritage):** Focus on legacy, serif fonts, sepia tones.
> * **Concept B (The Protector):** Focus on storm safety, bold shield imagery, heavy industrial type.
> * **Concept C (The Maverick):** 'We fix what others can't.' High contrast, neon orange, aggressive layout.
>
> **Decision:** Pick the concept that has the highest probability of 'stopping the scroll' for this specific industry. Output the 'Creative DNA' JSON for that concept."

### **3. Step 2: The Extended "Art Director" (The Blueprint)**

Now we integrate your request for  **loaders, motion, and layout** . The prompt needs to force specific technical choices that prevent "AI Slop."

**The Master Director Prompt:**

> **Role:** You are a Senior Frontend Architect known for Awwwards-winning creative developer portfolios.
>
> Context: We are building a site for [Business Name].
>
> Creative DNA: {generated_identity_json}
>
> **Task:** Create a technical design brief. Do not be timid.
>
> **1. The "Loading" Experience:**
>
> * Design a bespoke CSS-only loader that tells a story. (e.g., If it's a coffee shop, maybe the screen fills with liquid brown from the bottom up. If it's a tech firm, use a glitch-text decode effect).
> * *Constraint:* Must vanish automatically after 2.5s.
>
> **2. The "Hero" Hook:**
>
> * Ignore standard "H1 + Subtext" layouts.
> * Propose a "Scroll-Stopping" typography treatment. (e.g., Massive 15vw text, overlapping layers, or text that reveals based on mouse position).
>
> **3. Micro-Interactions & Cursor:**
>
> * Define a custom cursor interaction (e.g., "The cursor is a spotlight revealing the background," or "The cursor grows 4x when hovering links").
> * Define how the menu opens (e.g., "Full screen curtain drop" vs "Sidebar slide-in").
>
> **4. Texture & Atmosphere:**
>
> * Avoid flat colors. Define a CSS `background-image` strategy using gradients, noise (base64 data URI), or grid patterns to create depth.
> * Use `mix-blend-mode` in CSS to blend text with backgrounds creatively.
>
> **5. Typography:**
>
> * Select fonts from Google Fonts but **BAN** the following: Roboto, Open Sans, Lato, Montserrat, Poppins. Find something with character.
>
> **Output:** Return the technical specifications in a structured format for the Developer Agent.

### **4. Step 3: The "Memory" System (The Feedback Loop)**

You mentioned you want to learn from what works. Since you are saving the **Creative DNA** JSON, you can track performance.

1. **The Experiment:** The system generates 100 sites.
   * 30 are "Minimalist/Swiss Style"
   * 30 are "Dark Mode/Neon"
   * 40 are "Brutalist/Bold"
2. **The Feedback:** When a user clicks "Buy" or "Reply," the system flags that `business_id` as a  **WIN** .
3. **The Evolution:**
   * Every week, a separate "Trainer Agent" analyzes the **WIN** column.
   * *Insight:* "It appears that for 'Plumbers', 'Dark Mode/Neon' has a 4% conversion rate, while 'Minimalist' has 0.5%."
   * *Action:* The system automatically updates the "Concept Agent" prompt to favor Dark Mode concepts for future plumbing leads.

### **5. Revised Process Flow**

Here is how the "Autopilot" handles a single business from start to finish.

1. **Scrape:** Get "Joe's Pizza."
2. **Enrich:** (Optional) Use LLM to guess "Joe's" vibe from reviews (e.g., "Greasy, authentic, NY style").
3. **Concept Agent:** Assigns **"The Vibe"** (e.g., Retro 90s Arcade Pizza style).
   * *Saves `creative_dna.json` to DB.*
4. **Director Agent:** Reads `creative_dna`. Demands a "Pixel Art Loader" and "Neon Green" palette.
5. **Developer Agent:** Writes the code.
   * *User Tip:* Instruct the dev agent to keep CSS in a separate `<style>` block and JS in `<script>` so the file is clean, but keep it all in one `.html` file for easy portability during the sales phase (no assets to break).
6. **Sale/No Sale:**
   * *If Sale:* The system retrieves `creative_dna.json` to build the "Contact Us" page with the exact same pixel-art vibe.
   * *If No Sale:* The system marks "Retro 90s" as a potential fail for Pizza in that zip code.

### **Next Step: The "Vibe" List**

To help the Concept Agent, we should give it a "Menu of Vibes" to choose from so it doesn't default to generic styles.

* **Swiss International:** (Grid systems, Helvetica-ish, huge whitespace).
* **Neo-Brutalism:** (Hard outlines, raw HTML feel, high contrast colors).
* **Glassmorphism:** (Blur effects, frosted glass, soft gradients).
* **Dark Luxury:** (Gold/Silver on Black, Serif fonts, slow fades).
* **Industrial:** (Monospace fonts, technical lines, blueprint aesthetics).

Would you like me to write the **System Prompt for the "Concept Agent"** that forces it to choose one of these vibes based on the business category?




I was thinking about the way our system should work a bit more. Our system should make sure that we only contact businesses with great reviews and that have either an email or a phone number.

The message should be very friendly and based on the information we found about the business. It would like something like this:

Hi [name], I was checking your business on google maps and I see you have great reviews, your [food, services,products,etc] are awesome and people are very happy with [food, services,products etc] and I thought you could improve your visibility so much more by having a website. My name is Hugo, and I created a website for you. You can check it out here [site link]. If you like it, I'll be happy to make any adjustments and get it on your favorite domain for [$500-$800] plus $99 monthly to maintain it.

Also, our system should scrape the information about the business and have a master prompt to use that information to create a great website. Something like this:

"write me a prompt that I can use in a vibe codign software to build me a sexy website for a company called [name of company here] that has no website right now. Here's the info"

and we add the google my business info we scraped and we should get an amazing prompt back to build a great website that will be enough for the llm to execute and create a great website.

Then, our backend should also allow us to send those links to the website, so they can view the website and they can also pay the for the website online.



This is a smart refinement. By filtering for "great reviews," you are targeting businesses that  **already have momentum but lack the digital infrastructure to scale it** . These are your highest-probability buyers because they have something to lose (a good reputation) and something to gain (more customers seeing that reputation).

Here is the updated architecture and the specific **Master Prompts** to achieve this "Vibe Coding" workflow.

### **1. The New Logic Flow**

We are moving to a  **"Two-Pass" Intelligence System** :

1. **Pass 1 (The Analyst):** Reads the Google My Business (GMB) data. It does *not* write code. It writes the *Brief* and the  *Email* .
2. **Pass 2 (The Builder):** Takes the Brief from Pass 1 and writes the Code.

---

### **2. Step 1: The "Analyst" Agent (The Master Prompt)**

This is the brain. We feed it the raw JSON from Google Maps (Reviews, Category, Name). It outputs two things: the **"Vibe Coding" Prompt** (for the builder) and the **Personalized Hooks** (for the email).

**The System Prompt for the Analyst:**

**Plaintext**

```
You are a Creative Director and Sales Strategist.
INPUT: Raw Google My Business Data (Name, Reviews, Category, Photos).

TASK 1: ANALYZE FOR SALES (The Email Hook)
Read the reviews. Identify the SPECIFIC item or service people rave about.
- If a restaurant: Is it the "Crispy pepperoni pizza"?
- If a mechanic: Is it "Honest pricing" or "Fast turnaround"?
- Output variable: {review_highlight}

TASK 2: CREATE THE BUILDER PROMPT (The Vibe Code)
Write a prompt for a Senior Frontend Developer to build a site for this specific business. 
- DO NOT be generic. If it's a "Taco Truck," demand "Street style, graffiti textures, vibrant orange/pink."
- If it's a "Law Firm," demand "clean lines, navy blue, serif fonts, authority."
- Dictate the "Hero Section" copy based on their best review.

OUTPUT JSON FORMAT:
{
  "email_data": {
    "business_name": "...",
    "review_highlight": "people are obsessed with your Al Pastor tacos and the green salsa"
  },
  "builder_prompt": "Create a high-impact landing page for [Business Name]. \n\nDESIGN DIRECTION:\n- Vibe: [Insert Vibe based on industry].\n- Colors: [Specific Palette].\n- Hero Text: '[Headline based on reviews]'.\n- Special Feature: Use a [specific loader] and [specific scroll effect].\n- Images: Use placeholders for [specific industry terms]."
}
```

---

### **3. Step 2: The "Builder" Agent (The Execution)**

This agent receives the `builder_prompt` from Step 1. It doesn't need to "think" about the strategy anymore; it just executes the visual style defined by the Director.

**Why this works:** The "Analyst" separates the *strategy* from the  *coding* . A model trying to do both often gets confused and makes generic generic output.

---

### **4. The Outreach System (The Email)**

Your template is great, but we can make it even stickier using the data extracted in Step 1.

**Subject Line:** *Quick question about the [review_highlight]* (e.g., "Quick question about the Al Pastor tacos") -> *High open rate because it looks like a customer.*

**Body:**

> "Hi [Name],
>
> I was checking [Business Name] on Google Maps and the reviews are incredible. It looks like **[review_highlight]** (e.g.,  *people are very happy with the Al Pastor tacos and the green salsa* ).
>
> I noticed you don't have a website to showcase that reputation. You're leaving money on the table.
>
> My name is Hugo. I took the liberty of building a concept site for you already. I used your brand colors and focused on the reviews.
>
> **You can see it here:** [link_to_generated_site]
>
> If you like it, you can claim it right now for **$500** (one-time) + **$99/mo** for hosting. I can transfer it to your own domain (e.g., [businessname].com) immediately.
>
> Best,
>
> Hugo"

---

### **5. The Backend: Payment & Delivery**

To make this "Auto-Pilot," you cannot manually send invoices. You need  **Stripe Checkout** .

1. The "Claim" Button:
   On the generated website, place a floating bar at the bottom:

   * *Text:* "This is a preview. Owner of [Business Name]? Claim this site now."
   * *Action:* Clicking it opens a Stripe Checkout Session.
2. Stripe Metadata:
   When creating the payment link, pass the business_id in the metadata.
   **Python**

   ```
   session = stripe.checkout.Session.create(
     payment_method_types=['card'],
     line_items=[{
       'price_data': {
         'currency': 'usd',
         'product_data': {'name': 'Website Design & Setup'},
         'unit_amount': 50000, // $500.00
       },
       'quantity': 1,
     },
     {
       'price_data': {
         'currency': 'usd',
         'product_data': {'name': 'Monthly Hosting & Maintenance'},
         'unit_amount': 9900, // $99.00
         'recurring': {'interval': 'month'},
       },
       'quantity': 1,
     }],
     mode='subscription',
     success_url='https://yourplatform.com/success?session_id={CHECKOUT_SESSION_ID}',
     metadata={'business_id': 'gmb_123456'}
   )
   ```
3. The Webhook (The Handover):
   When Stripe confirms payment (checkout.session.completed):

   * System updates DB: `status = PAID`.
   * System emails you: "New Client: [Business Name]!"
   * System emails Client: "Welcome aboard! Reply to this email with any text changes you want."

### **Revised Action Plan**

1. **Filter Logic:** Update the scraper to strict mode: `rating >= 4.5`, `reviews >= 15`, `has_email == True` OR `has_phone == True`.
2. **Prompt Engineering:** Test the "Analyst" prompt manually on ChatGPT with 3 different businesses (a Gym, a Pizza place, a Dentist) to see if it correctly identifies the "Review Highlight" and the "Vibe."
3. **Stripe Setup:** Create a standard "Website Package" product in Stripe.

Would you like me to refine the **Analyst Prompt** further to include specific instructions for *layout types* (e.g., Bento Grids vs. Full Screen Hero) based on the industry?
