"""Sample content for the AI Governance, Stationery and Car Dashcam categories.

All companies, people, prices and references are fictional. Block types: ("p", text), ("bullets", [..]),
("table", rows, widths_mm or None).
"""

AI_GOV_RFP = {
    "category_code": "TECH_AI_GOV",
    "buyer": "Meridian Financial Services (MFS)",
    "reference": "MFS-RFP-2026-031",
    "title": "Enterprise AI Governance and Model Risk Platform",
}

AI_GOV_SUPPLIERS = [
    {
        "file": "clearmind_assurance", "format": "pdf", "name": "ClearMind Assurance",
        "submission_date": "2026-10-15", "experience_rating": 82, "accent": "#23395B",
        "tagline": "AI assurance and model risk specialists | Mumbai, London, Singapore",
        "sections": [
            ("1. Executive Summary", [
                ("p", "ClearMind Assurance proposes ClearMind Govern, an AI governance platform used by regulated banks and "
                      "insurers to inventory, approve, monitor and evidence every AI system in production. Our approach "
                      "treats governance as a control framework first and software second."),
                ("p", "We understand MFS currently runs 140 machine-learning models and 12 generative AI use cases, and "
                      "needs a single register, a consistent risk tiering method, and audit-ready evidence for the RBI, "
                      "the DPDP Act and the EU AI Act for its European subsidiary."),
            ]),
            ("2. Governance and Policy Framework", [
                ("bullets", [
                    "Central AI inventory covering ML models, vendor AI and generative AI use cases, with owners and lineage.",
                    "Pre-built policy library mapped to NIST AI RMF, ISO/IEC 42001 and the EU AI Act, with 180 configurable controls.",
                    "Risk tiering questionnaire with automatic routing to model risk, legal, privacy and the AI ethics committee.",
                    "Approval workflows with maker-checker sign-off and time-bound exceptions.",
                ]),
                ("p", "ClearMind is itself certified to ISO/IEC 42001:2023 (AI management system) and ISO/IEC 27001:2022."),
            ]),
            ("3. Model Risk and Monitoring", [
                ("p", "Monitoring covers data drift, prediction drift, performance decay against ground truth, and fairness "
                      "metrics across protected attributes. Generative AI use cases are evaluated for hallucination rate, "
                      "toxicity and prompt-injection resilience using scheduled test suites."),
                ("p", "Alerts route to model owners with severity levels and are linked to incident records, so every breach has "
                      "a documented response."),
            ]),
            ("4. Regulatory Compliance and Audit", [
                ("bullets", [
                    "EU AI Act conformity templates, including technical documentation for high-risk systems.",
                    "One-click evidence packs for internal audit and regulators, with immutable, time-stamped audit trails.",
                    "DPDP Act data protection impact assessment templates linked to each use case.",
                ]),
            ]),
            ("5. Integration, Deployment and Timeline", [
                ("p", "Connectors are available for Databricks, Azure Machine Learning, SageMaker and MLflow. The platform is "
                      "deployed as single-tenant SaaS in Azure Central India. Implementation takes 18 weeks, including "
                      "policy configuration and migration of the existing model inventory spreadsheet."),
            ]),
            ("6. Commercial Proposal and Support", [
                ("table", [["Item", "Basis", "Amount (INR, excl. GST)"],
                           ["Implementation and policy configuration", "Fixed price", "1,40,00,000"],
                           ["Platform subscription (up to 250 models)", "Per year x 3", "3,30,00,000"],
                           ["Premium support and assurance reviews", "Per year x 3", "45,00,000"],
                           ["Total three-year cost", "", "5,15,00,000"]], [70, 50, 46]),
                ("p", "Support is 24x7 for severity 1 incidents with a 1-hour response. References: two private-sector banks "
                      "and one general insurer in India, contact details provided on request."),
            ]),
        ],
    },
    {
        "file": "lumora_ai", "format": "docx", "name": "Lumora AI",
        "submission_date": "2026-10-13", "experience_rating": 64, "accent": "#5B3FA0",
        "tagline": "Observability for machine learning and generative AI | Bengaluru",
        "sections": [
            ("1. Executive Summary", [
                ("p", "Lumora AI offers Lumora Observe, a model observability platform that detects when AI systems drift, "
                      "degrade or behave unfairly, often before business users notice. We propose Lumora Observe as the "
                      "technical backbone of MFS's AI governance programme."),
            ]),
            ("2. Model Risk and Monitoring", [
                ("bullets", [
                    "Real-time drift detection on features and predictions with automatic root-cause analysis.",
                    "Fairness dashboards with 14 bias metrics and slice-level analysis.",
                    "LLM evaluation suite: hallucination scoring, groundedness checks against source documents, toxicity "
                    "and jailbreak testing, with human review queues.",
                    "Explainability using SHAP and counterfactual explanations for every scored record.",
                ]),
                ("p", "Our monitoring has run in production for more than 900 models across our customer base."),
            ]),
            ("3. Governance and Policy", [
                ("p", "Lumora Observe includes a model catalogue with owners and documentation fields. Policy workflows and "
                      "approval routing are on our product roadmap for the first half of 2027; until then MFS can continue to "
                      "manage approvals in its existing GRC tool, which we can integrate with through our API."),
            ]),
            ("4. Regulatory Compliance", [
                ("p", "Monitoring evidence can be exported as PDF reports for audit. We are preparing EU AI Act templates. "
                      "Lumora holds SOC 2 Type II; ISO/IEC 42001 certification is planned for 2027."),
            ]),
            ("5. Integration and Deployment", [
                ("p", "Lightweight SDKs for Python and Java, and native integrations with Databricks, SageMaker, Vertex AI "
                      "and Kafka. Lumora can be deployed in the customer's own cloud (AWS or Azure, India regions) or as "
                      "SaaS. A typical rollout takes 10 weeks."),
            ]),
            ("6. Commercials and Support", [
                ("table", [["Item", "Amount (INR, excl. GST)"],
                           ["Onboarding and integration", "60,00,000"],
                           ["Subscription, 3 years (usage-based, up to 200 models)", "2,70,00,000"],
                           ["Total three-year cost", "3,30,00,000"]], None),
                ("p", "Support is available in business hours (IST) with a 4-hour response for critical issues. "
                      "Reference: a digital lender with 60 production models."),
            ]),
        ],
    },
    {
        "file": "trustgrid_systems", "format": "pdf", "name": "TrustGrid Systems",
        "submission_date": "2026-10-16", "experience_rating": 70, "accent": "#0E6E6E",
        "tagline": "Responsible AI consulting and technology | Pune, Hyderabad",
        "sections": [
            ("1. Executive Summary", [
                ("p", "TrustGrid Systems proposes a combined platform-and-advisory engagement: the TrustGrid AI Control Tower "
                      "platform plus a governance operating model designed with MFS's Risk, Compliance and Data Science teams."),
            ]),
            ("2. Governance and Policy Coverage", [
                ("bullets", [
                    "AI inventory, risk tiering and lifecycle stage gates from ideation to retirement.",
                    "Policy and control library mapped to NIST AI RMF and ISO/IEC 42001, tailored during a 4-week design phase.",
                    "Operating model: RACI, AI ethics committee charter and training for 300 staff.",
                ]),
            ]),
            ("3. Model Risk and Monitoring", [
                ("p", "Scheduled validation jobs measure drift, stability and performance; fairness tests run before each "
                      "release. Generative AI use cases are tested with red-teaming playbooks every quarter. Real-time "
                      "monitoring is provided through partner tooling."),
            ]),
            ("4. Regulatory Compliance and Audit", [
                ("p", "Our regulatory team maps each use case to RBI guidance, the DPDP Act and the EU AI Act and produces "
                      "audit-ready documentation packs. Every approval and change is recorded in a tamper-evident audit log. "
                      "TrustGrid is ISO/IEC 27001 certified."),
            ]),
            ("5. Integration and Implementation Plan", [
                ("table", [["Phase", "Weeks", "Outcome"],
                           ["Design", "1-4", "Operating model, policies and risk tiers agreed"],
                           ["Configure and integrate", "5-12", "Control Tower live with MLflow, Databricks and ServiceNow"],
                           ["Pilot", "13-16", "20 priority models governed end to end"],
                           ["Scale", "17-20", "All 140 models and 12 GenAI use cases onboarded"]], [40, 20, 106]),
            ]),
            ("6. Commercials and Support", [
                ("table", [["Item", "Amount (INR, excl. GST)"],
                           ["Advisory and implementation (fixed price)", "95,00,000"],
                           ["Platform subscription, 3 years", "1,98,00,000"],
                           ["Managed governance support, 3 years", "36,00,000"],
                           ["Total three-year cost", "3,29,00,000"]], [110, 56]),
                ("p", "Support is 24x7 for priority 1 issues with a 2-hour response. References: a national insurer and a "
                      "payments company, both live since 2025."),
            ]),
        ],
    },
    {
        "file": "kavach_labs", "format": "doc", "name": "Kavach Labs",
        "submission_date": "2026-10-12", "experience_rating": 30, "accent": "#8A4B08",
        "tagline": "Affordable AI risk tooling for growing teams | Founded 2024 | Jaipur",
        "sections": [
            ("1. Summary", [
                ("p", "Kavach Labs offers Kavach Guard, a lightweight tool for registering AI models and running bias and "
                      "drift checks. We focus on getting teams started quickly at a low cost."),
            ]),
            ("2. Capabilities", [
                ("bullets", [
                    "Model register with owners and basic documentation templates.",
                    "Monthly drift reports and bias checks for tabular models.",
                    "Simple approval checklist that can be customised by the customer.",
                ]),
                ("p", "Generative AI monitoring is not yet available. Regulatory mapping to the EU AI Act and RBI guidance is "
                      "not included; customers typically engage their own consultants for this."),
            ]),
            ("3. Deployment", [
                ("p", "Kavach Guard is a SaaS product hosted in AWS Mumbai. It integrates with MLflow through a REST API. "
                      "Onboarding takes 6 weeks."),
            ]),
            ("4. Pricing and Support", [
                ("table", [["Item", "Amount (INR, excl. GST)"],
                           ["Onboarding", "12,00,000"],
                           ["Subscription, 3 years", "1,08,00,000"],
                           ["Total three-year cost", "1,20,00,000"]], None),
                ("p", "Support is by email during business hours. Our largest customer runs 25 models."),
            ]),
        ],
    },
]

STATIONERY_RFP = {
    "category_code": "OFFICE_STATIONERY",
    "buyer": "Harbourline Logistics Pvt Ltd",
    "reference": "HLL-RFP-2026-022",
    "title": "Annual Rate Contract for Stationery and Office Consumables (6 offices)",
}

STATIONERY_SUPPLIERS = [
    {
        "file": "inkwell_office_supplies", "format": "docx", "name": "Inkwell Office Supplies",
        "submission_date": "2026-10-20", "experience_rating": 75, "accent": "#1D4E89",
        "tagline": "Workplace supplies for 1,200 corporate customers | Delhi NCR, Mumbai, Chennai",
        "sections": [
            ("1. Company Overview", [
                ("p", "Inkwell Office Supplies has supplied stationery and office consumables to corporate customers since "
                      "2011. We operate four regional warehouses and serve 1,200 business customers."),
            ]),
            ("2. Product Range and Quality", [
                ("p", "We can supply all 214 items in the Harbourline item list, with at least two brand options for each "
                      "high-volume item. Free samples of the top 30 items will be provided within 7 days of request. "
                      "Substitutions are made only with written approval from the Harbourline admin team."),
            ]),
            ("3. Pricing (sample basket)", [
                ("table", [["Item", "Brand", "Unit price (INR, excl. GST)"],
                           ["A4 copier paper 75 GSM (ream of 500)", "JK Copier / equivalent", "238"],
                           ["Ball pens, blue (box of 50)", "Cello Pinpoint", "260"],
                           ["Box files, laminated", "Solo", "92"],
                           ["Whiteboard markers (set of 4)", "Camlin", "118"],
                           ["Toner cartridge, HP 88A compatible", "Inkwell Select", "1,450"]], None),
                ("p", "A volume discount of 4% applies on quarterly spend above INR 10 lakh. Prices are fixed for 12 months."),
            ]),
            ("4. Delivery and Logistics", [
                ("p", "Orders placed by 2 pm are delivered within 48 hours in metro locations and within 4 working days at "
                      "the Nagpur and Vizag sites. Ordering is through our web portal or a punch-out catalogue. Our fill rate "
                      "for the last 12 months was 97.5%."),
            ]),
            ("5. Service and Account Management", [
                ("p", "A dedicated key account manager and a back-up coordinator are assigned to Harbourline. Damaged or "
                      "incorrect items are replaced within 48 hours. Monthly consolidated invoicing with location-wise "
                      "spend reports is included."),
            ]),
            ("6. Sustainability", [
                ("bullets", [
                    "FSC-certified and 100% recycled paper options at the same price as standard paper.",
                    "Refillable markers and toner take-back with recycling certificates.",
                    "Plastic-free packaging for all deliveries since 2025.",
                ]),
            ]),
        ],
    },
    {
        "file": "papertrail_traders", "format": "pdf", "name": "PaperTrail Traders",
        "submission_date": "2026-10-18", "experience_rating": 60, "accent": "#7A2E2E",
        "tagline": "Wholesale stationery distributor | Mumbai",
        "sections": [
            ("1. Introduction", [
                ("p", "PaperTrail Traders is a wholesale distributor of stationery and office consumables serving offices in "
                      "Maharashtra, Telangana and Andhra Pradesh."),
            ]),
            ("2. Product Range", [
                ("p", "We can supply 196 of the 214 items in the item list. Specialist items such as archival boxes and "
                      "certain printer consumables will be sourced on request with a 7-day lead time."),
            ]),
            ("3. Pricing (sample basket)", [
                ("table", [["Item", "Unit price (INR, excl. GST)"],
                           ["A4 copier paper 75 GSM (ream of 500)", "232"],
                           ["Ball pens, blue (box of 50)", "245"],
                           ["Box files, laminated", "88"],
                           ["Whiteboard markers (set of 4)", "112"],
                           ["Toner cartridge, HP 88A compatible", "1,390"]], [110, 56]),
                ("p", "Prices are valid for 6 months and may be revised with 30 days' notice. A 2% discount applies on "
                      "monthly orders above INR 3 lakh."),
            ]),
            ("4. Delivery", [
                ("p", "Delivery within 24 to 48 hours in Mumbai and Hyderabad; 3 to 5 working days elsewhere. Minimum "
                      "order value is INR 5,000 per location."),
            ]),
            ("5. Service", [
                ("p", "Orders can be placed by email or WhatsApp with our sales desk. Returns are accepted within 7 days."),
            ]),
            ("6. Sustainability", [
                ("p", "Recycled paper is available on request at a 6% premium."),
            ]),
        ],
    },
    {
        "file": "officenest_india", "format": "pdf", "name": "OfficeNest India",
        "submission_date": "2026-10-18", "experience_rating": 80, "accent": "#2E6B3F",
        "tagline": "Managed office supplies programmes | Pan-India network of 22 fulfilment centres",
        "sections": [
            ("1. Executive Summary", [
                ("p", "OfficeNest India runs managed stationery programmes for multi-location companies. We propose a "
                      "single rate contract covering all six Harbourline offices, with one catalogue, one invoice and "
                      "one point of contact."),
            ]),
            ("2. Product Range and Quality", [
                ("p", "We can supply 205 of the 214 listed items from stock; the remaining 9 are available within 5 days. "
                      "All paper products meet IS 1848 standards."),
            ]),
            ("3. Pricing (sample basket)", [
                ("table", [["Item", "Unit price (INR, excl. GST)"],
                           ["A4 copier paper 75 GSM (ream of 500)", "236"],
                           ["Ball pens, blue (box of 50)", "250"],
                           ["Box files, laminated", "90"],
                           ["Whiteboard markers (set of 4)", "115"],
                           ["Toner cartridge, HP 88A compatible", "1,420"]], [110, 56]),
                ("p", "Prices are fixed for 12 months with a 3% rebate on annual spend above INR 40 lakh."),
            ]),
            ("4. Delivery and Logistics", [
                ("p", "Next-business-day delivery to all six offices, including Nagpur and Vizag, from our network of "
                      "fulfilment centres. No minimum order value."),
            ]),
            ("5. Service and Account Management", [
                ("p", "A named account manager, quarterly business reviews, an online ordering portal with approval "
                      "workflows and budget limits per department, and monthly spend analytics."),
            ]),
            ("6. Sustainability", [
                ("p", "A green catalogue with 60 eco-labelled products is available. Packaging uses recycled cartons."),
            ]),
        ],
    },
    {
        "file": "shree_ganesh_stationers", "format": "doc", "name": "Shree Ganesh Stationers",
        "submission_date": "2026-10-19", "experience_rating": 45, "accent": "#A0522D",
        "tagline": "Stationery wholesale since 1998 | Pune",
        "sections": [
            ("1. About Us", [
                ("p", "Shree Ganesh Stationers is a family-run wholesale business supplying schools, colleges and offices "
                      "in western India since 1998."),
            ]),
            ("2. Prices (sample basket)", [
                ("table", [["Item", "Unit price (INR, excl. GST)"],
                           ["A4 copier paper 75 GSM (ream of 500)", "219"],
                           ["Ball pens, blue (box of 50)", "228"],
                           ["Box files, laminated", "80"],
                           ["Whiteboard markers (set of 4)", "104"],
                           ["Toner cartridge, HP 88A compatible", "1,310"]], None),
                ("p", "These are our lowest prices, valid for 90 days."),
            ]),
            ("3. Range and Delivery", [
                ("p", "We stock most common office items; brands may vary depending on availability. Deliveries to Pune and "
                      "Mumbai within 3 days; other cities through courier within 6 to 8 days."),
            ]),
            ("4. Service", [
                ("p", "Orders are taken by phone. Payment within 15 days of invoice."),
            ]),
        ],
    },
]

DASHCAM_RFP = {
    "category_code": "AUTO_DASHCAM",
    "buyer": "Velocity Fleet Services Ltd",
    "reference": "VFS-RFP-2026-008",
    "title": "Supply of 5,000 dual-channel dashcams for the commercial fleet",
}

DASHCAM_SUPPLIERS = [
    {
        "file": "visiondrive_electronics", "format": "pdf", "name": "VisionDrive Electronics",
        "submission_date": "2026-10-21", "experience_rating": 85, "accent": "#1B3A57",
        "tagline": "Automotive camera systems for OEMs and fleets since 2008 | Chennai, Gurugram",
        "sections": [
            ("1. Executive Summary", [
                ("p", "VisionDrive Electronics proposes the VD-Pro X2, a dual-channel dashcam engineered for commercial "
                      "vehicles that run long shifts in Indian road and climate conditions."),
            ]),
            ("2. Product Specifications", [
                ("table", [["Feature", "VD-Pro X2"],
                           ["Front camera", "4K (3840x2160) at 30 fps, Sony STARVIS 2 sensor"],
                           ["Cabin camera", "1080p infrared for night-time driver monitoring"],
                           ["Field of view", "140 degrees front, 120 degrees cabin"],
                           ["Storage", "Up to 512 GB microSD, loop recording, event lock"],
                           ["Connectivity", "4G LTE, Wi-Fi and GPS with live tracking"],
                           ["ADAS", "Forward collision and lane departure warnings, driver fatigue alerts"]], [50, 116]),
            ]),
            ("3. Quality and Certifications", [
                ("p", "Built with automotive-grade components and a supercapacitor instead of a battery, rated for -20 to "
                      "70 degrees Celsius operation. The product is certified to AIS-140, BIS, CE and FCC. Our plant is "
                      "IATF 16949 certified and the field failure rate over the last 24 months was 0.6%."),
            ]),
            ("4. Manufacturing Capacity and Lead Time", [
                ("p", "Monthly capacity is 12,000 units at our Chennai plant. The first 2,000 units can ship 8 weeks after "
                      "purchase order, with the balance within 14 weeks."),
            ]),
            ("5. Pricing and Warranty", [
                ("table", [["Item", "Amount (INR, excl. GST)"],
                           ["VD-Pro X2 unit price at 5,000 units", "11,900"],
                           ["One-time tooling for custom mounting bracket", "6,50,000"],
                           ["Extended warranty (years 3-4), per unit", "900"]], [110, 56]),
                ("p", "Standard warranty is 2 years with advance replacement. Payment terms: 30% advance, 70% on delivery."),
            ]),
            ("6. Data Privacy and Firmware Support", [
                ("p", "Video is encrypted on the device (AES-256) and in transit. Cloud data is stored in India. Over-the-air "
                      "firmware updates are provided for 5 years, with security patches within 30 days of a disclosed "
                      "vulnerability."),
            ]),
        ],
    },
    {
        "file": "roadeye_technologies", "format": "docx", "name": "RoadEye Technologies",
        "submission_date": "2026-10-19", "experience_rating": 70, "accent": "#B4441B",
        "tagline": "High-volume dashcam manufacturing | Noida, Sri City",
        "sections": [
            ("1. Executive Summary", [
                ("p", "RoadEye Technologies is one of India's largest dashcam manufacturers by volume. We offer the RE-Fleet "
                      "200, a reliable dual-channel dashcam, with short lead times and competitive pricing."),
            ]),
            ("2. Product Specifications", [
                ("bullets", [
                    "Front camera 2K (2560x1440) at 30 fps; cabin camera 1080p with infrared.",
                    "Field of view 130 degrees front.",
                    "Storage up to 256 GB microSD with loop recording.",
                    "GPS and 4G LTE; ADAS features are not included.",
                ]),
            ]),
            ("3. Quality and Certifications", [
                ("p", "The RE-Fleet 200 is AIS-140 and BIS certified; CE certification is in progress. Units are burn-in "
                      "tested for 24 hours before dispatch. Operating temperature is 0 to 60 degrees Celsius."),
            ]),
            ("4. Manufacturing Capacity and Lead Time", [
                ("p", "With two plants and a combined capacity of 40,000 units per month, we can deliver all 5,000 units "
                      "within 4 weeks of purchase order. We keep 3 months of buffer stock for key components."),
            ]),
            ("5. Pricing and Warranty", [
                ("table", [["Item", "Amount (INR, excl. GST)"],
                           ["RE-Fleet 200 unit price at 5,000 units", "8,700"],
                           ["Tooling / NRE", "Nil"]], None),
                ("p", "Warranty is 18 months, with replacement within 10 working days."),
            ]),
            ("6. Data Privacy and Firmware", [
                ("p", "Recordings are stored on the SD card; cloud upload uses TLS. Firmware updates are provided through "
                      "our service centres for 2 years."),
            ]),
        ],
    },
    {
        "file": "kestrel_auto_imaging", "format": "pdf", "name": "Kestrel Auto Imaging",
        "submission_date": "2026-10-22", "experience_rating": 50, "accent": "#4A5D23",
        "tagline": "Imported automotive electronics | Kolkata",
        "sections": [
            ("1. Introduction", [
                ("p", "Kestrel Auto Imaging imports and distributes the K-Eye 4K dashcam, manufactured by our contract "
                      "partner, and provides local service in India."),
            ]),
            ("2. Product Specifications", [
                ("bullets", [
                    "4K front camera at 30 fps and 1080p cabin camera.",
                    "Field of view 150 degrees front.",
                    "Storage up to 256 GB microSD; Wi-Fi app for downloads.",
                    "Lane departure warning; no 4G connectivity in the standard model.",
                ]),
            ]),
            ("3. Quality and Certifications", [
                ("p", "The K-Eye 4K is CE and FCC certified. BIS certification will be applied for after the order is "
                      "confirmed. Operating temperature is -10 to 60 degrees Celsius."),
            ]),
            ("4. Supply and Lead Time", [
                ("p", "Units are shipped by sea from our contract manufacturer. Expected lead time is 12 to 16 weeks, "
                      "depending on shipping schedules and customs clearance."),
            ]),
            ("5. Pricing and Warranty", [
                ("table", [["Item", "Amount (INR, excl. GST)"],
                           ["K-Eye 4K unit price at 5,000 units", "7,950"],
                           ["Warranty", "1 year, return to base"]], [110, 56]),
            ]),
            ("6. Data and Firmware", [
                ("p", "The companion app stores clips on a cloud service hosted outside India. Encryption of stored video "
                      "is not supported. Firmware updates are released by the manufacturer from time to time."),
            ]),
        ],
    },
    {
        "file": "zento_mobility", "format": "docx", "name": "Zento Mobility",
        "submission_date": "2026-10-20", "experience_rating": 65, "accent": "#006D77",
        "tagline": "Connected-vehicle safety products | Bengaluru, Pune",
        "sections": [
            ("1. Executive Summary", [
                ("p", "Zento Mobility proposes the Zento Guard Duo, a dual-channel AI dashcam with a privacy-first design "
                      "and a fleet safety portal, built and supported in India."),
            ]),
            ("2. Product Specifications", [
                ("bullets", [
                    "Front camera 2K HDR at 60 fps with Sony STARVIS sensor; cabin camera 1080p infrared.",
                    "Field of view 140 degrees front.",
                    "Storage up to 512 GB with encrypted eMMC backup of event clips.",
                    "4G LTE, GPS, ADAS alerts and driver distraction detection.",
                ]),
            ]),
            ("3. Quality and Certifications", [
                ("p", "AIS-140, BIS and CE certified; FCC not applicable for the Indian market. Operating range -20 to 65 "
                      "degrees Celsius. Manufactured at our ISO 9001 certified plant in Pune."),
            ]),
            ("4. Manufacturing Capacity and Lead Time", [
                ("p", "Monthly capacity is 15,000 units. All 5,000 units can be delivered within 6 weeks of purchase order."),
            ]),
            ("5. Pricing and Warranty", [
                ("table", [["Item", "Amount (INR, excl. GST)"],
                           ["Zento Guard Duo unit price at 5,000 units", "10,400"],
                           ["Fleet safety portal, per vehicle per year", "600"]], None),
                ("p", "Warranty is 2 years with on-site replacement in 20 cities."),
            ]),
            ("6. Data Privacy and Firmware Support", [
                ("p", "End-to-end encryption from device to cloud, data hosted in India, role-based access and automatic "
                      "face blurring for shared clips, aligned with the DPDP Act. Over-the-air firmware updates are "
                      "guaranteed for 6 years."),
            ]),
        ],
    },
]
