# Management Report: Payment & Cost Analysis

**Audience:** Executive / Senior Management  
**Subject:** Cash outflows, cost mix, and approval workflow for two flagship projects  
**Data source:** ERPNext (MilestoneKSA) — Purchase Invoices, Payment Entries, Payment Approval Requests, Project master  
**Generated:** 2026-04-01  
**Projects:** Milestone-101 (Al Nathym النظيم), Milestone-106 (Al Aqeeq)

---

## 1. Executive summary

This report explains **what the company paid**, **to whom**, **through which payment channels**, and **how costs group into management concepts** (labor, building/contracting, consulting, governmental fees, materials, etc.). It combines:

| Layer | What it represents |
|--------|-------------------|
| **Supplier payments (Payment Entry → Purchase Invoice)** | **Cash / bank / custody** actually allocated to supplier invoices linked to the project. This is the primary measure of **money out**. |
| **Purchase Invoice lines (by concept)** | **Booked supplier cost** by category, derived from invoice line items (names, item groups, suppliers). Used to compute **% mix** of spend. |
| **Payment Approval Request (PAR)** | **Internal approval narrative** — why a payment was requested, priority, and remarks. PAR amounts are **not** merged into supplier payment totals (they may precede or overlap invoicing). |

**Key figures (from live system run)**

| Project | Total paid (supplier → PI) | PAR subtotal (approved workflow) | Land / area used for m² |
|---------|-----------------------------:|----------------------------------:|--------------------------|
| **Milestone-101** Al Nathym | **1,335,756.30** SAR | **123,497.08** SAR | **1,400.66 m²** (`total_land_area_custom`) |
| **Milestone-106** Al Aqeeq | **117,148.00** SAR | **48,805.00** SAR | Not set — per-m² not computed |

---

## 2. Methodology (how numbers are produced)

### 2.1 Which purchase invoices belong to a project?

Invoices are included if any line is tied to the project via:

- Item line `project` = project, **or**
- Blank item project but header `project` = project, **or**
- Line linked to a **Purchase Order** whose header `project` = project.

This matches the same logic used for **Total Purchase Cost** on the Project in MilestoneKSA.

### 2.2 “Total paid”

Sum of **Payment Entry Reference** rows where:

- `party_type` = Supplier  
- `reference_doctype` = Purchase Invoice  
- `reference_name` = one of the project’s purchase invoices  
- Payment Entry is **submitted** (`docstatus` = 1)

Amount used: **`allocated_amount`** (amount applied to that specific invoice).

### 2.3 Cost concepts (PI lines)

Each **Purchase Invoice Item** line is classified into a **concept bucket** using automated rules on:

- Item name and item code  
- Item group  
- Supplier name  

Arabic and English keywords map lines to: **Governmental / licenses / fees**, **Consulting & engineering**, **Labor & manpower**, **Materials & supplies**, **Building / contracting works**, or **Other**.

> **Limitation:** Classification is **rule-based**, not manual accounting coding. Unusual descriptions may land in **Other** or the nearest keyword. For audit-grade splits, introduce a **mandatory category field** on PAR or PI line (future enhancement).

### 2.4 “Estimated paid by concept”

Total **supplier payments** to the project are **distributed across concepts in the same proportions** as **PI line net amounts** by concept.  

So: if **53%** of PI net is classified as “Labor & manpower,” then **~53%** of total paid is **attributed** to labor for management reporting.

> This assumes payments follow the **same mix** as invoiced costs. If large prepayments or invoices exist without matching payment timing, the **mix** still reflects **invoice composition**, not timing of cash.

### 2.5 Payment Approval Requests

Submitted PARs with **Project** = Milestone-101 or Milestone-106 are listed with **amount**, **description** (why), **final remarks**, and a **rough concept tag** from text (for quick scanning only).

**PAR total is not added to “Total paid.”** PAR explains **intent and approval**; **PI + Payment Entry** explain **accounting outflow** against suppliers.

### 2.6 Cost per m² (Milestone-101 only)

- **Area field used:** `total_land_area_custom` = **1,400.66 m²** (building area was not set; when `total_building_area_custom` is populated, reports should prefer it for “built floor” KPIs).  
- **Overall paid per m²** = Total paid ÷ area = **953.66 SAR/m²** (land basis).

---

## 3. Milestone-101 — Al Nathym النظيم

### 3.1 Scale

- **Progress (system):** ~83.87% (reference from project dashboard)  
- **Total supplier payments allocated to project PIs:** **1,335,756.30 SAR**

### 3.2 Payment Approval Requests (internal narrative)

- **Count:** 18 submitted PARs linked to the project  
- **Subtotal of PAR amounts:** **123,497.08 SAR**  

These requests cover items such as: safety/fire drawings approval, electrical and plumbing materials, interlock supply, camera installation, pump installments, AC contractor payments, land subdivision fees, guard salary, engineering license fees, HVAC duct work, etc. They provide **traceability and “why we asked for money”** for auditors and management.

*(Full line-by-line list is in the system export; key themes: materials, electromechanical, licenses, subcontractor installments.)*

### 3.3 Purchase invoice mix (booked cost by concept)

| Concept | PI line net (SAR) | Share |
|---------|------------------:|------:|
| Labor & manpower | 640,538.96 | 53.3% |
| Building / contracting works | 545,200.00 | 45.3% |
| Consulting & engineering | 14,130.44 | 1.2% |
| Other / unclassified | 2,521.74 | 0.2% |
| **Total PI net** | **1,202,391.14** | 100% |

### 3.4 Estimated paid by concept (payment × same mix as PI)

| Concept | Attributed paid (SAR) | Share |
|---------|----------------------:|------:|
| Labor & manpower | 711,585.38 | 53.3% |
| Building / contracting works | 605,671.74 | 45.3% |
| Consulting & engineering | 15,697.74 | 1.2% |
| Other / unclassified | 2,801.44 | 0.2% |
| **Total** | **1,335,756.30** | 100% |

### 3.5 Cost intensity (land area basis)

**Area:** 1,400.66 m² (`total_land_area_custom`)

| Metric | SAR/m² |
|--------|--------:|
| Overall paid | **953.66** |
| Labor & manpower (attributed) | 508.04 |
| Building / contracting (attributed) | 432.42 |
| Consulting & engineering (attributed) | 11.21 |
| Other (attributed) | 2.00 |

### 3.6 Who we paid (suppliers)

| Supplier | Amount (SAR) | Share of paid |
|----------|-------------:|--------------:|
| مؤسسة أطراف نجد للمقاولات | 931,902.00 | 69.8% |
| شركة أعالي الخليج للمقاولات | 234,600.00 | 17.6% |
| منير شعبان | 115,000.00 | 8.6% |
| شركة افكار السلامة لانظمة الاطفاء والانذار | 24,800.00 | 1.9% |
| مكتب سلة الابداع للاستشارات الهندسية | 16,250.00 | 1.2% |
| شركة تكنوميك تكنولوجي المحدودة | 13,204.30 | 1.0% |

**Management note:** Concentration is high: **~70%** to one main contractor (أطراف نجد). Risk and progress should be monitored against that supplier’s contract and milestones.

### 3.7 How we paid (mode of payment)

| Mode | Amount (SAR) | Share |
|------|-------------:|------:|
| Bank Alrajhi | 871,585.41 | 65.3% |
| عهدة المهندس عبد الله ال ربيع | 444,672.04 | 33.3% |
| (not set) | 9,498.85 | 0.7% |
| عهدة أ.محمد قطيفان | 5,000.00 | 0.4% |
| عهدة خالد بن ظفير | 5,000.00 | 0.4% |

**Management note:** A significant share moves via **عهدة (custody / imprest)** — ensure reconciliation and retirement of custody advances is documented in finance policy.

---

## 4. Milestone-106 — Al Aqeeq

### 4.1 Scale

- **Progress (system):** ~80% (reference)  
- **Total supplier payments allocated to project PIs:** **117,148.00 SAR**

### 4.2 Project area

**total_building_area_custom** and **total_land_area_custom** were **not set** at report time — **per-m² KPIs were not calculated**. Recommendation: maintain **building footprint or GFA** on the Project for comparable intensity metrics.

### 4.3 Payment Approval Requests

- **Count:** 8 submitted PARs  
- **Subtotal:** **48,805.00 SAR**  

Themes include: excavation installments, municipal fees for advertising board, building license fees, insurance document fees, engineering office first payment (مثلث الرسم), and component invoices to أمانة الرياض.

### 4.4 Purchase invoice mix (booked cost by concept)

| Concept | PI line net (SAR) | Share |
|---------|------------------:|------:|
| Building / contracting works | 60,000.00 | 51.4% |
| Consulting & engineering | 25,400.00 | 21.7% |
| Labor & manpower | 22,756.51 | 19.5% |
| Governmental / licenses / fees | 8,650.00 | 7.4% |
| **Total** | **116,806.51** | 100% |

### 4.5 Estimated paid by concept

| Concept | Attributed paid (SAR) | Share |
|---------|----------------------:|------:|
| Building / contracting works | 60,175.41 | 51.4% |
| Consulting & engineering | 25,474.26 | 21.7% |
| Labor & manpower | 22,823.04 | 19.5% |
| Governmental / licenses / fees | 8,675.29 | 7.4% |
| **Total** | **117,148.00** | 100% |

### 4.6 Who we paid

| Supplier | Amount (SAR) | Share |
|----------|-------------:|------:|
| مؤسسة منطقة التألق التجارية | 69,000.00 | 58.9% |
| يوسف فؤاد رفاعي (الثلاثاء للطباعة) | 24,000.00 | 20.5% |
| مؤسسة غزل الخليج للمقاولات العامة | 12,800.00 | 10.9% |
| شركة مسار الجودة للتحقق | 9,948.00 | 8.5% |
| مكتب رمز الدقة للاستشارات الهندسية | 1,400.00 | 1.2% |

### 4.7 How we paid

| Mode | Amount (SAR) | Share |
|------|-------------:|------:|
| Bank Alrajhi | 112,148.00 | 95.7% |
| عهدة خالد بن ظفير | 5,000.00 | 4.3% |

---

## 5. How to read this for decision-making

1. **Use “Total paid”** for **cash and supplier exposure**; use **PAR** for **governance and story** (who requested, why, urgency).  
2. **Concept %** supports **portfolio talk** (labor vs shell vs compliance). Refine with **explicit coding** on transactions if board reporting must be exact.  
3. **Milestone-101** shows **high single-supplier concentration** and heavy use of **bank + custody** — align with contract strategy and liquidity.  
4. **Milestone-106** has a **stronger share of governmental/consulting** in the PI mix — typical for early-stage permitting and design.  
5. **Per m²** on Milestone-101 is on **land area**; for **apples-to-apples** across projects, standardize on **GFA or built area** in the Project form.

---

## 6. Technical: regenerating this analysis

From the server:

```bash
bench --site milestoneksa.com execute milestoneksa.payment_distribution_report.run
```

Source module: `milestoneksa/payment_distribution_report.py`

---

## 7. Document control

| Version | Date | Notes |
|---------|------|--------|
| 1.0 | 2026-04-01 | Initial management pack from automated export |

*Figures reflect ERP state at generation time; after new payments or invoices, re-run the command to refresh.*
