<div align="center">

# Customer Churn Intelligence & Management System

### سامانه تحلیل هوشمند و مدیریت ریزش مشتری

**Enterprise-Grade Churn Early Warning · AI Behavioral Diagnosis · Automated Next Best Action (NBA)**

[Executive Summary](#-executive-summary--the-business-problem) ·
[System Architecture](#️-system-architecture--pipeline) ·
[Integration Gateway](#-plug-and-play-integration-gateway) ·
[Dashboard Features](#-key-dashboard-features) ·
[Behavioral Playbooks](#-behavioral-next-best-action-nba-playbooks) ·
[Quickstart Guide](#-quickstart-guide) ·
[Project Structure](#️-project-structure)

</div>

---

## Executive Summary & The Business Problem

Many e-commerce stores and subscription businesses only discover customer churn **after customers stop purchasing**. By that time, the money spent to get that customer has already been used, and bringing them back can be difficult and expensive.

This platform analyzes behavioral customer signals to **identify churn risks long** before customers leave. Using machine learning, it predicts the risk of leaving, pinpoints the main reason behind that risk, and recommends one of **practical retention actions (Next Best Action - NBA)**. This allows marketing, support, and sales teams to step in early and protect business revenue.

### What the Data Reveals (5,630 Customers)

| Finding | What the Data Shows | What It Means for Business |
|---|---|---|
| **Baseline Churn** | **16.84%** of customers left (948 out of 5,630). | Keeping existing customers is the fastest way to protect profit margins. |
| **Complaint Multiplier** | Customers with complaints churn at **31.7%** vs. **10.9%** without (about **3× higher**). Over half of all lost customers had complained. | Solving customer complaints quickly is critical to preventing churn. |
| **First-Month Cliff** | **51.8%** of customers leave in their first month, making up **65.5%** of all lost customers. | The first 30 days and securing the second purchase determine long-term loyalty. |
| **Satisfaction Paradox** | Customers giving a top score of 5/5 churn at **23.8%**, compared to **11.5%** for those scoring 1/5. | Survey scores can be misleading; watching real buying behavior is much more reliable. |
| **Category Risk** | Mobile phones: **27.4%** churn · Fashion: **15.5%** · Laptops: **10.2%** · Grocery: **4.9%**. | Electronics face quick brand-switching, while grocery shoppers build stronger daily habits. |
| **Delivery & Rewards** | Churn rises from **13.5%** to **20.4%** as distance grows, but drops to **10.2%** when cashback rewards increase. | Slow or costly delivery drives customers away; cashback rewards keep them coming back. |

---

## 🏗️ System Architecture & Pipeline

The system uses a fast and lightweight **Client-Server setup**:
* **Backend:** Built with **FastAPI** (Python) for quick data processing and real-time model scoring.

* **Frontend:** A responsive **Single Page Application (SPA)** using clean HTML, modern CSS, and Chart.js for smooth data visualization.

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
 │      ├── static/style.css    (Enterprise UI design system)                         │
 │      └── static/app.js       (Reactive state, Chart.js charts, modal controller)   │
 └────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Consistent Data Processing:** All data-cleaning rules, category mappings, and average values are saved directly inside the model file (`models/churn_model.joblib`). This ensures the live system processes incoming customer data exactly the same way it was trained, preventing errors and data mismatches.
2. **Clear & Fast Explainability:** Instead of using heavy, slow external libraries, the system uses a fast, built-in method in NumPy to explain predictions. It instantly shows the exact percentage impact of each reason causing the customer's churn risk.
3. **Actionable Risk Levels:** Customers are grouped into three simple, practical categories:
   * 🟢 **Stable / Low Risk (`Risk < 35%`):** Healthy, regular shoppers who do not need promotional messages, helping protect profit margins.
   * 🟠 **Warning (`35% ≤ Risk ≤ 70%`):** Customers showing early warning signs who need a timely reminder or offer.
   * 🔴 **Critical (`Risk > 70%`):** Customers very likely to leave who require immediate attention and high-priority recovery actions.

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

## Plug-and-Play Integration Gateway

This platform is engineered not as an isolated data silo, but as a modular intelligence layer built to seamlessly plug into any existing business ecosystem, IT stack, or operational workflow:

1. **Real-Time REST API & Webhooks (Super Fast < 80ms):**
   * Built for online stores and cloud CRMs.
   * Checks customer risk instantly when an event happens (such as a customer filing a complaint, abandoning a cart, or stopping purchases) and sends immediate alerts back to your CRM or marketing system.

2. **Safe Database Sync (For Accounting & ERP Systems):**
   * Connects safely to popular business databases (SQL Server, MySQL, PostgreSQL, Oracle).
   * Runs an automatic, read-only check each night to score all customer accounts without slowing down daily business operations.

3. **Simple Excel / CSV Upload (No Coding Needed):**
   * Made for sales, marketing, and support teams without technical skills.
   * Simply upload a customer spreadsheet to instantly receive a list of customers grouped by risk level, clear reasons for each risk, and ready-to-send SMS messages with discount codes.

---

## ✨Key Dashboard Features

The web application is structured into **three operational tabs**, catering to executive stakeholders, marketing retention teams, and frontline account managers:

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                     DASHBOARD NAVIGATION TABS                          │
 ├─────────────────────────┬────────────────────────┬─────────────────────┤
 │  📊 تحلیل‌های استراتژیک  │  ⚡ رادار و آزمایشگاه  │  📋 فهرست مشتریان  │
 │  Strategic Intelligence │  Live Radar & Lab      │  Customer Directory │
 │                         │  & Customer Retention  │  & 360° Dossier     │
 └─────────────────────────┴────────────────────────┴─────────────────────┘
```

---

### Tab 1 — Strategic Intelligence (Executive View)

* **Key Business KPIs:** Shows the **16.84% baseline churn** (948 lost customers), overall model accuracy (**98.0%**), and an interactive slider to estimate revenue lost to churn.
* **5 Key Behavioral Analyses:**
  1. *Satisfaction Paradox:* Explains why 5/5 rated customers still leave.
  2. *Complaint Impact:* Unresolved complaints raise churn risk by nearly **3×**.
  3. *Month-One Cliff:* **65.5%** of all churn happens within the first 30 days.
  4. *Category Risk:* High churn in **Mobile Phones (27.4%)** vs. high loyalty in **Groceries (4.9%)**.
  5. *Delivery & Cashback:* Farther shipping distance increases churn; higher cashback reduces it.
* **Action Roadmap:** Practical steps tailored for Marketing, Support, Logistics, and Loyalty teams.

---

### Tab 2 — Live Radar & Customer Evaluation Lab

* **Live Customer Radar:** Automatically scans **2 incoming customer profiles every 6 seconds**, showing their live churn probability and risk tier (🔴 Critical, 🟠 Warning, 🟢 Stable). Clicking any card opens their full profile.
* **Interactive Customer Evaluation Form:** Test any customer situation in real time:
  * **Quick Demo Scenarios:** One-click presets for *Unhappy Customer*, *Stable Customer*, or *Inactive Customer*.
  * **Instant AI Output:** Displays the predicted churn risk, root-cause friction point, estimated annual value of keeping them, and a ready-to-send SMS with an action code.

---

### Tab 3 — Customer 360° Directory & Action Hub

* **Customer Directory Table:**
  * Search by Customer ID and filter by risk level (Critical, Warning, Stable).
  * Color-coded risk badges and action recommendations.
  * Tracks customer progress: `Pending` vs. `In Treatment`.
* **Interactive 360° Customer Dossier:** Click **"مشاهده پرونده"** to view a two-column profile:
  * **Right Panel:** A complete breakdown of customer identity, order history, and app activity.
  * **Left Panel (AI Action Center):**
    * *Stable Customers (< 35%):* **"Strategic Silence"** — no marketing SMS sent, protecting profit margins and avoiding customer annoyance.
    * *At-Risk Customers (≥ 35%):* Surfaces the main reason for leaving, the recommended business strategy, and a pre-written SMS with an activation code.
    * **Action Button:** Instantly flags the customer as `Under Intervention (In Treatment) ✅`.

---

## Behavioral Next Best Action (NBA) Playbooks

Instead of sending generic blanket discounts that waste profit margins, the platform uses a **6-Playbook Decision Engine** (`explorer_recommendation` in `main.py`). It analyzes real behavioral signals to choose the most effective, margin-safe retention action:

| # | Playbook | When It Triggers | Business Strategy | Action / Code |
|---|---|---|---|---|
| 1 | **Strategic Do-Not-Disturb**<br>*(سکوت استراتژیک)* | `Risk < 35%` · `Complain == 0` · `Days < 15` | **Marketing Silence:** Customer is buying naturally. Avoid promotional spam to protect profit margins and brand value. | *No message / No discount* |
| 2 | **Trust Restoration**<br>*(جبران تجربه نامطلوب)* | `Complain == 1` OR `Score ≤ 2` | **Relationship Repair:** Service failure is the #1 churn driver. Solve emotional friction with a doorstep return guarantee and proactive care. | `CARE20` (20% goodwill voucher) |
| 3 | **Streak Challenge**<br>*(تثبیت حلقه خرید دوم)* | `Tenure ≤ 2 mos` · `Days ≥ 4` | **Habit Formation:** 65.5% of churn happens in month 1. A 5-day purchase challenge builds a repeat buying routine. | `STREAK` (Wallet credit reward) |
| 4 | **VIP Elevation**<br>*(ارتقای عضویت VIP)* | `Tenure ≥ 6 mos` OR `Orders ≥ 3` | **Status Re-engagement:** High-value customers rarely leave over price. A 30-day Gold VIP pass and recognition make them feel valued. | `VIP30` (30% VIP privilege) |
| 5 | **Smart Unbundling**<br>*(هدیه متناسب با خرید)* | `Distance > 15 km` OR `Tier ≥ 2` | **Offsetting Delivery Friction:** Distant shipping adds friction. A free matching physical gift delights the customer without devaluing product price. | `GIFT` (Complementary gift) |
| 6 | **Time-Sensitive Winback**<br>*(مشوق بازگشت زمان‌دار)* | `Days ≥ 15` OR `Risk ≥ 35%` | **Urgency Reactivation:** Inactive buyers need immediate motivation. A 48-hour expiring voucher restarts stalled purchasing habits. | `RECOVER` (25% flash credit) |

---

## 🚀 Quickstart Guide

### Prerequisites
* **Python:** 3.10 or newer (tested on Python 3.12)
* **Modern Web Browser:** Chrome, Edge, Firefox, or Safari

### 1. Clone the Repository
```bash
git clone https://github.com/Arshia-Rasouli/customer_churn.git
cd customer_churn
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
The repository includes pre-fitted weights in `models/churn_model.joblib` and evaluation records in `data/test_stream_data.csv`. To retrain the Random Forest model:
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

## Project Structure

```text
customer_churn_project/
├── main.py                     # FastAPI backend application & NBA recommendation engine
├── churn_inference.py          # Real-time ML inference engine & additive driver attribution
├── export_model.py             # Reproducible training pipeline: preprocessing, fitting & bundle export
├── test_run.py                 # Smoke test script for backend inference verification
├── requirements.txt            # Python package dependencies (FastAPI, Uvicorn, scikit-learn, etc.)
├── README.md                   # System documentation and operational manual
│
├── static/                     # Single Page Application (SPA) frontend
│   ├── index.html              # Dashboard semantic layout, modal structure & view containers
│   ├── style.css               # Enterprise UI design system (#C4D5F9, #3157B7, responsive layout)
│   ├── app.js                  # Client state manager, API fetch controllers, Chart.js renderers
│   └── chart.umd.min.js        # Local Chart.js library for offline graph rendering
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
