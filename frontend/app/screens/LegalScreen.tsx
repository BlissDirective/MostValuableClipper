import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  ActivityIndicator,
  Linking,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

type Tab = 'privacy' | 'terms' | 'dmca';

interface Section {
  title: string;
  content: string[];
}

const privacySections: Section[] = [
  {
    title: '1. Introduction',
    content: [
      'BlissClip ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our mobile application and services (collectively, the "Service").',
      'This Privacy Policy applies to all users of our Service worldwide. By accessing or using our Service, you agree to the collection and use of information in accordance with this policy.',
      'Company Information:\n- Business Name: BlissClip (BlissDirective LLC)\n- Contact Email: privacy@blissclip.app\n- Data Protection Officer: dpo@blissclip.app',
    ],
  },
  {
    title: '2. Information We Collect',
    content: [
      'Account Information: Email address, password (secure hash), display name, profile photo (optional), and account preferences.',
      'Video Content: Source videos you upload or provide URLs for, generated clips, thumbnails, transcripts, and metadata extracted during processing.',
      'Social Media Accounts: OAuth tokens for connected platforms (TikTok, Instagram, YouTube, Facebook), profile information, and posting history.',
      'Usage Data: Device information, log data (IP address, access times), feature usage, performance data, and session information.',
      'Payment Information: Billing information processed securely through Stripe. We do not store full credit card numbers.',
      'AI Processing Data: Video content for scene detection, audio for transcription, caption text, and performance feedback.',
    ],
  },
  {
    title: '3. How We Use Your Information',
    content: [
      'Primary Purposes: Provide and maintain the Service, process your requests, authenticate your identity, process payments, and communicate with you.',
      'AI and Machine Learning: Process videos through our AI pipeline, improve algorithms using aggregated anonymized data, personalize clip suggestions, and generate insights (with opt-in consent).',
      'Analytics: Use aggregated, de-identified data to analyze usage patterns, improve app performance, debug issues, and develop new features.',
      'Legal Compliance: Comply with legal obligations, enforce Terms of Service, protect rights, and prevent fraud.',
    ],
  },
  {
    title: '4. Your Data Rights',
    content: [
      'GDPR Rights (EEA Users): Right to access, rectification, erasure ("right to be forgotten"), restrict processing, data portability, object to processing, withdraw consent, and lodge complaints.',
      'CCPA/CPRA Rights (California Users): Right to know, delete, opt-out (we do not sell data), non-discrimination, correct, and limit use of sensitive personal information.',
      'Account Deletion: You can delete your account anytime via Settings → Account → Delete Account. All personal data is removed within 30 days (payment records retained 7 years per legal requirements).',
      'To exercise rights: Email privacy@blissclip.app or use in-app controls at Settings → Privacy.',
    ],
  },
  {
    title: '5. Data Sharing',
    content: [
      'Service Providers: Supabase (database), Cloudflare R2 (video storage), Stripe (payments), Upstash (queues), Modal (AI compute), and optional Sentry (error tracking).',
      'Social Media Platforms: Clips and captions shared only with platforms you authorize. OAuth tokens stored encrypted. You control all sharing.',
      'We do not sell your personal information to third parties.',
    ],
  },
  {
    title: '6. Data Security & Retention',
    content: [
      'Security Measures: TLS 1.3 encryption in transit, database encryption at rest, secure authentication (JWT/bcrypt), role-based access controls, and encrypted OAuth tokens.',
      'Retention: Account info until deletion, source videos 90 days (configurable), generated clips until deletion, social tokens until disconnect, payment records 7 years, usage logs 90 days.',
      'Data Breach: We will notify affected users within 72 hours of discovery and report to authorities as required by law.',
    ],
  },
  {
    title: '7. AI-Specific Disclosures',
    content: [
      'AI-Generated Content: Our Service uses AI for video analysis, caption generation, and transcript creation.',
      'Content Ownership: You retain rights to source videos. AI-generated clips are licensed to you for use, distribution, and monetization.',
      'Cohort Learning: Optional feature (OFF by default). Uses anonymized patterns to improve recommendations. You can disable anytime in Settings → Privacy → Cohort Learning.',
      'Transparency: We clearly indicate AI-generated content and provide information about AI models used.',
    ],
  },
  {
    title: '8. International Data Transfers',
    content: [
      'Your data may be transferred to the United States and other countries where our service providers operate.',
      'For EEA transfers, we use Standard Contractual Clauses (SCCs) and supplementary technical and organizational safeguards.',
      'Contact privacy@blissclip.app for a copy of our transfer safeguards.',
    ],
  },
  {
    title: '9. Children\'s Privacy',
    content: [
      'Our Service is not intended for children under 13 (or 16 in the EU). We do not knowingly collect personal information from children.',
      'If you believe a child has provided us with personal information, contact privacy@blissclip.app immediately and we will delete the information.',
    ],
  },
  {
    title: '10. DMCA & Copyright',
    content: [
      'Our Service detects copyrighted material using audio fingerprinting (Chromaprint) against a curated database.',
      'Infringing content is automatically blocked from posting. Users must attest they have rights to source content.',
      'DMCA Agent: dmca@blissclip.app. Reports processed within 24 hours.',
      'Accounts with 3+ valid DMCA notices will be terminated.',
    ],
  },
  {
    title: '11. Changes to This Policy',
    content: [
      'We may update this Privacy Policy. Material changes will be communicated at least 30 days in advance via in-app notification and email.',
      'Your continued use of the Service after changes constitutes acceptance.',
      'Last Updated: May 15, 2026',
    ],
  },
  {
    title: '12. Contact Us',
    content: [
      'Privacy Questions: privacy@blissclip.app',
      'Data Protection Officer: dpo@blissclip.app',
      'EU Complaints: You have the right to lodge a complaint with your local supervisory authority.',
    ],
  },
];

const termsSections: Section[] = [
  {
    title: '1. Agreement to Terms',
    content: [
      'By accessing or using BlissClip, you agree to be bound by these Terms of Service.',
      'Eligibility: You must be at least 13 years old (16 in the EU). By using the Service, you represent that you meet the minimum age requirement and have legal capacity to enter these Terms.',
      'Changes: We may modify these Terms with 30 days notice for material changes. Your continued use constitutes acceptance.',
    ],
  },
  {
    title: '2. Description of Service',
    content: [
      'BlissClip is an AI-powered video content creation platform for generating short-form clips from source videos.',
      'Subscription Tiers: Basic ($19/month), Premium ($39/month), Studio (Custom), and a 14-day free trial.',
      'The Service is provided "as is" without guarantees of uninterrupted service, specific clip quality, virality, or platform acceptance.',
      'We may modify, suspend, or discontinue any part of the Service at any time.',
    ],
  },
  {
    title: '3. User Accounts',
    content: [
      'Account Security: You are responsible for safeguarding your credentials and all activity under your account. Notify us immediately of unauthorized access.',
      'Account Deletion: You may delete your account anytime. All personal data is deleted within 30 days (payment records retained 7 years). Deletion is irreversible.',
      'Termination by BlissClip: We may terminate accounts for Terms violations, illegal activity, copyright infringement (3+ DMCA notices), non-payment, or risk to our operations.',
    ],
  },
  {
    title: '4. Content Ownership & Licenses',
    content: [
      'You retain ownership of your original content (source videos, profile information).',
      'You grant us a limited license to host, process, and transmit your content solely to provide the Service.',
      'AI-generated clips are licensed to you for use, distribution, and monetization.',
      'You represent that you own or have rights to all content you submit and that it does not violate third-party rights.',
    ],
  },
  {
    title: '5. Social Media Integration',
    content: [
      'You authorize us to post content on your behalf to connected accounts. You can revoke this anytime.',
      'You are solely responsible for content posted through our Service and must comply with each platform\'s terms.',
      'OAuth tokens are stored encrypted and never used without your approval (unless Full Auto mode is enabled).',
      'We are not responsible for platform rejections, removals, or account actions.',
    ],
  },
  {
    title: '6. Prohibited Conduct',
    content: [
      'You may NOT use the Service to: violate laws, infringe intellectual property, post illegal/fraudulent/defamatory content, post sexually explicit material, harass others, impersonate, distribute malware, scrape/reverse-engineer, spam, or abuse free trials.',
      'Source content must be properly licensed or qualify as fair use. Our systems may block high copyright-risk content.',
      'Violations may result in content removal, account termination, legal action, and reporting to authorities.',
    ],
  },
  {
    title: '7. Fees & Payment',
    content: [
      'Subscriptions auto-renew. Cancel anytime; cancellation takes effect at the end of the current billing period.',
      'No refunds for partial periods (except where required by law).',
      'Price changes require 30 days notice for existing subscribers.',
      'Annual subscriptions receive a 15% discount and are billed upfront.',
    ],
  },
  {
    title: '8. Intellectual Property',
    content: [
      'BlissClip owns the software, algorithms, design, and branding. You may not copy, modify, reverse-engineer, or remove proprietary marks.',
      'Open-source components remain subject to their respective licenses.',
      'Feedback you provide becomes our property without compensation.',
    ],
  },
  {
    title: '9. DMCA Policy',
    content: [
      'Copyright complaints: Send notice to dmca@blissclip.app with your signature, identification of the work, location of infringing material, your contact info, and statements of good-faith belief and accuracy.',
      'Counter-notices available for mistaken removals.',
      'Accounts with 3+ valid DMCA notices are terminated.',
      'False claims may result in liability for damages.',
    ],
  },
  {
    title: '10. Disclaimer of Warranties',
    content: [
      'THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND.',
      'We do not warrant that the Service will meet your requirements, be uninterrupted, secure, or error-free.',
      'AI-generated content may contain inaccuracies and requires human review before posting.',
      'We are not responsible for third-party services (social platforms, payment processors, infrastructure providers).',
    ],
  },
  {
    title: '11. Limitation of Liability',
    content: [
      'OUR TOTAL LIABILITY IS LIMITED TO THE GREATER OF: (a) AMOUNT YOU PAID US IN THE 12 MONTHS PRECEDING THE CLAIM, OR (b) $100 USD.',
      'WE ARE NOT LIABLE FOR: indirect, incidental, special, consequential, or punitive damages; lost profits or revenue; social media platform actions; AI content errors; copyright claims; or viral content outcomes.',
      'This limitation is a fundamental element of our pricing and service structure.',
    ],
  },
  {
    title: '12. Indemnification',
    content: [
      'You agree to indemnify BlissClip against claims arising from your use of the Service, your content, violation of these Terms, violation of third-party rights, social media platform terms, or your misconduct.',
    ],
  },
  {
    title: '13. Dispute Resolution',
    content: [
      'Informal Resolution: Contact support@blissclip.app first. Allow 30 days for resolution.',
      'Governing Law: Delaware, USA.',
      'Arbitration (US users): Binding arbitration through AAA. No class actions.',
      'International users: Disputes resolved in Delaware courts.',
    ],
  },
  {
    title: '14. Contact',
    content: [
      'General Support: support@blissclip.app',
      'Legal Inquiries: legal@blissclip.app',
      'DMCA Agent: dmca@blissclip.app',
    ],
  },
];

const dmcaSections: Section[] = [
  {
    title: 'DMCA Agent Information',
    content: [
      'Designated Agent: [To be registered with US Copyright Office]',
      'Email: dmca@blissclip.app',
      'Physical Address: [To be updated upon LLC formation]',
    ],
  },
  {
    title: 'Copyright Infringement Notification',
    content: [
      'To report copyright infringement, send a written notice including:',
      '1. Physical or electronic signature of the copyright owner or authorized agent',
      '2. Identification of the copyrighted work claimed to be infringed',
      '3. Identification of the infringing material and its location on the Service',
      '4. Your contact information (address, phone, email)',
      '5. A statement that you have a good-faith belief the use is not authorized',
      '6. A statement that the information is accurate and you are authorized to act on behalf of the owner',
    ],
  },
  {
    title: 'Counter-Notice Procedure',
    content: [
      'If your content was removed due to a DMCA notice and you believe it was a mistake:',
      '1. Send a counter-notice with your signature',
      '2. Identify the removed material and its prior location',
      '3. State under penalty of perjury that you believe removal was a mistake',
      '4. Provide your contact information',
      '5. Consent to jurisdiction of federal court in your district',
    ],
  },
  {
    title: 'Repeat Infringers',
    content: [
      'We maintain a policy of terminating accounts subject to three or more valid DMCA notices.',
      'Valid notices are those that comply with all DMCA requirements and relate to separate infringing works.',
    ],
  },
  {
    title: 'False Claims',
    content: [
      'Knowingly submitting false DMCA notices or counter-notices may result in liability for damages, including costs and attorney fees, under Section 512(f) of the DMCA.',
    ],
  },
  {
    title: 'Automated Copyright Detection',
    content: [
      'Our Service employs audio fingerprinting (Chromaprint) to detect copyrighted material against a curated database of charting music, sports broadcasts, and popular films.',
      'Content flagged by our systems is blocked from posting to social media platforms.',
      'Users must attest they have rights to source content before processing.',
    ],
  },
];

const LegalDocument: React.FC<{ sections: Section[] }> = ({ sections }) => (
  <View style={styles.documentContainer}>
    {sections.map((section, index) => (
      <View key={index} style={styles.sectionBlock}>
        <Text style={styles.sectionHeader}>{section.title}</Text>
        {section.content.map((paragraph, pIndex) => (
          <Text key={pIndex} style={styles.paragraph}>
            {paragraph}
          </Text>
        ))}
      </View>
    ))}
  </View>
);

export default function LegalScreen() {
  const { tab } = useLocalSearchParams<{ tab?: string }>();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>((tab as Tab) || 'privacy');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (tab && ['privacy', 'terms', 'dmca'].includes(tab)) {
      setActiveTab(tab as Tab);
    }
  }, [tab]);

  const tabs: { key: Tab; label: string }[] = [
    { key: 'privacy', label: 'Privacy' },
    { key: 'terms', label: 'Terms' },
    { key: 'dmca', label: 'DMCA' },
  ];

  const getDocument = () => {
    switch (activeTab) {
      case 'privacy':
        return <LegalDocument sections={privacySections} />;
      case 'terms':
        return <LegalDocument sections={termsSections} />;
      case 'dmca':
        return <LegalDocument sections={dmcaSections} />;
      default:
        return null;
    }
  };

  const getTitle = () => {
    switch (activeTab) {
      case 'privacy':
        return 'Privacy Policy';
      case 'terms':
        return 'Terms of Service';
      case 'dmca':
        return 'DMCA / Copyright';
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Text style={styles.backButtonText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{getTitle()}</Text>
        <View style={styles.placeholder} />
      </View>

      {/* Tab Bar */}
      <View style={styles.tabBar}>
        {tabs.map((t) => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tab, activeTab === t.key && styles.activeTab]}
            onPress={() => setActiveTab(t.key)}
          >
            <Text
              style={[
                styles.tabText,
                activeTab === t.key && styles.activeTabText,
              ]}
            >
              {t.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={true}>
        {loading ? (
          <View style={styles.loader}>
            <ActivityIndicator size="large" color="#6366f1" />
          </View>
        ) : (
          <>
            <View style={styles.lastUpdated}>
              <Text style={styles.lastUpdatedText}>Last Updated: May 15, 2026</Text>
            </View>
            {getDocument()}
            <View style={styles.bottomPadding} />
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f0f',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  backButton: {
    padding: 4,
  },
  backButtonText: {
    color: '#6366f1',
    fontSize: 16,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
  },
  placeholder: {
    width: 60,
  },
  tabBar: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
    backgroundColor: '#1a1a1a',
  },
  tab: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#6366f1',
  },
  tabText: {
    color: '#888',
    fontSize: 14,
    fontWeight: '500',
  },
  activeTabText: {
    color: '#6366f1',
    fontWeight: '600',
  },
  scrollView: {
    flex: 1,
  },
  lastUpdated: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  lastUpdatedText: {
    color: '#666',
    fontSize: 12,
    fontStyle: 'italic',
  },
  documentContainer: {
    padding: 16,
  },
  sectionBlock: {
    marginBottom: 24,
  },
  sectionHeader: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 12,
    lineHeight: 22,
  },
  paragraph: {
    fontSize: 14,
    color: '#ccc',
    lineHeight: 22,
    marginBottom: 12,
  },
  loader: {
    padding: 40,
    alignItems: 'center',
  },
  bottomPadding: {
    height: 40,
  },
});