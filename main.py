"""
main.py
=======
Backend server for the Customer Churn Analysis & Retention Management System.
Built with FastAPI, replacing Streamlit with an industrial Client-Server architecture.

Endpoints:
    GET  /api/insights     -> Strategic data & insights from the historical dataset (DATASET dict)
    GET  /api/radar        -> Live radar: 2 random customers scored with predict_single_customer
    POST /api/evaluate     -> Customer evaluation lab: scores custom inputs and suggests retention SMS
    GET  /api/customers    -> Full list of 200 stream customers with churn scores and 360 profiles
    POST /api/action       -> Register an action for a customer ID or lab scenario
    GET  /                 -> Serves static/index.html
"""

from __future__ import annotations

import html
import random
import sys
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure local imports work reliably
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from churn_inference import predict_single_customer

# --------------------------------------------------------------------------- #
# Paths & Constants
# --------------------------------------------------------------------------- #
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"

MODEL_PATH = MODELS_DIR / "churn_model.joblib"
STREAM_PATH = DATA_DIR / "test_stream_data.csv"

DEFAULT_STORE = "کسب‌وکار شما"
RED_FROM = 70.0
AMBER_FROM = 35.0

# Category mappings
CATEGORY_FA = {
    "Mobile Phone": "موبایل و دیجیتال",
    "Mobile": "موبایل و دیجیتال",
    "Laptop & Accessory": "لپ‌تاپ و تجهیزات",
    "Laptop and Accessory": "لپ‌تاپ و تجهیزات",
    "Laptop Accessory": "لپ‌تاپ و تجهیزات",
    "Fashion": "مد و پوشاک",
    "Grocery": "خواربار",
    "Others": "سایر",
}

PAYMENT_FA = {
    "Debit Card": "کارت بانکی",
    "Credit Card": "کارت بانکی",
    "CC": "کارت بانکی",
    "E wallet": "کیف پول الکترونیکی",
    "Cash on Delivery": "پرداخت در محل",
    "COD": "پرداخت در محل",
    "UPI": "درگاه اینترنتی",
}

COLUMN_FA = {
    "PreferredLoginDevice": "دستگاه ورود",
    "PreferredPaymentMode": "روش پرداخت",
    "Gender": "جنسیت",
    "PreferedOrderCat": "دسته خرید",
    "MaritalStatus": "وضعیت تأهل",
}

VALUE_FA = {
    "Mobile Phone": "موبایل",
    "Phone": "تلفن",
    "Computer": "رایانه",
    "Male": "مرد",
    "Female": "زن",
    "Single": "مجرد",
    "Married": "متأهل",
    "Divorced": "جداشده",
    "Laptop & Accessory": "لپ‌تاپ و تجهیزات",
    "Laptop and Accessory": "لپ‌تاپ و تجهیزات",
    "Laptop Accessory": "لپ‌تاپ و تجهیزات",
    "Fashion": "مد و پوشاک",
    "Grocery": "خواربار",
    "Others": "سایر",
}

LOGIN_FA = {
    "Mobile Phone": "موبایل",
    "Phone": "موبایل",
    "Computer": "رایانه",
}

CATEGORY_ANNUAL_VALUE = {
    "Mobile Phone": 60_000_000,
    "Laptop & Accessory": 90_000_000,
    "Fashion": 40_500_000,
    "Grocery": 30_000_000,
    "Others": 30_500_000,
}

LAB_OFFERS = {
    "red": {"discount": 10, "code": "VIP-CARE10", "tag": "تخفیف ویژه دلجویی", "css": "gold"},
    "amber": {"discount": 5, "code": "RETURN5", "tag": "تخفیف یادآوری", "css": "silver"},
}

SCENARIOS = {
    "complaint": {"label": "پیگیری و جبران شکایت", "prefix": "JOBRAN", "discount": 30},
    "newbie": {"label": "خوش‌آمدگویی و مشوق خرید دوم", "prefix": "KHOSHAMAD", "discount": 15},
    "gap": {"label": "دعوت به بازگشت با ارسال رایگان", "prefix": "BAZGASHT", "discount": 0},
    "general": {"label": "پیشنهاد بازگشت مشتری", "prefix": "VAFADARI", "discount": 10},
}

STATUS_LABEL = {"red": "بحرانی", "amber": "هشدار", "green": "پایدار"}

DATASET = {
    "n": 5630,
    "churned": 948,
    "retained": 4682,
    "churn_rate": 16.84,
    "detection_power": 99.8,
    "accuracy": 98.0,
    "satisfaction": {1: 11.5, 2: 12.6, 3: 17.2, 4: 17.1, 5: 23.8},
    "complain": {"بدون شکایت": 10.9, "دارای شکایت": 31.7},
    "complain_share_of_churners": 53.6,
    "complain_customers": 1604,
    "tenure": {"۰ تا ۱ ماه": 51.8, "۲ تا ۳ ماه": 8.8, "۴ تا ۶ ماه": 7.5, "۷ تا ۱۲ ماه": 9.8, "بیش از ۱۲ ماه": 5.0},
    "tenure_mean_loyal": 11.4,
    "tenure_mean_churned": 3.9,
    "first_month_share_of_churners": 65.5,
    "category": {"Mobile Phone": 27.4, "Fashion": 15.5, "Laptop & Accessory": 10.2, "Others": 7.6, "Grocery": 4.9},
    "cashback_rate": [29.5, 20.3, 12.2, 10.2],
    "cashback_bounds_raw": [130, 160, 200],
    "cashback_mean_loyal_raw": 178.4,
    "cashback_mean_churned_raw": 159.6,
    "distance": {"تا ۱۰": 13.5, "۱۱ تا ۲۰": 17.6, "بیش از ۲۰": 20.4},
    "recency": {"۰ تا ۲ روز": 24.9, "بیش از ۱۰ روز": 6.2},
}

SATISFACTION_COUNTS = {
    1: {"loyal": 1030, "churned": 134},
    2: {"loyal": 512, "churned": 74},
    3: {"loyal": 1406, "churned": 292},
    4: {"loyal": 890, "churned": 184},
    5: {"loyal": 844, "churned": 264},
}

PROFILE_FIELDS = [
    "CityTier", "WarehouseToHome", "HourSpendOnApp", "NumberOfDeviceRegistered", "SatisfactionScore",
    "NumberOfAddress", "OrderAmountHikeFromlastYear", "CouponUsed", "OrderCount", "CashbackAmount",
    "PreferredLoginDevice", "PreferredPaymentMode", "Gender", "MaritalStatus"
]

SEGMENT_PROFILES = {
    ('Mobile Phone', 0, 'new'): (1.0, 14.0, 3.0, 4.0, 3.0, 3.0, 15.0, 1.0, 2.0, 144.0, 'Phone', 'Credit Card', 'Male', 'Single'),
    ('Mobile Phone', 0, 'mid'): (1.0, 13.0, 3.0, 4.0, 3.0, 3.0, 15.0, 1.0, 2.0, 137.0, 'Phone', 'Debit Card', 'Male', 'Married'),
    ('Mobile Phone', 0, 'old'): (1.0, 14.0, 3.0, 4.0, 3.0, 5.0, 15.0, 1.0, 2.0, 148.0, 'Phone', 'Debit Card', 'Male', 'Married'),
    ('Mobile Phone', 1, 'new'): (1.0, 13.0, 3.0, 4.0, 3.0, 3.0, 14.0, 1.0, 2.0, 146.0, 'Phone', 'Debit Card', 'Male', 'Single'),
    ('Mobile Phone', 1, 'mid'): (1.0, 12.0, 3.0, 4.0, 3.0, 3.0, 14.0, 1.0, 2.0, 132.0, 'Phone', 'Debit Card', 'Male', 'Married'),
    ('Mobile Phone', 1, 'old'): (1.0, 13.0, 3.0, 4.0, 3.0, 5.0, 15.0, 1.0, 2.0, 148.0, 'Phone', 'Credit Card', 'Male', 'Married'),
    ('Fashion', 0, 'new'): (3.0, 16.0, 3.0, 4.0, 3.0, 3.0, 13.0, 1.0, 2.0, 200.5, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Fashion', 0, 'mid'): (1.0, 14.0, 3.0, 4.0, 3.0, 3.0, 15.0, 2.0, 2.5, 205.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Fashion', 0, 'old'): (1.0, 13.0, 3.0, 4.0, 3.0, 5.0, 15.0, 2.0, 2.5, 210.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Fashion', 1, 'new'): (2.0, 20.5, 3.0, 4.0, 3.0, 3.0, 15.5, 2.0, 3.5, 216.0, 'Mobile Phone', 'Cash on Delivery', 'Male', 'Married'),
    ('Fashion', 1, 'mid'): (1.0, 16.0, 3.0, 4.0, 3.0, 3.0, 14.0, 1.0, 2.0, 208.5, 'Mobile Phone', 'Debit Card', 'Female', 'Married'),
    ('Fashion', 1, 'old'): (1.0, 13.0, 3.0, 4.0, 3.0, 5.0, 15.0, 1.0, 2.0, 209.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Laptop & Accessory', 0, 'new'): (3.0, 15.0, 3.0, 4.0, 3.0, 3.0, 16.0, 1.0, 2.0, 165.0, 'Mobile Phone', 'Debit Card', 'Male', 'Single'),
    ('Laptop & Accessory', 0, 'mid'): (1.0, 14.0, 3.0, 4.0, 3.0, 3.0, 15.0, 1.0, 2.0, 168.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Laptop & Accessory', 0, 'old'): (1.0, 14.0, 3.0, 4.0, 3.0, 4.0, 15.0, 1.0, 2.0, 167.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Laptop & Accessory', 1, 'new'): (3.0, 16.0, 3.0, 4.0, 3.0, 3.0, 14.0, 1.0, 2.0, 167.0, 'Mobile Phone', 'E wallet', 'Male', 'Married'),
    ('Laptop & Accessory', 1, 'mid'): (1.0, 15.0, 3.0, 4.0, 3.0, 3.0, 14.0, 1.0, 2.0, 168.0, 'Mobile Phone', 'Debit Card', 'Female', 'Married'),
    ('Laptop & Accessory', 1, 'old'): (1.0, 14.0, 3.0, 4.0, 3.0, 4.0, 15.5, 1.0, 2.0, 166.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Grocery', 0, 'new'): (1.0, 10.0, 3.0, 4.0, 3.0, 5.0, 15.0, 2.0, 4.0, 270.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Grocery', 0, 'mid'): (1.0, 15.0, 3.0, 4.0, 3.0, 5.0, 12.0, 5.0, 6.0, 262.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Grocery', 0, 'old'): (1.0, 10.0, 3.0, 4.0, 3.0, 4.0, 15.0, 2.0, 4.0, 271.0, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Grocery', 1, 'new'): (1.0, 18.0, 3.0, 4.0, 3.0, 4.0, 14.0, 2.0, 3.0, 263.5, 'Mobile Phone', 'Credit Card', 'Female', 'Married'),
    ('Grocery', 1, 'mid'): (1.0, 18.0, 3.0, 4.0, 3.0, 4.0, 14.0, 2.0, 3.0, 263.5, 'Mobile Phone', 'Credit Card', 'Female', 'Married'),
    ('Grocery', 1, 'old'): (1.0, 15.0, 3.0, 4.0, 3.0, 4.0, 14.0, 2.0, 3.0, 264.0, 'Mobile Phone', 'Credit Card', 'Female', 'Married'),
    ('Others', 0, 'new'): (1.0, 11.0, 3.0, 4.0, 3.0, 4.0, 14.0, 2.0, 4.0, 302.5, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Others', 0, 'mid'): (1.0, 11.0, 3.0, 4.0, 3.0, 4.0, 14.0, 2.0, 4.0, 302.5, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Others', 0, 'old'): (1.0, 11.0, 3.0, 4.0, 3.0, 4.0, 14.0, 2.0, 4.0, 305.5, 'Mobile Phone', 'Debit Card', 'Male', 'Married'),
    ('Others', 1, 'new'): (1.0, 9.0, 3.0, 4.0, 3.5, 5.0, 14.0, 2.0, 2.0, 303.0, 'Mobile Phone', 'Credit Card', 'Male', 'Married'),
    ('Others', 1, 'mid'): (1.0, 9.0, 3.0, 4.0, 3.5, 5.0, 14.0, 2.0, 2.0, 303.0, 'Mobile Phone', 'Credit Card', 'Male', 'Married'),
    ('Others', 1, 'old'): (1.0, 9.0, 3.0, 4.0, 3.0, 5.0, 14.0, 2.0, 2.0, 309.5, 'Mobile Phone', 'Credit Card', 'Male', 'Married'),
}

CATEGORY_RESOLVER = {
    "موبایل و دیجیتال": "Mobile Phone",
    "دیجیتال": "Mobile Phone",
    "تلفن همراه": "Mobile Phone",
    "Mobile Phone": "Mobile Phone",
    "Mobile": "Mobile Phone",
    "Phone": "Mobile Phone",
    "مد و پوشاک": "Fashion",
    "پوشاک": "Fashion",
    "Fashion": "Fashion",
    "سوپرمارکت و خواربار": "Grocery",
    "سوپرمارکت": "Grocery",
    "خواربار": "Grocery",
    "Grocery": "Grocery",
    "لپ‌تاپ و تجهیزات": "Laptop & Accessory",
    "لپ‌تاپ": "Laptop & Accessory",
    "Laptop & Accessory": "Laptop & Accessory",
    "Laptop and Accessory": "Laptop & Accessory",
    "Laptop Accessory": "Laptop & Accessory",
    "سایر": "Others",
    "Others": "Others",
}

# --------------------------------------------------------------------------- #
# Helper Functions
# --------------------------------------------------------------------------- #
def tone_of(risk: float) -> str:
    if risk >= RED_FROM:
        return "red"
    if risk >= AMBER_FROM:
        return "amber"
    return "green"


def cat_fa(raw: Any) -> str:
    if raw is None or pd.isna(raw):
        return "نامشخص"
    s = str(raw).strip()
    return CATEGORY_FA.get(s, s)


def pay_fa(raw: Any) -> str:
    if raw is None or pd.isna(raw):
        return "نامشخص"
    return PAYMENT_FA.get(str(raw).strip(), "سایر")


def tenure_bucket(months: int) -> str:
    return "new" if months <= 1 else "mid" if months <= 12 else "old"


def segment_profile(category_raw: str, complain: int, tenure_months: int) -> dict:
    bucket = tenure_bucket(int(tenure_months))
    profile = SEGMENT_PROFILES.get((category_raw, int(complain), bucket))
    if profile is None:
        profile = SEGMENT_PROFILES.get((category_raw, int(complain), "mid"))
    if profile is None:
        profile = SEGMENT_PROFILES.get(("Mobile Phone", int(complain), bucket))
    return dict(zip(PROFILE_FIELDS, profile))


def input_scenario(tenure_months: int, complain: int, days: int) -> str:
    if complain:
        return "complaint"
    if tenure_months <= 6:
        return "newbie"
    if days >= 20:
        return "gap"
    return "general"


def cash_toman(raw_value: Any) -> str:
    if raw_value is None or pd.isna(raw_value):
        return "ثبت نشده"
    try:
        val = float(raw_value) * 2000
        return f"{int(round(val)):,} تومان"
    except Exception:
        return "ثبت نشده"


def describe_driver(driver: dict) -> dict:
    feature, value = str(driver["feature"]), driver["value"]
    num = value if isinstance(value, (int, float)) else 0

    if " != " in feature or " = " in feature:
        sep = " != " if " != " in feature else " = "
        col, val = feature.split(sep, 1)
        shown = pay_fa(val) if col == "PreferredPaymentMode" else VALUE_FA.get(val, val)
        label = f"{COLUMN_FA.get(col, col)}: {shown}"
        return {"title": label if sep == " = " else f"غیر از «{label}»", "detail": "الگوی رفتاری پرریسک"}

    table = {
        "Tenure": ("سابقهٔ کم همراهی", f"{int(num)} ماه همراهی"),
        "Complain": ("ثبت شکایت", "شکایت بدون پاسخ رضایت‌بخش" if num >= 1 else "بدون شکایت"),
        "WarehouseToHome": ("فاصلهٔ زیاد تا انبار", f"حدود {int(num)} کیلومتر"),
        "DaySinceLastOrder": ("فاصله از آخرین خرید", f"{int(num)} روز از آخرین سفارش"),
        "avg_cashbk_per_order": ("میانگین بازگشت وجه هر سفارش", cash_toman(num)),
        "CashbackAmount": ("بازگشت وجه", cash_toman(num)),
        "SatisfactionScore": ("الگوی رضایت", f"امتیاز {int(num)} از ۵"),
        "OrderCount": ("تعداد سفارش اندک", f"{int(num)} سفارش"),
        "CouponUsed": ("استفادهٔ کم از کوپن", f"{int(num)} کوپن"),
        "HourSpendOnApp": ("زمان کم در اپلیکیشن", f"حدود {int(num)} ساعت"),
        "NumberOfDeviceRegistered": ("تعداد دستگاه ثبت‌شده", f"{int(num)} دستگاه"),
        "NumberOfAddress": ("تعداد آدرس ثبت‌شده", f"{int(num)} آدرس"),
        "CityTier": ("سطح شهر", f"سطح {int(num)}"),
        "OrderAmountHikeFromlastYear": ("تغییر مبلغ سفارش", f"{int(num)}٪ نسبت به پارسال"),
    }
    title, detail = table.get(feature, ("عامل رفتاری", "الگوی مشابه مشتریان ریزشی"))
    return {"title": title, "detail": detail}


def pick_scenario(drivers: list[dict]) -> tuple[str, dict | None]:
    for d in drivers:
        f, v = d["feature"], d["value"]
        if f == "Complain" and v >= 1:
            return "complaint", d
        if f == "Tenure" and v <= 12:
            return "newbie", d
        if f == "DaySinceLastOrder" and v >= 5:
            return "gap", d
    return "general", None


def build_offer_sms(scenario: str, store: str, coupon: str, discount: int) -> str:
    d = discount
    if scenario == "complaint":
        return (
            f"مشتری گرامی، بابت تجربه‌ای که داشتید از طرف {store} صمیمانه عذرخواهی می‌کنیم.\n"
            f"رضایت شما برای ما اهمیت دارد و خوشحال می‌شویم فرصت دوباره‌ای برای جبران این تجربه داشته باشیم.\n"
            f"برای خرید بعدی، {d}٪ تخفیف ویژه برای شما در نظر گرفته‌ایم.\n"
            f"کافی است هنگام ثبت سفارش، کد تخفیف زیر را وارد کنید و از پیشنهاد ویژه خود استفاده کنید.\n"
            f"کد تخفیف: {coupon}\n"
            f"منتظر دیدار دوباره شما هستیم."
        )
    if scenario == "newbie":
        return (
            f"خوشحالیم که شما را در جمع مشتریان {store} داریم.\n"
            f"برای اینکه دوباره تجربه خریدی لذت‌بخش داشته باشید، {d}٪ تخفیف ویژه برای خرید بعدی شما در نظر گرفته‌ایم.\n"
            f"کافی است هنگام ثبت سفارش، کد تخفیف زیر را وارد کنید و از پیشنهاد ویژه خود استفاده کنید.\n"
            f"کد تخفیف: {coupon}\n"
            f"منتظر دیدار دوباره شما هستیم."
        )
    if scenario == "gap":
        return (
            f"مدتی است شما را در {store} ندیده‌ایم و خوشحال می‌شویم دوباره میزبان شما باشیم.\n"
            f"برای بازگشت شما، {d}٪ تخفیف ویژه برای خرید بعدی در نظر گرفته‌ایم.\n"
            f"کافی است هنگام ثبت سفارش، کد تخفیف زیر را وارد کنید و از پیشنهاد ویژه خود استفاده کنید.\n"
            f"کد تخفیف: {coupon}\n"
            f"منتظر دیدار دوباره شما هستیم."
        )
    return (
        f"از همراهی شما با {store} سپاسگزاریم.\n"
        f"برای اینکه دوباره تجربه خریدی لذت‌بخش داشته باشید، {d}٪ تخفیف ویژه برای خرید بعدی شما در نظر گرفته‌ایم.\n"
        f"کافی است هنگام ثبت سفارش، کد تخفیف زیر را وارد کنید و از پیشنهاد ویژه خود استفاده کنید.\n"
        f"کد تخفیف: {coupon}\n"
        f"منتظر دیدار دوباره شما هستیم."
    )


def retention_value(category_raw: str, risk: float) -> int:
    annual_val = CATEGORY_ANNUAL_VALUE.get(category_raw, 35_000_000)
    return int(round(annual_val * risk / 100 / 10_000) * 10_000)


def explorer_recommendation(
    risk: float,
    drivers: list = None,
    store_name: str = DEFAULT_STORE,
    features: dict = None
) -> dict:
    """
    Next Best Action (NBA) 5-Dimensional Behavioral Decision Engine.
    Evaluates: Complain, SatisfactionScore, Tenure, WarehouseToHome, CityTier, OrderCount, DaySinceLastOrder, and Risk.
    Returns one of the 5 strategic behavioral playbooks:
      1. VIP Status Elevation (ارتقای آنی به سطح طلایی)
      2. Trust Restoration (ضمانت طلایی مرجوعی در محل)
      3. Gamified Streak Challenge (ماموریت چالش خرید با پاداش صعودی)
      4. Smart Unbundling (بسته محصول هدیه مکمل همصنف)
      5. Strategic Do-Not-Disturb (سکوت استراتژیک و منع تبلیغات)
    """
    drivers = drivers or []
    feats = features or {}

    # Extract behavioral signals from features (or drivers fallback)
    complain = int(feats.get("Complain") or 0)
    sat = float(feats.get("SatisfactionScore") or 3.0)
    tenure = float(feats.get("Tenure") or 0.0)
    w_to_h = float(feats.get("WarehouseToHome") or 0.0)
    tier = int(float(feats.get("CityTier") or 1))
    order_count = float(feats.get("OrderCount") or 1.0)
    days = float(feats.get("DaySinceLastOrder") or 0.0)

    # If features was empty, infer available factors from drivers
    if not feats and drivers:
        for d in drivers:
            f, v = str(d.get("feature", "")), d.get("value")
            if f == "Complain" and v is not None:
                complain = int(v)
            elif f == "SatisfactionScore" and v is not None:
                sat = float(v)
            elif f == "Tenure" and v is not None:
                tenure = float(v)
            elif f == "WarehouseToHome" and v is not None:
                w_to_h = float(v)
            elif f == "CityTier" and v is not None:
                tier = int(float(v))
            elif f == "OrderCount" and v is not None:
                order_count = float(v)
            elif f == "DaySinceLastOrder" and v is not None:
                days = float(v)

    # 1. Strategic Do-Not-Disturb (Stable Customers: Risk < 50% and Complain == 0)
    if risk < 35.0 and complain == 0:
        return {
            "playbook_id": "do_not_disturb",
            "playbook_title": "سکوت استراتژیک",
            "playbook_badge": "سکوت استراتژیک",
            "playbook_badge_fa": "سکوت استراتژیک",
            "root_cause_short": "مشتری پایدار، کم‌ریسک و بدون نشانه نارضایتی",
            "strategy": "حفظ تجربه فعلی مشتری بدون ارسال پیشنهاد تبلیغاتی غیرضروری",
            "strategy_desc": "برای این مشتری مداخله لازم نیست. ارتباط تبلیغاتی اضافی می‌تواند مزاحمت ایجاد کند و رفتار خرید طبیعی مشتری را تحت تأثیر قرار دهد.",
            "action": "عدم ارسال پیام تبلیغاتی",
            "action_text": "مشتری در وضعیت پایدار قرار دارد؛ فعلاً هیچ پیام تخفیف، تماس یا کمپین بازگشتی برای او فعال نشود.",
            "code": "",
            "discount": 0,
            "sms": ""
        }

    # 2. Trust Restoration (Complaint == 1 or SatisfactionScore <= 2)
    if complain == 1 or sat <= 2:
        return {
            "playbook_id": "trust_restoration",
            "playbook_title": "جبران تجربه نامطلوب / گارانتی مرجوعی در محل",
            "playbook_badge": "جبران تجربه نامطلوب",
            "playbook_badge_fa": "جبران تجربه نامطلوب",
            "root_cause_short": "شکایت ثبت‌شده یا رضایت پایین از تجربه خرید",
            "strategy": "بازسازی اعتماد با پیگیری اولویت‌دار، گارانتی مرجوعی در محل و کد CARE20",
            "strategy_desc": "ابتدا مسئله مشتری را با پیگیری اولویت‌دار حل کنید؛ سپس امکان تست کالا هنگام تحویل، گارانتی مرجوعی در محل و کد تخفیف جبرانی CARE20 را برای بازگرداندن اعتماد فعال کنید.",
            "action": "پیگیری فوری پشتیبانی و فعال‌سازی کد CARE20",
            "action_text": "ثبت مشتری در صف تماس ویژه پشتیبانی، گارانتی مرجوعی در محل و تخصیص کد جبرانی CARE20.",
            "code": "CARE20",
            "discount": 20,
            "sms": f"{store_name}: مشتری گرامی، بابت تجربه اخیر شما متأسفیم. برای جبران، ۲۰٪ تخفیف همراه با گارانتی مرجوعی در محل برای خرید بعدی شما فعال شد.\nکد: CARE20"
        }

    # 3. Gamified Streak Challenge (Tenure <= 2 and DaySinceLastOrder >= 4)
    if tenure <= 2 and days >= 4:
        return {
            "playbook_id": "streak_challenge",
            "playbook_title": "تثبیت حلقه خرید دوم (چالش ۵ روزه خرید با پاداش کیف پول)",
            "playbook_badge": "تثبیت حلقه خرید دوم",
            "playbook_badge_fa": "تثبیت حلقه خرید دوم",
            "root_cause_short": "ریسک توقف پس از سفارشات نخست",
            "strategy": "ایجاد انگیزه فوری با چالش ۵ روزه خرید با پاداش کیف پول و کد STREAK",
            "strategy_desc": "بیش از ۶۵٪ ریزش مشتریان در ماه اول رخ می‌دهد. این راهبرد با تعیین چالش ۵ روزه خرید و پاداش کیف پول، مشتری تک‌خریده را به مشتری تکرارکننده تبدیل می‌کند.",
            "action": "تخصیص اعتبار پلکانی و فعال‌سازی کد STREAK",
            "action_text": "ارسال چالش ۵ روزه خرید با پاداش کیف پول و فعال‌سازی کد STREAK.",
            "code": "STREAK",
            "discount": 15,
            "sms": f"{store_name}: از اعتمادتان سپاسگزاریم! تا ۵ روز آینده با ثبت خرید بعدی، پاداش کیف پول به همراه تخفیف ویژه برای شما فعال می‌شود.\nکد فعال‌سازی: STREAK"
        }

    # 4. VIP Status Elevation (Tenure >= 6 or OrderCount >= 3)
    if tenure >= 6 or order_count >= 3:
        return {
            "playbook_id": "vip_elevation",
            "playbook_title": "ارتقای عضویت VIP",
            "playbook_badge": "ارتقای عضویت VIP",
            "playbook_badge_fa": "ارتقای عضویت VIP",
            "root_cause_short": "کاهش فعالیت مشتری باسابقه و وفادار",
            "strategy": "ارتقای موقت به سطح VIP برای حفظ مشتری ارزشمند و جلوگیری از افت خرید",
            "strategy_desc": "برای جلوگیری از افت خرید، عضویت VIP مشتری را برای ۳۰ روز فعال کنید و مزایای ملموس مانند ارسال رایگان، پشتیبانی اولویت‌دار و تخفیف VIP ارائه دهید.",
            "action": "فعال‌سازی سطح ویژه VIP با کد VIP30",
            "action_text": "تخصیص عضویت VIP شامل ارسال رایگان، پشتیبانی اولویت‌دار و ۳۰٪ تخفیف برای خریدهای ۳۰ روز آینده.",
            "code": "VIP30",
            "discount": 30,
            "sms": f"{store_name}: برای قدردانی از همراهی شما، عضویت VIP برای ۳۰ روز فعال شد؛ با مزایایی مانند ارسال رایگان و ۳۰٪ تخفیف در خرید بعدی.\nکد: VIP30"
        }

    # 5. Smart Unbundling (WarehouseToHome > 15 or CityTier >= 2)
    if w_to_h > 15 or tier >= 2:
        return {
            "playbook_id": "smart_unbundling",
            "playbook_title": "هدیه متناسب با خرید",
            "playbook_badge": "هدیه متناسب با خرید",
            "playbook_badge_fa": "هدیه متناسب با خرید",
            "root_cause_short": "فاصله یا هزینه ارسال بالا برای مشتری",
            "strategy": "جبران اصطکاک ارسال با یک هدیه کاربردی متناسب با دسته خرید مشتری",
            "strategy_desc": "به‌جای تخفیف مستقیم، یک هدیه مکمل و کاربردی متناسب با خرید مشتری ارائه کنید تا ارزش سفارش بیشتر شود و حساسیت مشتری نسبت به زمان یا هزینه ارسال کاهش یابد.",
            "action": "فعال‌سازی هدیه مکمل با کد GIFT",
            "action_text": "هدیه متناسب با دسته خرید مشتری به‌صورت خودکار به سفارش بعدی افزوده شود و همراه سفارش ارسال گردد.",
            "code": "GIFT",
            "discount": 10,
            "sms": f"{store_name}: برای سفارش بعدی شما یک هدیه ویژه متناسب با خریدتان در نظر گرفته‌ایم که به همراه سفارش ارسال خواهد شد.\nکد هدیه: GIFT"
        }

    # 6. Time-Sensitive Re-engagement (Default Fallback for Risk >= 50%)
    return {
        "playbook_id": "winback_offer",
        "playbook_title": "مشوق بازگشت زماندار",
        "playbook_badge": "مشوق بازگشت زمان‌دار",
        "playbook_badge_fa": "مشوق بازگشت زمان‌دار",
        "root_cause_short": "کاهش نرخ تعامل و توقف موقت سفارش‌ها",
        "strategy": "ارائه مشوق مالی مشروط با مهلت محدود ۴۸ ساعته جهت ایجاد فوریت خرید",
        "strategy_desc": "برای تحریک مجدد مشتری، یک بن خرید اختصاصی با مهلت ۴۸ ساعته فعال کنید تا از تصمیم‌گیری زودهنگام مشتری برای ترک کامل پلتفرم جلوگیری شود.",
        "action": "ارسال بن بازگشت زمان‌دار با کد RECOVER",
        "action_text": "تخصیص اعتبار خرید اختصاصی با مهلت ۴۸ ساعته و یادآوری محصولات بازدیدشده در سبد خرید.",
        "code": "RECOVER",
        "discount": 25,
        "sms": f"{store_name}: دلتنگ شما هستیم! برای سبد خرید شما اعتبار اختصاصی با مهلت ۴۸ ساعته فعال شد. استفاده با کد: RECOVER"
    }



def full_info_rows(features: dict, customer_id: int) -> list[dict]:
    tier = features.get("CityTier")
    sat = features.get("SatisfactionScore")
    cash = features.get("CashbackAmount")
    order_count = features.get("OrderCount")

    tier_txt = "ثبت نشده"
    if tier is not None and not pd.isna(tier):
        try:
            t = int(float(tier))
            tier_txt = {1: "کلان‌شهر", 2: "شهرهای بزرگ", 3: "سایر مناطق"}.get(t, f"سطح {t}")
        except Exception:
            pass

    def _safe_str(val, suffix=""):
        if val is None or pd.isna(val):
            return "ثبت نشده"
        try:
            v = float(val)
            txt = f"{int(v)}" if v == int(v) else f"{round(v, 1)}"
            return f"{txt}{suffix}"
        except Exception:
            return "ثبت نشده"

    avg_cash = "ثبت نشده"
    try:
        if cash is not None and order_count is not None and float(order_count) > 0:
            avg_cash = cash_toman(float(cash) / float(order_count))
    except Exception:
        pass

    return [
        # ۱. مشخصات هویتی و جغرافیایی (Identity & Geography)
        {"label": "شناسه مشتری", "value": str(customer_id), "group": "identity", "group_title": "مشخصات هویتی و جغرافیایی"},
        {"label": "سطح شهر", "value": tier_txt, "group": "identity", "group_title": "مشخصات هویتی و جغرافیایی"},
        {"label": "فاصله تا انبار", "value": _safe_str(features.get("WarehouseToHome"), " کیلومتر"), "group": "identity", "group_title": "مشخصات هویتی و جغرافیایی"},
        {"label": "جنسیت", "value": VALUE_FA.get(str(features.get("Gender")), "ثبت نشده"), "group": "identity", "group_title": "مشخصات هویتی و جغرافیایی"},
        {"label": "وضعیت تأهل", "value": VALUE_FA.get(str(features.get("MaritalStatus")), "ثبت نشده"), "group": "identity", "group_title": "مشخصات هویتی و جغرافیایی"},
        {"label": "آدرس‌های ثبت‌شده", "value": _safe_str(features.get("NumberOfAddress")), "group": "identity", "group_title": "مشخصات هویتی و جغرافیایی"},

        # ۲. تاریخچه تراکنش و مالی (Transactions & Financial)
        {"label": "سابقه همراهی", "value": _safe_str(features.get("Tenure"), " ماه"), "group": "finance", "group_title": "تاریخچه تراکنش و مالی"},
        {"label": "دسته خرید اصلی", "value": cat_fa(features.get("PreferedOrderCat")), "group": "finance", "group_title": "تاریخچه تراکنش و مالی"},
        {"label": "روش پرداخت ترجیحی", "value": pay_fa(features.get("PreferredPaymentMode")), "group": "finance", "group_title": "تاریخچه تراکنش و مالی"},
        {"label": "تعداد کل سفارش‌ها", "value": _safe_str(features.get("OrderCount")), "group": "finance", "group_title": "تاریخچه تراکنش و مالی"},
        {"label": "فاصله از آخرین خرید", "value": _safe_str(features.get("DaySinceLastOrder"), " روز"), "group": "finance", "group_title": "تاریخچه تراکنش و مالی"},
        {"label": "میانگین کشبک هر سفارش", "value": avg_cash, "group": "finance", "group_title": "تاریخچه تراکنش و مالی"},
        {"label": "کل بازگشت وجه دریافتی", "value": cash_toman(cash), "group": "finance", "group_title": "تاریخچه تراکنش و مالی"},
        {"label": "رشد مبلغ سفارش نسبت به پارسال", "value": _safe_str(features.get("OrderAmountHikeFromlastYear"), "٪"), "group": "finance", "group_title": "تاریخچه تراکنش و مالی"},

        # ۳. رفتار اپلیکیشن و تعامل (App Behavior & Engagement)
        {"label": "شکایت در ماه اخیر", "value": "بله" if int(features.get("Complain") or 0) == 1 else "خیر", "group": "app", "group_title": "رفتار در اپلیکیشن و تعامل"},
        {"label": "امتیاز رضایت", "value": f"{int(float(sat))} از ۵" if sat is not None and not pd.isna(sat) else "ثبت نشده", "group": "app", "group_title": "رفتار در اپلیکیشن و تعامل"},
        {"label": "دستگاه ترجیحی ورود", "value": LOGIN_FA.get(str(features.get("PreferredLoginDevice")), "ثبت نشده"), "group": "app", "group_title": "رفتار در اپلیکیشن و تعامل"},
        {"label": "استفاده روزانه از اپلیکیشن", "value": _safe_str(features.get("HourSpendOnApp"), " ساعت"), "group": "app", "group_title": "رفتار در اپلیکیشن و تعامل"},
        {"label": "دستگاه‌های متصل", "value": _safe_str(features.get("NumberOfDeviceRegistered")), "group": "app", "group_title": "رفتار در اپلیکیشن و تعامل"},
    ]


# --------------------------------------------------------------------------- #
# In-Memory Database & Data Engine
# --------------------------------------------------------------------------- #
class CustomerDatabase:
    def __init__(self, stream_path: Path, model_path: Path):
        self.stream_path = stream_path
        self.model_path = model_path
        self.df = pd.DataFrame()
        self.customers_by_id: Dict[int, dict] = {}
        self.all_customers_cache: List[dict] = []
        self.registered_actions: set = set()
        self.load_data()

    def load_data(self):
        if not self.stream_path.exists():
            raise FileNotFoundError(f"Stream dataset not found at {self.stream_path}")
        if not self.model_path.exists():
            raise FileNotFoundError(f"Trained model not found at {self.model_path}")

        df = pd.read_csv(self.stream_path)
        df["CustomerID"] = df["CustomerID"].astype(int)
        self.df = df

        # Fill display medians for stable presentation
        display_df = df.copy()
        for col in display_df.select_dtypes(include=[np.number]).columns:
            display_df[col] = display_df[col].fillna(display_df[col].median())

        def _clean_val(v):
            if v is None:
                return None
            if hasattr(v, "item"):
                v = v.item()
            if isinstance(v, float) and (np.isnan(v) or not np.isfinite(v)):
                return None
            return v

        scored_list = []
        for raw_row, disp_row in zip(df.to_dict("records"), display_df.to_dict("records")):
            cid = int(raw_row["CustomerID"])
            raw_features = {k: _clean_val(v) for k, v in raw_row.items() if k not in {"CustomerID", "Churn"}}
            disp_features = {k: _clean_val(v) for k, v in disp_row.items() if k not in {"CustomerID", "Churn"}}

            # Perform prediction using raw_features (churn_inference handles missing values using model training medians)
            result = predict_single_customer(raw_features, model_path=self.model_path)
            risk = float(result["churn_probability_pct"])
            tone = tone_of(risk)

            drivers = [{**d, **describe_driver(d)} for d in result["top_risk_drivers"]]
            scenario, trigger = pick_scenario(drivers)
            rec = explorer_recommendation(risk, drivers, DEFAULT_STORE, features=disp_features)
            modal_cards = full_info_rows(disp_features, cid)

            c_dict = {
                "id": cid,
                "CustomerID": cid,
                "tenure": disp_features.get("Tenure"),
                "category_raw": disp_features.get("PreferedOrderCat"),
                "category_fa": cat_fa(disp_features.get("PreferedOrderCat")),
                "payment": disp_features.get("PreferredPaymentMode"),
                "payment_fa": pay_fa(disp_features.get("PreferredPaymentMode")),
                "complain": int(disp_features.get("Complain") or 0),
                "risk": risk,
                "tone": tone,
                "status_label": STATUS_LABEL[tone],
                "drivers": drivers,
                "trigger": trigger,
                "scenario": scenario,
                "features": disp_features,
                "raw_features": raw_features,
                "modal_cards": modal_cards,
                "recommendation": rec,
                "nba": rec,
                "nba_playbook": rec.get("playbook_badge", "NBA"),
                "nba_playbook_fa": rec.get("playbook_badge_fa", rec.get("playbook_badge", "NBA")),
                "nba_title": rec.get("playbook_title", ""),
            }
            scored_list.append(c_dict)
            self.customers_by_id[cid] = c_dict

        self.all_customers_cache = scored_list

    def get_random_sample(self, k: int = 2) -> List[dict]:
        if len(self.all_customers_cache) < k:
            return self.all_customers_cache
        chosen = random.sample(self.all_customers_cache, k)
        return chosen

    def get_customer(self, customer_id: int) -> Optional[dict]:
        return self.customers_by_id.get(customer_id)


# Initialize In-Memory Database
db = CustomerDatabase(STREAM_PATH, MODEL_PATH)

# --------------------------------------------------------------------------- #
# FastAPI Application & CORS
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="سامانه تحلیل هوشمند و مدیریت ریزش مشتری",
    description="سیستم مدرن ارزیابی و پایش ریسک ریزش مشتری با هوش مصنوعی و معماری Client-Server",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# Pydantic Request & Response Models
# --------------------------------------------------------------------------- #
class EvaluateRequest(BaseModel):
    tenure: int = Field(default=2, ge=0, le=60, description="Customer tenure in months")
    days_since_last_order: int = Field(default=3, ge=0, le=90, description="Days since last purchase")
    complain: int = Field(default=0, ge=0, le=1, description="Complain in the last month (0 or 1)")
    satisfaction_score: int = Field(default=3, ge=1, le=5, description="Satisfaction score 1 to 5")
    category: str = Field(default="Mobile Phone", description="Preferred order category")
    order_count: int = Field(default=2, ge=1, le=50, description="Total order count")
    city_tier: int = Field(default=1, ge=1, le=3, description="City tier (1, 2, or 3)")
    store_name: str = Field(default=DEFAULT_STORE, description="Business/Store name for SMS")


class ActionRequest(BaseModel):
    target_id: str = Field(..., description="Customer ID or Lab ID to register action for")


# --------------------------------------------------------------------------- #
# API Endpoints
# --------------------------------------------------------------------------- #
@app.get("/api/insights")
def get_insights():
    """
    Returns section 1 strategic analysis, historical dataset stats, and roadmap.
    """
    analyses = [
        {
            "id": "complaint",
            "kicker": "تحلیل ۱ · اهرم شکایت‌ها",
            "title": "یک شکایت، ریزش را ≈ ۳ برابر می‌کند",
            "numbers": [
                {"value": f"{DATASET['complain']['بدون شکایت']}٪", "label": "ریزش بدون شکایت", "color": "green"},
                {"value": f"{DATASET['complain']['دارای شکایت']}٪", "label": "ریزش با شکایت", "color": "red"},
                {"value": f"{DATASET['complain_share_of_churners']}٪", "label": "سهم شاکیان از خارج‌شدگان", "color": "blue"},
            ],
            "bullets": [
                f"({round(DATASET['complain_customers'] / DATASET['n'] * 100, 1)}٪ از کل مشتریان) شکایت ثبت کرده‌اند.",
                "بیش از نیمی از کل مشتریان خارج‌شده پیش از رفتن شکایت داشته‌اند؛ شکایت قوی‌ترین هشدار زودهنگام است.",
                "پیشنهاد اجرایی: شکایت‌ها را به‌عنوان هشدار ریزش پایش کنید و پیش از خروج مشتری، مداخله کنید."
            ],
            "takeaway": "شکایت را به‌عنوان یک سیگنال ریزش جدی بگیرید، نه صرفاً یک مسئله خدماتی.",
            "chart_type": "complaint"
        },
        {
            "id": "tenure",
            "kicker": "تحلیل ۲ · ماه‌های نخست؛ نقطه حساس مشتری",
            "title": "بحران در ماه نخست همراهی رخ می‌دهد",
            "numbers": [
                {"value": f"{DATASET['tenure_mean_loyal']}", "label": "میانگین سابقه ماندگاران (ماه)", "color": "green"},
                {"value": f"{DATASET['tenure_mean_churned']}", "label": "میانگین سابقه خارج‌شدگان (ماه)", "color": "red"},
                {"value": f"{DATASET['tenure']['۰ تا ۱ ماه']}٪", "label": "از مشتریان ماه اول ریزش کرده‌اند", "color": "blue"},
            ],
            "bullets": [
                f"{DATASET['first_month_share_of_churners']}٪ از کل مشتریان خارج‌شده حداکثر ۱ ماه سابقه داشته‌اند.",
                "بعد از ماه دوم، نرخ ریزش به ۵ تا ۱۰٪ می‌رسد و در سابقهٔ بالای ۱۲ ماه حدود ۵٪ است.",
                "ریسک در ابتدای رابطه متمرکز است، نه پراکنده در طول عمر مشتری."
            ],
            "takeaway": "برنامهٔ ۳۰ روز اول (خوش‌آمد، بن خرید دوم، تماس پیگیری) بیشترین بازده را دارد.",
            "chart_type": "tenure"
        },
        {
            "id": "satisfaction",
            "kicker": "تحلیل ۳ · رضایت مشتری همیشه کافی نیست",
            "title": "رضایت بالا، اما ریزش همچنان وجود دارد",
            "numbers": [
                {"value": f"{DATASET['satisfaction'][5]}٪", "label": "ریزش با رضایت ۵", "color": "red"},
                {"value": f"{DATASET['satisfaction'][1]}٪", "label": "ریزش با رضایت ۱", "color": "green"},
                {"value": f"{round(DATASET['satisfaction'][5] / DATASET['satisfaction'][1], 1)}×", "label": "نسبت ریزش", "color": "blue"},
            ],
            "bullets": [
                "در این داده‌ها، نرخ ریزش در بالاترین سطح رضایت نیز پایین‌تر نشده و از ۱۱٫۵٪ تا ۲۳٫۸٪ تغییر می‌کند.",
                "«ریزش خاموش»: مشتری بدون هیچ اعتراضی و حتی با امتیاز عالی می‌رود؛ نظرسنجی سنتی این گروه را «وفادار» ثبت می‌کند.",
                "رضایت باید در کنار سابقه، شکایت و الگوی خرید مشتری بررسی شود؛ یک امتیاز رضایت به‌تنهایی تصویر کاملی از ریسک ریزش نمی‌دهد."
            ],
            "takeaway": "نمرهٔ رضایت را جایگزین پایش رفتاری نکنید؛ سابقه، شکایت و الگوی خرید را زنده رصد کنید.",
            "chart_type": "satisfaction"
        },
        {
            "id": "category",
            "kicker": "تحلیل ۴ · ریزش مشتری بر اساس دسته خرید",
            "title": "نرخ ریزش در دسته‌ کالاهای مختلف یکسان نیست",
            "numbers": [
                {"value": f"{DATASET['category']['Mobile Phone']}٪", "label": "ریزش در موبایل و دیجیتال", "color": "red"},
                {"value": f"{DATASET['category']['Fashion']}٪", "label": "ریزش در مد و پوشاک", "color": "blue"},
                {"value": f"{DATASET['category']['Grocery']}٪", "label": "ریزش در خواربار", "color": "green"},
            ],
            "bullets": [
                f"خواربار با ریزش {DATASET['category']['Grocery']}٪ (وفاداری بالای ۹۵٪) نشان می‌دهد خرید تکرارشونده وفاداری می‌سازد.",
                "تفاوت نرخ ریزش میان دسته‌های خرید نشان می‌دهد رفتار مشتری در همه محصولات یکسان نیست."
            ],
            "takeaway": "برای هر دسته محصولات فروشگاه، متناسب با سطح ریسک آن اقدام کنید.",
            "chart_type": "category"
        },
        {
            "id": "behaviour",
            "kicker": "تحلیل ۵ · پاداش خرید و رفتار مشتری",
            "title": "پاداش خرید بیشتر و ارسال سریع‌تر، وفاداری بیشتر مشتریان",
            "numbers": [
                {"value": f"{DATASET['cashback_rate'][0]}٪", "label": "ریزش با پاداش خرید کم", "color": "red"},
                {"value": f"{DATASET['cashback_rate'][3]}٪", "label": "ریزش با پاداش خرید مناسب", "color": "green"},
                {"value": f"{DATASET['distance']['بیش از ۲۰']}٪", "label": "ریزش با فاصله ارسال زیاد", "color": "blue"},
            ],
            "bullets": [
                f"میانگین پاداش خرید مشتریان ماندگار {cash_toman(DATASET['cashback_mean_loyal_raw'])} در برابر {cash_toman(DATASET['cashback_mean_churned_raw'])} برای خارج‌شدگان.",
                "ریزش با افزایش فاصله ارسال محصول از ۱۳٫۵٪ به ۲۰٫۴٪ می‌رسد.",
                f"الگوی «خرید و خداحافظی»: ریزش مشتریان با ۰ تا ۲ روز فاصله از خرید {DATASET['recency']['۰ تا ۲ روز']}٪ و بالای ۱۰ روز {DATASET['recency']['بیش از ۱۰ روز']}٪ است.",
                "رابطه پاداش خرید و ریزش، یک الگوی آماری است و پاداش پلکانی ابزار قدرتمند وفادارسازی است."
            ],
            "takeaway": "پاداش خرید (سیستم کش‌بک) پلکانی و ارسال سریع برای مناطق دور، دو اهرم کم‌هزینهٔ نگهداشت‌اند.",
            "chart_type": "behaviour"
        }
    ]

    roadmap = [
        {
            "stage": "مرحله ۱ · شروع رابطه",
            "title": "تمرکز بر مشتریان تازه‌وارد",
            "bullets": ["طراحی مسیر مشوق خرید دوم", "پایش ویژه مشتریان با سابقهٔ کمتر از یک ماه"],
            "target": "هدف: کاهش قابل‌توجه ریزش مشتریان در ماه اول"
        },
        {
            "stage": "مرحله ۲ · پشتیبانی",
            "title": "تبدیل شکایت به فرصت حفظ مشتری",
            "bullets": ["اولویت‌دهی به مشتریان دارای شکایت", "طراحی فرآیند مشخص برای پیگیری و جبران نارضایتی"],
            "target": "هدف: کاهش قابل‌توجه ریزش در میان مشتریان دارای شکایت"
        },
        {
            "stage": "مرحله ۳ · تجربه ارسال",
            "title": "کاهش ریسک ناشی از فاصله ارسال",
            "bullets": ["بررسی راهکارهای بهبود زمان و کیفیت ارسال برای مناطق دور", "ارزیابی امکان نزدیک‌تر کردن نقاط توزیع به مشتریان"],
            "target": "هدف: کاهش ریزش مشتریان در مناطق با فاصلهٔ بیشتر از ۲۰ کیلومتر"
        },
        {
            "stage": "مرحله ۴ · وفاداری",
            "title": "تقویت پاداش خرید و حفظ مشتری",
            "bullets": ["طراحی پاداش خرید متناسب با ارزش و رفتار مشتری", "تمرکز بیشتر بر دسته‌های خرید با نرخ ریزش بالاتر"],
            "target": "هدف: کاهش ریزش در گروه‌های دریافت‌کننده پاداش خرید کمتر"
        }
    ]

    return {
        "dataset": DATASET,
        "satisfaction_counts": SATISFACTION_COUNTS,
        "analyses": analyses,
        "roadmap": roadmap
    }


@app.get("/api/radar")
def get_radar_customers():
    """
    Randomly selects 2 customers from the stream file, executes predict_single_customer,
    and returns their risk percentage, churn reasons, and customer features.
    """
    samples = db.get_random_sample(2)
    response_items = []

    for item in samples:
        # Re-score directly via predict_single_customer using raw features (training medians applied in inference)
        raw_feats = item.get("raw_features", item["features"])
        result = predict_single_customer(raw_feats, model_path=MODEL_PATH)
        risk = float(result["churn_probability_pct"])
        tone = tone_of(risk)

        drivers = [{**d, **describe_driver(d)} for d in result["top_risk_drivers"]]
        scenario, trigger = pick_scenario(drivers)

        main_cause_item = trigger if trigger else (drivers[0] if drivers else None)
        main_cause_text = f"{main_cause_item['title']} — {main_cause_item['detail']}" if main_cause_item else "ترکیب چند عامل رفتاری"

        response_items.append({
            "id": item["id"],
            "risk": risk,
            "tone": tone,
            "status_label": STATUS_LABEL[tone],
            "category": item["category_fa"],
            "tenure": item["tenure"],
            "payment": item["payment_fa"],
            "complain": item["complain"],
            "drivers": drivers,
            "main_cause": main_cause_text,
            "scenario": scenario,
            "scenario_label": SCENARIOS.get(scenario, SCENARIOS["general"])["label"],
            "features": item["features"],
            "full_info": item["modal_cards"],
        })

    return response_items


@app.post("/api/evaluate")
def evaluate_customer(req: EvaluateRequest):
    """
    Customer Evaluation Lab: Receives custom factor inputs, executes model inference,
    and returns risk percentage, 2 main root drivers, and suggested SMS scenario with discount code.
    """
    # 1. Resolve raw category
    cat_raw = CATEGORY_RESOLVER.get(req.category.strip(), "Mobile Phone")

    # 2. Build feature vector using segment profile fallback
    features = segment_profile(cat_raw, req.complain, req.tenure)
    features.update({
        "Tenure": float(req.tenure),
        "Complain": int(req.complain),
        "PreferedOrderCat": cat_raw,
        "DaySinceLastOrder": float(req.days_since_last_order),
        "CityTier": float(req.city_tier),
        "SatisfactionScore": float(req.satisfaction_score),
        "OrderCount": float(req.order_count),
    })

    # 3. Model Inference
    result = predict_single_customer(features, model_path=MODEL_PATH)
    risk = float(result["churn_probability_pct"])
    tone = tone_of(risk)

    # 4. Extract top 2 drivers with descriptions
    drivers = [{**d, **describe_driver(d)} for d in result["top_risk_drivers"]]
    top_2 = drivers[:2]

    # 5. Recommendation (Unified 6 Playbooks Engine)
    store = (req.store_name or DEFAULT_STORE).strip() or DEFAULT_STORE
    rec = explorer_recommendation(risk, drivers, store, features=features)

    # 6. Retention Value & Output Payload
    ret_val = retention_value(cat_raw, risk)
    lab_id = f"LAB-{zlib.crc32(repr(sorted(req.model_dump().items())).encode()) % 90000 + 10000}"

    main_cause_text = rec.get("root_cause_short")
    if not main_cause_text:
        main_cause_item = drivers[0] if drivers else None
        main_cause_text = f"{main_cause_item['title']} — {main_cause_item['detail']}" if main_cause_item else "ترکیب چند عامل رفتاری"

    sms_code = rec.get("code", "")
    sms_discount = rec.get("discount", 0)
    sms_obj = {
        "tag": rec.get("playbook_badge", "راهبرد مداخله"),
        "code": sms_code,
        "discount": sms_discount,
        "message": rec.get("sms", ""),
        "css": "gold" if sms_code in {"VIP30", "RECOVER"} else "silver"
    }

    return {
        "lab_id": lab_id,
        "risk": risk,
        "tone": tone,
        "status_label": STATUS_LABEL[tone],
        "top_drivers": top_2,
        "main_cause": main_cause_text,
        "scenario": rec["playbook_id"],
        "scenario_label": rec["playbook_title"],
        "intervention": rec["playbook_title"],
        "strategy": rec.get("strategy", ""),
        "strategy_desc": rec.get("strategy_desc", ""),
        "action": rec.get("action", ""),
        "code": sms_code,
        "discount": sms_discount,
        "retention_value": ret_val,
        "retention_value_formatted": f"{ret_val:,}",
        "nba": rec,
        "recommendation": rec,
        "sms": sms_obj,
        "is_registered": (str(lab_id) in db.registered_actions or lab_id in db.registered_actions)
    }


@app.get("/api/customers")
def get_customers():
    """
    Returns list of 200 stream customers with their churn risk for Tab 3 table and 360 modal.
    """
    # Annotate with registered state
    result = []
    for c in db.all_customers_cache:
        c_copy = dict(c)
        c_copy["is_registered"] = (
            str(c["id"]) in db.registered_actions or c["id"] in db.registered_actions
        )
        c_copy.pop("raw_features", None)
        result.append(c_copy)
    return result


@app.post("/api/action")
def register_action(req: ActionRequest):
    """
    Registers an intervention action for a customer or lab scenario ID.
    """
    target = str(req.target_id).strip()
    db.registered_actions.add(target)
    return {"status": "success", "target_id": req.target_id, "total_registered": len(db.registered_actions)}


# --------------------------------------------------------------------------- #
# Static Files & SPA Root
# --------------------------------------------------------------------------- #
STATIC_DIR.mkdir(exist_ok=True)

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found in static directory")
    return FileResponse(index_file)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
