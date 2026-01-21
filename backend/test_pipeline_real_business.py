"""
Test the complete website generation pipeline with real business data.
Tests: Analyst → Concept → Art Director → Architect → Generated Website
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Business data from Google Maps
BUSINESS_DATA = {
    "name": "Los Angeles Plumbing Pros",
    "category": "Plumber",
    "address": "1901 E Gage Ave, Los Angeles, CA 90001, United States",
    "city": "Los Angeles",
    "state": "CA",
    "country": "United States",
    "postal_code": "90001",
    "phone": "+1 310-861-9785",
    "email": None,  # Not provided
    "website": None,  # No website - that's why we're generating one!
    "rating": 5.0,
    "review_count": 64,
    "hours": "Open 24 hours",
    "reviews_data": [
        {
            "author": "Mariam Jakayla",
            "rating": 5,
            "text": "The technician verified that no pressure issues existed.",
            "time_description": "recent"
        },
        {
            "author": "Mariela Yaritza",
            "rating": 5,
            "text": "Excellent service and professional staff.",
            "time_description": "recent"
        },
        {
            "author": "Aimee Byrne",
            "rating": 5,
            "text": "He is the best service technician I've ever had in my home.",
            "time_description": "recent"
        }
    ],
    "photos_urls": [],  # No photos provided in the data
}


async def test_creative_pipeline():
    """Run the complete creative pipeline."""
    print("=" * 80)
    print("🧪 TESTING WEBSITE GENERATION PIPELINE")
    print("=" * 80)
    print(f"\nBusiness: {BUSINESS_DATA['name']}")
    print(f"Category: {BUSINESS_DATA['category']}")
    print(f"Location: {BUSINESS_DATA['city']}, {BUSINESS_DATA['state']}")
    print(f"Rating: {BUSINESS_DATA['rating']}★ ({BUSINESS_DATA['review_count']} reviews)")
    print(f"Phone: {BUSINESS_DATA['phone']}")
    print(f"Hours: {BUSINESS_DATA['hours']}")
    print(f"\nReviews:")
    for i, review in enumerate(BUSINESS_DATA['reviews_data'], 1):
        print(f"  {i}. {review['author']}: \"{review['text']}\" - {review['rating']}★")
    
    print("\n" + "=" * 80)
    print("STEP 1: Initialize Creative Pipeline")
    print("=" * 80)
    
    from services.creative.orchestrator import CreativeOrchestrator
    from core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        orchestrator = CreativeOrchestrator(db)
        
        print("\n✅ CreativeOrchestrator initialized")
        print(f"   - Analyst Agent: Ready")
        print(f"   - Concept Agent: Ready")
        print(f"   - Art Director Agent: Ready")
        print(f"   - Architect Agent: Ready")
        
        # Create output directory
        output_dir = Path("test_output/los_angeles_plumbing_pros")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📁 Output directory: {output_dir}")
        
        # Start pipeline
        print("\n" + "=" * 80)
        print("STEP 2: Run Creative Pipeline")
        print("=" * 80)
        
        try:
            # Generate the website
            result = await orchestrator.generate_website(
                business_data=BUSINESS_DATA,
                save_intermediate=True
            )
            
            # Extract website data from nested structure
            website = result.get("website", {})
            
            # Save results
            print("\n" + "=" * 80)
            print("STEP 3: Save Results")
            print("=" * 80)
            
            # 1. Brand Analysis
            if result.get("analysis"):
                analysis_file = output_dir / "01_brand_analysis.json"
                with open(analysis_file, "w") as f:
                    json.dump(result["analysis"], f, indent=2)
                print(f"✅ Brand Analysis saved: {analysis_file}")
            
            # 2. Creative DNA
            if result.get("creative_dna"):
                dna_file = output_dir / "02_creative_dna.json"
                with open(dna_file, "w") as f:
                    json.dump(result["creative_dna"], f, indent=2)
                print(f"✅ Creative DNA saved: {dna_file}")
            
            # 3. Design Brief
            if result.get("design_brief"):
                brief_file = output_dir / "03_design_brief.json"
                with open(brief_file, "w") as f:
                    json.dump(result["design_brief"], f, indent=2)
                print(f"✅ Design Brief saved: {brief_file}")
            
            # 4. HTML
            if website.get("html"):
                html_file = output_dir / "04_website.html"
                with open(html_file, "w") as f:
                    f.write(website["html"])
                print(f"✅ HTML saved: {html_file}")
            
            # 5. CSS
            if website.get("css"):
                css_file = output_dir / "05_styles.css"
                with open(css_file, "w") as f:
                    f.write(website["css"])
                print(f"✅ CSS saved: {css_file}")
            
            # 6. JavaScript
            if website.get("js"):
                js_file = output_dir / "06_scripts.js"
                with open(js_file, "w") as f:
                    f.write(website["js"])
                print(f"✅ JavaScript saved: {js_file}")
            
            # 7. Generated Images
            if website.get("generated_images"):
                images_file = output_dir / "07_generated_images.json"
                with open(images_file, "w") as f:
                    json.dump(website["generated_images"], f, indent=2)
                print(f"✅ Generated Images metadata: {images_file}")
            
            # 8. Complete package
            complete_file = output_dir / "00_complete_result.json"
            with open(complete_file, "w") as f:
                # Don't save the full HTML/CSS/JS in JSON (too large)
                summary = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "business": BUSINESS_DATA["name"],
                    "category": BUSINESS_DATA["category"],
                    "location": f"{BUSINESS_DATA['city']}, {BUSINESS_DATA['state']}",
                    "html_length": len(website.get("html", "")),
                    "css_length": len(website.get("css", "")),
                    "js_length": len(website.get("js", "")),
                    "brand_analysis": result.get("analysis"),
                    "creative_dna": result.get("creative_dna"),
                    "design_brief": result.get("design_brief"),
                    "generated_images": website.get("generated_images"),
                    "meta": website.get("meta"),
                    "total_duration_ms": result.get("total_duration_ms"),
                    "status": result.get("status"),
                }
                json.dump(summary, f, indent=2)
            print(f"✅ Complete summary: {complete_file}")
            
            # Display summary
            print("\n" + "=" * 80)
            print("✅ PIPELINE COMPLETE - RESULTS SUMMARY")
            print("=" * 80)
            
            total_duration = result.get("total_duration_ms", 0) / 1000
            print(f"\n⏱️  Total Generation Time: {total_duration:.1f} seconds")
            
            print(f"\n📊 Content Generated:")
            html_len = len(website.get('html', ''))
            css_len = len(website.get('css', ''))
            js_len = len(website.get('js', ''))
            print(f"   - HTML: {html_len:,} characters")
            print(f"   - CSS: {css_len:,} characters")
            print(f"   - JavaScript: {js_len:,} characters")
            
            if result.get("analysis"):
                analysis = result["analysis"]
                print(f"\n🎯 Brand Analysis:")
                print(f"   - Brand Archetype: {analysis.get('brand_archetype', 'N/A')}")
                print(f"   - Target Audience: {analysis.get('target_audience', 'N/A')}")
                traits = analysis.get('personality_traits', [])
                if traits:
                    print(f"   - Personality Traits: {', '.join(traits[:3])}")
            
            if result.get("creative_dna"):
                dna = result["creative_dna"]
                print(f"\n🧬 Creative DNA:")
                print(f"   - Brand Archetype: {dna.get('brand_archetype', 'N/A')}")
                print(f"   - Value Proposition: {dna.get('value_proposition', 'N/A')}")
                traits = dna.get('personality_traits', [])
                if traits:
                    print(f"   - Personality Traits: {', '.join(traits[:3])}")
            
            if result.get("design_brief"):
                brief = result["design_brief"]
                print(f"\n🎨 Design Brief:")
                print(f"   - Vibe: {brief.get('vibe', 'N/A')}")
                colors = brief.get('colors', {})
                print(f"   - Primary Color: {colors.get('primary', 'N/A')}")
                print(f"   - Secondary Color: {colors.get('secondary', 'N/A')}")
                print(f"   - Accent Color: {colors.get('accent', 'N/A')}")
                typography = brief.get('typography', {})
                print(f"   - Display Font: {typography.get('display', 'N/A')}")
                print(f"   - Body Font: {typography.get('body', 'N/A')}")
            
            if website.get("generated_images"):
                images = website["generated_images"]
                print(f"\n🖼️  Generated Images: {len(images)}")
                for img in images:
                    img_size = img['size_bytes']
                    print(f"   - {img['type'].title()}: {img['filename']} ({img_size:,} bytes)")
            
            print(f"\n📁 All files saved to: {output_dir.absolute()}")
            
            print("\n" + "=" * 80)
            print("🎉 TEST COMPLETE!")
            print("=" * 80)
            print(f"\n💡 Next steps:")
            print(f"   1. Open {output_dir / '04_website.html'} in a browser")
            print(f"   2. Review the generated brand analysis and design")
            print(f"   3. Check the AI-generated images (if any)")
            print(f"   4. If satisfied, deploy to production!")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("\n🚀 Starting Website Generation Pipeline Test\n")
    success = asyncio.run(test_creative_pipeline())
    
    if success:
        print("\n✅ Test completed successfully!")
        exit(0)
    else:
        print("\n❌ Test failed!")
        exit(1)
