"""
database.py — SQL Server persistence layer for FinanceIQ
pip install pyodbc
"""
from __future__ import annotations

import pyodbc
import json
from datetime import date, datetime

CONN_STR = (
    r"DRIVER={ODBC Driver 17 for SQL Server};"
    r"SERVER=localhost\SQLExpress;"
    r"DATABASE=FinanceIQ;"
    r"Trusted_Connection=yes;"
)
DB_PATH = "SQL Server › FinanceIQ"


def get_connection():
    return pyodbc.connect(CONN_STR)


def dict_factory(cursor, row):
    return {col[0]: val for col, val in zip(cursor.description, row)}


def _to_float(v):
    """Convert Decimal / None to float safely."""
    if v is None:
        return 0.0
    return float(v)


def init_db():
    conn = get_connection()
    cur  = conn.cursor()
    _migrate(cur)
    conn.commit()
    conn.close()


def _migrate(cur):
    # accounts.account_number
    cur.execute("""
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                       WHERE TABLE_NAME='accounts' AND COLUMN_NAME='account_number')
        ALTER TABLE accounts ADD account_number NVARCHAR(100)
    """)
    # transactions columns
    for col, dtype in [
        ("is_transfer",             "BIT DEFAULT 0"),
        ("transfer_to_account_id",  "INT"),
        ("transfer_investment_cat", "NVARCHAR(100)"),
        ("tags",                    "NVARCHAR(MAX)"),
    ]:
        cur.execute(f"""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                           WHERE TABLE_NAME='transactions' AND COLUMN_NAME='{col}')
            ALTER TABLE transactions ADD {col} {dtype}
        """)

    # Goals table
    cur.execute("""
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='goals')
        CREATE TABLE goals (
            id              INT           IDENTITY(1,1) PRIMARY KEY,
            name            NVARCHAR(255) NOT NULL,
            goal_type       NVARCHAR(50)  DEFAULT 'total',  -- 'total' or 'monthly'
            target_amount   DECIMAL(18,2) NOT NULL,
            monthly_amount  DECIMAL(18,2) NULL,
            target_date     DATE          NULL,
            account_id      INT           NULL,
            created_at      DATETIME2     DEFAULT GETDATE()
        )
    """)

    # Budget: add carry_forward and effective_date columns
    cur.execute("""
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                       WHERE TABLE_NAME='budgets' AND COLUMN_NAME='carry_forward')
        ALTER TABLE budgets ADD carry_forward BIT DEFAULT 0
    """)
    cur.execute("""
        IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                       WHERE TABLE_NAME='budgets' AND COLUMN_NAME='carry_forward_type')
        ALTER TABLE budgets ADD carry_forward_type NVARCHAR(50) DEFAULT 'none'
    """)


# ─── Month helpers ─────────────────────────────────────────────────────────────

def _month_key_to_date(month_key: str) -> date:
    """'2025-03' → date(2025,3,1)"""
    parts = month_key.split("-")
    return date(int(parts[0]), int(parts[1]), 1)


# ─── Account helpers ───────────────────────────────────────────────────────────

def get_accounts():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM accounts ORDER BY type, name")
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["balance"] = _to_float(r.get("balance"))
    return rows


def get_account_balances():
    return get_accounts()


def upsert_account(name, institution, acc_type, currency="CAD", account_number=None):
    conn = get_connection()
    cur  = conn.cursor()
    # Step 1: INSERT if not exists — commit fully before any SELECT
    if account_number:
        cur.execute("""
            IF NOT EXISTS (SELECT 1 FROM accounts WHERE institution=? AND account_number=?)
            INSERT INTO accounts (name, institution, type, currency, account_number)
            VALUES (?,?,?,?,?)
        """, (institution, account_number, name, institution, acc_type, currency, account_number))
    else:
        cur.execute("""
            IF NOT EXISTS (SELECT 1 FROM accounts WHERE name=? AND institution=?)
            INSERT INTO accounts (name, institution, type, currency)
            VALUES (?,?,?,?)
        """, (name, institution, name, institution, acc_type, currency))
    conn.commit()
    cur.close()

    # Step 2: fresh cursor for SELECT — avoids HY010 pending result-set error
    cur2 = conn.cursor()
    if account_number:
        cur2.execute("SELECT id FROM accounts WHERE institution=? AND account_number=?",
                     (institution, account_number))
    else:
        cur2.execute("SELECT id FROM accounts WHERE name=? AND institution=?",
                     (name, institution))
    row = cur2.fetchone()
    cur2.close()
    conn.close()
    return row[0] if row else None


def update_account_name(account_id, new_name):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE accounts SET name=? WHERE id=?", (new_name, account_id))
    conn.commit()
    conn.close()


def update_account_balance(account_id, balance):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE accounts SET balance=? WHERE id=?", (float(balance), account_id))
    conn.commit()
    conn.close()


# ─── Category helpers ──────────────────────────────────────────────────────────

def get_categories():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, ISNULL(p.icon,'💰') AS icon,
               ISNULL(p.color,'#6b7280') AS color,
               p.is_income, NULL AS parent
        FROM parent_categories p
        UNION ALL
        SELECT c.id, c.name, ISNULL(c.icon,'💰') AS icon,
               ISNULL(c.color,'#6b7280') AS color,
               c.is_income, p.name AS parent
        FROM child_categories c
        JOIN parent_categories p ON c.parent_id = p.id
        ORDER BY parent, name
    """)
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_category(name, parent=None, icon="💰", color="#6b7280", is_income=0):
    conn = get_connection()
    cur  = conn.cursor()
    if parent:
        cur.execute("SELECT id FROM parent_categories WHERE name=?", (parent,))
        p = cur.fetchone()
        if p:
            cur.execute(
                "INSERT INTO child_categories (parent_id,name,icon,color,is_income) VALUES (?,?,?,?,?)",
                (p[0], name, icon, color, is_income))
    else:
        cur.execute(
            "INSERT INTO parent_categories (name,icon,color,is_income) VALUES (?,?,?,?)",
            (name, icon, color, is_income))
    conn.commit()
    conn.close()


def _resolve_child_id(cur, category_name):
    cur.execute("SELECT id FROM child_categories WHERE name=?", (category_name,))
    row = cur.fetchone()
    return row[0] if row else None


# ─── Transaction helpers ───────────────────────────────────────────────────────

def insert_transactions(txns):
    conn = get_connection()
    cur  = conn.cursor()
    inserted = skipped = 0
    for t in txns:
        try:
            child_id = t.get("child_category_id")
            if child_id is None and t.get("category"):
                child_id = _resolve_child_id(cur, t["category"])
            cur.execute("""
                INSERT INTO transactions
                  (account_id,date,description,original_desc,amount,
                   child_category_id,memo,currency,tags,ai_confidence,hash)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                t.get("account_id"), t["date"], t["description"],
                t.get("original_desc", t["description"]), float(t["amount"]),
                child_id, t.get("memo"), t.get("currency","CAD"),
                json.dumps(t.get("tags",[])), float(t.get("ai_confidence",0.0)),
                t.get("hash"),
            ))
            inserted += 1
        except pyodbc.IntegrityError:
            skipped += 1
    conn.commit()
    conn.close()
    return inserted, skipped


def get_transactions(account_id=None, limit=None, start_date=None,
                     end_date=None, category=None, search=None,
                     payee=None, tags_filter=None):
    conn = get_connection()
    cur  = conn.cursor()
    top  = f"TOP ({int(limit)})" if limit else ""
    query = f"""
        SELECT {top}
               t.id, t.account_id, t.date, t.description,
               t.original_desc, t.amount, t.memo,
               ISNULL(t.is_split,    0) AS is_split,
               ISNULL(t.is_transfer, 0) AS is_transfer,
               t.transfer_to_account_id,
               t.transfer_investment_cat,
               t.currency, t.ai_confidence,
               ISNULL(t.tags, '[]') AS tags,
               a.name           AS account_name,
               a.account_number AS account_number,
               p.name           AS parent_cat_name,
               c.name           AS child_cat_name,
               c.name           AS category
        FROM transactions t
        LEFT JOIN accounts          a ON t.account_id        = a.id
        LEFT JOIN child_categories  c ON t.child_category_id = c.id
        LEFT JOIN parent_categories p ON c.parent_id         = p.id
        WHERE 1=1
    """
    params = []
    if account_id  is not None: query += " AND t.account_id=?";           params.append(account_id)
    if start_date  is not None: query += " AND t.date>=?";                 params.append(start_date)
    if end_date    is not None: query += " AND t.date<=?";                 params.append(end_date)
    if category    is not None: query += " AND c.name=?";                  params.append(category)
    if search      is not None: query += " AND t.description LIKE ?";      params.append(f"%{search}%")
    if payee       is not None: query += " AND t.description LIKE ?";      params.append(f"%{payee}%")
    query += " ORDER BY t.date DESC, t.id DESC"
    cur.execute(query, params)
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["amount"] = _to_float(r.get("amount"))
        if not r.get("category"):
            r["category"] = "Uncategorized"
        # parse tags JSON
        try:
            r["tags"] = json.loads(r.get("tags") or "[]")
        except Exception:
            r["tags"] = []
    # client-side tags filter
    if tags_filter:
        rows = [r for r in rows if any(t in r["tags"] for t in tags_filter)]
    return rows


def update_transaction(txn_id, **kwargs):
    conn = get_connection()
    cur  = conn.cursor()
    for key, val in kwargs.items():
        if key == "category":
            child_id = _resolve_child_id(cur, val)
            if child_id:
                cur.execute("UPDATE transactions SET child_category_id=? WHERE id=?", (child_id, txn_id))
        elif key == "tags":
            cur.execute("UPDATE transactions SET tags=? WHERE id=?", (json.dumps(val), txn_id))
        else:
            cur.execute(f"UPDATE transactions SET {key}=? WHERE id=?", (val, txn_id))
    conn.commit()
    conn.close()


def mark_transfer(txn_id, dest_account_id, inv_cat=None):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        UPDATE transactions SET is_transfer=1,
               transfer_to_account_id=?, transfer_investment_cat=?
        WHERE id=?
    """, (dest_account_id, inv_cat, txn_id))
    conn.commit()
    conn.close()


def get_all_tags():
    """Return all unique tags used across transactions."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT ISNULL(tags,'[]') FROM transactions WHERE tags IS NOT NULL AND tags != '[]'")
    rows = cur.fetchall()
    conn.close()
    tags = set()
    for r in rows:
        try:
            for t in json.loads(r[0]):
                if t:
                    tags.add(t)
        except Exception:
            pass
    return sorted(tags)


# ─── Split transaction helpers ─────────────────────────────────────────────────

def get_split_transactions(txn_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT s.id, s.transaction_id, s.amount, s.memo, c.name AS category
        FROM split_transactions s
        JOIN child_categories c ON s.child_category_id=c.id
        WHERE s.transaction_id=?
    """, (txn_id,))
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["amount"] = _to_float(r.get("amount"))
    return rows


def save_split_transactions(txn_id, splits):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM split_transactions WHERE transaction_id=?", (txn_id,))
    for s in splits:
        child_id = _resolve_child_id(cur, s["category"])
        if child_id:
            cur.execute("""
                INSERT INTO split_transactions (transaction_id,child_category_id,amount,memo)
                VALUES (?,?,?,?)
            """, (txn_id, child_id, float(s["amount"]), s.get("memo")))
    cur.execute("UPDATE transactions SET is_split=1 WHERE id=?", (txn_id,))
    conn.commit()
    conn.close()


# ─── Budget helpers ────────────────────────────────────────────────────────────

def get_budgets(month_key: str):
    """month_key = 'YYYY-MM'. Returns most-recent budget <= that month per category."""
    mo_date = _month_key_to_date(month_key)
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT b.id, b.amount, b.month_year,
               ISNULL(b.carry_forward, 0) AS carry_forward,
               ISNULL(b.carry_forward_type, 'none') AS carry_forward_type,
               c.name AS category
        FROM budgets b
        JOIN child_categories c ON b.child_category_id = c.id
        WHERE b.month_year = (
            SELECT MAX(b2.month_year) FROM budgets b2
            WHERE b2.child_category_id = b.child_category_id
              AND b2.month_year <= ?
        )
    """, (mo_date,))
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["amount"] = _to_float(r.get("amount"))
    return rows


def upsert_budget(category, month_key: str, amount: float,
                  carry_forward: bool = False, carry_forward_type: str = "none",
                  effective_date: date = None):
    """effective_date overrides month_key if provided."""
    if effective_date:
        mo_date = effective_date.replace(day=1)
    else:
        mo_date = _month_key_to_date(month_key)
    conn = get_connection()
    cur  = conn.cursor()
    child_id = _resolve_child_id(cur, category)
    if child_id is None:
        conn.close()
        return
    cur.execute("""
        IF EXISTS (SELECT 1 FROM budgets WHERE child_category_id=? AND month_year=?)
            UPDATE budgets SET amount=?, carry_forward=?, carry_forward_type=?
            WHERE child_category_id=? AND month_year=?
        ELSE
            INSERT INTO budgets (child_category_id, month_year, amount, carry_forward, carry_forward_type)
            VALUES (?,?,?,?,?)
    """, (child_id, mo_date, float(amount), int(carry_forward), carry_forward_type,
          child_id, mo_date, child_id, mo_date, float(amount), int(carry_forward), carry_forward_type))
    conn.commit()
    conn.close()


def get_budget_with_carryforward(category: str, month_key: str,
                                  spending_prev: float = 0.0, budget_base: float = 0.0) -> float:
    """Compute effective budget for a month considering carry-forward setting."""
    budgets = get_budgets(month_key)
    bmap = {b["category"]: b for b in budgets}
    b = bmap.get(category)
    if not b:
        return 0.0
    base = b["amount"]
    cft  = b.get("carry_forward_type", "none")
    if cft == "none":
        return base
    # prev month
    mo_date = _month_key_to_date(month_key)
    if mo_date.month == 1:
        prev_key = f"{mo_date.year-1}-12"
    else:
        prev_key = f"{mo_date.year}-{mo_date.month-1:02d}"
    prev_budgets = get_budgets(prev_key)
    prev_bmap = {b["category"]: b for b in prev_budgets}
    prev_b = prev_bmap.get(category)
    prev_base = prev_b["amount"] if prev_b else 0.0
    delta = prev_base - spending_prev  # positive = underspent, negative = overspent
    if cft == "underspent" and delta > 0:
        return base + delta
    if cft == "overspent" and delta < 0:
        return base + delta  # delta is negative, reducing next month
    if cft == "both":
        return base + delta
    return base


# ─── Categorization rule helpers ───────────────────────────────────────────────

def get_rules():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT r.id, r.pattern, r.match_type, r.priority,
               ISNULL(r.use_count,0) AS use_count, c.name AS category
        FROM categorization_rules r
        JOIN child_categories c ON r.child_category_id=c.id
        ORDER BY r.priority DESC, r.use_count DESC
    """)
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_rule(pattern, category, match_type="contains", priority=5):
    conn = get_connection()
    cur  = conn.cursor()
    child_id = _resolve_child_id(cur, category)
    if child_id:
        cur.execute("""
            INSERT INTO categorization_rules (pattern,child_category_id,match_type,priority)
            VALUES (?,?,?,?)
        """, (pattern, child_id, match_type, priority))
        conn.commit()
    conn.close()


def increment_rule_use(rule_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE categorization_rules SET use_count=ISNULL(use_count,0)+1 WHERE id=?",
                (rule_id,))
    conn.commit()
    conn.close()


# ─── Reporting helpers ─────────────────────────────────────────────────────────

def get_monthly_cash_flow(months=12):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(f"""
        SELECT TOP ({int(months)})
               FORMAT(date,'yyyy-MM') AS month,
               SUM(CASE WHEN amount>0 THEN amount      ELSE 0 END) AS income,
               SUM(CASE WHEN amount<0 THEN ABS(amount) ELSE 0 END) AS expenses
        FROM transactions
        WHERE ISNULL(is_transfer,0)=0
        GROUP BY FORMAT(date,'yyyy-MM')
        ORDER BY month DESC
    """)
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["income"]   = _to_float(r.get("income"))
        r["expenses"] = _to_float(r.get("expenses"))
    return list(reversed(rows))


def get_spending_by_category(start_date, end_date):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT c.name AS category, p.name AS parent_category,
               SUM(ABS(t.amount)) AS total
        FROM transactions t
        JOIN child_categories  c ON t.child_category_id=c.id
        JOIN parent_categories p ON c.parent_id=p.id
        WHERE t.amount<0
          AND ISNULL(t.is_transfer,0)=0
          AND t.date BETWEEN ? AND ?
          AND p.is_income=0
        GROUP BY c.name, p.name
        ORDER BY total DESC
    """, (start_date, end_date))
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["total"] = _to_float(r.get("total"))
    return rows


def get_income_by_category(start_date, end_date):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT c.name AS category, p.name AS parent_category,
               SUM(t.amount) AS total
        FROM transactions t
        JOIN child_categories  c ON t.child_category_id=c.id
        JOIN parent_categories p ON c.parent_id=p.id
        WHERE t.amount>0
          AND ISNULL(t.is_transfer,0)=0
          AND t.date BETWEEN ? AND ?
          AND p.is_income=1
        GROUP BY c.name, p.name
        ORDER BY total DESC
    """, (start_date, end_date))
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["total"] = _to_float(r.get("total"))
    return rows


def get_category_monthly_summary(start_date, end_date):
    """Returns spending per category per month for the Income & Expense report."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT FORMAT(t.date,'yyyy-MM') AS month,
               p.name AS parent_category,
               c.name AS category,
               p.is_income,
               SUM(t.amount) AS total
        FROM transactions t
        JOIN child_categories  c ON t.child_category_id=c.id
        JOIN parent_categories p ON c.parent_id=p.id
        WHERE ISNULL(t.is_transfer,0)=0
          AND t.date BETWEEN ? AND ?
        GROUP BY FORMAT(t.date,'yyyy-MM'), p.name, c.name, p.is_income
        ORDER BY month, parent_category, category
    """, (start_date, end_date))
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["total"] = _to_float(r.get("total"))
    return rows


# ─── Goals helpers ─────────────────────────────────────────────────────────────

def get_goals():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT g.*, a.name AS account_name
        FROM goals g
        LEFT JOIN accounts a ON g.account_id = a.id
        ORDER BY g.id
    """)
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["target_amount"]  = _to_float(r.get("target_amount"))
        r["monthly_amount"] = _to_float(r.get("monthly_amount"))
    return rows


def add_goal(name, goal_type, target_amount, monthly_amount=None,
             target_date=None, account_id=None):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO goals (name, goal_type, target_amount, monthly_amount, target_date, account_id)
        VALUES (?,?,?,?,?,?)
    """, (name, goal_type, float(target_amount),
          float(monthly_amount) if monthly_amount else None,
          target_date, account_id))
    conn.commit()
    conn.close()


def delete_goal(goal_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM goals WHERE id=?", (goal_id,))
    conn.commit()
    conn.close()


def update_goal(goal_id, **kwargs):
    conn = get_connection()
    cur  = conn.cursor()
    for key, val in kwargs.items():
        cur.execute(f"UPDATE goals SET {key}=? WHERE id=?", (val, goal_id))
    conn.commit()
    conn.close()


# ─── Investment helpers ────────────────────────────────────────────────────────

def get_investment_transfers(start_date=None, end_date=None):
    conn = get_connection()
    cur  = conn.cursor()
    query = """
        SELECT t.*, a.name AS from_account, da.name AS to_account,
               t.transfer_investment_cat AS inv_category
        FROM transactions t
        LEFT JOIN accounts a  ON t.account_id             =a.id
        LEFT JOIN accounts da ON t.transfer_to_account_id =da.id
        WHERE ISNULL(t.is_transfer,0)=1
    """
    params = []
    if start_date: query += " AND t.date>=?"; params.append(start_date)
    if end_date:   query += " AND t.date<=?"; params.append(end_date)
    query += " ORDER BY t.date DESC"
    cur.execute(query, params)
    rows = [dict_factory(cur, r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["amount"] = _to_float(r.get("amount"))
    return rows
