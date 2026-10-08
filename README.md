<div align="center">

# 📊 Customer Churn Intelligence & Management System

### سامانه تحلیل هوشمند و مدیریت ریزش مشتری

**Enterprise-grade Churn Early Warning · AI Behavioral Diagnosis · Automated Next Best Action (NBA) Playbooks**

[Executive Summary](#-executive-summary--the-business-problem) ·
[Architecture](#%EF%B8%8F-system-architecture--pipeline) ·
[Dashboard Features](#-key-dashboard-features) ·
[Behavioral Playbooks](#-behavioral-next-best-action-nba-playbooks) ·
[Quickstart](#-quickstart-guide) ·
[Project Structure](#%EF%B8%8F-project-structure) ·

</div>

---

## 🎯 Executive Summary & The Business Problem

Many e-commerce and subscription businesses realize that a customer is leaving **only after they stop buying**. At that point, the cost of finding a new customer has already been spent, and bringing the customer back can be difficult and expensive.

This platform analyzes past customer behavior to **identify customers who may be at risk of leaving early**. It uses machine learning to estimate churn risk, find the main reasons behind that risk, and recommend one of **six practical actions (Next Best Action - NBA)**. This gives marketing, support, and CRM teams a chance to act before the customer leaves.


### What the Data Reveals (5,630 Customers)

| Finding | Metric / Evidence | Business Implication |
|---|---|---|
|  **Baseline Churn** | **16.84 %** overall churn rate (948 of 5,630 customers) | Systematic retention represents the single highest-margin revenue lever. |
|  **Complaint Multiplier** | **31.7 %** churn among complainants vs. **10.9 %** without (≈ **2.9×** multiplier) | 53.6 % of all churners lodged a complaint; immediate resolution is critical. |
|  **First-Month Cliff** | **51.8 %** churn for tenure ≤ 1 month; **65.5 %** of churners quit in month 1 | Onboarding and the second-order activation loop decide long-term retention. |
|  **Satisfaction Paradox** | **23.8 %** churn at score 5/5 vs. **11.5 %** at score 1/5 | Survey scores create false security; behavioral drop-off precedes survey feedback. |
|  **Category Vulnerability** | Mobile Phone **27.4 %**, Fashion **15.5 %**, Laptop **10.2 %**, Grocery **4.9 %** | Digital categories suffer high brand-switching; grocery exhibits habit loyalty. |
|  **Logistics & Rewards** | Churn rises from **13.5 %** to **20.4 %** with delivery distance; falls to **10.2 %** with cashback | Shipping friction accelerates attrition; cashback acts as a tangible retention lock. |



---

## 🏗️ System Architecture & Pipeline

The system is built on an enterprise **Client-Server Architecture**, pairing an asynchronous **FastAPI** backend with a high-performance **Single Page Application (SPA)** frontend built with vanilla JavaScript, modern CSS, and Chart.js.

```text
 ┌─────────────────────────── OFFLINE PIPELINE (Run Once) ───────────────────────────┐
 │                                                                                    │
 │   data/E-Commerce-Dataset.csv         5,630 rows × 20 behavioral attributes        │
 │             │                                                                      │
 │             ▼                                                                      │
 │   export_model.py ── fit_preprocessing()                                           │
 │      1. Strip CustomerID and target column                                         │
 │      2. Median imputation for missing numeric features                             │
 │      3. Category consolidation (Mobile→Mobile Phone, CC→Credit Card, ...)          │
 │      4. Interquartile Range (IQR) outlier capping on 9 continuous features         │
 │      5. Feature Engineering: avg_cashbk_per_order = CashbackAmount / OrderCount    │
 │      6. One-hot encoding (drop_first=True) → 27 final numerical dimensions         │
 │             │                                                                      │
 │             ▼                                                                      │
 │      Stratified 80 / 20 Train-Test Split (random_state = 42)                       │
 │      RandomForestClassifier (300 estimators, balanced class weights)               │
 │             │                                                                      │
 │             ├──► models/churn_model.joblib  (Trained bundle: estimator, medians,   │
 │             │                                IQR bounds, categorical maps, meta)   │
 │             └──► data/test_stream_data.csv  (200 held-out evaluation customers)   │
 └────────────────────────────────────────────────────────────────────────────────────┘

 ┌─────────────────────────── ONLINE RUNTIME (FastAPI + SPA) ─────────────────────────┐
 │                                                                                    │
 │   FastAPI Backend (main.py + Uvicorn @ Port 8000)                                  │
 │      │                                                                             │
 │      ├── In-Memory Scored Customer Store (200 records + real-time status tracker)  │
 │      ├── churn_inference.predict_single_customer()                                 │
 │      │     • Bundled preprocessing reproduction (zero training-serving skew)       │
 │      │     • Tree-path feature attribution (Saabas-style exact additive Shapley)   │
 │      ├── 6-Playbook NBA Decision Engine (explorer_recommendation)                  │
 │      │                                                                             │
 │      └── RESTful Endpoints:                                                        │
 │            • GET  /api/insights     → Macro dataset KPIs, 5 analyses, roadmap      │
 │            • GET  /api/radar        → Live dual-stream random customer feed        │
 │            • POST /api/evaluate     → Interactive form inference & NBA recommendation│
 │            • GET  /api/customers    → 200 customer directory & 360° dossier payload│
 │            • POST /api/action       → Live intervention registration tracking      │
 │                                                                                    │
 │   Frontend Presentation Layer (static/ SPA)                                        │
 │      ├── static/index.html   (Semantic dashboard markup & 360° modal dialog)       │
 │      ├── static/style.css    (Enterprise UI design system)       │
 │      └── static/app.js       (Reactive state, Chart.js charts, modal controller)   │
 └────────────────────────────────────────────────────────────────────────────────────┘
```

### Architectural Principles

1. **Deterministic Preprocessing:** All imputation medians, IQR clipping thresholds, and categorical levels are encapsulated within `models/churn_model.joblib`. Serving logic strictly replicates training transformations without data leakage or feature drift.
2. **Lightweight Native Explainability:** Root-cause drivers are generated directly from tree traversal path attribution implemented in pure NumPy, calculating exact percentage-point impacts for each factor without external runtime overhead.


### Model Performance Metrics

| Metric | Score / Benchmark | Note |
|---|---|---|
| **Algorithm** | Random Forest Classifier | 300 decision trees, `class_weight="balanced"` |
| **Validation Split** | Stratified 80 / 20 | 4,504 training rows · 1,126 testing rows |
| **Overall Accuracy** | **≈ 98.0 %** | Evaluated on held-out test distribution |
| **ROC-AUC Score** | **≈ 0.998** | Near-perfect class separability |
| **Churn Recall (Test)** | **≈ 88.0 %** | Minimal false negatives on departing customers |
| **Churn Precision** | **≈ 100.0 %** | Negligible false alarms for retention campaigns |

---

## ✨ Key Dashboard Features

The web application is structured into **three operational tabs**, catering to executive stakeholders, marketing retention teams, and frontline account managers:

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                     DASHBOARD NAVIGATION TABS                          │
 ├─────────────────────────┬────────────────────────┬─────────────────────┤
 │  📊 تحلیل‌های استراتژیک  │  ⚡ رادار و آزمایشگاه  │  📋 فهرست مشتریان  │
 │  Strategic Intelligence │  Live Radar & Lab      │  Customer Directory │
 └─────────────────────────┴────────────────────────┴─────────────────────┘
```

---

### 📊 Tab 1 — Strategic Intelligence (Executive View)


### **Executive KPIs**

* **Current Churn Rate:** **16.84%** of customers are at risk of leaving, with **948 lost customers**.
* **Revenue at Risk Simulator:** An interactive slider that estimates potential annual financial loss based on the number of customers.
* **Model Performance:** **99.8%** pattern detection accuracy and **98.0%** machine-learning precision.

### **5 Customer Behavior Analyses**

1. **The Satisfaction Paradox:** Shows why even highly satisfied customers may still leave.
2. **The Complaint Effect:** Compares churn rates between customers with and without complaints, showing a nearly **3× higher churn rate** among customers with complaints.
3. **The First-Month Risk:** Shows that the first month is the most critical period, with **65.5% of churn occurring within the first 30 days**.
4. **Category Risk:** Compares churn risk across different product categories, including **Mobile Phone and Grocery**.
5. **Delivery & Rewards:** Examines the relationship between delivery distance, purchase rewards, and customer retention.

### **Executive Action Roadmap**

A practical action plan for **Marketing, Customer Support, Logistics, and Loyalty teams**, helping each team focus on the areas with the highest churn risk.

---

### ⚡ Tab 2 — Customer Monitoring & Retention

Designed for real-time customer monitoring and testing different customer situations.

#### **1. Live Customer Radar**

* **Live Customer Monitoring:** Automatically checks **2 customers every 6 seconds** and shows their current churn risk.
* **Scan Countdown:** A live countdown shows when the next customers will be checked, with an option to pause or resume monitoring.
* **Risk Levels:**

  * 🔴 **High Risk** (>70%): Clear warning with the main factors related to the risk.
  * 🟠 **Medium Risk** (50%–70%): Warning status with the main customer behavior behind the risk.
  * 🟢 **Low Risk** (<35%): Customer is currently in a stable position.
* **Customer Details:** View the customer's full information directly from the radar without leaving the page. Monitoring pauses while the details are open.

#### **2. Customer Retention Analysis**

Enter a few basic customer details and see how the system evaluates that customer:

* Membership duration
* Days since the last purchase
* Complaint status
* Satisfaction score (1–5)
* Preferred product category
* Number of previous orders
* City type
* Business or store name

#### **Quick Customer Examples**

Three ready-to-use examples are available for a quick demonstration:

* ⚠️ **Unhappy Customer** — New customer with a complaint
* 🟢 **Stable Customer** — Long-term customer with no complaint
* ⏳ **Inactive Customer** — New customer who has not purchased recently

#### **AI Customer Evaluation**

After entering the customer information, the system shows:

* **Churn Probability:** How likely the customer is to leave.
* **Risk Level:** Low, medium, or high.
* **Main Risk Factors:** The most important customer behaviors linked to the risk.
* **Estimated Retention Value:** The potential annual value of keeping the customer.
* **Recommended Action:** One of **6 practical retention actions**, including a suitable offer and ready-to-send customer message.
* **Register Action:** Save the recommended action in the system with one click.



---

###  Tab 3 — Customer 360° Dossier & Treatment Table

An enterprise customer directory and intervention dispatch hub modeled after Stripe and Linear interfaces:

* **200-Customer Directory Table:**
  * Searchable by numeric Customer ID.
  * Filterable by risk category (All, Critical, Warning, Stable).
  * Color-coded risk pills with live Persian formatting.
  * Visual **Next Best Action (NBA) Playbook Badges** representing prescribed interventions.
  * Treatment state tags: `در انتظار اقدام` (Pending) vs. `تحت مداخله (In Treatment) ✅`.
* **Interactive 360° Customer Dossier Modal:**
  * Triggered via the **«مشاهده پرونده»** action button.
  * Seamlessly dismissible via header close button (`✕`), background overlay click, or keyboard `Escape` key.
  * **Right Column — Comprehensive 19-Variable Profile (Categorized into 3 Panels):**
    1. *Identity & Geography (مشخصات هویتی و جغرافیایی):* Customer ID, City Tier, Warehouse-to-Home Distance, Number of Registered Addresses, etc.
    2. *Transaction & Financial History (تاریخچه تراکنش و مالی):* Tenure, Preferred Category, Order Count, Cashback Amount, Average Cashback per Order, Order Growth YoY, Coupon Usage.
    3. *App Behavior & Engagement (رفتار در اپلیکیشن و تعامل):* Hours on App, Registered Devices, Preferred Payment Mode, Satisfaction Score, Complain Flag.
  * **Left Column — NBA Command Console:**
    * *Stable Customers (< 50 % & No Complaints):* Authoritative **«سکوت استراتژیک» (Strategic Do-Not-Disturb)** panel — protecting profit margin and customer peace.
    * *At-Risk Customers (≥ 50 % or Complaints):* 3 minimal structured cards:
      1. ⚠️ **Main Risk Cause:** Concise diagnostic summary of primary friction point.
      2. 💡 **Bold Proposed Strategy:** Tailored business playbook and operational direction.
      3. 📱 **SMS / Dispatch Draft:** Pre-written copy with highlighted promo code and one-click copy button.
    * **Action Execution CTA:** Single-click button to register the customer as `تحت مداخله (In Treatment) ✅` across the entire session.

---

## 🧠 Behavioral Next Best Action (NBA) Playbooks

Instead of generic blanket discounting, the platform incorporates a **6-Playbook Behavioral Decision Engine** (`explorer_recommendation` in `main.py`). The engine analyzes customer signals (`Complain`, `SatisfactionScore`, `Tenure`, `DaySinceLastOrder`, `WarehouseToHome`, `CityTier`, `OrderCount`) to prescribe the exact optimal tactical response:

| # | Playbook | Trigger Criteria | Tactical Strategy | Promo Code | Discount / Incentive |
|---|---|---|---|---|---|
| 1 | **Strategic Do-Not-Disturb**<br>*(سکوت استراتژیک)* | `Risk < 50 %` AND `Complain == 0` | **Marketing Silence:** Customer is stable. Do not send promotional SMS to prevent marketing fatigue, protect margin, and preserve organic buying habits. | — | None (No SMS) |
| 2 | **Trust Restoration**<br>*(جبران تجربه نامطلوب)* | `Complain == 1` OR `SatisfactionScore ≤ 2` | **Relationship Repair:** Priority customer care outreach, guaranteed hassle-free doorstep returns, and compensation discount voucher. | `CARE20` | **20 %** compensation |
| 3 | **Streak Challenge**<br>*(تثبیت حلقه خرید دوم)* | `Tenure ≤ 2` AND `DaySinceLastOrder ≥ 4` | **Second-Order Habit Formation:** Mitigate the month-1 cliff with a gamified 5-day purchase challenge paired with wallet credit rewards. | `STREAK` | **15 %** wallet booster |
| 4 | **VIP Elevation**<br>*(ارتقای عضویت VIP)* | `Tenure ≥ 6` OR `OrderCount ≥ 3` | **Status Re-engagement:** Grant 30-day temporary VIP tier access with complimentary shipping, priority dispatch, and executive discount. | `VIP30` | **30 %** VIP privilege |
| 5 | **Smart Unbundling**<br>*(هدیه متناسب با خرید)* | `WarehouseToHome > 15` OR `CityTier ≥ 2` | **Logistics Friction Offset:** Instead of price cuts, provide a relevant complementary physical gift matching their order category to offset delivery distance. | `GIFT` | **10 %** complementary gift |
| 6 | **Time-Sensitive Winback**<br>*(مشوق بازگشت زمان‌دار)* | General Fallback for `Risk ≥ 50 %` | **Urgency Re-activation:** Deploy a 48-hour deadline voucher targeting abandoned basket items to prevent finalized attrition. | `RECOVER` | **25 %** flash credit |

---

## 🚀 Quickstart Guide

### Prerequisites
* **Python:** 3.10 or newer (tested on Python 3.12)
* **Modern Web Browser:** Chrome, Edge, Firefox, or Safari

### 1. Clone the Repository
```bash
git clone https://github.com/<USER>/<REPO>.git
cd customer_churn_project
```

### 2. Create and Activate Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

<details>
<summary>📦 View <code>requirements.txt</code> dependencies</summary>

```text
fastapi>=0.100.0
uvicorn>=0.22.0
pydantic>=2.0.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
joblib>=1.3.0
```
</details>

### 4. (Optional) Retrain or Re-export the Model
The repository includes pre-fitted weights in `models/churn_model.joblib` and stream rows in `data/test_stream_data.csv`. To retrain the Random Forest model:
```bash
python export_model.py
```

### 5. Verify Model Inference (Smoke Test)
```bash
python test_run.py
```
*Scores a sample customer profile and prints the predicted churn probability and top risk drivers.*

### 6. Launch the Server & Application
```bash
uvicorn main:app --reload --port 8000
```

### 7. Access the Dashboard
Open your browser and navigate to:
```text
http://localhost:8000
```

---

## 🗂️ Project Structure

```text
customer_churn_project/
├── main.py                     # FastAPI backend application
├── churn_inference.py          # Real-time ML inference engine & additive driver attribution
├── export_model.py             # Reproducible training pipeline: preprocessing, fitting & bundle export
├── test_run.py                 # Smoke test script for backend inference verification
├── requirements.txt            # Python package dependencies (FastAPI, Uvicorn, scikit-learn, etc.)
├── README.md                   # System documentation and operational manual
│
├── static/                     # Single Page Application 
│   ├── index.html              # Dashboard semantic layout, modal structure & view containers
│   ├── style.css               # Enterprise design system (#C4D5F9, #3157B7, responsive layout)
│   ├── app.js                  # Client state manager, API fetch controllers, Chart.js renderers
│   └── chart.umd.min.js        # Local Chart.js library for independent offline graph rendering
│
├── data/                       # Dataset storage
│   ├── E-Commerce-Dataset.csv  # Raw training dataset (5,630 e-commerce records)
│   └── test_stream_data.csv    # 200 held-out test customer records for live streaming
│
├── models/                     # Serialized artifacts
│   └── churn_model.joblib      # Random Forest model bundle + imputation medians + IQR bounds
│
└── notebooks/                  # Research & EDA
    └── churn_porject.ipynb     # Exploratory analysis notebook documenting statistical findings
```

---

<div align="center">
  <sub>Developed for Enterprise Machine Learning Deployment & Churn Mitigation Operations</sub>
</div>
