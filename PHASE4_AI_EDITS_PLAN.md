# Phase 4: AI-Powered Site Edits - Implementation Plan

**Estimated Time:** 4-6 hours  
**Priority:** High (Core revenue feature)  
**Complexity:** Medium  

---

## 🎯 OBJECTIVE

Enable customers to request AI-powered edits to their purchased websites through a simple interface, with preview, approval, and automatic version control.

---

## 💰 BUSINESS VALUE

### **Why This Matters:**
- **Key Differentiator**: AI-powered edits make the platform unique
- **Customer Retention**: Reduces need for external developers
- **Upsell Opportunity**: Could charge per edit or include in subscription
- **Competitive Advantage**: Instant modifications vs manual development

### **Pricing Strategy:**
```
Option A: Included in $95/month subscription
  - Limit: 5 edits/month
  - Additional edits: $20 each

Option B: Add-on Package
  - $25/month for 10 edits
  - Unlimited: $50/month

Option C: Pay-per-edit
  - Simple edit: $15
  - Complex edit: $40
  - Complete redesign: $100

Recommended: Option A (builds subscription value)
```

---

## 📋 FEATURES TO IMPLEMENT

### **1. Edit Request System** ✅ (Database ready)
```
Table: edit_requests
- id (UUID)
- site_id (FK to sites)
- request_text (text)  # Natural language: "Change button color to blue"
- request_type (string)  # text, style, layout, content, image
- status (string)  # pending, processing, preview_ready, approved, rejected, failed
- ai_analysis (JSONB)  # AI's understanding of request
- original_content (text)  # Backup before changes
- preview_content (text)  # Generated preview HTML
- applied_at (timestamp)  # When changes went live
- rejected_reason (text)  # If customer rejects
```

### **2. Customer Interface** (Frontend)
```tsx
// Edit request form
<EditRequestForm>
  - Text input for natural language request
  - Category selection (text/style/layout/image)
  - Example requests shown
  - Upload images (if changing images)
  - Submit button
</EditRequestForm>

// Preview interface
<EditPreview>
  - Side-by-side: Current vs Preview
  - Approve/Reject buttons
  - Request changes button
  - Change history
</EditPreview>

// Edit history
<EditHistory>
  - List all past edits
  - Revert capability
  - View diffs
</EditHistory>
```

### **3. AI Processing Pipeline**
```python
Step 1: Parse Request
  - Extract intent (what to change)
  - Identify affected elements
  - Validate feasibility

Step 2: Generate Changes
  - Use Claude Sonnet to modify HTML/CSS
  - Preserve site structure
  - Maintain responsive design
  - Keep SEO optimization

Step 3: Create Preview
  - Generate modified HTML
  - Save as preview version
  - Create diff for review

Step 4: Apply Changes
  - Create new site version
  - Update live site
  - Backup previous version
  - Log changes
```

---

## 🏗️ ARCHITECTURE

### **Service Layer:**
```python
# backend/services/edit_service.py
class EditService:
    @staticmethod
    async def create_edit_request(
        db: AsyncSession,
        site_id: UUID,
        request_text: str,
        request_type: str,
        images: Optional[List] = None
    ) -> EditRequest:
        """Create new edit request."""
        
    @staticmethod
    async def process_edit_request(
        db: AsyncSession,
        request_id: UUID
    ) -> EditRequest:
        """Process edit with AI."""
        
    @staticmethod
    async def generate_preview(
        db: AsyncSession,
        request_id: UUID
    ) -> str:
        """Generate preview HTML."""
        
    @staticmethod
    async def approve_edit(
        db: AsyncSession,
        request_id: UUID,
        customer_id: UUID
    ) -> Site:
        """Apply approved changes to live site."""
        
    @staticmethod
    async def reject_edit(
        db: AsyncSession,
        request_id: UUID,
        reason: str
    ) -> EditRequest:
        """Reject preview."""
```

### **AI Agent:**
```python
# backend/services/creative/agents/editor.py
class EditorAgent:
    """AI agent specialized in site modifications."""
    
    async def analyze_request(
        self,
        request_text: str,
        current_html: str
    ) -> Dict:
        """Understand what customer wants to change."""
        
    async def generate_modifications(
        self,
        analysis: Dict,
        current_html: str
    ) -> str:
        """Generate modified HTML."""
        
    async def validate_changes(
        self,
        original: str,
        modified: str
    ) -> Dict:
        """Ensure changes are safe and valid."""
```

---

## 🔄 WORKFLOW

### **Customer Journey:**
```
1. Customer opens "Edit Site" interface
   ↓
2. Types request: "Make the header blue"
   ↓
3. System creates EditRequest (status: pending)
   ↓
4. Celery task processes with AI (status: processing)
   ↓
5. AI generates preview (status: preview_ready)
   ↓
6. Customer views side-by-side comparison
   ↓
7. Customer clicks "Approve" or "Reject"
   ↓
8. If approved:
   - Create new SiteVersion
   - Update live site files
   - Send confirmation email
   ↓
9. If rejected:
   - Save rejection reason
   - Allow revised request
```

---

## 📝 API ENDPOINTS

### **Edit Requests:**
```python
POST   /api/v1/edits/request
  Body: {
    "request_text": "Change button color to blue",
    "request_type": "style",
    "images": []  # Optional
  }
  Response: {
    "id": "uuid",
    "status": "pending",
    "estimated_time": "2-5 minutes"
  }

GET    /api/v1/edits/{edit_id}
  Response: {
    "id": "uuid",
    "status": "preview_ready",
    "request_text": "...",
    "preview_url": "https://sites.lavish.solutions/preview/uuid"
  }

GET    /api/v1/edits/history
  Response: {
    "edits": [...],
    "total": 12,
    "remaining_this_month": 3  # If using limits
  }

POST   /api/v1/edits/{edit_id}/approve
  Response: {
    "success": true,
    "applied_at": "2026-01-21T10:00:00Z",
    "new_version": 5
  }

POST   /api/v1/edits/{edit_id}/reject
  Body: {
    "reason": "Color too bright"
  }
  Response: {
    "success": true,
    "can_retry": true
  }
```

---

## 🧪 TESTING STRATEGY

### **Unit Tests:**
```python
# test_edit_service.py
test_create_edit_request()
test_process_simple_text_change()
test_process_style_change()
test_process_layout_change()
test_generate_preview()
test_approve_edit()
test_reject_edit()
test_revert_to_previous_version()
```

### **Integration Tests:**
```python
# test_edit_workflow.py
test_complete_edit_flow()
test_multiple_edits_sequentially()
test_concurrent_edit_requests()
test_invalid_request_handling()
test_ai_failure_recovery()
```

### **Manual Tests:**
```
✓ Submit text change request
✓ Submit style change request
✓ Submit layout modification
✓ View preview comparison
✓ Approve and verify live update
✓ Reject and request changes
✓ Revert to previous version
```

---

## 🎨 EDIT TYPES SUPPORTED

### **1. Text Changes** (Easy)
```
Examples:
- "Change heading to 'Best Plumbing in LA'"
- "Update phone number to (555) 123-4567"
- "Add testimonial about service"

AI Task:
- Find text element
- Replace with new text
- Maintain formatting
```

### **2. Style Changes** (Easy)
```
Examples:
- "Make buttons blue"
- "Increase font size for headings"
- "Change background to gradient"

AI Task:
- Identify CSS rules
- Modify colors/sizes
- Ensure consistency
```

### **3. Layout Changes** (Medium)
```
Examples:
- "Move contact form to sidebar"
- "Add 3-column services section"
- "Make hero section taller"

AI Task:
- Understand structure
- Modify HTML layout
- Adjust responsive breakpoints
```

### **4. Content Changes** (Medium)
```
Examples:
- "Add FAQ section"
- "Create pricing table"
- "Add customer logos"

AI Task:
- Generate new HTML
- Match existing style
- Integrate seamlessly
```

### **5. Image Changes** (Complex - Phase 4.5)
```
Examples:
- "Replace hero image"
- "Generate new logo"
- "Add team photos"

AI Task:
- Handle image uploads
- Optimize images
- Update references
```

---

## 🚀 IMPLEMENTATION PHASES

### **Phase 4.1: Core Infrastructure** (2 hours)
```
✓ Edit request API endpoints
✓ EditService implementation
✓ Database CRUD operations
✓ Basic validation
```

### **Phase 4.2: AI Integration** (2 hours)
```
✓ EditorAgent implementation
✓ Claude Sonnet prompts
✓ Preview generation
✓ Change validation
```

### **Phase 4.3: Preview System** (1 hour)
```
✓ Preview URL generation
✓ Side-by-side comparison
✓ Diff visualization
✓ Approval/rejection flow
```

### **Phase 4.4: Testing & Polish** (1 hour)
```
✓ Comprehensive testing
✓ Error handling
✓ Email notifications
✓ Documentation
```

---

## 📧 EMAIL NOTIFICATIONS

### **Edit Request Received:**
```
Subject: We're Working on Your Edit Request
Body:
- Confirmation of request
- Estimated completion time
- What happens next
```

### **Preview Ready:**
```
Subject: Your Site Edit is Ready to Preview
Body:
- Link to preview
- How to approve/reject
- Reminder of request
```

### **Edit Approved:**
```
Subject: Your Site Has Been Updated!
Body:
- Changes are now live
- Link to updated site
- Version number
- Revert instructions if needed
```

---

## 🔒 SECURITY & VALIDATION

### **Input Validation:**
```python
✓ Sanitize request text (no injection)
✓ Validate request type
✓ Rate limiting (5 requests/hour)
✓ Ownership verification
✓ Subscription status check
```

### **AI Safety:**
```python
✓ Prevent code injection
✓ Maintain site structure
✓ No external links without approval
✓ Preserve responsive design
✓ Validate generated HTML
```

### **Change Limits:**
```python
✓ Max 1000 characters per request
✓ Complex changes require approval
✓ Some elements locked (business info)
✓ Rollback always available
```

---

## 💡 TECHNICAL DECISIONS

### **1. Synchronous vs Async Processing:**
**Decision:** Async (Celery task)  
**Reason:** AI processing takes 30-60 seconds, don't block API  

### **2. Preview Storage:**
**Decision:** Temporary files with 24-hour expiry  
**Reason:** Don't clutter database, encourage quick decisions  

### **3. Version Limit:**
**Decision:** Keep last 10 versions per site  
**Reason:** Balance storage vs rollback capability  

### **4. AI Model:**
**Decision:** Claude Sonnet 3.5  
**Reason:** Best at code generation, understands intent  

---

## 📊 SUCCESS METRICS

### **Technical:**
- Preview generation time < 60 seconds
- 95%+ successful edit requests
- Zero data loss on failures
- 99.9% uptime

### **Business:**
- Average edits per customer/month
- Approval rate (target: 85%+)
- Time to approval (target: < 2 hours)
- Customer satisfaction score

---

## 🎯 NEXT STEPS AFTER PHASE 4

1. **Advanced Edit Types:**
   - Form modifications
   - Animation additions
   - Interactive elements

2. **Bulk Edits:**
   - Apply same change to multiple pages
   - Template modifications

3. **AI Suggestions:**
   - Proactive improvement recommendations
   - A/B testing capabilities

---

_Planning Document Created: January 21, 2026_  
_Estimated Implementation: 4-6 hours_  
_Dependencies: Phase 2 & 3 complete_  
_Priority: HIGH (Core feature)_

**Ready to implement when you are!** 🚀
