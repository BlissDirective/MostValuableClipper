from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse

router = APIRouter()

PRIVACY_POLICY_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - BlissClip</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f0f; 
            color: #e0e0e0; 
            line-height: 1.6; 
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: #fff; font-size: 32px; margin-bottom: 8px; }
        .updated { color: #888; font-size: 14px; margin-bottom: 40px; }
        h2 { color: #6366f1; font-size: 20px; margin: 32px 0 16px; font-weight: 600; }
        h3 { color: #fff; font-size: 16px; margin: 24px 0 12px; }
        p { margin-bottom: 16px; font-size: 15px; }
        ul { margin: 16px 0; padding-left: 24px; }
        li { margin-bottom: 8px; font-size: 15px; }
        .highlight { background: #1a1a1a; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 3px solid #6366f1; }
        .contact { background: #1a1a1a; padding: 24px; border-radius: 12px; margin-top: 40px; }
        .contact h2 { margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2a2a2a; }
        th { color: #6366f1; font-weight: 600; }
        a { color: #6366f1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Privacy Policy</h1>
        <p class="updated">Last Updated: May 15, 2026</p>
        
        <h2>1. Introduction</h2>
        <p>BlissClip ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our mobile application and services (collectively, the "Service").</p>
        <p>This Privacy Policy applies to all users of our Service worldwide. By accessing or using our Service, you agree to the collection and use of information in accordance with this policy.</p>
        <div class="highlight">
            <strong>Company Information:</strong><br>
            Business Name: BlissClip (BlissDirective LLC)<br>
            Contact Email: privacy@blissclip.app<br>
            Data Protection Officer: dpo@blissclip.app
        </div>

        <h2>2. Information We Collect</h2>
        <h3>Account Information</h3>
        <ul>
            <li>Email address, password (stored as a secure hash), display name, profile photo (optional)</li>
        </ul>
        <h3>Video Content and Source Materials</h3>
        <ul>
            <li>Source videos you upload or provide URLs for</li>
            <li>Generated clips created through our AI pipeline</li>
            <li>Thumbnails, transcripts, and metadata</li>
        </ul>
        <h3>Social Media Account Information</h3>
        <ul>
            <li>OAuth tokens for connected platforms (stored encrypted)</li>
            <li>Profile information and posting history (with your explicit authorization only)</li>
        </ul>
        <h3>Usage Data and Analytics</h3>
        <ul>
            <li>Device information, log data, feature usage, performance data, session information</li>
        </ul>
        <h3>Payment Information</h3>
        <ul>
            <li>Billing information processed securely through Stripe. We do not store full credit card numbers.</li>
        </ul>

        <h2>3. How We Use Your Information</h2>
        <ul>
            <li><strong>Primary Purposes:</strong> Provide and maintain the Service, process requests, authenticate identity, process payments, communicate with you</li>
            <li><strong>AI and Machine Learning:</strong> Process videos, improve algorithms using aggregated anonymized data, personalize suggestions (with opt-in consent for cohort learning)</li>
            <li><strong>Analytics:</strong> Analyze usage patterns, improve performance, debug issues, develop new features</li>
            <li><strong>Legal Compliance:</strong> Comply with obligations, enforce Terms of Service, protect rights, prevent fraud</li>
        </ul>

        <h2>4. Your Data Rights</h2>
        <h3>GDPR Rights (EEA Users)</h3>
        <ul>
            <li>Right to access, rectification, erasure ("right to be forgotten"), restrict processing, data portability, object to processing, withdraw consent, and lodge complaints</li>
        </ul>
        <h3>CCPA/CPRA Rights (California Users)</h3>
        <ul>
            <li>Right to know, delete, opt-out (we do not sell data), non-discrimination, correct, and limit use of sensitive personal information</li>
        </ul>
        <h3>Account Deletion</h3>
        <p>You can delete your account anytime via Settings → Account → Delete Account. All personal data is removed within 30 days (payment records retained 7 years per legal requirements).</p>

        <h2>5. Data Sharing and Third Parties</h2>
        <table>
            <tr><th>Service Provider</th><th>Purpose</th></tr>
            <tr><td>Supabase</td><td>Database, authentication, storage</td></tr>
            <tr><td>Cloudflare R2</td><td>Video and clip storage</td></tr>
            <tr><td>Stripe</td><td>Payment processing</td></tr>
            <tr><td>Upstash</td><td>Job queue and caching</td></tr>
            <tr><td>Modal</td><td>AI/ML compute</td></tr>
            <tr><td>Social Platforms</td><td>Content posting (your authorization only)</td></tr>
        </table>
        <p><strong>We do not sell your personal information to third parties.</strong></p>

        <h2>6. Data Security & Retention</h2>
        <ul>
            <li>TLS 1.3 encryption in transit, database encryption at rest</li>
            <li>Secure authentication (JWT/bcrypt), role-based access controls</li>
            <li>Encrypted OAuth tokens</li>
            <li>Source videos: 90 days (configurable), Generated clips: until deletion</li>
            <li>Payment records: 7 years (legal requirement)</li>
            <li>Data breach notification within 72 hours</li>
        </ul>

        <h2>7. AI-Specific Disclosures</h2>
        <ul>
            <li>You retain ownership of source videos</li>
            <li>AI-generated clips are licensed to you for use, distribution, and monetization</li>
            <li><strong>Cohort Learning:</strong> Optional feature, OFF by default. Uses anonymized patterns. You can disable anytime in Settings → Privacy.</li>
            <li>We clearly indicate AI-generated content and provide information about AI models used</li>
        </ul>

        <h2>8. International Data Transfers</h2>
        <p>Your data may be transferred to the United States. For EEA transfers, we use Standard Contractual Clauses (SCCs) and supplementary safeguards. Contact privacy@blissclip.app for a copy of our transfer safeguards.</p>

        <h2>9. Children's Privacy</h2>
        <p>Our Service is not intended for children under 13 (or 16 in the EU). We do not knowingly collect personal information from children. Contact us immediately if you believe a child has provided personal information.</p>

        <h2>10. DMCA & Copyright</h2>
        <p>Our Service detects copyrighted material using audio fingerprinting (Chromaprint). Infringing content is automatically blocked. DMCA Agent: dmca@blissclip.app. Reports processed within 24 hours. Accounts with 3+ valid DMCA notices will be terminated.</p>

        <h2>11. Changes to This Policy</h2>
        <p>Material changes communicated at least 30 days in advance via in-app notification and email. Your continued use after changes constitutes acceptance.</p>

        <div class="contact">
            <h2>12. Contact Us</h2>
            <p><strong>Privacy Questions:</strong> privacy@blissclip.app</p>
            <p><strong>Data Protection Officer:</strong> dpo@blissclip.app</p>
            <p><strong>EU Complaints:</strong> You have the right to lodge a complaint with your local supervisory authority.</p>
        </div>
    </div>
</body>
</html>
"""

TERMS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - BlissClip</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f0f; 
            color: #e0e0e0; 
            line-height: 1.6; 
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: #fff; font-size: 32px; margin-bottom: 8px; }
        .updated { color: #888; font-size: 14px; margin-bottom: 40px; }
        h2 { color: #6366f1; font-size: 20px; margin: 32px 0 16px; font-weight: 600; }
        h3 { color: #fff; font-size: 16px; margin: 24px 0 12px; }
        p { margin-bottom: 16px; font-size: 15px; }
        ul { margin: 16px 0; padding-left: 24px; }
        li { margin-bottom: 8px; font-size: 15px; }
        .highlight { background: #1a1a1a; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 3px solid #6366f1; }
        .warning { background: #3a1a1a; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 3px solid #ef4444; }
        .contact { background: #1a1a1a; padding: 24px; border-radius: 12px; margin-top: 40px; }
        .contact h2 { margin-top: 0; }
        a { color: #6366f1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Terms of Service</h1>
        <p class="updated">Last Updated: May 15, 2026</p>
        
        <h2>1. Agreement to Terms</h2>
        <p>By accessing or using BlissClip, you agree to be bound by these Terms of Service. You must be at least 13 years old (16 in the EU). By using the Service, you represent that you meet the minimum age requirement and have legal capacity to enter these Terms.</p>
        <p>We may modify these Terms with 30 days notice for material changes. Your continued use constitutes acceptance.</p>

        <h2>2. Description of Service</h2>
        <p>BlissClip is an AI-powered video content creation platform for generating short-form clips from source videos.</p>
        <ul>
            <li>Basic ($19/month): 1 pipeline, 50 clips/month</li>
            <li>Premium ($39/month): 5 pipelines, 300 clips/month</li>
            <li>Studio (Custom): Multiple accounts, managed onboarding</li>
            <li>14-day free trial available</li>
        </ul>
        <div class="warning">
            <strong>Disclaimer:</strong> The Service is provided "as is" without guarantees of uninterrupted service, specific clip quality, virality, or platform acceptance.
        </div>

        <h2>3. User Accounts</h2>
        <ul>
            <li>You are responsible for safeguarding your credentials and all activity under your account</li>
            <li>Notify us immediately of unauthorized access</li>
            <li>You may delete your account anytime via Settings → Account → Delete Account</li>
            <li>All personal data is deleted within 30 days (payment records retained 7 years)</li>
            <li>We may terminate accounts for Terms violations, illegal activity, copyright infringement (3+ DMCA notices), or non-payment</li>
        </ul>

        <h2>4. Content Ownership & Licenses</h2>
        <ul>
            <li>You retain ownership of your original content (source videos, profile information)</li>
            <li>You grant us a limited license to host, process, and transmit your content solely to provide the Service</li>
            <li>AI-generated clips are licensed to you for use, distribution, and monetization</li>
            <li>You represent that you own or have rights to all content you submit</li>
        </ul>

        <h2>5. Social Media Integration</h2>
        <ul>
            <li>You authorize us to post content on your behalf to connected accounts</li>
            <li>You can revoke authorization at any time</li>
            <li>You are solely responsible for content posted through our Service</li>
            <li>OAuth tokens are stored encrypted</li>
            <li>We are not responsible for platform rejections, removals, or account actions</li>
        </ul>

        <h2>6. Prohibited Conduct</h2>
        <p>You may NOT use the Service to: violate laws, infringe intellectual property, post illegal/fraudulent/defamatory content, post sexually explicit material, harass others, impersonate, distribute malware, scrape/reverse-engineer, spam, or abuse free trials.</p>
        <p>Source content must be properly licensed or qualify as fair use. Our systems may block high copyright-risk content. Violations may result in content removal, account termination, legal action, and reporting to authorities.</p>

        <h2>7. Fees & Payment</h2>
        <ul>
            <li>Subscriptions auto-renew. Cancel anytime; cancellation takes effect at the end of the current billing period</li>
            <li>No refunds for partial periods (except where required by law)</li>
            <li>Price changes require 30 days notice for existing subscribers</li>
            <li>Annual subscriptions receive a 15% discount</li>
        </ul>

        <h2>8. Intellectual Property</h2>
        <ul>
            <li>BlissClip owns the software, algorithms, design, and branding</li>
            <li>You may not copy, modify, reverse-engineer, or remove proprietary marks</li>
            <li>Open-source components remain subject to their respective licenses</li>
        </ul>

        <h2>9. DMCA Policy</h2>
        <p>Send copyright complaints to dmca@blissclip.app including: your signature, identification of the work, location of infringing material, your contact info, and statements of good-faith belief and accuracy.</p>
        <p>Counter-notices available for mistaken removals. Accounts with 3+ valid DMCA notices are terminated. False claims may result in liability for damages.</p>

        <h2>10. Disclaimer of Warranties</h2>
        <div class="warning">
            THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND. We do not warrant that the Service will meet your requirements, be uninterrupted, secure, or error-free. AI-generated content may contain inaccuracies and requires human review before posting.
        </div>

        <h2>11. Limitation of Liability</h2>
        <div class="warning">
            <strong>OUR TOTAL LIABILITY IS LIMITED TO THE GREATER OF:</strong><br>
            (a) Amount you paid us in the 12 months preceding the claim, OR<br>
            (b) $100 USD<br><br>
            WE ARE NOT LIABLE FOR: indirect, incidental, special, consequential, or punitive damages; lost profits or revenue; social media platform actions; AI content errors; copyright claims; or viral content outcomes.
        </div>

        <h2>12. Indemnification</h2>
        <p>You agree to indemnify BlissClip against claims arising from your use of the Service, your content, violation of these Terms, violation of third-party rights, social media platform terms, or your misconduct.</p>

        <h2>13. Dispute Resolution</h2>
        <ul>
            <li>Contact support@blissclip.app first for informal resolution (30 days)</li>
            <li>Governing Law: Delaware, USA</li>
            <li>US users: Binding arbitration through AAA. No class actions.</li>
            <li>International users: Disputes resolved in Delaware courts</li>
        </ul>

        <div class="contact">
            <h2>14. Contact</h2>
            <p><strong>General Support:</strong> support@blissclip.app</p>
            <p><strong>Legal Inquiries:</strong> legal@blissclip.app</p>
            <p><strong>DMCA Agent:</strong> dmca@blissclip.app</p>
        </div>
    </div>
</body>
</html>
"""

@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Serve the privacy policy as an HTML page."""
    return HTMLResponse(content=PRIVACY_POLICY_HTML)

@router.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    """Serve the terms of service as an HTML page."""
    return HTMLResponse(content=TERMS_HTML)

@router.get("/dmca", response_class=HTMLResponse)
async def dmca_policy():
    """Serve the DMCA policy as an HTML page."""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DMCA Policy - BlissClip</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f0f; 
            color: #e0e0e0; 
            line-height: 1.6; 
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: #fff; font-size: 32px; margin-bottom: 8px; }
        h2 { color: #6366f1; font-size: 20px; margin: 32px 0 16px; font-weight: 600; }
        p { margin-bottom: 16px; font-size: 15px; }
        ul { margin: 16px 0; padding-left: 24px; }
        li { margin-bottom: 8px; font-size: 15px; }
        .highlight { background: #1a1a1a; padding: 16px; border-radius: 8px; margin: 16px 0; border-left: 3px solid #6366f1; }
        .contact { background: #1a1a1a; padding: 24px; border-radius: 12px; margin-top: 40px; }
        a { color: #6366f1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>DMCA / Copyright Policy</h1>
        
        <h2>DMCA Agent Information</h2>
        <div class="highlight">
            <strong>Designated Agent:</strong> [To be registered with US Copyright Office]<br>
            <strong>Email:</strong> dmca@blissclip.app<br>
            <strong>Physical Address:</strong> [To be updated upon LLC formation]
        </div>

        <h2>Copyright Infringement Notification</h2>
        <p>To report copyright infringement, send a written notice including:</p>
        <ul>
            <li>Physical or electronic signature of the copyright owner or authorized agent</li>
            <li>Identification of the copyrighted work claimed to be infringed</li>
            <li>Identification of the infringing material and its location on the Service</li>
            <li>Your contact information (address, phone, email)</li>
            <li>A statement that you have a good-faith belief the use is not authorized</li>
            <li>A statement that the information is accurate and you are authorized to act on behalf of the owner</li>
        </ul>

        <h2>Counter-Notice Procedure</h2>
        <p>If your content was removed due to a DMCA notice and you believe it was a mistake:</p>
        <ul>
            <li>Send a counter-notice with your signature</li>
            <li>Identify the removed material and its prior location</li>
            <li>State under penalty of perjury that you believe removal was a mistake</li>
            <li>Provide your contact information</li>
            <li>Consent to jurisdiction of federal court in your district</li>
        </ul>

        <h2>Repeat Infringers</h2>
        <p>We maintain a policy of terminating accounts subject to three or more valid DMCA notices.</p>

        <h2>False Claims</h2>
        <p>Knowingly submitting false DMCA notices or counter-notices may result in liability for damages, including costs and attorney fees, under Section 512(f) of the DMCA.</p>

        <h2>Automated Copyright Detection</h2>
        <p>Our Service employs audio fingerprinting (Chromaprint) to detect copyrighted material against a curated database of charting music, sports broadcasts, and popular films. Content flagged by our systems is blocked from posting to social media platforms. Users must attest they have rights to source content before processing.</p>

        <div class="contact">
            <h2>Contact</h2>
            <p><strong>DMCA Agent:</strong> dmca@blissclip.app</p>
            <p><strong>General Support:</strong> support@blissclip.app</p>
        </div>
    </div>
</body>
</html>
""")
