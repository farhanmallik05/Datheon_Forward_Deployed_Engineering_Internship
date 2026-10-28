"""Synthetic corporate document generator for enterprise FDE evaluation.

Generates realistic multi-format documents (PDFs, CSVs, Markdown) with
embedded metadata (department, clearance tier, author, date, document IDs).
"""
import csv
import json
from pathlib import Path
from fpdf import FPDF

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"


class NumberedPDF(FPDF):
    """Custom PDF class with headers and page number footers."""
    def __init__(self, title_text: str, dept: str, clearance: str):
        super().__init__()
        self.doc_title = title_text
        self.doc_dept = dept
        self.doc_clearance = clearance

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"CONFIDENTIAL - {self.doc_dept.upper()} | CLEARANCE: {self.doc_clearance}", 0, 1, "R")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"Page {self.page_no()} | Datheon Enterprise VPC Archive", 0, 0, "C")


def generate_finance_audit_pdf(dest_path: Path):
    """Generates a 3-page formal financial audit report."""
    pdf = NumberedPDF("Q3 Financial Audit & Compliance Report", "Finance", "L3_CONFIDENTIAL")
    pdf.set_auto_page_break(auto=True, margin=18)

    # Page 1: Executive Summary & Segment Breakdown
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 35, 60)
    pdf.cell(0, 12, "Q3 2026 Financial Audit & Compliance Report", ln=True)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, "Prepared by: Directorate of Internal Audit | Date: 2026-10-15 | Clearance: Tier 3 (Strict)", ln=True)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 40, 50)
    pdf.cell(0, 8, "1. Executive Summary & Revenue Recognition", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    summary_text = (
        "During the third fiscal quarter of 2026, Datheon Enterprise Solutions achieved total consolidated "
        "revenue of $48.6M across enterprise AI software subscriptions and professional forward deployment services. "
        "Operating margin reached 24.8%, exceeding initial street guidance by 180 basis points. "
        "Cloud hosting and infrastructure expenditures on AWS and GCP totaled $11.2M, driven primarily by high-throughput "
        "GPU inference clusters and private VPC interconnects. All revenue recognized complies strictly with ASC 606 "
        "guidelines regarding multi-year contract milestone deliverables."
    )
    pdf.multi_cell(0, 6, summary_text)
    pdf.ln(4)

    # Page 2: Capital Allocations & SOX 404 Findings
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "2. Capital Expenditures & Hardware Amortization", ln=True)
    pdf.set_font("Helvetica", "", 10)
    capex_text = (
        "Capital expenditure for Q3 2026 stood at $6.4M, allocated toward on-premise hardware appliances deployed "
        "at regulated client datacenters. Server depreciation schedules follow a 36-month linear amortization standard. "
        "Vendor commitments with NVIDIA and Supermicro total $14.5M in pending hardware purchase orders scheduled "
        "for fulfillment across Q4 2026 and Q1 2027."
    )
    pdf.multi_cell(0, 6, capex_text)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "3. Sarbanes-Oxley (SOX) Section 404 Controls", ln=True)
    pdf.set_font("Helvetica", "", 10)
    sox_text = (
        "Internal audit tested 142 discrete internal financial controls. Zero material weaknesses were identified. "
        "Three minor deficiency observations were noted within manual ERP wire transfer reconciliation, specifically "
        "requiring secondary sign-off on accounts payable transactions exceeding $250,000 USD. "
        "A remediation SLA of 30 business days was assigned to the Global Accounts Payable supervisor."
    )
    pdf.multi_cell(0, 6, sox_text)

    # Page 3: Forward Guidance & Executive Disclosures
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "4. Q4 2026 Projections & Tax Reserves", ln=True)
    pdf.set_font("Helvetica", "", 10)
    tax_text = (
        "Projected full-year 2026 consolidated gross revenue is estimated at $198M-$205M. "
        "Effective corporate tax rate reserve is held at 21.4%. The company maintains $32.8M in liquid cash and "
        "cash equivalents with tier-one banking partners. Wire disbursements require dual authorized officer signatures "
        "under Board Policy 2024-B."
    )
    pdf.multi_cell(0, 6, tax_text)

    pdf.output(str(dest_path))


def generate_hr_handbook_pdf(dest_path: Path):
    """Generates an executive compensation and retention policy document."""
    pdf = NumberedPDF("Executive Compensation & Equity Policy", "HR", "L3_CONFIDENTIAL")
    pdf.set_auto_page_break(auto=True, margin=18)

    # Page 1: Compensation Tiers
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(80, 20, 40)
    pdf.cell(0, 12, "Corporate Policy 804: Executive Compensation & Severance", ln=True)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Department: Human Resources & Compensation Committee | Clearance: L3_CONFIDENTIAL", ln=True)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "1. Executive Salary Bands & Bonus Multipliers", ln=True)
    pdf.set_font("Helvetica", "", 10)
    comp_text = (
        "Band E1 (VP Engineering / Product): Base salary range $280,000 - $350,000 USD with a target performance "
        "bonus of 35% tied directly to enterprise ARR delivery and platform uptime SLAs (99.99%). "
        "Band E2 (SVP / C-Level Executives): Base salary range $380,000 - $520,000 USD with a performance multiplier "
        "of up to 60% based on EBITDA thresholds and Board consensus review."
    )
    pdf.multi_cell(0, 6, comp_text)
    pdf.ln(6)

    # Page 2: Equity Vesting & Severance Schedules
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "2. Accelerated Vesting and Change of Control Terms", ln=True)
    pdf.set_font("Helvetica", "", 10)
    vesting_text = (
        "All executive equity grants operate on a standard 4-year schedule with a 1-year cliff. "
        "In the event of a qualifying Change of Control (M&A transaction exceeding $500M enterprise valuation) "
        "followed by termination without cause within 12 months (Double Trigger), 100% of unvested equity options "
        "and RSUs shall accelerate immediately. Severance for Band E1 comprises 6 months base salary plus health insurance continuation; "
        "Band E2 comprises 12 months base salary plus full vesting acceleration."
    )
    pdf.multi_cell(0, 6, vesting_text)

    pdf.output(str(dest_path))


def generate_legal_nda_pdf(dest_path: Path):
    """Generates standard legal enterprise mutual NDA document."""
    pdf = NumberedPDF("Enterprise Mutual Non-Disclosure Agreement", "Legal", "L2_RESTRICTED")
    pdf.set_auto_page_break(auto=True, margin=18)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 20, 60)
    pdf.cell(0, 10, "Standard Master Mutual Non-Disclosure Agreement (M-NDA)", ln=True)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Doc ID: LGL-NDA-2026-V4 | Department: Legal | Clearance: L2_RESTRICTED", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Section 1: Definition of Confidential Information", ln=True)
    pdf.set_font("Helvetica", "", 10)
    p1 = (
        "'Confidential Information' refers to proprietary software source code, machine learning model weights, "
        "client VPC network topologies, financial forecasts, and trade secret algorithms disclosed by either party. "
        "The receiving party shall protect all disclosed confidential data using the same degree of care it uses for "
        "its own sensitive assets, but not less than reasonable care."
    )
    pdf.multi_cell(0, 6, p1)
    pdf.ln(4)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Section 2: Term, Exclusions, and Governing Law", ln=True)
    pdf.set_font("Helvetica", "", 10)
    p2 = (
        "The confidentiality obligations under this Agreement shall endure for a period of five (5) years following the "
        "date of initial disclosure. However, with respect to proprietary trade secrets and core algorithmic architectures, "
        "the duty of non-disclosure shall persist in perpetuity until publicly released by the disclosing party without breach. "
        "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, "
        "without regard to its conflict of laws principles."
    )
    pdf.multi_cell(0, 6, p2)

    pdf.output(str(dest_path))


def generate_csv_files(finance_dir: Path):
    """Generates structured CSV files for ERP ingestion and analytics."""
    vendor_invoices_path = finance_dir / "vendor_invoices_2026.csv"
    invoices = [
        {"invoice_id": "INV-2026-901", "vendor": "NVIDIA Cloud Compute", "po_number": "PO-88210", "department": "engineering", "amount_usd": 145000.0, "status": "APPROVED", "clearance": "L2_RESTRICTED", "date": "2026-09-12"},
        {"invoice_id": "INV-2026-902", "vendor": "Snowflake Data Warehouse", "po_number": "PO-88211", "department": "finance", "amount_usd": 38400.0, "status": "PAID", "clearance": "L2_RESTRICTED", "date": "2026-09-18"},
        {"invoice_id": "INV-2026-903", "vendor": "PwC Advisory & Audit", "po_number": "PO-88215", "department": "finance", "amount_usd": 85000.0, "status": "APPROVED", "clearance": "L3_CONFIDENTIAL", "date": "2026-09-25"},
        {"invoice_id": "INV-2026-904", "vendor": "CrowdStrike SecOps", "po_number": "PO-88220", "department": "engineering", "amount_usd": 42000.0, "status": "PENDING_APPROVAL", "clearance": "L2_RESTRICTED", "date": "2026-10-02"},
        {"invoice_id": "INV-2026-905", "vendor": "Executive Search Partners", "po_number": "PO-88224", "department": "hr", "amount_usd": 65000.0, "status": "PAID", "clearance": "L3_CONFIDENTIAL", "date": "2026-10-05"},
        {"invoice_id": "INV-2026-906", "vendor": "Equinix Colocation DC", "po_number": "PO-88231", "department": "engineering", "amount_usd": 27500.0, "status": "APPROVED", "clearance": "L2_RESTRICTED", "date": "2026-10-14"},
    ]

    with open(vendor_invoices_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(invoices[0].keys()))
        writer.writeheader()
        writer.writerows(invoices)


def generate_markdown_docs(eng_dir: Path):
    """Generates technical architectural specifications in Markdown."""
    vpc_path = eng_dir / "VPC_Network_Architecture_v2.md"
    vpc_content = """---
document_id: ENG-ARCH-VPC-002
department: engineering
clearance: L2_RESTRICTED
author: Staff Cloud Infrastructure Architect
date: 2026-09-30
title: Datheon VPC Multi-Region Deployment Architecture
---

# Enterprise VPC Network Architecture Specification v2.0

## 1. Network Topology & CIDR Allocation
The corporate cloud environment is deployed inside AWS `us-east-1` and Google Cloud `us-central1` using dual-hub Transit Gateway interconnection.
Primary VPC CIDR block is allocated as `10.180.0.0/16`, partitioned across three availability zones:
- `10.180.10.0/24`: Public Subnet AZ-A (ALB / Ingress Gateways)
- `10.180.20.0/24`: Private Application Subnet AZ-A (FastAPI Microservices)
- `10.180.30.0/24`: Isolated Data Subnet AZ-A (Qdrant Vector Cluster & PostgreSQL)

## 2. Ingress & Egress Security Rules
Strict security group isolation prohibits inbound ingress directly from the public internet into private application subnets.
All ingress must terminate at the hardened Envoy reverse proxy with Mutual TLS (mTLS) enforcement.
Outbound egress to external APIs requires routing through dual NAT Gateways with static Elastic IP whitelisting.

## 3. Bastion Host & SecOps Auditing
SSH access to private instances is strictly mediated through AWS Systems Manager (SSM) Session Manager.
Direct SSH port 22 is disabled at the security group perimeter. All shell sessions are logged to CloudWatch Logs with immutable KMS encryption.
"""
    with open(vpc_path, "w", encoding="utf-8") as f:
        f.write(vpc_content)

    rate_limit_path = eng_dir / "api_rate_limiting_spec.md"
    rate_limit_content = """---
document_id: ENG-SPEC-RATE-001
department: engineering
clearance: L1_PUBLIC
author: Senior API Platform Engineer
date: 2026-10-01
title: Enterprise API Gateway Rate Limiting Policy
---

# API Gateway Rate Limiting & Quota Specifications

## 1. Rate Limiting Algorithm
The Datheon API Gateway employs the Token Bucket algorithm backed by distributed Redis key-value storage.
Bursts are permitted up to 1.5x of the sustained transactions-per-second (TPS) ceiling.

## 2. Tiered Clearance Quotas
Rate limits are enforced at the API key level based on employee clearance tier:
- Tier L1 (Public / General): 500 requests per minute. Maximum burst: 750 requests.
- Tier L2 (Restricted Departmental): 2,000 requests per minute. Maximum burst: 3,000 requests.
- Tier L3 (Confidential / SecOps): 5,000 requests per minute. Maximum burst: 7,500 requests.

## 3. Rate Limit Exceeded Headers
When a client exceeds the threshold, the gateway returns HTTP 429 Too Many Requests with headers:
- `X-RateLimit-Limit`: Maximum requests permitted in window.
- `X-RateLimit-Remaining`: Remaining capacity.
- `Retry-After`: Seconds until quota replenishment.
"""
    with open(rate_limit_path, "w", encoding="utf-8") as f:
        f.write(rate_limit_content)


def generate_mock_erp_database(data_dir: Path):
    """Generates the initial database state for mock ERP/CRM services."""
    mock_db = {
        "inventory": [
            {"sku": "SKU-H100-80G", "product_name": "NVIDIA H100 80GB SXM5 Node", "category": "Hardware", "quantity_on_hand": 14, "unit_cost_usd": 32000.0, "warehouse_id": "WH-US-EAST", "reorder_level": 5},
            {"sku": "SKU-L40S-48G", "product_name": "NVIDIA L40S 48GB PCIe Server", "category": "Hardware", "quantity_on_hand": 38, "unit_cost_usd": 11500.0, "warehouse_id": "WH-US-WEST", "reorder_level": 10},
            {"sku": "SKU-NET-SWITCH-400G", "product_name": "Arista 400G Enterprise Spine Switch", "category": "Networking", "quantity_on_hand": 8, "unit_cost_usd": 18200.0, "warehouse_id": "WH-US-EAST", "reorder_level": 4},
            {"sku": "SKU-NVME-STORAGE-30TB", "product_name": "PureStorage FlashBlade NVMe Tray", "category": "Storage", "quantity_on_hand": 6, "unit_cost_usd": 45000.0, "warehouse_id": "WH-EU-CENTRAL", "reorder_level": 2},
        ],
        "leads": [
            {"lead_id": "LEAD-2026-101", "company_name": "Apex Global Financial", "contact_email": "cto@apexglobal.com", "estimated_arr_usd": 350000.0, "pipeline_stage": "NEGOTIATION", "assigned_rep": "Sarah Jenkins", "notes": "Requires on-prem VPC deployment with FIPS-140-3 validation."},
            {"lead_id": "LEAD-2026-102", "company_name": "BioHealth Genomics", "contact_email": "vpe@biohealth.org", "estimated_arr_usd": 180000.0, "pipeline_stage": "QUALIFIED", "assigned_rep": "David Chen", "notes": "Evaluating vector ETL latency on clinical patient records."},
            {"lead_id": "LEAD-2026-103", "company_name": "Vanguard Logistics", "contact_email": "ops@vanguardlogistics.com", "estimated_arr_usd": 520000.0, "pipeline_stage": "PROPOSAL_DELIVERED", "assigned_rep": "Sarah Jenkins", "notes": "Multi-agent ERP tool orchestration POC required."},
        ],
        "tickets": [
            {"ticket_id": "TCK-8801", "account_id": "ACC-5001", "subject": "Vector DB query timeout on Qdrant batch upsert", "priority": "HIGH", "status": "OPEN", "assigned_engineer": "Alex Mercer", "created_at": "2026-10-25T14:22:00Z"},
            {"ticket_id": "TCK-8802", "account_id": "ACC-5002", "subject": "RBAC clearance denial for Finance audit team", "priority": "CRITICAL", "status": "IN_PROGRESS", "assigned_engineer": "Maria Santos", "created_at": "2026-10-26T09:10:00Z"},
            {"ticket_id": "TCK-8803", "account_id": "ACC-5003", "subject": "Request for custom CSV parser with ISO-8601 timestamps", "priority": "MEDIUM", "status": "RESOLVED", "assigned_engineer": "Alex Mercer", "created_at": "2026-10-24T11:45:00Z"},
        ],
        "purchase_orders": [
            {"po_number": "PO-88210", "vendor": "NVIDIA Cloud Compute", "amount_usd": 145000.0, "status": "APPROVED", "requires_hitl": True, "approval_token": None},
            {"po_number": "PO-88220", "vendor": "CrowdStrike SecOps", "amount_usd": 42000.0, "status": "PENDING_APPROVAL", "requires_hitl": True, "approval_token": None},
            {"po_number": "PO-88299", "vendor": "Supermicro GPU Enclosures", "amount_usd": 285000.0, "status": "PENDING_APPROVAL", "requires_hitl": True, "approval_token": None},
        ],
        "audit_log": []
    }

    db_path = data_dir / "mock_erp_db.json"
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(mock_db, f, indent=2)


def main():
    print("[*] Generating synthetic enterprise documents and mock ERP database...")
    finance_dir = RAW_DIR / "finance"
    hr_dir = RAW_DIR / "hr"
    legal_dir = RAW_DIR / "legal"
    eng_dir = RAW_DIR / "engineering"

    finance_dir.mkdir(parents=True, exist_ok=True)
    hr_dir.mkdir(parents=True, exist_ok=True)
    legal_dir.mkdir(parents=True, exist_ok=True)
    eng_dir.mkdir(parents=True, exist_ok=True)

    generate_finance_audit_pdf(finance_dir / "Q3_Financial_Audit_Report.pdf")
    generate_hr_handbook_pdf(hr_dir / "employee_handbook_compensation_tier3.pdf")
    generate_legal_nda_pdf(legal_dir / "enterprise_nda_template.pdf")
    generate_csv_files(finance_dir)
    generate_markdown_docs(eng_dir)
    generate_mock_erp_database(DATA_DIR)

    print("[+] All synthetic legacy documents successfully generated in data/raw/")


if __name__ == "__main__":
    main()

