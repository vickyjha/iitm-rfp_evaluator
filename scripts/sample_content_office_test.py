"""A second, independent Office Supplies RFP for testing with a real AI model (no mock fixtures exist for it).

All companies, people, prices and references are fictional.
"""

TEST_RFP = {
    "category_code": "OFFICE_STATIONERY",
    "buyer": "Northgate Engineering Pvt Ltd",
    "reference": "NGE-RFP-2026-041",
    "title": "2027 Rate Contract for Office Stationery and Printer Consumables (4 offices)",
}

RFP_BRIEF = [
    ("1. About this RFP", [
        ("p", "Northgate Engineering Pvt Ltd invites proposals for a 12-month rate contract (January to December 2027) "
              "to supply office stationery and printer consumables to its four offices in Pune (head office), "
              "Chennai, Ahmedabad and Kochi. Expected annual spend is INR 42 lakh across about 650 employees."),
    ]),
    ("2. Scope", [
        ("bullets", [
            "Catalogue of 180 items: paper, writing instruments, files and folders, desk supplies, printer toner "
            "and ink, and pantry consumables.",
            "Sample basket for price comparison: A4 copier paper 75 GSM (ream), blue ball pens (box of 50), "
            "lever-arch files, sticky notes 3x3 (pack of 12) and HP 26A compatible toner.",
            "Delivery to all four offices with monthly consolidated invoicing per location.",
        ]),
    ]),
    ("3. What suppliers must include", [
        ("bullets", [
            "Unit prices for the sample basket, discounts and how long prices are fixed.",
            "Coverage of the item list, brands offered and quality standards.",
            "Delivery lead times per city, minimum order values and ordering channels.",
            "Account management, returns process and reporting.",
            "Sustainability: recycled/FSC products, packaging and take-back schemes.",
        ]),
    ]),
    ("4. Timeline", [
        ("table", [["Milestone", "Date"],
                   ["RFP issued", "10 October 2026"],
                   ["Proposals due", "28 October 2026"],
                   ["Supplier selected", "20 November 2026"],
                   ["Contract start", "1 January 2027"]], [80, 86]),
    ]),
]

TEST_SUPPLIERS = [
    {
        "file": "crestline_office_solutions", "format": "pdf", "name": "Crestline Office Solutions",
        "submission_date": "2026-10-24", "experience_rating": 72, "accent": "#1F4E79",
        "tagline": "Corporate office supplies since 2006 | Pune, Chennai, Hyderabad",
        "sections": [
            ("1. Executive Summary", [
                ("p", "Crestline Office Solutions proposes a single managed rate contract for all four Northgate offices. "
                      "We already serve 35 engineering and manufacturing companies in western and southern India and "
                      "run our own warehouses in Pune and Chennai."),
            ]),
            ("2. Product Range and Quality", [
                ("p", "We can supply 176 of the 180 items in the Northgate catalogue from stock. The remaining four "
                      "(specialist drafting supplies) are available within 7 working days. We offer two brand choices "
                      "for every high-volume item, and all paper meets IS 1848. Substitutions are made only with "
                      "written approval from the office administrator."),
            ]),
            ("3. Pricing (sample basket)", [
                ("table", [["Item", "Brand", "Unit price (INR, excl. GST)"],
                           ["A4 copier paper 75 GSM (ream of 500)", "JK Easy Copier", "241"],
                           ["Ball pens, blue (box of 50)", "Reynolds 045", "255"],
                           ["Lever-arch file", "Solo", "96"],
                           ["Sticky notes 3x3 (pack of 12)", "Post-it compatible", "310"],
                           ["Toner, HP 26A compatible", "Crestline Pro", "2,150"]], [70, 50, 46]),
                ("p", "Prices are fixed for the full 12-month contract. A 3% rebate applies when annual spend exceeds "
                      "INR 35 lakh, credited quarterly."),
            ]),
            ("4. Delivery and Logistics", [
                ("p", "Next-business-day delivery in Pune and Chennai; 2 working days to Ahmedabad and Kochi through our "
                      "logistics partner. No minimum order value. Orders are placed through a web portal with "
                      "department budgets and manager approvals, or by email. Our fill rate over the last 12 months "
                      "was 98.1%."),
            ]),
            ("5. Service and Account Management", [
                ("p", "A named key account manager based in Pune, with a regional coordinator in Chennai. Damaged or wrong "
                      "items are replaced within 2 working days. Monthly invoices per office and a quarterly spend "
                      "report by category and department are included."),
            ]),
            ("6. Sustainability", [
                ("p", "Recycled copier paper is available at a 2% premium. Toner cartridges are collected for recycling "
                      "every quarter. We are working towards plastic-free packaging by the end of 2027."),
            ]),
        ],
    },
    {
        "file": "quicksupply_mart", "format": "docx", "name": "QuickSupply Mart",
        "submission_date": "2026-10-27", "experience_rating": 40, "accent": "#B03A2E",
        "tagline": "Lowest prices on office essentials | Online wholesale",
        "sections": [
            ("1. Introduction", [
                ("p", "QuickSupply Mart is an online wholesaler of office products. We offer some of the lowest prices "
                      "in the market by buying in bulk directly from manufacturers."),
            ]),
            ("2. Pricing (sample basket)", [
                ("table", [["Item", "Unit price (INR, excl. GST)"],
                           ["A4 copier paper 75 GSM (ream of 500)", "219"],
                           ["Ball pens, blue (box of 50)", "230"],
                           ["Lever-arch file", "84"],
                           ["Sticky notes 3x3 (pack of 12)", "265"],
                           ["Toner, HP 26A compatible", "1,690"]], None),
                ("p", "Prices are valid for 60 days and subject to change with market conditions. Free shipping on "
                      "orders above INR 15,000."),
            ]),
            ("3. Products", [
                ("p", "We stock most popular office items. Brands depend on availability at the time of order and "
                      "equivalent products may be substituted."),
            ]),
            ("4. Delivery", [
                ("p", "Orders are shipped by courier within 3 to 7 working days to any city in India. Orders below "
                      "INR 15,000 carry a delivery charge of INR 350."),
            ]),
            ("5. Support", [
                ("p", "Customer support is available by email. Returns are accepted within 5 days for unopened items."),
            ]),
        ],
    },
    {
        "file": "greenleaf_workplace", "format": "pdf", "name": "GreenLeaf Workplace Supplies",
        "submission_date": "2026-10-22", "experience_rating": 65, "accent": "#2E7D32",
        "tagline": "Sustainable office supplies | B Corp certified | Bengaluru",
        "sections": [
            ("1. Executive Summary", [
                ("p", "GreenLeaf Workplace Supplies helps companies cut the environmental footprint of their offices "
                      "without compromising on quality. We propose a fully sustainable catalogue for Northgate, with "
                      "carbon reporting included."),
            ]),
            ("2. Product Range and Quality", [
                ("p", "We cover 158 of the 180 catalogue items with eco-certified alternatives. The other 22 items "
                      "(mainly specific toner models and pantry items) can be sourced as standard products on request. "
                      "All paper is FSC-certified or 100% recycled."),
            ]),
            ("3. Pricing (sample basket)", [
                ("table", [["Item", "Unit price (INR, excl. GST)"],
                           ["A4 recycled copier paper 75 GSM (ream of 500)", "262"],
                           ["Ball pens, blue, recycled plastic (box of 50)", "290"],
                           ["Lever-arch file, recycled board", "104"],
                           ["Sticky notes 3x3, recycled (pack of 12)", "335"],
                           ["Toner, HP 26A remanufactured", "1,980"]], [110, 56]),
                ("p", "Prices are fixed for 12 months. No volume discount is offered."),
            ]),
            ("4. Delivery and Logistics", [
                ("p", "Consolidated weekly deliveries to each office using electric vehicles in Pune and Chennai, and "
                      "rail freight to Ahmedabad and Kochi. Lead time is 3 to 5 working days. Minimum order value is "
                      "INR 5,000 per office."),
            ]),
            ("5. Service and Account Management", [
                ("p", "A dedicated sustainability account manager, quarterly reviews, and an online ordering portal. "
                      "Replacements for damaged goods within 5 working days."),
            ]),
            ("6. Sustainability", [
                ("bullets", [
                    "B Corp certified since 2023; ISO 14001 certified warehouse.",
                    "Quarterly carbon report showing emissions saved per office.",
                    "Take-back of toner cartridges, pens and packaging with recycling certificates.",
                    "Plastic-free, reusable crate deliveries.",
                ]),
            ]),
        ],
    },
    {
        "file": "metro_paper_house", "format": "doc", "name": "Metro Paper House",
        "submission_date": "2026-10-20", "experience_rating": 58, "accent": "#5D4037",
        "tagline": "Paper and stationery distributors | Ahmedabad",
        "sections": [
            ("1. About Us", [
                ("p", "Metro Paper House has distributed paper and stationery in Gujarat for 22 years and supplies "
                      "several government offices and schools."),
            ]),
            ("2. Our Offer", [
                ("p", "We can supply paper, files, pens and general stationery for all Northgate offices. Printer "
                      "consumables can be arranged through our partner."),
                ("p", "Detailed pricing will be shared after a meeting with your purchase team, as rates depend on the "
                      "final quantities."),
            ]),
            ("3. Delivery", [
                ("p", "Same-day delivery within Ahmedabad. Other cities will be served through transport agents; "
                      "timelines to be confirmed."),
            ]),
        ],
    },
]
