"""Offline stand-in for the LLM, used when no OpenAI key is configured (LLM_MODE=mock).

* For the bundled sample suppliers it returns hand-written scorecards whose evidence is quoted from the PDFs.
  Quasar Solutions deliberately omits two criteria, to exercise the Validation Tool.
* For any other supplier or criterion it uses a transparent keyword heuristic, so the app still works
  end to end with any PDF and any criteria the senior reviewer configures.
The output is plain JSON text, exactly like a real LLM response, so it goes through the same validation.
"""
from __future__ import annotations

import json
import re

_STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to with will
    our we you your their they them per plus overall""".split())

# (score, justification, evidence) keyed by supplier then criterion name (lower-case)
FIXTURES: dict[str, dict] = {
    "apex systems": {
        "criteria": {
            "technical capability": (9, "Cloud-native microservices with DR, certified SAP and Shopify connectors, Genesys CTI and documented load testing.",
                                     "Load tested to 5,000 concurrent agent sessions and 1,200 messages per second; target availability SLA of 99.95% per month."),
            "implementation plan": (7, "Clear four-phase plan with milestones and a pilot, but a longer 24-week timeline and a less detailed risk plan.",
                                    "Total duration is 24 weeks from contract signature to go-live, followed by 4 weeks of hypercare."),
            "commercial value": (5, "Pricing is transparent and fixed, but at INR 6.18 crore it is the most expensive option.",
                                 "Total three-year cost of ownership 6,17,60,000"),
            "security & compliance": (9, "ISO 27001/27701, SOC 2 Type II, customer-managed keys, immutable audit logs and DPDP features.",
                                      "ISO/IEC 27001:2022 and ISO/IEC 27701 certified; SOC 2 Type II report"),
            "support & experience": (7, "24x7 support with 30-minute P1 response; six similar implementations but only one named reference with details.",
                                     "P1 incidents receive a 30-minute response; P2 within 2 hours"),
        },
        "risks": ["Highest total cost of the field", "24-week timeline leaves less buffer before peak season"],
        "overall_summary": "Technically the strongest and most secure proposal, at a premium price.",
    },
    "brightpath tech": {
        "criteria": {
            "technical capability": (5, "Covers email, chat and WhatsApp, but SAP is a custom build, voice is only manual logging and hosting region is unconfirmed.",
                                     "Voice: agents can log calls manually; native telephony integration is on our 2027 roadmap."),
            "implementation plan": (5, "Fast 12-week plan, but a thin team, big-bang go-live and no ticket migration in scope.",
                                    "Migration of historical tickets is not included in this timeline."),
            "commercial value": (9, "Lowest three-year cost with clear per-agent pricing; some open-ended extras for SAP effort and WhatsApp charges.",
                                 "Total three-year cost 2,38,50,000"),
            "security & compliance": (3, "No ISO 27001 or SOC 2; generic statements only and DPDP review deferred.",
                                      "We are currently working towards ISO 27001 certification and expect to begin the audit process next year."),
            "support & experience": (3, "Business-hours support only and largest deployment is 60 agents versus MRG's 350.",
                                     "Our largest current deployment is 60 agents at an online electronics retailer."),
        },
        "risks": ["No security certification", "Limited experience at MRG's scale", "No native voice integration"],
        "overall_summary": "Cheapest and fastest option, but weak on compliance, voice and scale experience.",
    },
    "nexaworks": {
        "criteria": {
            "technical capability": (8, "Native SAP, Shopify and Genesys connectors, India-hosted with geo-redundant backup; 99.9% SLA slightly below Apex.",
                                     "Native connectors for Shopify Plus and SAP S/4HANA (via SAP Integration Suite), plus Genesys Cloud CTI."),
            "implementation plan": (9, "Most complete plan: stage gates, pilot, named dedicated team, RAID log and specific risk mitigations in 20 weeks.",
                                    "We deliver in five phases over 20 weeks with formal stage gates."),
            "commercial value": (7, "Mid-range fixed-price offer with locked licence pricing and migration included.",
                                 "Total three-year cost 4,48,60,000"),
            "security & compliance": (7, "ISO 27001 certified and SOC 2 Type I, with Type II still in progress.",
                                      "NexaWorks is ISO/IEC 27001:2022 certified and has completed a SOC 2 Type I assessment"),
            "support & experience": (9, "24x7 with 15-minute P1 response, TAM, CSM and service credits; strong references at similar scale.",
                                     "24x7x365 service desk with P1 response in 15 minutes and resolution target of 4 hours"),
        },
        "risks": ["SOC 2 Type II not yet complete"],
        "overall_summary": "Balanced proposal with the strongest implementation plan and support model.",
    },
    "orbit digital": {
        "criteria": {
            "technical capability": (6, "Capable platform, but integrations with ERP, e-commerce and telephony are not designed yet.",
                                     "Integrations with MRG's ERP, e-commerce platform and telephony will be analysed and scoped during the discovery phase"),
            "implementation plan": (5, "Indicative 26-week timeline with ranges, no named team and staffing deferred until after discovery.",
                                    "The indicative timeline is approximately 26 weeks, subject to confirmation after discovery"),
            "commercial value": (6, "Medium licence price, but implementation is time-and-materials and will be re-baselined.",
                                 "implementation is estimated on a time-and-materials basis and will be re-baselined after discovery"),
            "security & compliance": (6, "ISO 27001 certified with SSO and encryption, but few specifics on audit, testing or DPDP controls.",
                                      "Orbit Digital holds ISO/IEC 27001 certification."),
            "support & experience": (8, "Deepest retail experience with four named references; non-P1 support is business hours only.",
                                     "15 years in customer experience, 22 retail contact-centre implementations"),
        },
        "risks": ["Integration scope and cost uncertain until discovery", "Time-and-materials implementation pricing"],
        "overall_summary": "Most experienced supplier with strong references, but integration plan and costs are vague.",
    },
    "quasar solutions": {
        # Commercial Value and Security & Compliance intentionally missing -> validation imputes 0 with warnings
        "criteria": {
            "technical capability": (3, "Only email and web chat initially; SAP and Shopify deferred to later phases.",
                                     "Other channels and integrations with SAP and Shopify can be added in later phases."),
            "implementation plan": (3, "Only a rough 16-week estimate and a team of four; no milestones or risk plan.",
                                    "We estimate an initial rollout in around 16 weeks with a team of four consultants."),
            "support & experience": (2, "No retail experience and no references provided.",
                                     "References will be shared at a later stage."),
        },
        "omit": ["commercial value", "security & compliance"],
        "risks": ["Pricing, security and support model not submitted"],
        "overall_summary": "Incomplete proposal; key sections are missing.",
    },
    # ------------------------------------------------------------------ Technology - AI Governance
    "clearmind assurance": {
        "criteria": {
            "governance & policy coverage": (9, "Complete inventory, risk tiering and approval workflows with a policy library mapped to NIST AI RMF, ISO/IEC 42001 and the EU AI Act.",
                                             "Pre-built policy library mapped to NIST AI RMF, ISO/IEC 42001 and the EU AI Act, with 180 configurable controls."),
            "model risk & monitoring": (8, "Covers drift, performance decay, fairness and GenAI hallucination and prompt-injection testing, linked to incidents.",
                                        "Generative AI use cases are evaluated for hallucination rate, toxicity and prompt-injection resilience using scheduled test suites."),
            "regulatory compliance & audit": (9, "EU AI Act conformity templates, evidence packs and immutable audit trails; the supplier is itself ISO/IEC 42001 certified.",
                                              "One-click evidence packs for internal audit and regulators, with immutable, time-stamped audit trails."),
            "integration & deployment": (7, "Connectors for the main ML platforms, India-hosted single-tenant SaaS; 18-week implementation is longer than peers.",
                                         "Implementation takes 18 weeks, including policy configuration and migration of the existing model inventory spreadsheet."),
            "commercials & support": (5, "Most expensive offer at INR 5.15 crore over three years, though support is strong (24x7, 1-hour response).",
                                      "Total three-year cost 5,15,00,000"),
        },
        "risks": ["Highest three-year cost", "Longest implementation timeline"],
        "overall_summary": "Most complete governance and compliance proposal, at a premium price.",
    },
    "lumora ai": {
        "criteria": {
            "governance & policy coverage": (6, "Good model catalogue, but policy workflows and approval routing are only on the 2027 roadmap.",
                                             "Policy workflows and approval routing are on our product roadmap for the first half of 2027"),
            "model risk & monitoring": (9, "Strongest monitoring: real-time drift with root-cause analysis, 14 bias metrics, LLM groundedness and jailbreak testing.",
                                        "Real-time drift detection on features and predictions with automatic root-cause analysis."),
            "regulatory compliance & audit": (6, "SOC 2 Type II and PDF audit exports, but EU AI Act templates are still being prepared and no ISO 42001 yet.",
                                              "We are preparing EU AI Act templates."),
            "integration & deployment": (8, "Broad SDK and platform integrations, in-customer-cloud option and a short 10-week rollout.",
                                         "A typical rollout takes 10 weeks."),
            "commercials & support": (7, "Mid-range price; support is business hours only with a 4-hour critical response.",
                                      "Support is available in business hours (IST) with a 4-hour response for critical issues."),
        },
        "risks": ["Governance workflows not yet available", "Business-hours support only"],
        "overall_summary": "Best-in-class monitoring, but governance and compliance features are incomplete.",
    },
    "trustgrid systems": {
        "criteria": {
            "governance & policy coverage": (8, "Inventory, lifecycle stage gates and a tailored control library, plus an operating model and staff training.",
                                             "Operating model: RACI, AI ethics committee charter and training for 300 staff."),
            "model risk & monitoring": (7, "Scheduled validation and quarterly GenAI red-teaming; real-time monitoring relies on partner tooling.",
                                        "Real-time monitoring is provided through partner tooling."),
            "regulatory compliance & audit": (8, "Use-case mapping to RBI, DPDP and EU AI Act with documentation packs and a tamper-evident audit log.",
                                              "Every approval and change is recorded in a tamper-evident audit log."),
            "integration & deployment": (8, "Clear 20-week phased plan with a pilot and integrations to MLflow, Databricks and ServiceNow.",
                                         "Control Tower live with MLflow, Databricks and ServiceNow"),
            "commercials & support": (8, "Competitive INR 3.29 crore total with fixed-price implementation and 24x7 P1 support.",
                                      "Total three-year cost 3,29,00,000"),
        },
        "risks": ["Real-time monitoring depends on a partner product"],
        "overall_summary": "Balanced platform-plus-advisory offer with strong value for money.",
    },
    "kavach labs": {
        "criteria": {
            "governance & policy coverage": (5, "Basic model register and a customisable checklist; no policy library or risk tiering.",
                                             "Simple approval checklist that can be customised by the customer."),
            "model risk & monitoring": (6, "Monthly drift and bias reports for tabular models only; no generative AI monitoring.",
                                        "Generative AI monitoring is not yet available."),
            "regulatory compliance & audit": (4, "No regulatory mapping; customers must engage their own consultants.",
                                              "Regulatory mapping to the EU AI Act and RBI guidance is not included"),
            "integration & deployment": (6, "Simple SaaS in AWS Mumbai with an MLflow API integration and 6-week onboarding.",
                                         "It integrates with MLflow through a REST API."),
            "commercials & support": (9, "Lowest cost at INR 1.2 crore; email support only and limited scale experience.",
                                      "Total three-year cost 1,20,00,000"),
        },
        "risks": ["No regulatory compliance support", "Largest customer runs only 25 models"],
        "overall_summary": "Low-cost starter tool that does not meet MFS's compliance needs.",
    },
    # ------------------------------------------------------------------ Office Supplies - Stationery
    "inkwell office supplies": {
        "criteria": {
            "pricing & discounts": (8, "Competitive basket prices fixed for 12 months, with a 4% volume discount.",
                                    "A volume discount of 4% applies on quarterly spend above INR 10 lakh. Prices are fixed for 12 months."),
            "product range & quality": (9, "Covers all 214 items with two brand options and free samples; substitutions need written approval.",
                                        "We can supply all 214 items in the Harbourline item list"),
            "delivery & logistics": (7, "48-hour metro delivery, 4 working days at Nagpur and Vizag; 97.5% fill rate.",
                                     "Our fill rate for the last 12 months was 97.5%."),
            "service & account management": (9, "Dedicated key account manager plus back-up, 48-hour replacements and location-wise reporting.",
                                             "A dedicated key account manager and a back-up coordinator are assigned to Harbourline."),
            "sustainability": (9, "FSC and recycled paper at no premium, take-back programme and plastic-free packaging.",
                               "FSC-certified and 100% recycled paper options at the same price as standard paper."),
        },
        "risks": ["Slower delivery to non-metro sites"],
        "overall_summary": "Most complete offer across range, service and sustainability.",
    },
    "papertrail traders": {
        "criteria": {
            "pricing & discounts": (9, "Low basket prices, but valid for only 6 months and open to revision.",
                                    "Prices are valid for 6 months and may be revised with 30 days' notice."),
            "product range & quality": (8, "Covers 196 of 214 items; specialist items sourced on request.",
                                        "We can supply 196 of the 214 items in the item list."),
            "delivery & logistics": (8, "Fast in Mumbai and Hyderabad, slower elsewhere, with a minimum order value per location.",
                                     "Minimum order value is INR 5,000 per location."),
            "service & account management": (7, "Ordering by email or WhatsApp; no named account manager or reporting.",
                                             "Orders can be placed by email or WhatsApp with our sales desk."),
            "sustainability": (5, "Recycled paper only on request at a premium.",
                               "Recycled paper is available on request at a 6% premium."),
        },
        "risks": ["Short price validity", "Limited sustainability options"],
        "overall_summary": "Good prices and delivery, weaker service and sustainability.",
    },
    "officenest india": {
        "criteria": {
            "pricing & discounts": (9, "Prices fixed for 12 months with a 3% annual rebate.",
                                    "Prices are fixed for 12 months with a 3% rebate on annual spend above INR 40 lakh."),
            "product range & quality": (7, "205 of 214 items from stock; remaining items within 5 days; paper meets IS 1848.",
                                        "We can supply 205 of the 214 listed items from stock"),
            "delivery & logistics": (8, "Next-business-day delivery to all six offices with no minimum order value.",
                                     "Next-business-day delivery to all six offices, including Nagpur and Vizag"),
            "service & account management": (8, "Named account manager, QBRs, approval workflows and spend analytics.",
                                             "A named account manager, quarterly business reviews, an online ordering portal"),
            "sustainability": (6, "Green catalogue of 60 products; limited programme beyond that.",
                               "A green catalogue with 60 eco-labelled products is available."),
        },
        "risks": ["Smaller in-stock range than the leader"],
        "overall_summary": "Strong managed-programme offer with excellent delivery coverage.",
    },
    "shree ganesh stationers": {
        "criteria": {
            "pricing & discounts": (10, "Lowest prices in the field, but valid for only 90 days.",
                                    "These are our lowest prices, valid for 90 days."),
            "product range & quality": (6, "Stocks common items only and brands may vary.",
                                        "brands may vary depending on availability"),
            "delivery & logistics": (6, "3 days to Pune and Mumbai, 6 to 8 days by courier elsewhere.",
                                     "other cities through courier within 6 to 8 days"),
            "service & account management": (6, "Phone ordering only; no account management or reporting.",
                                             "Orders are taken by phone."),
            "sustainability": (3, "No sustainability information provided.", ""),
        },
        "risks": ["Slow delivery outside Maharashtra", "No sustainability commitments"],
        "overall_summary": "Cheapest supplier, but weak on range, service and delivery coverage.",
    },
    # ------------------------------------------------------------------ Automotive - Car Dashcams
    "visiondrive electronics": {
        "criteria": {
            "product specifications": (9, "4K STARVIS 2 front, IR cabin camera, 512 GB, 4G/GPS and full ADAS.",
                                       "4K (3840x2160) at 30 fps, Sony STARVIS 2 sensor"),
            "quality & certifications": (9, "Supercapacitor design, -20 to 70°C, AIS-140/BIS/CE/FCC, IATF 16949 plant, 0.6% failure rate.",
                                         "The product is certified to AIS-140, BIS, CE and FCC."),
            "manufacturing capacity & lead time": (7, "12,000 units/month but full delivery takes 14 weeks.",
                                                   "The first 2,000 units can ship 8 weeks after purchase order, with the balance within 14 weeks."),
            "pricing & warranty": (6, "Highest unit price plus tooling cost; 2-year warranty with advance replacement.",
                                   "VD-Pro X2 unit price at 5,000 units"),
            "data privacy & firmware support": (8, "AES-256 on device, India-hosted cloud, 5 years of OTA updates.",
                                                "Video is encrypted on the device (AES-256) and in transit."),
        },
        "risks": ["Highest unit price", "14-week full delivery"],
        "overall_summary": "Best hardware and quality credentials, at a premium price.",
    },
    "roadeye technologies": {
        "criteria": {
            "product specifications": (7, "2K front and IR cabin camera with 4G/GPS, but no ADAS features.",
                                       "GPS and 4G LTE; ADAS features are not included."),
            "quality & certifications": (7, "AIS-140 and BIS certified, CE pending; narrower 0 to 60°C range.",
                                         "CE certification is in progress."),
            "manufacturing capacity & lead time": (9, "40,000 units/month and full delivery in 4 weeks with buffer stock.",
                                                   "we can deliver all 5,000 units within 4 weeks of purchase order"),
            "pricing & warranty": (8, "Low unit price, no tooling cost, 18-month warranty.",
                                   "Warranty is 18 months, with replacement within 10 working days."),
            "data privacy & firmware support": (6, "TLS for uploads but no device encryption; firmware updates only via service centres for 2 years.",
                                                "Firmware updates are provided through our service centres for 2 years."),
        },
        "risks": ["No ADAS", "Limited firmware support period"],
        "overall_summary": "Fastest delivery at a good price, with fewer features and weaker privacy controls.",
    },
    "kestrel auto imaging": {
        "criteria": {
            "product specifications": (8, "4K front with wide 150° view, but no 4G connectivity.",
                                       "Lane departure warning; no 4G connectivity in the standard model."),
            "quality & certifications": (6, "CE and FCC only; BIS certification not yet applied for.",
                                         "BIS certification will be applied for after the order is confirmed."),
            "manufacturing capacity & lead time": (6, "Imported by sea with an uncertain 12 to 16 week lead time.",
                                                   "Expected lead time is 12 to 16 weeks"),
            "pricing & warranty": (9, "Lowest unit price; 1-year return-to-base warranty.",
                                   "K-Eye 4K unit price at 5,000 units"),
            "data privacy & firmware support": (4, "Cloud storage outside India and no encryption of stored video.",
                                                "Encryption of stored video is not supported."),
        },
        "risks": ["Data stored outside India without encryption", "BIS certification missing"],
        "overall_summary": "Cheapest option with significant compliance and privacy gaps.",
    },
    "zento mobility": {
        "criteria": {
            "product specifications": (8, "2K HDR at 60 fps, IR cabin camera, encrypted backup, 4G/GPS, ADAS and distraction detection.",
                                       "4G LTE, GPS, ADAS alerts and driver distraction detection."),
            "quality & certifications": (8, "AIS-140, BIS and CE certified, -20 to 65°C, ISO 9001 plant.",
                                         "AIS-140, BIS and CE certified"),
            "manufacturing capacity & lead time": (8, "15,000 units/month with full delivery in 6 weeks.",
                                                   "All 5,000 units can be delivered within 6 weeks of purchase order."),
            "pricing & warranty": (7, "Mid-range unit price plus portal fee; 2-year on-site warranty.",
                                   "Warranty is 2 years with on-site replacement in 20 cities."),
            "data privacy & firmware support": (9, "End-to-end encryption, India hosting, face blurring and 6 years of OTA updates.",
                                                "End-to-end encryption from device to cloud, data hosted in India"),
        },
        "risks": ["Recurring portal fee adds to total cost"],
        "overall_summary": "Well-balanced offer with the strongest privacy and firmware commitments.",
    },
}


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3 and w not in _STOP]


def _heuristic(criterion: dict, document_text: str) -> tuple[float, str, str]:
    keys = set(_tokens(f"{criterion['name']} {criterion['description']}"))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", document_text) if len(s.strip()) > 30]
    scored = sorted(((sum(1 for w in set(_tokens(s)) if w in keys), i, s) for i, s in enumerate(sentences)),
                    key=lambda t: (-t[0], t[1]))
    hits = [t for t in scored if t[0] > 0]
    coverage = min(1.0, sum(t[0] for t in hits[:8]) / max(1, len(keys) * 1.5))
    score = round(criterion["max_score"] * coverage)
    evidence = hits[0][2][:300] if hits else ""
    why = (f"Mock heuristic: {len(hits)} sentence(s) mention terms related to this criterion "
           f"(coverage {coverage:.0%}).") if hits else "Mock heuristic: the document does not address this criterion."
    return score, why, evidence


def mock_evaluate(supplier_name: str, criteria: list[dict], document_text: str) -> str:
    fixture = FIXTURES.get(supplier_name.strip().lower())
    out = []
    for c in criteria:
        key = c["name"].strip().lower()
        entry = fixture["criteria"].get(key) if fixture else None
        if fixture and key in fixture.get("omit", []):
            continue  # fixture deliberately leaves this criterion out (validation demo)
        if entry is None:
            score, why, ev = _heuristic(c, document_text)
        else:
            score, why, ev = entry
            score = round(score / 10 * c["max_score"], 2)  # fixtures are written on a 0-10 scale
        out.append({"criterion_id": c["criterion_id"], "score": score, "max_score": c["max_score"],
                    "justification": why, "evidence": ev})
    return json.dumps({
        "supplier_name": supplier_name,
        "criteria": out,
        "risks": fixture["risks"] if fixture else [],
        "overall_summary": fixture["overall_summary"] if fixture else "Generated by the offline mock evaluator.",
    })
