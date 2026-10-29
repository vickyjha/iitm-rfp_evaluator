"""Sample content: Others category (omnichannel customer support platform, the original brief's scenario)."""
from reportlab.lib.units import mm

RFP = {
    "category_code": "OTHERS",
    "category_note": "IT services - Omnichannel customer support platform",
    "buyer": "Meridian Retail Group (MRG)",
    "reference": "MRG-RFP-2026-014",
    "title": "Omnichannel Customer Support Platform",
}

OTHERS_SUPPLIERS: list[dict] = [
    {
        "file": "apex_systems.pdf",
        "name": "Apex Systems",
        "submission_date": "2026-10-10",
        "experience_rating": 78,
        "accent": "#1F4E79",
        "tagline": "Enterprise platform engineering since 2009 | Bengaluru, Pune, Singapore",
        "sections": [
            ("1. Executive Summary", [
                ("p", "Apex Systems is pleased to respond to MRG-RFP-2026-014. We propose ApexDesk Enterprise, a cloud-native "
                      "omnichannel support platform engineered for high-volume retail contact centres. Our design prioritises "
                      "reliability during peak trading periods, deep integration with MRG's commerce and ERP landscape, and a "
                      "security posture that meets the Digital Personal Data Protection (DPDP) Act, 2023."),
                ("p", "We understand that MRG needs to consolidate email, web chat, WhatsApp and voice interactions for 350 "
                      "agents across three contact centres into a single agent workspace, with a unified customer view drawn "
                      "from SAP S/4HANA and Shopify Plus, and with data held in India. Our proposal addresses each requirement "
                      "with production-proven components rather than custom development."),
            ]),
            ("2. Proposed Solution and Architecture", [
                ("p", "ApexDesk runs as a set of containerised microservices on Kubernetes in the AWS Mumbai region (ap-south-1), "
                      "with a warm standby in AWS Hyderabad (ap-south-2) for disaster recovery. All channels feed a common "
                      "event bus (Apache Kafka), which keeps channels decoupled and lets the platform scale each service "
                      "independently."),
                ("bullets", [
                    "Pre-built, certified connectors for SAP S/4HANA (OData v4 order, return and invoice APIs) and Shopify "
                    "Plus (Admin GraphQL API and webhooks) give agents live order status inside the ticket view.",
                    "Genesys Cloud CTI integration for voice: screen-pop, click-to-dial and call recordings linked to tickets.",
                    "WhatsApp Business Platform integration through Meta's Cloud API with template management.",
                    "Open REST and GraphQL APIs with an API gateway, rate limiting and versioning for future integrations.",
                    "Load tested to 5,000 concurrent agent sessions and 1,200 messages per second; target availability "
                    "SLA of 99.95% per month.",
                    "AI-assisted routing, suggested replies and knowledge-base recommendations (can be switched off per queue).",
                ]),
                ("p", "Data residency: all customer personal data, attachments, backups and logs are stored in India. No "
                      "personal data leaves Indian regions, including for AI features, which use models hosted in ap-south-1."),
            ]),
            ("3. Implementation Approach, Timeline and Team", [
                ("p", "We follow a four-phase delivery approach with a fixed scope baseline agreed at the end of Discovery. "
                      "Total duration is 24 weeks from contract signature to go-live, followed by 4 weeks of hypercare."),
                ("table", [["Phase", "Weeks", "Key milestones"],
                           ["Discovery & design", "1-4", "Solution design sign-off; integration specifications"],
                           ["Build & integrate", "5-14", "SAP and Shopify connectors live in test; channel set-up"],
                           ["Test & migrate", "15-20", "SIT, performance test, UAT sign-off; ticket history migration"],
                           ["Rollout", "21-24", "Pilot centre (Pune) week 21; all three centres live week 24"]],
                 [38 * mm, 18 * mm, 110 * mm]),
                ("p", "Team: engagement director (part-time), project manager, solution architect, 2 integration engineers, "
                      "2 platform engineers, QA lead, change and training lead. Implementation risks such as SAP API "
                      "availability and data migration quality are tracked in a weekly risk log reviewed with MRG."),
            ]),
            ("4. Commercial Proposal", [
                ("p", "Pricing is in Indian Rupees, exclusive of GST, for a three-year term."),
                ("table", [["Item", "Basis", "Amount (INR)"],
                           ["Implementation services (fixed price)", "One-time", "1,10,00,000"],
                           ["ApexDesk subscription, 350 agent licences", "INR 3,600 per agent per month", "4,53,60,000"],
                           ["Premium support and 24x7 operations", "Per year x 3", "54,00,000"],
                           ["Total three-year cost of ownership", "", "6,17,60,000"]],
                 [70 * mm, 55 * mm, 41 * mm]),
                ("p", "Assumptions: MRG provides SAP and Shopify sandbox access by week 3; up to 2 million historical tickets "
                      "are migrated; licence price is fixed for three years; payment milestones are 20% at signature, 40% at "
                      "UAT sign-off and 40% at go-live for the implementation fee."),
            ]),
            ("5. Security, Compliance and Risk Controls", [
                ("bullets", [
                    "Certifications: ISO/IEC 27001:2022 and ISO/IEC 27701 certified; SOC 2 Type II report (latest period "
                    "ending June 2026) available under NDA.",
                    "Encryption: AES-256 at rest with customer-managed keys in AWS KMS; TLS 1.3 in transit.",
                    "Identity: SAML 2.0 / OIDC single sign-on with MRG's Azure AD, role-based access control, MFA enforced.",
                    "Audit: immutable audit logs of every agent and administrator action, retained for 3 years and exportable "
                    "to MRG's SIEM.",
                    "Testing: annual third-party penetration test and quarterly vulnerability scans; findings shared with MRG.",
                    "Privacy: DPDP Act consent capture, data principal requests (access, correction, erasure) and "
                    "configurable retention policies are built in.",
                    "Business continuity: RPO 15 minutes, RTO 4 hours, with twice-yearly DR drills.",
                ]),
            ]),
            ("6. Support Model, Experience and References", [
                ("p", "Support is provided 24x7 by our Bengaluru operations centre. P1 incidents receive a 30-minute response; "
                      "P2 within 2 hours; P3 next business day. A named service manager provides monthly service reviews."),
                ("p", "Relevant experience: six omnichannel contact-centre implementations in the last four years, including "
                      "two for retailers with more than 200 agents."),
                ("bullets", [
                    "Northstar Fashion (retail, 280 agents) - ApexDesk with SAP integration, live since 2024.",
                    "Kavya Home Stores (retail, 140 agents) - reference available on request.",
                ]),
            ]),
        ],
    },
    {
        "file": "brightpath_tech.pdf",
        "name": "BrightPath Tech",
        "submission_date": "2026-10-08",
        "experience_rating": 35,
        "accent": "#E07A1F",
        "tagline": "Fast, affordable customer experience software | Founded 2022 | Indore",
        "sections": [
            ("1. Executive Summary", [
                ("p", "BrightPath Tech thanks Meridian Retail Group for the opportunity to respond. Our product, BrightDesk, "
                      "is a modern, lightweight help desk that gets teams live quickly at a fraction of the cost of legacy "
                      "enterprise suites. We can have MRG's agents working on BrightDesk in 12 weeks."),
                ("p", "We understand MRG wants one tool for email, chat, WhatsApp and phone tickets for its contact centre "
                      "agents, connected to its online store and ERP. BrightDesk already supports most of these channels "
                      "out of the box."),
            ]),
            ("2. Proposed Solution", [
                ("p", "BrightDesk is a multi-tenant SaaS application. Key capabilities offered to MRG:"),
                ("bullets", [
                    "Shared inbox for email, website chat widget and WhatsApp (via a third-party WhatsApp gateway partner).",
                    "Shopify app available in the Shopify App Store to show order details in the ticket sidebar.",
                    "SAP integration will be built as a custom connector during the project using SAP's standard APIs.",
                    "Voice: agents can log calls manually; native telephony integration is on our 2027 roadmap.",
                    "Macros, canned responses, simple automation rules and dashboards.",
                ]),
                ("p", "The platform is hosted on a leading public cloud provider. Hosting region will be confirmed during "
                      "onboarding. The system scales automatically with demand."),
            ]),
            ("3. Implementation Approach and Timeline", [
                ("p", "Our rapid onboarding method takes 12 weeks end to end:"),
                ("table", [["Weeks", "Activity"],
                           ["1-2", "Kick-off and configuration workshop"],
                           ["3-8", "Channel set-up, Shopify app install, SAP connector build"],
                           ["9-10", "Testing and agent training (train-the-trainer)"],
                           ["11-12", "Go-live for all three centres together"]],
                 [30 * mm, 136 * mm]),
                ("p", "Team: one project manager and two implementation consultants. Additional developers will be assigned "
                      "for the SAP connector as needed. Migration of historical tickets is not included in this timeline."),
            ]),
            ("4. Commercial Proposal", [
                ("p", "BrightPath offers highly competitive pricing (INR, excluding GST, three-year term):"),
                ("table", [["Item", "Basis", "Amount (INR)"],
                           ["Onboarding and configuration", "One-time", "18,00,000"],
                           ["BrightDesk Pro licences, 350 agents", "INR 1,750 per agent per month", "2,20,50,000"],
                           ["Standard support", "Included", "0"],
                           ["Total three-year cost", "", "2,38,50,000"]],
                 [70 * mm, 55 * mm, 41 * mm]),
                ("p", "Assumptions: SAP connector effort above 40 person-days will be billed at INR 22,000 per person-day. "
                      "WhatsApp gateway message charges are billed separately by the gateway partner. Prices valid for 60 days."),
            ]),
            ("5. Security and Compliance", [
                ("p", "Security is important to BrightPath. We follow industry best practices, including encrypted "
                      "connections (HTTPS) and password-protected user accounts. Data is backed up daily."),
                ("p", "We are currently working towards ISO 27001 certification and expect to begin the audit process next "
                      "year. A SOC 2 report is not available at this time. We will cooperate with MRG's security "
                      "questionnaire. DPDP Act requirements will be reviewed with MRG's legal team during onboarding."),
            ]),
            ("6. Support and Experience", [
                ("p", "Support is available by email and chat from 9:00 to 19:00 IST, Monday to Saturday. We aim to respond to "
                      "urgent issues within 4 business hours."),
                ("p", "BrightPath was founded in 2022 and serves 40+ small and mid-sized businesses. Our largest current "
                      "deployment is 60 agents at an online electronics retailer. Reference: Zippy Gadgets (60 agents)."),
            ]),
        ],
    },
    {
        "file": "nexaworks.pdf",
        "name": "NexaWorks",
        "submission_date": "2026-10-12",
        "experience_rating": 72,
        "accent": "#2E7D5B",
        "tagline": "Customer operations transformation partner | Hyderabad, Chennai, Dubai",
        "sections": [
            ("1. Executive Summary and Understanding of Requirement", [
                ("p", "NexaWorks proposes to implement NexaService Cloud for Meridian Retail Group as a managed transformation "
                      "programme, not just a software installation. We understand MRG's objectives as: (a) a single agent "
                      "workspace across email, chat, WhatsApp and voice for 350 agents; (b) a 360-degree customer view from "
                      "SAP S/4HANA and Shopify Plus; (c) Indian data residency and DPDP compliance; and (d) a stable go-live "
                      "well before the festive peak season."),
                ("p", "Our proposal balances capability, cost and delivery certainty. Its distinguishing features are a "
                      "phased, low-risk rollout plan and a support model that stays engaged long after go-live."),
            ]),
            ("2. Proposed Solution", [
                ("bullets", [
                    "NexaService Cloud hosted in Microsoft Azure Central India with geo-redundant backup in Azure South India.",
                    "Native connectors for Shopify Plus and SAP S/4HANA (via SAP Integration Suite), plus Genesys Cloud CTI.",
                    "WhatsApp Business Platform, web chat and email channels with unified routing and SLA timers.",
                    "Knowledge base, agent assist and supervisor real-time dashboards.",
                    "Documented REST APIs; availability SLA of 99.9% per month.",
                ]),
            ]),
            ("3. Implementation Plan", [
                ("p", "We deliver in five phases over 20 weeks with formal stage gates. A pilot with one centre de-risks the "
                      "full rollout, and each phase has entry and exit criteria agreed with MRG."),
                ("table", [["Phase", "Weeks", "Deliverables and exit criteria"],
                           ["0. Mobilise", "1-2", "Project charter, RACI, governance calendar, risk register baseline"],
                           ["1. Discover & design", "3-6", "Process maps, solution design, integration specs signed off"],
                           ["2. Build & configure", "7-12", "Sprint demos every 2 weeks; SAP/Shopify integrations in SIT"],
                           ["3. Test & pilot", "13-16", "SIT, performance and security test, UAT; Chennai pilot live wk 15"],
                           ["4. Rollout & hypercare", "17-20", "Remaining two centres live wk 18; 6 weeks of hypercare"]],
                 [36 * mm, 17 * mm, 113 * mm]),
                ("p", "Named team: Programme Director (Ravi Menon, 18 years), Project Manager (PMP), Solution Architect, "
                      "Integration Lead, 3 developers, QA Lead with 2 testers, Change Manager and Training Lead, and a "
                      "Data Migration Specialist. Team is 100% dedicated during weeks 3-18."),
                ("p", "Governance: weekly project status, fortnightly steering committee with MRG leadership, and a RAID log "
                      "(risks, assumptions, issues, dependencies). Top risks and mitigations:"),
                ("table", [["Risk", "Mitigation"],
                           ["SAP API access delayed", "Mock services from week 7; escalation path via steering committee"],
                           ["Agent adoption", "Super-user network, role-based training, floor walkers in hypercare"],
                           ["Peak-season clash", "Go-live freeze date agreed; rollback plan rehearsed before each cutover"],
                           ["Data migration quality", "Two trial migrations with reconciliation reports before final load"]],
                 [50 * mm, 116 * mm]),
            ]),
            ("4. Commercial Proposal", [
                ("table", [["Item", "Basis", "Amount (INR, excl. GST)"],
                           ["Implementation (fixed price)", "One-time", "85,00,000"],
                           ["NexaService Cloud, 350 agents", "INR 2,600 per agent per month", "3,27,60,000"],
                           ["Customer success and enhanced support", "INR 12,00,000 per year x 3", "36,00,000"],
                           ["Total three-year cost", "", "4,48,60,000"]],
                 [62 * mm, 56 * mm, 48 * mm]),
                ("p", "Assumptions: licence price locked for 3 years with a maximum 5% uplift at renewal; migration of up to "
                      "1.5 million historical tickets included; change requests above 10 person-days are quoted separately."),
            ]),
            ("5. Security, Compliance and Risk Controls", [
                ("p", "NexaWorks is ISO/IEC 27001:2022 certified and has completed a SOC 2 Type I assessment; the Type II "
                      "audit window closes in March 2027. Data is encrypted at rest (AES-256) and in transit (TLS 1.2+). "
                      "Single sign-on with Azure AD, role-based access, audit trails, and a DPDP-aligned data retention and "
                      "deletion process are provided. An external penetration test is performed annually."),
            ]),
            ("6. Support Model, Experience and References", [
                ("p", "Support model: 24x7x365 service desk with P1 response in 15 minutes and resolution target of 4 hours; "
                      "P2 response 1 hour; P3 response 4 hours. MRG gets a dedicated Technical Account Manager, a Customer "
                      "Success Manager running quarterly business reviews, and an in-region L3 engineering team. Service "
                      "credits apply if SLAs are missed."),
                ("p", "Experience: 11 contact-centre platform programmes in retail and consumer brands since 2019."),
                ("bullets", [
                    "UrbanCart India (e-commerce, 420 agents) - NexaService with SAP and Shopify, live 2025.",
                    "Saffron Lifestyle (retail, 190 agents) - multi-centre rollout, live 2024.",
                    "Coastal Consumer Electronics (220 agents) - contact details provided in Annex B.",
                ]),
            ]),
        ],
    },
    {
        "file": "orbit_digital.pdf",
        "name": "Orbit Digital",
        "submission_date": "2026-10-09",
        "experience_rating": 90,
        "accent": "#6A3FA0",
        "tagline": "15 years of customer experience delivery | Mumbai, Gurugram, London",
        "sections": [
            ("1. Executive Summary", [
                ("p", "Orbit Digital has delivered customer service transformations for leading retailers for over fifteen "
                      "years. We are excited to partner with Meridian Retail Group to modernise its customer support "
                      "operations with OrbitCX, our omnichannel engagement platform."),
                ("p", "Having implemented contact-centre platforms for 22 retail organisations, we understand the pressures "
                      "of peak trading, store and online order queries, and the need for agents to resolve issues in a "
                      "single interaction."),
            ]),
            ("2. Proposed Solution", [
                ("p", "OrbitCX provides email, chat, social and WhatsApp channels in one agent desktop, with workflow "
                      "automation, knowledge management and reporting. Voice is supported through our telephony partners."),
                ("p", "Integration approach: OrbitCX has an integration framework that can connect to most enterprise "
                      "systems. Integrations with MRG's ERP, e-commerce platform and telephony will be analysed and "
                      "scoped during the discovery phase, and the detailed design will be finalised then. We expect "
                      "to reuse patterns from previous retail projects where possible."),
                ("p", "Hosting will be on a cloud platform in India selected together with MRG."),
            ]),
            ("3. Implementation Approach and Timeline", [
                ("p", "Orbit uses its proven OrbitPath methodology. The indicative timeline is approximately 26 weeks, "
                      "subject to confirmation after discovery:"),
                ("table", [["Stage", "Indicative duration"],
                           ["Discovery and integration scoping", "6-8 weeks"],
                           ["Configuration and integration build", "10-12 weeks"],
                           ["Testing and training", "4 weeks"],
                           ["Go-live and stabilisation", "2-4 weeks"]],
                 [90 * mm, 76 * mm]),
                ("p", "Team: an engagement manager, a delivery lead and a pool of consultants and developers allocated by "
                      "phase. Detailed staffing will be shared after discovery."),
            ]),
            ("4. Commercial Proposal", [
                ("table", [["Item", "Basis", "Amount (INR, excl. GST)"],
                           ["Discovery phase", "Fixed", "15,00,000"],
                           ["Implementation (estimate)", "Time and materials", "75,00,000"],
                           ["OrbitCX licences, 350 agents", "INR 2,400 per agent per month", "3,02,40,000"],
                           ["Annual support", "INR 10,00,000 per year x 3", "30,00,000"],
                           ["Estimated three-year total", "", "4,22,40,000"]],
                 [62 * mm, 56 * mm, 48 * mm]),
                ("p", "Assumptions: implementation is estimated on a time-and-materials basis and will be re-baselined after "
                      "discovery once integrations are scoped; telephony partner licences are not included."),
            ]),
            ("5. Security and Compliance", [
                ("p", "Orbit Digital holds ISO/IEC 27001 certification. OrbitCX supports single sign-on, role-based access and "
                      "data encryption. We comply with applicable Indian data protection laws, including the DPDP Act, and "
                      "will complete MRG's security assessment during contracting."),
            ]),
            ("6. Support, Experience and References", [
                ("p", "Support: 24x7 for P1 incidents (1-hour response) and business-hours support for other priorities, "
                      "delivered from our Gurugram service centre."),
                ("p", "Experience: 15 years in customer experience, 22 retail contact-centre implementations, and 3,000+ "
                      "agents currently supported on OrbitCX. Client references (contacts available on request):"),
                ("bullets", [
                    "Shree Hypermarkets (retail, 600 agents) - OrbitCX since 2019, renewed twice.",
                    "Lotus Apparel Group (retail, 320 agents) - multi-country rollout, 2022.",
                    "GreenLeaf Pharmacy Chain (240 agents) - omnichannel rollout, 2023.",
                    "Metro Furnishings (150 agents) - migration from legacy CRM, 2025.",
                ]),
            ]),
        ],
    },
    {
        "file": "quasar_solutions.pdf",
        "name": "Quasar Solutions",
        "submission_date": "2026-10-14",
        "experience_rating": 50,
        "accent": "#9E2A2B",
        "tagline": "Digital services | Ahmedabad",
        "sections": [
            ("1. Summary", [
                ("p", "Quasar Solutions is interested in supporting Meridian Retail Group with a new customer support "
                      "platform. We propose to configure a leading open-source help desk platform for MRG's needs."),
            ]),
            ("2. Solution and Approach", [
                ("p", "We will install and configure the help desk with email and web chat channels. Other channels and "
                      "integrations with SAP and Shopify can be added in later phases. We estimate an initial rollout in "
                      "around 16 weeks with a team of four consultants."),
            ]),
            ("3. Experience", [
                ("p", "Quasar has delivered help desk set-ups for several mid-sized companies in manufacturing and education. "
                      "References will be shared at a later stage."),
                ("p", "Note: pricing, security details and the support model will be submitted separately."),
            ]),
        ],
    },
]
