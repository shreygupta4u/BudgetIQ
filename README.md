# 💎 FinanceIQ — Personal Budgeting App

A Quicken-inspired personal budgeting app built with Python + Streamlit.  
**No AI required** — categorization is rule-based and fully manual.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch
streamlit run app.py
```

Opens at **http://localhost:8501**

---

## Features

- **Multi-institution CSV import** — Wealthsimple Cash, Rogers Mastercard, Questrade, Wealthsimple Invest, CIBC Mortgage
- **Incremental imports / deduplication** — Upload next month's statement safely; duplicates are auto-detected and skipped
- **Manual categorization** — Edit any transaction category; choose from 50+ built-in categories
- **Rule-based auto-categorization** — 100+ built-in Canadian merchant patterns (Tim Hortons, Loblaws, Petro-Canada, etc.)
- **Auto-learning rules** — Every manual correction saves a keyword rule so future imports are smarter
- **Split transactions** — Divide one transaction across multiple categories (e.g. mortgage principal vs interest)
- **Budget tracking** — Monthly budgets per category with visual progress bars
- **Cash flow charts** — 6/12-month income vs expenses
- **Full reports** — Spending trends, category breakdowns, monthly summaries
- **Net worth** — Track assets and liabilities across all accounts

## How Deduplication Works

Every transaction is fingerprinted as `MD5(account + date + description + amount)`.  
On each import, any transaction whose fingerprint already exists in the database is **silently skipped**.  
You can safely re-upload a full bank statement — only genuinely new rows are added.

## How Categorization Works

1. **User-saved rules** (highest priority) — keyword rules you created or that were auto-saved from corrections
2. **Built-in regex patterns** — 100+ patterns for Canadian merchants
3. **Uncategorized** — anything that didn't match; edit it manually in the Transactions tab

Each correction you make saves a new keyword rule → next import auto-categorizes the same merchant.

## CSV Format Guide

| Institution | Key Columns |
|---|---|
| Wealthsimple Cash | Date, Description, Withdrawals ($), Deposits ($), Balance ($) |
| Rogers Mastercard | Transaction Date, Description, Transaction Amount, Type |
| Questrade | Transaction Date, Action, Symbol, Description, Net Amount, Currency |
| Wealthsimple Invest | Date, Type, Symbol, Description, Net Amount, Currency |
| CIBC Mortgage | Date, Description, Debit ($), Credit ($), Balance ($) |

## Data Location

SQLite database stored at `~/.financeiq/budget.db` — fully local, nothing sent to the cloud.
