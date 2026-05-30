from __future__ import annotations


BANK_KEYWORDS = ("bank", "small finance", "financial institution")
NBFC_KEYWORDS = ("finance", "housing", "credit", "capital", "leasing", "nbfc")
INSURANCE_KEYWORDS = ("insurance", "assurance", "life")
IT_KEYWORDS = ("software", "technology", "it services", "consulting")
MANUFACTURING_KEYWORDS = (
    "auto",
    "cement",
    "chemicals",
    "steel",
    "metals",
    "pharma",
    "textiles",
    "engineering",
    "manufacturing",
)


def classify_company_type(name: str | None, sector: str | None = None, industry: str | None = None) -> str:
    text = " ".join(part or "" for part in (name, sector, industry)).lower()
    if any(keyword in text for keyword in BANK_KEYWORDS):
        return "BANK"
    if any(keyword in text for keyword in INSURANCE_KEYWORDS):
        return "INSURANCE"
    if any(keyword in text for keyword in NBFC_KEYWORDS):
        return "NBFC"
    if any(keyword in text for keyword in IT_KEYWORDS):
        return "SERVICES"
    if any(keyword in text for keyword in MANUFACTURING_KEYWORDS):
        return "MANUFACTURING"
    if any(keyword in text for keyword in ("realty", "infrastructure", "power", "utilities")):
        return "ASSET_HEAVY"
    if any(keyword in text for keyword in ("consumer", "retail", "media", "telecom", "healthcare")):
        return "SERVICES"
    return "GENERAL"


def key_monitoring_metrics(company_type: str) -> list[str]:
    if company_type in {"BANK", "NBFC"}:
        return ["GNPA", "NIM", "CASA", "Loan Growth", "Provision Coverage"]
    if company_type == "INSURANCE":
        return ["Combined Ratio", "Solvency", "Premium Growth", "Persistency", "Claim Ratio"]
    if company_type == "MANUFACTURING":
        return ["Revenue Growth", "EBITDA Margin", "Capacity Utilization", "Working Capital", "Order Book"]
    if company_type == "SERVICES":
        return ["Revenue Growth", "EBIT Margin", "Employee Cost", "Client Additions", "FCF Conversion"]
    return ["Revenue Growth", "EBITDA Margin", "ROCE", "FCF Conversion", "Net Debt/EBITDA"]
