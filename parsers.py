"""
parsers.py — CSV parsers for Canadian financial institutions.
Auto-extracts account/card number from file to create unique accounts.
Python 3.8 compatible.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Optional, Tuple
import pandas as pd


def _make_hash(account_ref, date, description, amount):
    raw = "{}|{}|{}|{}".format(account_ref, date, description, amount)
    return hashlib.md5(raw.encode()).hexdigest()


def _clean_amount(val):
    if pd.isna(val):
        return 0.0
    s = str(val).strip().replace(",", "").replace("$", "").replace(" ", "")
    if s.startswith("(") and s.endswith(")"):
        try:
            return -float(s[1:-1])
        except ValueError:
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_date(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y",
                "%B %d, %Y", "%Y/%m/%d", "%d-%b-%Y", "%m-%d-%Y"]:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s


def _extract_account_number(df: pd.DataFrame, text_hint: str = "") -> Optional[str]:
    """
    Try to find an account/card number from:
    1. A column named 'Account #', 'Card Number', etc.
    2. First row values that look like account numbers.
    3. The text_hint string (e.g. filename).
    Returns last-4 digits string like "****1234" or None.
    """
    # Check column names
    for col in df.columns:
        cl = col.lower().replace(" ", "").replace("_", "")
        if any(k in cl for k in ["account#", "accountno", "accountnumber",
                                   "cardnumber", "card#", "maskedcard"]):
            val = str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else ""
            cleaned = re.sub(r"[^0-9Xx*]", "", val)
            if len(cleaned) >= 4:
                return "****" + cleaned[-4:]

    # Check first few rows for anything that looks like a card/account number
    for col in df.columns:
        for cell in df[col].dropna().head(3):
            s = str(cell)
            m = re.search(r"\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b", s)
            if m:
                digits = re.sub(r"\D", "", m.group(1))
                return "****" + digits[-4:]
            m2 = re.search(r"\b\d{10,}\b", s)
            if m2:
                return "****" + m2.group(0)[-4:]

    # Check filename hint
    m = re.search(r"(\d{4,})", text_hint)
    if m:
        return "****" + m.group(1)[-4:]

    return None


# ─── Wealthsimple Cash ────────────────────────────────────────────────────────

def parse_wealthsimple_cash(file_obj, account_id, account_name="Wealthsimple Cash",
                             account_number=None):
    df = pd.read_csv(file_obj)
    df.columns = [c.strip() for c in df.columns]

    acc_num = account_number or _extract_account_number(df) or "default"
    ref = "{}_{}".format(account_name, acc_num)
    txns = []

    has_wd = any("withdrawal" in c.lower() or "debit" in c.lower() for c in df.columns)
    wd_col  = next((c for c in df.columns if "withdrawal" in c.lower() or "debit" in c.lower()), None)
    dep_col = next((c for c in df.columns if "deposit" in c.lower() or "credit" in c.lower()), None)
    amt_col = next((c for c in df.columns if "amount" in c.lower()), None)
    bal_col = next((c for c in df.columns if "balance" in c.lower()), None)

    for _, row in df.iterrows():
        date = _parse_date(row.get("Date") or row.get("Transaction Date"))
        if not date:
            continue
        desc = str(row.get("Description") or row.get("Merchant Name") or "").strip()
        if has_wd:
            wd  = _clean_amount(row.get(wd_col, 0))
            dep = _clean_amount(row.get(dep_col, 0))
            amount = dep - wd if dep else -wd
        else:
            amount = _clean_amount(row.get(amt_col, 0)) if amt_col else 0.0

        bal = _clean_amount(row.get(bal_col, 0)) if bal_col else None
        txns.append({
            "account_id": account_id,
            "date": date,
            "description": desc,
            "original_desc": desc,
            "amount": amount,
            "currency": "CAD",
            "memo": "Balance: ${:.2f}".format(bal) if bal is not None else None,
            "hash": _make_hash(ref, date, desc, amount),
        })
    return txns


# ─── Rogers Mastercard ────────────────────────────────────────────────────────

def parse_rogers_mastercard(file_obj, account_id, account_name="Rogers Mastercard",
                             account_number=None):
    df = pd.read_csv(file_obj)
    df.columns = [c.strip() for c in df.columns]

    acc_num = account_number or _extract_account_number(df) or "default"
    ref = "{}_{}".format(account_name, acc_num)
    txns = []

    date_col = next((c for c in df.columns
                     if "transaction date" in c.lower() or c.lower() == "date"), None)
    amt_col  = next((c for c in df.columns if "amount" in c.lower()), None)

    for _, row in df.iterrows():
        date = _parse_date(row.get(date_col))
        if not date:
            continue
        desc   = str(row.get("Description") or row.get("Merchant Name") or "").strip()
        amount = _clean_amount(row.get(amt_col, 0)) if amt_col else 0.0
        txn_type = str(row.get("Type", "")).lower()

        if "payment" in txn_type or "credit" in txn_type:
            amount = abs(amount)
        else:
            amount = -abs(amount)

        txns.append({
            "account_id": account_id,
            "date": date,
            "description": desc,
            "original_desc": desc,
            "amount": amount,
            "currency": "CAD",
            "hash": _make_hash(ref, date, desc, amount),
        })
    return txns


# ─── Questrade ────────────────────────────────────────────────────────────────

def parse_questrade(file_obj, account_id, account_name="Questrade",
                    account_number=None):
    df = pd.read_csv(file_obj)
    df.columns = [c.strip() for c in df.columns]

    # Questrade often has "Account #" column
    acc_num = account_number or _extract_account_number(df) or "default"
    if acc_num == "default":
        acct_col = next((c for c in df.columns if "account" in c.lower()), None)
        if acct_col:
            val = str(df[acct_col].dropna().iloc[0]) if len(df[acct_col].dropna()) > 0 else ""
            digits = re.sub(r"\D", "", val)
            if digits:
                acc_num = "****" + digits[-4:]

    ref = "{}_{}".format(account_name, acc_num)
    txns = []

    net_col   = next((c for c in df.columns if "net amount" in c.lower() or c.lower() == "net"), None)
    gross_col = next((c for c in df.columns if "gross" in c.lower()), None)
    amt_col   = net_col or gross_col

    for _, row in df.iterrows():
        date = _parse_date(row.get("Transaction Date") or row.get("Activity Date"))
        if not date:
            continue

        action   = str(row.get("Action", row.get("Activity Type", ""))).strip()
        symbol   = str(row.get("Symbol", "")).strip()
        desc_raw = str(row.get("Description", "")).strip()

        if symbol and symbol != "nan":
            desc = "{} {} - {}".format(action, symbol, desc_raw) if desc_raw else "{} {}".format(action, symbol)
        else:
            desc = desc_raw or action

        amount   = _clean_amount(row.get(amt_col, 0)) if amt_col else 0.0
        currency = str(row.get("Currency", "CAD")).strip()

        au = action.upper()
        if au in ("BUY", "TFI"):
            category = "Stocks"
        elif au in ("SELL", "TFO"):
            category = "Stocks"
        elif au in ("DEP", "CSH", "EFT", "CON"):
            category = "Transfer"
        elif au in ("DIV",):
            category = "Dividends"
        elif au == "INT":
            category = "Interest Income"
        elif au in ("FEE", "MNG"):
            category = "Bank Fees"
        else:
            category = "Investments"

        txns.append({
            "account_id": account_id,
            "date": date,
            "description": desc,
            "original_desc": desc_raw,
            "amount": amount,
            "category": category,
            "currency": currency,
            "hash": _make_hash(ref, date, desc, amount),
        })
    return txns


# ─── Wealthsimple Invest ──────────────────────────────────────────────────────

def parse_wealthsimple_invest(file_obj, account_id, account_name="Wealthsimple Invest",
                               account_number=None):
    df = pd.read_csv(file_obj)
    df.columns = [c.strip() for c in df.columns]

    acc_num = account_number or _extract_account_number(df) or "default"
    ref = "{}_{}".format(account_name, acc_num)
    txns = []

    net_col = next((c for c in df.columns if "net" in c.lower() or "amount" in c.lower()), None)

    for _, row in df.iterrows():
        date = _parse_date(row.get("Date") or row.get("Activity Date") or row.get("Transaction Date"))
        if not date:
            continue

        txn_type = str(row.get("Type") or row.get("Activity Type") or "").strip()
        symbol   = str(row.get("Symbol") or row.get("Security") or "").strip()
        desc_raw = str(row.get("Description") or "").strip()

        desc = "{}: {}".format(txn_type, symbol) if (symbol and symbol != "nan") else (desc_raw or txn_type)

        amount   = _clean_amount(row.get(net_col, 0)) if net_col else 0.0
        currency = str(row.get("Currency", "CAD")).strip()

        tl = txn_type.lower()
        if "buy" in tl or "purchase" in tl:
            category = "ETFs"
        elif "sell" in tl:
            category = "ETFs"
        elif "dividend" in tl:
            category = "Dividends"
        elif "contribution" in tl or "deposit" in tl:
            category = "Transfer"
        elif "withdrawal" in tl:
            category = "Transfer"
        elif "fee" in tl:
            category = "Bank Fees"
        elif "interest" in tl:
            category = "Interest Income"
        else:
            category = "Investments"

        txns.append({
            "account_id": account_id,
            "date": date,
            "description": desc,
            "original_desc": desc_raw,
            "amount": amount,
            "category": category,
            "currency": currency,
            "hash": _make_hash(ref, date, desc, amount),
        })
    return txns


# ─── CIBC Mortgage ────────────────────────────────────────────────────────────

def parse_cibc_mortgage(file_obj, account_id, account_name="CIBC Mortgage",
                         account_number=None):
    df = pd.read_csv(file_obj)
    df.columns = [c.strip() for c in df.columns]

    acc_num = account_number or _extract_account_number(df) or "default"
    ref = "{}_{}".format(account_name, acc_num)
    txns = []

    has_principal = any("principal" in c.lower() for c in df.columns)
    debit_col  = next((c for c in df.columns if "debit" in c.lower() or "withdrawal" in c.lower()), None)
    credit_col = next((c for c in df.columns if "credit" in c.lower() or "deposit" in c.lower()), None)
    bal_col    = next((c for c in df.columns if "balance" in c.lower()), None)

    for _, row in df.iterrows():
        date = _parse_date(row.get("Date") or row.get("Transaction Date"))
        if not date:
            continue

        desc = str(row.get("Description") or row.get("Activity") or "Mortgage Payment").strip()

        if has_principal:
            principal = _clean_amount(row.get("Principal", 0))
            interest  = _clean_amount(row.get("Interest", 0))
            total     = _clean_amount(row.get("Total Payment") or row.get("Payment") or (principal + interest))
            amount    = -abs(total)
            memo      = "Principal: ${:.2f} | Interest: ${:.2f}".format(principal, interest)
        else:
            debit  = _clean_amount(row.get(debit_col, 0)) if debit_col else 0.0
            credit = _clean_amount(row.get(credit_col, 0)) if credit_col else 0.0
            amount = credit - debit if credit else -debit
            bal    = _clean_amount(row.get(bal_col, 0)) if bal_col else None
            memo   = "Balance: ${:.2f}".format(bal) if bal is not None else None

        txns.append({
            "account_id": account_id,
            "date": date,
            "description": desc,
            "original_desc": desc,
            "amount": amount,
            "category": "Mortgage",
            "memo": memo,
            "currency": "CAD",
            "hash": _make_hash(ref, date, desc, amount),
        })
    return txns


# ─── Registry ─────────────────────────────────────────────────────────────────

INSTITUTION_PARSERS = {
    "Wealthsimple Cash":   parse_wealthsimple_cash,
    "Rogers Mastercard":   parse_rogers_mastercard,
    "Questrade":           parse_questrade,
    "Wealthsimple Invest": parse_wealthsimple_invest,
    "CIBC Mortgage":       parse_cibc_mortgage,
}

ACCOUNT_TYPES = {
    "Wealthsimple Cash":   ("Wealthsimple", "checking"),
    "Rogers Mastercard":   ("Rogers Bank",  "credit"),
    "Questrade":           ("Questrade",    "investment"),
    "Wealthsimple Invest": ("Wealthsimple", "investment"),
    "CIBC Mortgage":       ("CIBC",         "mortgage"),
}


def extract_account_info(file_obj, institution: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse the CSV header / first rows to extract account number.
    Returns (display_name, account_number).
    E.g. ("Rogers Mastercard ****1234", "****1234")
    """
    try:
        import io
        if hasattr(file_obj, "read"):
            raw = file_obj.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            file_obj.seek(0)
            df = pd.read_csv(io.StringIO(raw), nrows=5)
        else:
            df = pd.read_csv(file_obj, nrows=5)

        df.columns = [c.strip() for c in df.columns]
        acc_num = _extract_account_number(df)
        if acc_num:
            display = "{} {}".format(institution, acc_num)
            return display, acc_num
    except Exception:
        pass
    return institution, None


def parse_csv(file_obj, institution: str, account_id: int, account_name: str,
              account_number: Optional[str] = None):
    parser = INSTITUTION_PARSERS.get(institution)
    if not parser:
        raise ValueError("Unknown institution: {}".format(institution))
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    return parser(file_obj, account_id, account_name, account_number=account_number)
