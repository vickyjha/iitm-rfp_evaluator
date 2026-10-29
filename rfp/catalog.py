"""Seed catalogue: procurement categories and their default evaluation criteria.

Each category has its own criteria set (weights total 100). A senior reviewer can change them in the app;
every change is written to the audit history. "Others" uses general-purpose criteria and asks the user
to describe the category when creating an evaluation.
"""
from __future__ import annotations

CATEGORIES: list[dict] = [
    {
        "code": "TECH_AI_GOV",
        "group_name": "Technology",
        "name": "AI Governance",
        "description": "Platforms and services for AI model inventory, risk assessment, monitoring and regulatory compliance.",
        "icon": "🧠",
        "requires_note": 0,
        "criteria": [
            ("Governance & Policy Coverage", "Model inventory, approval workflows, policy library, roles and accountability, alignment to frameworks such as NIST AI RMF and ISO/IEC 42001.", 25, 10),
            ("Model Risk & Monitoring", "Bias/fairness testing, drift and performance monitoring, explainability tooling, incident management and alerting.", 25, 10),
            ("Regulatory Compliance & Audit", "Support for the EU AI Act, DPDP Act and sector regulators; audit trails, evidence packs and certifications.", 20, 10),
            ("Integration & Deployment", "Integration with ML platforms and data stack, deployment options (SaaS/on-prem), implementation plan and timeline.", 15, 10),
            ("Commercials & Support", "Pricing transparency, total cost of ownership, support model, SLAs and relevant references.", 15, 10),
        ],
    },
    {
        "code": "OFFICE_STATIONERY",
        "group_name": "Office Supplies",
        "name": "Stationery",
        "description": "Rate contracts for stationery and office consumables across office locations.",
        "icon": "✏️",
        "requires_note": 0,
        "criteria": [
            ("Pricing & Discounts", "Unit prices for the sample basket, volume discounts, price validity and escalation terms.", 30, 10),
            ("Product Range & Quality", "Coverage of the item list, brands offered, quality standards, samples and substitution policy.", 25, 10),
            ("Delivery & Logistics", "Delivery lead times, coverage of all office locations, minimum order values, ordering channels and fill rate.", 20, 10),
            ("Service & Account Management", "Dedicated account manager, returns and replacement process, invoicing and reporting.", 15, 10),
            ("Sustainability", "Recycled/FSC products, eco-labels, packaging reduction and take-back programmes.", 10, 10),
        ],
    },
    {
        "code": "AUTO_DASHCAM",
        "group_name": "Automotive",
        "name": "Car Dashcam Manufacturers",
        "description": "OEM supply of dashboard cameras for fleet and passenger vehicles.",
        "icon": "📷",
        "requires_note": 0,
        "criteria": [
            ("Product Specifications", "Video resolution, low-light performance, field of view, storage, GPS/ADAS features and connectivity.", 25, 10),
            ("Quality & Certifications", "Automotive-grade components, operating temperature range, AIS/BIS/CE/FCC certifications, failure rates and testing.", 20, 10),
            ("Manufacturing Capacity & Lead Time", "Monthly capacity, lead times for the requested volume, supply-chain resilience and plant locations.", 20, 10),
            ("Pricing & Warranty", "Unit price at volume, tooling/NRE costs, payment terms, warranty length and replacement policy.", 20, 10),
            ("Data Privacy & Firmware Support", "Data encryption, privacy controls, over-the-air firmware updates and long-term software support.", 15, 10),
        ],
    },
    {
        "code": "OTHERS",
        "group_name": "Others",
        "name": "Other categories",
        "description": "Any other procurement. Uses general-purpose criteria; describe the category when you create the evaluation.",
        "icon": "📦",
        "requires_note": 1,
        "criteria": [
            ("Technical Capability", "Architecture, integrations, scalability and overall technical fit to the requirement.", 30, 10),
            ("Implementation Plan", "Timeline, milestones, staffing, governance and implementation risk plan.", 20, 10),
            ("Commercial Value", "Pricing clarity, total cost of ownership, payment terms and stated assumptions.", 20, 10),
            ("Security & Compliance", "Security controls, certifications, data privacy, auditability and regulatory compliance.", 20, 10),
            ("Support & Experience", "Support model and SLAs, similar past projects and verifiable client references.", 10, 10),
        ],
    },
]


def category_label(cat: dict) -> str:
    """Display label such as 'Technology – AI Governance'."""
    if cat["group_name"] == "Others":
        return "Others"
    return f"{cat['group_name']} – {cat['name']}"
