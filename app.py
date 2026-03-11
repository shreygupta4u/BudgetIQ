"""
app.py — FinanceIQ personal budgeting app  (v2)
Run: streamlit run app.py
"""
from __future__ import annotations

import io
from datetime import date, timedelta
from calendar import monthrange

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_option_menu import option_menu

import database as db
import parsers as p
import categorizer as cat_engine

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="FinanceIQ", page_icon="💎",
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap');

:root {
    --bg:     #080c14;
    --card:   #0f1623;
    --elev:   #161d2e;
    --elev2:  #1c2438;
    --gold:   #f5a623;
    --teal:   #00d4b4;
    --red:    #ff4f6d;
    --green:  #00c896;
    --blue:   #4f8ef7;
    --purple: #9b6dff;
    --fg:     #e8edf5;
    --muted:  #8892a4;
    --bdr:    #1e2a3d;
    --bdr2:   #2a3650;
}

html,body,[class*="css"] {
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--fg);
}
section[data-testid="stSidebar"] {
    background: var(--card) !important;
    border-right: 1px solid var(--bdr);
}
header[data-testid="stHeader"] { display: none }
.main .block-container { padding: 1rem 1.6rem 2rem; max-width: 1500px }
h1,h2,h3 { font-family: 'Syne', sans-serif; letter-spacing: -.02em }

/* ── KPI Cards ── */
.kpi {
    background: linear-gradient(135deg, var(--elev) 0%, var(--card) 100%);
    border: 1px solid var(--bdr2);
    border-radius: 12px;
    padding: .85rem 1.1rem;
    position: relative; overflow: hidden;
}
.kpi::before {
    content: ''; position: absolute; top: 0; left: 0;
    width: 3px; height: 100%; background: var(--gold);
    border-radius: 4px 0 0 4px;
}
.kpi::after {
    content: ''; position: absolute; top: -20px; right: -20px;
    width: 70px; height: 70px; border-radius: 50%;
    background: var(--gold); opacity: .04;
}
.kpi.g::before { background: var(--green) }
.kpi.g::after  { background: var(--green) }
.kpi.r::before { background: var(--red) }
.kpi.r::after  { background: var(--red) }
.kpi.t::before { background: var(--teal) }
.kpi.t::after  { background: var(--teal) }
.kpi.b::before { background: var(--blue) }
.kpi.b::after  { background: var(--blue) }
.kpi-lbl {
    font-size: .64rem; font-weight: 600; letter-spacing: .09em;
    text-transform: uppercase; color: var(--muted); margin-bottom: .3rem;
}
.kpi-val { font-size: 1.45rem; font-weight: 700; line-height: 1.1 }
.kpi-sub { font-size: .7rem; color: var(--muted); margin-top: .25rem }

/* ── Section header ── */
.sh {
    font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700;
    letter-spacing: .02em; color: var(--fg);
    border-bottom: 1px solid var(--bdr); padding-bottom: .5rem; margin-bottom: 1rem;
    display: flex; align-items: center; gap: .5rem;
}

/* ── Transaction rows ── */
.txn-date   { font-size: .76rem; color: var(--muted); font-variant-numeric: tabular-nums }
.txn-desc   { font-size: .84rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.amt-pos    { color: var(--green); font-weight: 700; font-size: .86rem; font-variant-numeric: tabular-nums }
.amt-neg    { color: var(--red);   font-weight: 700; font-size: .86rem; font-variant-numeric: tabular-nums }

/* ── Category badge — colored, wider ── */
.cat-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 12px; border-radius: 20px;
    font-size: .72rem; font-weight: 600; letter-spacing: .02em;
    white-space: nowrap;
}

/* ── Tag badges ── */
.tag-pill {
    display: inline-flex; align-items: center; gap: 3px;
    background: #9b6dff22; color: var(--purple); border: 1px solid #9b6dff44;
    font-size: .66rem; padding: 1px 8px; border-radius: 10px; font-weight: 600;
}
.tag-split {
    background: #00d4b422; color: var(--teal); border: 1px solid var(--teal)44;
    font-size: .67rem; padding: 1px 7px; border-radius: 10px;
}

/* ── Split bar ── */
.split-bar {
    display: flex; border-radius: 6px; overflow: hidden;
    height: 8px; gap: 1px;
}
.split-seg { height: 100%; border-radius: 2px }

/* ── Split category box — compact inline ── */
.split-catbox {
    display: inline-flex; align-items: center; gap: 4px;
    background: var(--elev2); border: 1px solid var(--bdr2);
    border-radius: 20px; padding: 3px 10px;
    font-size: .70rem; font-weight: 600; width: 100%;
    flex-wrap: wrap;
}
.split-seg-label {
    display: inline-flex; align-items: center; gap: 3px;
    white-space: nowrap;
}
.split-dot {
    width: 7px; height: 7px; border-radius: 50%;
    display: inline-block; flex-shrink: 0;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--gold), #e8941a);
    color: #080c14; border: none; border-radius: 8px;
    font-weight: 700; font-family: 'Inter', sans-serif;
    padding: .4rem 1.1rem; transition: all .15s; letter-spacing: .01em;
}
.stButton > button:hover { opacity: .88; transform: translateY(-1px) }
button[kind="secondary"] {
    background: var(--elev2) !important; color: var(--muted) !important;
    border: 1px solid var(--bdr2) !important;
    padding: .25rem .55rem !important; border-radius: 7px !important;
    font-size: .83rem !important; min-width: 0 !important;
}
button[kind="secondary"]:hover { color: var(--fg) !important; border-color: var(--bdr2) !important }

/* ── Inputs ── */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > textarea,
.stDateInput > div > div > input {
    background: var(--elev) !important;
    color: var(--fg) !important;
    border: 1px solid var(--bdr2) !important;
    border-radius: 8px !important;
}
.stSelectbox > div > div:focus-within,
.stTextInput > div > div > input:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 0 2px var(--gold)22 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--card); border-radius: 10px; padding: 3px; gap: 3px;
    border: 1px solid var(--bdr);
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--muted);
    border-radius: 8px; font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: var(--elev2) !important;
    color: var(--gold) !important; font-weight: 600 !important;
}

/* ── Budget bars ── */
.bb  { background: var(--elev2); border-radius: 6px; height: 7px; overflow: hidden; margin: 3px 0 }
.bbf { height: 100%; border-radius: 6px; transition: width .3s }

/* ── Goal bars ── */
.goal-card {
    background: var(--elev); border: 1px solid var(--bdr2);
    border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: .75rem;
}
.goal-progress {
    background: var(--elev2); border-radius: 6px; height: 10px;
    overflow: hidden; margin: .5rem 0;
}
.goal-pf { height: 100%; border-radius: 6px; background: var(--teal) }

/* ── Sidebar logo ── */
.logo {
    font-family: 'Syne', sans-serif; font-size: 1.5rem; font-weight: 800;
    color: var(--gold); padding: .6rem 0 1.6rem .2rem; letter-spacing: -.02em;
}
.logo small {
    display: block; font-family: 'Inter', sans-serif; font-size: .65rem;
    color: var(--muted); letter-spacing: .12em; text-transform: uppercase;
    font-weight: 500;
}

/* ── Filter panel ── */
.filter-panel {
    background: var(--card); border: 1px solid var(--bdr2);
    border-radius: 12px; padding: .9rem 1.1rem; margin-bottom: 1rem;
}
.filter-section-lbl {
    font-size: .68rem; font-weight: 600; letter-spacing: .10em;
    text-transform: uppercase; color: var(--muted); margin-bottom: .4rem;
}
.active-filter-chip {
    display: inline-flex; align-items: center; gap: 4px;
    background: var(--gold)22; border: 1px solid var(--gold)44;
    color: var(--gold); border-radius: 20px; padding: 2px 10px;
    font-size: .73rem; font-weight: 600;
}

/* ── Investment pill ── */
.inv-pill {
    background: #00c89622; color: var(--green);
    border: 1px solid var(--green)44;
    font-size: .7rem; padding: 2px 9px; border-radius: 10px; font-weight: 600;
}

/* ── Dialog ── */
[data-testid="stModal"] > div {
    background: var(--card) !important;
    border: 1px solid var(--bdr2); border-radius: 16px;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    background: var(--card); border-radius: 10px; border: 1px solid var(--bdr);
}

/* ── Report tabs ── */
.report-tab-bar {
    display: flex; gap: 4px; background: var(--card);
    border-radius: 10px; padding: 4px; border: 1px solid var(--bdr);
    margin-bottom: 1rem;
}
.report-tab {
    flex: 1; text-align: center; padding: .45rem .5rem;
    border-radius: 8px; font-size: .8rem; font-weight: 500;
    color: var(--muted); cursor: pointer;
}
.report-tab.active {
    background: var(--elev2); color: var(--gold); font-weight: 600;
}

/* reduce streamlit default element spacing */
.stMarkdown, .element-container { margin-bottom: 0 !important }
div[data-testid="column"] { padding: 0 4px !important }
div[data-testid="stVerticalBlock"] > div { gap: 4px !important }
.stSelectbox { margin-bottom: 0 !important }
.stTextInput { margin-bottom: 0 !important }
/* Tighter expanders */
details summary { padding: .4rem .6rem !important }
details[open] { padding-bottom: .2rem !important }
::-webkit-scrollbar-track { background: var(--bg) }
::-webkit-scrollbar-thumb { background: var(--bdr2); border-radius: 3px }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px }
    cursor: pointer; opacity: .5; font-size: .85rem; margin-left: 6px;
    transition: opacity .15s;
}
.budget-edit-icon:hover { opacity: 1; color: var(--gold) }
</style>
""", unsafe_allow_html=True)

# ── Init ──────────────────────────────────────────────────────────────────────
db.init_db()
today = date.today()

PAGE_SIZE = 25

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("txn_page", 1), ("_prev_filter", ""),
             ("show_filter_panel", False), ("report_tab", "Spending")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(v):
    if v is None: return "$0.00"
    v = float(v)
    return "-${:,.2f}".format(abs(v)) if v < 0 else "${:,.2f}".format(v)

def kpi(label, value, cls="", sub=""):
    s = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="kpi {cls}">'
        f'<div class="kpi-lbl">{label}</div>'
        f'<div class="kpi-val">{fmt(value)}</div>{s}</div>',
        unsafe_allow_html=True)

def pb_base(margin=None):
    """Base plotly layout kwargs. Pass margin=dict(...) to override."""
    m = margin if margin is not None else dict(l=8, r=8, t=32, b=8)
    return dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color="#8892a4"),
                margin=m)

def mrange(yr, mo):
    return date(yr, mo, 1), date(yr, mo, monthrange(yr, mo)[1])

@st.cache_data(ttl=30)
def _cats():
    return db.get_categories()

# ── Category helpers ──────────────────────────────────────────────────────────
SPLIT_COLORS = ["#f5a623","#00d4b4","#4f8ef7","#ff4f6d","#9b6dff",
                "#00c896","#f97316","#22d3ee","#a78bfa","#fb923c"]

# Map each child category to a colour based on its parent
CAT_PALETTE = {
    "Income": "#22c55e", "Housing": "#3b82f6", "Utilities": "#0ea5e9",
    "Food & Dining": "#f59e0b", "Transportation": "#8b5cf6",
    "Health & Medical": "#ef4444", "Personal Care": "#a78bfa",
    "Shopping": "#ec4899", "Entertainment": "#06b6d4", "Travel": "#14b8a6",
    "Education": "#fbbf24", "Children & Family": "#fb923c",
    "Pets": "#84cc16", "Gifts & Donations": "#f87171",
    "Subscriptions": "#7c3aed", "Cell Phone": "#0284c7",
    "Financial": "#64748b", "Investments": "#10b981",
    "Taxes": "#dc2626", "Business Expenses": "#78716c",
    "Uncategorized": "#6b7280",
}

def _cat_color(cat_name: str, cats_list: list) -> str:
    for c in cats_list:
        if c["name"] == cat_name:
            parent = c.get("parent") or c["name"]
            return CAT_PALETTE.get(parent, "#6b7280")
    return "#6b7280"

def flat_cat_list():
    cats = _cats()
    out  = []
    parents = [c for c in cats if not c["parent"]]
    for par in parents:
        for ch in [c for c in cats if c["parent"] == par["name"]]:
            out.append(f"{par['name']} > {ch['name']}")
    return out

def child_from_display(display):
    if ">" in display:
        return display.split(">")[-1].strip()
    return display.strip()

def find_cat_index(cats_list, child_name):
    for i, c in enumerate(cats_list):
        if child_from_display(c) == child_name:
            return i
    return 0

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="logo">💎 FinanceIQ<small>Smart Money Management</small></div>',
                unsafe_allow_html=True)

    selected = option_menu(
        menu_title=None,
        options=["Dashboard","Transactions","Budgets","Goals","Accounts",
                 "Reports","Investments","Import","Settings"],
        icons=["speedometer2","list-ul","pie-chart","bullseye","bank",
               "bar-chart-line","graph-up-arrow","upload","gear"],
        default_index=0,
        styles={
            "container":          {"background-color":"transparent","padding":"0"},
            "icon":               {"color":"#8892a4","font-size":"0.85rem"},
            "nav-link":           {"font-size":"0.84rem","color":"#8892a4","border-radius":"9px",
                                   "margin":"2px 0","--hover-color":"#161d2e"},
            "nav-link-selected":  {"background-color":"#1c2438","color":"#f5a623","font-weight":"600"},
        },
    )

    st.markdown("---")
    st.markdown('<p style="font-size:.68rem;color:#8892a4;text-transform:uppercase;'
                'letter-spacing:.10em;margin-bottom:.3rem">Period</p>',
                unsafe_allow_html=True)
    period = st.selectbox("Period",
        ["Last 30 Days","This Month","Last Month","Last 3 Months","Last 6 Months","This Year","Custom"],
        label_visibility="collapsed")

    if   period == "Last 30 Days":  d_start, d_end = today - timedelta(days=30), today
    elif period == "This Month":   d_start, d_end = mrange(today.year, today.month)
    elif period == "Last Month":
        lm = today.replace(day=1) - timedelta(days=1)
        d_start, d_end = mrange(lm.year, lm.month)
    elif period == "Last 3 Months":
        d_start = (today.replace(day=1)-timedelta(days=90)).replace(day=1); d_end = today
    elif period == "Last 6 Months":
        d_start = (today.replace(day=1)-timedelta(days=180)).replace(day=1); d_end = today
    elif period == "This Year":    d_start, d_end = date(today.year,1,1), today
    else:
        d_start = st.date_input("From", today.replace(day=1))
        d_end   = st.date_input("To",   today)


# ═══════════════════════════════════════════════════════════════════════════════
# SPLIT DIALOG  (2 rows default, auto-balance second row)
# ═══════════════════════════════════════════════════════════════════════════════
@st.dialog("✂️ Split Transaction", width="large")
def split_dialog(txn):
    total = float(txn["amount"])
    cats  = flat_cat_list()

    st.markdown(
        "**{}**  ·  {}  ·  "
        "<span style='color:{};font-size:1.1rem;font-weight:700'>{}</span>".format(
            txn["description"][:60], txn["date"],
            "#00c896" if total >= 0 else "#ff4f6d", fmt(total)),
        unsafe_allow_html=True)
    st.markdown("---")

    key      = f"splits_{txn['id']}"
    existing = db.get_split_transactions(txn["id"])

    if key not in st.session_state:
        if existing:
            st.session_state[key] = [
                {"cat": s["category"], "amt": float(s["amount"]), "memo": s.get("memo","") or ""}
                for s in existing]
        else:
            st.session_state[key] = [
                {"cat": txn.get("category") or "Uncategorized", "amt": total, "memo": ""},
                {"cat": "Uncategorized", "amt": 0.0, "memo": ""},
            ]

    rows = st.session_state[key]
    n    = len(rows)

    tid = txn['id']

    # ── Auto-balance: update row[1] session_state BEFORE widgets render ─────
    # This means when row[1]'s number_input renders, it already has the right value
    # without needing st.rerun(), so the dialog stays open.
    if n == 2:
        k0 = f"sdlg_amt_{tid}_0"
        k1 = f"sdlg_amt_{tid}_1"
        if k0 in st.session_state:
            balanced = round(total - float(st.session_state[k0]), 2)
            st.session_state[k1] = balanced
            rows[1]["amt"] = balanced

    for i, row in enumerate(rows):
        c1, c2, c3, c4 = st.columns([3.2, 1.8, 2.2, 0.5])
        with c1:
            cidx = find_cat_index(cats, row["cat"])
            sel  = st.selectbox("Category", cats, index=cidx,
                                key=f"sdlg_cat_{tid}_{i}",
                                label_visibility="collapsed",
                                format_func=child_from_display)
            rows[i]["cat"] = child_from_display(sel)
        with c2:
            amt = st.number_input("Amount", value=float(row["amt"]),
                                  step=0.01, format="%.2f",
                                  key=f"sdlg_amt_{tid}_{i}",
                                  label_visibility="collapsed")
            rows[i]["amt"] = float(amt)
        with c3:
            memo = st.text_input("Note", value=row["memo"],
                                 key=f"sdlg_mem_{tid}_{i}",
                                 placeholder="optional note",
                                 label_visibility="collapsed")
            rows[i]["memo"] = memo
        with c4:
            if n > 2:
                if st.button("✕", key=f"sdlg_del_{tid}_{i}", type="secondary"):
                    rows.pop(i)
                    # Clear widget keys for removed row so state is clean
                    for suffix in ("cat","amt","mem"):
                        k = f"sdlg_{suffix}_{tid}_{i}"
                        if k in st.session_state: del st.session_state[k]
                    st.rerun()

    allocated = sum(float(r["amt"]) for r in rows)
    leftover  = round(total - allocated, 2)
    lc = "#00c896" if abs(leftover) < 0.01 else "#ff4f6d"
    st.markdown(
        f"<div style='display:flex;gap:1.5rem;margin:.5rem 0;font-size:.85rem;"
        f"background:#1c2438;border-radius:8px;padding:.5rem .9rem'>"
        f"<span>Total: <b style='color:#e8edf5'>{fmt(total)}</b></span>"
        f"<span>Allocated: <b style='color:#e8edf5'>{fmt(allocated)}</b></span>"
        f"<span>Remaining: <b style='color:{lc}'>{fmt(leftover)}</b></span></div>",
        unsafe_allow_html=True)

    ba, bb, bc, bd = st.columns([1.5, 2, 2, 1.5])
    with ba:
        if st.button("➕ Row", key=f"sdlg_addrow_{tid}"):
            rows.append({"cat":"Uncategorized","amt":0.0,"memo":""}); st.rerun()
    with bb:
        if abs(leftover) > 0.01:
            if st.button("⟵ Fill remaining", key=f"sdlg_fill_{tid}"):
                rows[-1]["amt"] = round(float(rows[-1]["amt"]) + leftover, 2)
                st.session_state[key] = rows; st.rerun()
    with bc:
        if st.button("💾 Save Splits", type="primary", key=f"sdlg_save_{tid}"):
            if abs(leftover) > 0.01:
                st.warning(f"Splits don't balance — {fmt(leftover)} unallocated.")
            else:
                splits = [{"category": r["cat"], "amount": float(r["amt"]), "memo": r["memo"]}
                          for r in rows]
                db.save_split_transactions(txn["id"], splits)
                del st.session_state[key]
                st.success("✓ Splits saved!"); st.rerun()
    with bd:
        if st.button("✕ Cancel", type="secondary", key=f"sdlg_cancel_{tid}"):
            if key in st.session_state: del st.session_state[key]
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# BUDGET EDIT DIALOG
# ═══════════════════════════════════════════════════════════════════════════════
@st.dialog("✏️ Edit Budget", width="large")
def budget_edit_dialog(cat_name, current_amount, mo_key):
    st.markdown(f"**Category:** {cat_name}")
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        new_amount = st.number_input("Budget Amount ($)", value=float(current_amount),
                                     min_value=0.0, step=25.0, format="%.2f")
    with c2:
        eff_date = st.date_input("Effective From",
                                  value=date(int(mo_key[:4]), int(mo_key[5:]), 1),
                                  help="Can be backdated, current or future month")

    st.markdown("**Carry Forward Setting:**")
    cft = st.selectbox("Carry Forward",
                        ["none", "underspent", "overspent", "both"],
                        format_func=lambda x: {
                            "none": "None — fresh budget each month",
                            "underspent": "Roll over unspent amount",
                            "overspent":  "Deduct overspend from next month",
                            "both":       "Both: roll over under- and over-spend",
                        }[x])

    if st.button("💾 Save Budget", type="primary"):
        db.upsert_budget(cat_name, mo_key, new_amount,
                         carry_forward=(cft != "none"),
                         carry_forward_type=cft,
                         effective_date=eff_date)
        st.success(f"Saved {cat_name}: {fmt(new_amount)} effective {eff_date.strftime('%b %Y')}")
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAGS + NOTES DIALOG  — single combobox-style input, auto-creates new tags
# ═══════════════════════════════════════════════════════════════════════════════
@st.dialog("🏷️ Tags & Notes", width="large")
def tags_dialog(txn):
    st.markdown(
        f"<div style='font-size:.88rem;font-weight:600;color:#e8edf5;margin-bottom:.1rem'>"
        f"{txn['description'][:60]}</div>"
        f"<div style='font-size:.75rem;color:#8892a4;margin-bottom:.8rem'>"
        f"{txn['date']}</div>",
        unsafe_allow_html=True)

    current_tags = list(txn.get("tags") or [])
    all_tags     = db.get_all_tags()

    # ── Tags section ──────────────────────────────────────────────────────────
    st.markdown("**Tags**")

    # Show current tags as removable pills
    if current_tags:
        tag_row = st.columns(min(len(current_tags), 6))
        for i, tg in enumerate(current_tags):
            with tag_row[i % len(tag_row)]:
                if st.button(f"✕ {tg}", key=f"rmtag_{txn['id']}_{i}", type="secondary"):
                    current_tags.remove(tg)
                    db.update_transaction(txn["id"], tags=current_tags)
                    st.rerun()
    else:
        st.markdown("<span style='color:#8892a4;font-size:.78rem'>No tags yet.</span>",
                    unsafe_allow_html=True)

    # Single combobox-style input: type a tag name
    # If it matches an existing one → add it; if new → create it with notice
    tag_input = st.text_input(
        "Add tag (type to search or create new)",
        placeholder="e.g. vacation, tax-deductible, business…",
        key=f"tag_input_{txn['id']}")

    if tag_input.strip():
        tg_val   = tag_input.strip()
        is_new   = tg_val not in all_tags
        already  = tg_val in current_tags

        if already:
            st.caption("✓ Already added to this transaction.")
        elif is_new:
            st.info(f"✨ Creating new tag **'{tg_val}'** — press Add below")
        else:
            st.caption(f"Existing tag · press Add to apply")

        btn_label = "➕ Create & Add" if is_new else "➕ Add"
        if st.button(btn_label, key=f"add_tag_{txn['id']}") and not already:
            current_tags.append(tg_val)
            db.update_transaction(txn["id"], tags=current_tags)
            if is_new:
                st.toast(f"✨ New tag '{tg_val}' created & added")
            else:
                st.toast(f"✓ Tag '{tg_val}' added")
            st.rerun()

    # Quick-pick from existing unused tags
    unused = [t for t in all_tags if t not in current_tags]
    if unused:
        st.caption("Quick-add existing tags:")
        qcols = st.columns(min(len(unused), 5))
        for i, t in enumerate(unused[:10]):
            with qcols[i % 5]:
                if st.button(f"+ {t}", key=f"qtag_{txn['id']}_{t}", type="secondary"):
                    current_tags.append(t)
                    db.update_transaction(txn["id"], tags=current_tags)
                    st.rerun()

    st.markdown("---")

    # ── Notes section ─────────────────────────────────────────────────────────
    st.markdown("**Notes**")
    cur_notes = txn.get("notes") or ""
    new_notes = st.text_area(
        "Notes", value=cur_notes,
        placeholder="Add any personal notes about this transaction…",
        height=100, label_visibility="collapsed",
        key=f"notes_{txn['id']}")

    if st.button("💾 Save Notes", type="primary", key=f"save_notes_{txn['id']}"):
        db.update_transaction(txn["id"], notes=new_notes)
        st.toast("✓ Notes saved")
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if selected == "Dashboard":
    st.markdown("<h1 style='margin-bottom:0'>Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8892a4;margin-top:2px'>{d_start.strftime('%b %d')} – {d_end.strftime('%b %d, %Y')}</p>",
                unsafe_allow_html=True)

    txns     = db.get_transactions(start_date=d_start, end_date=d_end)
    skip     = {"Transfer","Credit Card Payment"}
    income   = sum(float(t["amount"]) for t in txns if float(t["amount"])>0 and t["category"] not in skip and not t.get("is_transfer"))
    expenses = sum(abs(float(t["amount"])) for t in txns if float(t["amount"])<0 and t["category"] not in skip and not t.get("is_transfer"))
    savings  = income - expenses
    savr     = (savings/income*100) if income else 0.0

    accts  = db.get_account_balances()
    assets = sum(a["balance"] for a in accts if a["type"] in ("checking","investment") and a["balance"]>0)
    liabs  = sum(abs(a["balance"]) for a in accts if a["type"] in ("credit","mortgage"))
    nw     = assets - liabs

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("💵 Income",      income,  "g")
    with c2: kpi("💳 Expenses",    expenses,"r")
    with c3: kpi("🏦 Net Savings", savings, "t", f"{savr:.1f}% rate")
    with c4: kpi("📊 Net Worth",   nw,      "b", f"Assets {fmt(assets)}")
    l, r = st.columns([3,2])

    with l:
        st.markdown('<div class="sh">📈 Cash Flow — Last 6 Months</div>', unsafe_allow_html=True)
        cf = db.get_monthly_cash_flow(6)
        if cf:
            df_cf = pd.DataFrame(cf)
            fig   = go.Figure()
            fig.add_bar(x=df_cf["month"], y=df_cf["income"],   name="Income",  marker_color="#00c896", opacity=.85)
            fig.add_bar(x=df_cf["month"], y=df_cf["expenses"], name="Expenses",marker_color="#ff4f6d", opacity=.85)
            fig.add_scatter(x=df_cf["month"], y=df_cf["income"]-df_cf["expenses"],
                            name="Net", line=dict(color="#f5a623",width=2.5), mode="lines+markers",
                            marker=dict(size=6, color="#f5a623"))
            fig.update_layout(barmode="group",
                              legend=dict(orientation="h", y=1.12, font=dict(size=11)),
                              xaxis=dict(gridcolor="#1e2a3d"),
                              yaxis=dict(gridcolor="#1e2a3d"), **pb_base())
            st.plotly_chart(fig, use_container_width=True, key="dash_cashflow")
        else:
            st.info("Import transactions to see cash flow.")

    with r:
        st.markdown('<div class="sh">🍩 Spending by Category</div>', unsafe_allow_html=True)
        sp = db.get_spending_by_category(d_start, d_end)
        if sp:
            s_df = pd.DataFrame(sp[:10])
            fig2 = go.Figure(go.Pie(
                labels=s_df["category"], values=s_df["total"], hole=.58,
                textinfo="percent", textfont_size=11,
                marker=dict(colors=px.colors.qualitative.Vivid,
                            line=dict(color="#080c14",width=2))))
            fig2.update_layout(legend=dict(font=dict(size=10), x=1, y=.5), **pb_base())
            st.plotly_chart(fig2, use_container_width=True, key="dash_spending_pie")
        else:
            st.info("No spending data yet.")

    la, lb = st.columns([3,2])
    with la:
        st.markdown('<div class="sh">🕐 Recent Transactions</div>', unsafe_allow_html=True)
        recent = db.get_transactions(start_date=d_start, end_date=d_end, limit=10)
        if recent:
            rows_d = [{"Date":t["date"],"Description":t["description"][:42],
                       "Category":t["category"] or "—","Amount":float(t["amount"]),
                       "Account":(t.get("account_name") or "")[:18]} for t in recent]
            st.dataframe(pd.DataFrame(rows_d), use_container_width=True, hide_index=True,
                         column_config={"Amount": st.column_config.NumberColumn(format="$%.2f")})
        else:
            st.info("No transactions yet — use Import.")

    with lb:
        st.markdown('<div class="sh">🔥 Top Spending</div>', unsafe_allow_html=True)
        if sp:
            mv = sp[0]["total"]
            for item in sp[:7]:
                pct = min(float(item["total"])/float(mv)*100, 100)
                bc  = "#ff4f6d" if pct>80 else "#f5a623" if pct>50 else "#00c896"
                st.markdown(
                    f"<div style='margin-bottom:.75rem'>"
                    f"<div style='display:flex;justify-content:space-between;"
                    f"font-size:.82rem;margin-bottom:3px'>"
                    f"<span style='font-weight:500'>{item['category']}</span>"
                    f"<span style='color:#f5a623;font-weight:700'>{fmt(item['total'])}</span></div>"
                    f"<div class='bb'><div class='bbf' style='width:{pct:.1f}%;background:{bc}'>"
                    f"</div></div></div>",
                    unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif selected == "Transactions":
    st.markdown("<h1 style='margin-bottom:.3rem'>Transactions</h1>", unsafe_allow_html=True)

    cats_flat    = flat_cat_list()
    cats_clean   = [child_from_display(c) for c in cats_flat]
    all_cats_raw = _cats()
    accts_all    = db.get_accounts()
    all_tags     = db.get_all_tags()

    # ── Compact always-visible filter bar ──────────────────────────────────────
    # Row 1: search | account | type | sort | reset
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns([2.6, 1.6, 1.2, 1.4, 0.5])
    with r1c1:
        search = st.text_input("🔍", placeholder="Search description…",
                               key="txn_search", label_visibility="collapsed")
    with r1c2:
        acc_options = {a["name"]: a["id"] for a in accts_all}
        sel_acc_label = st.selectbox("Account", ["All Accounts"] + list(acc_options.keys()),
                                     key="txn_acc", label_visibility="collapsed")
        sel_acc_ids    = [] if sel_acc_label == "All Accounts" else [acc_options[sel_acc_label]]
        sel_acc_labels = [] if sel_acc_label == "All Accounts" else [sel_acc_label]
    with r1c3:
        amt_filter = st.selectbox("Type",
            ["All","Expenses","Income","Amount >…","Amount <…"],
            key="txn_type", label_visibility="collapsed")
    with r1c4:
        sort_by = st.selectbox("Sort", ["Date ↓","Date ↑","Amount ↓","Amount ↑"],
                               key="txn_sort", label_visibility="collapsed")
    with r1c5:
        if st.button("↺", key="txn_reset", help="Reset all filters", type="secondary"):
            for k in ["txn_search","txn_acc","txn_type","txn_sort",
                      "txn_cats","txn_tags","txn_df","txn_dt","txn_amtval","txn_page"]:
                if k in st.session_state: del st.session_state[k]
            st.rerun()

    # Row 2: categories | tags | date-from | date-to | amount-value (if needed)
    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns([2.2, 1.8, 1.2, 1.2, 1.4])
    with r2c1:
        sel_cats = st.multiselect("Categories", cats_clean, default=[],
                                  key="txn_cats", label_visibility="collapsed",
                                  placeholder="Filter by category…")
    with r2c2:
        sel_tags = st.multiselect("Tags", all_tags, default=[],
                                  key="txn_tags", label_visibility="collapsed",
                                  placeholder="Filter by tag…")
    with r2c3:
        # Default: last 30 days (independent of sidebar period)
        txn_default_start = today - timedelta(days=30)
        f_date_from = st.date_input("From", value=txn_default_start, key="txn_df",
                                    label_visibility="collapsed")
    with r2c4:
        f_date_to = st.date_input("To", value=today, key="txn_dt",
                                  label_visibility="collapsed")
    with r2c5:
        amt_val = 0.0
        if amt_filter in ("Amount >…", "Amount <…"):
            amt_val = st.number_input("Amount", value=0.0, step=10.0, format="%.2f",
                                      key="txn_amtval", label_visibility="collapsed")
        else:
            st.markdown("<span style='font-size:.73rem;color:#8892a4;line-height:3rem'>"
                        "From · To dates above</span>", unsafe_allow_html=True)

    # ── Fetch & filter ──
    txns_raw = db.get_transactions(
        start_date=f_date_from, end_date=f_date_to,
        search=search or None,
    )

    if sel_acc_ids:
        txns_raw = [t for t in txns_raw if t["account_id"] in sel_acc_ids]
    if sel_cats:
        txns_raw = [t for t in txns_raw if t.get("category") in sel_cats]
    if sel_tags:
        txns_raw = [t for t in txns_raw if any(tg in (t.get("tags") or []) for tg in sel_tags)]
    if amt_filter == "Expenses":
        txns_raw = [t for t in txns_raw if float(t["amount"]) < 0]
    elif amt_filter == "Income":
        txns_raw = [t for t in txns_raw if float(t["amount"]) > 0]
    elif amt_filter == "Amount >…":
        txns_raw = [t for t in txns_raw if abs(float(t["amount"])) > amt_val]
    elif amt_filter == "Amount <…":
        txns_raw = [t for t in txns_raw if abs(float(t["amount"])) < amt_val]

    sort_fns = {
        "Date ↓":   (lambda x: x["date"],            True),
        "Date ↑":   (lambda x: x["date"],            False),
        "Amount ↓": (lambda x: float(x["amount"]),   True),
        "Amount ↑": (lambda x: float(x["amount"]),   False),
    }
    fn, rev = sort_fns[sort_by]
    txns_raw.sort(key=fn, reverse=rev)

    txns        = txns_raw
    total_count = len(txns)
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)

    cur_filter = f"{sel_acc_ids}|{sel_cats}|{sel_tags}|{search}|{sort_by}|{amt_filter}|{amt_val}|{f_date_from}|{f_date_to}"
    if cur_filter != st.session_state["_prev_filter"]:
        st.session_state["txn_page"] = 1
        st.session_state["_prev_filter"] = cur_filter

    cur_page  = min(st.session_state["txn_page"], total_pages)
    page_txns = txns[(cur_page-1)*PAGE_SIZE : cur_page*PAGE_SIZE]

    # Summary bar
    exp_total = sum(abs(float(t["amount"])) for t in txns if float(t["amount"])<0)
    inc_total = sum(float(t["amount"])       for t in txns if float(t["amount"])>0)

    chips = []
    if sel_acc_labels:              chips.append(f"📦 {sel_acc_label}")
    if sel_cats:                    chips.append(f"🏷 {', '.join(sel_cats)}")
    if sel_tags:                    chips.append(f"🔖 {', '.join(sel_tags)}")
    if amt_filter not in ("All",):  chips.append(amt_filter)
    chip_html = "".join(f"<span class='active-filter-chip'>{c}</span> " for c in chips)

    st.markdown(
        f"<div style='display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;"
        f"font-size:.78rem;color:#8892a4;margin:.3rem 0 .5rem'>"
        f"<b style='color:#e8edf5'>{total_count}</b> transactions  ·  "
        f"<span style='color:#00c896'>▲ {fmt(inc_total)}</span>  "
        f"<span style='color:#ff4f6d'>▼ {fmt(exp_total)}</span>  "
        f"<span>pg {cur_page}/{total_pages}</span>"
        f"{'  ' + chip_html if chips else ''}</div>",
        unsafe_allow_html=True)

    if not txns:
        st.info("No transactions found. Adjust filters or import data.")
    else:
        # ── Column headers ──
        h = st.columns([0.85, 2.6, 2.4, 0.95, 1.4, 0.3])
        for col, lbl in zip(h, ["Date","Description + Tags / Notes","Category","Amount","Account","✂"]):
            col.markdown(
                f"<span style='font-size:.65rem;color:#8892a4;text-transform:uppercase;"
                f"letter-spacing:.08em;font-weight:600'>{lbl}</span>",
                unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#1e2a3d;margin:2px 0 4px'>",
                    unsafe_allow_html=True)

        # ── Pre-fetch split data ──
        split_map = {}
        for txn in page_txns:
            if txn.get("is_split"):
                split_map[txn["id"]] = db.get_split_transactions(txn["id"])

        for txn in page_txns:
            tid  = txn["id"]
            cols = st.columns([0.85, 2.6, 2.4, 0.95, 1.4, 0.3])

            # ── Date ──
            cols[0].markdown(f"<span class='txn-date'>{txn['date']}</span>",
                             unsafe_allow_html=True)

            # ── Description + inline tags & notes ──
            cur_tags  = list(txn.get("tags") or [])
            cur_notes = txn.get("notes") or ""
            tag_pills = ""
            if txn.get("is_split"):
                tag_pills += " <span class='tag-split'>✂</span>"
            for tg in cur_tags:
                tag_pills += f" <span class='tag-pill'>{tg}</span>"

            with cols[1]:
                st.markdown(
                    f"<span class='txn-desc'>{txn['description'][:44]}</span>{tag_pills}",
                    unsafe_allow_html=True)
                # Two compact inputs side-by-side
                ti1, ti2 = st.columns([1, 1.6])
                with ti1:
                    new_tag = st.text_input("tag", value="",
                                            placeholder="＋ add tag…",
                                            key=f"ti_tag_{tid}",
                                            label_visibility="collapsed")
                    if new_tag.strip():
                        t = new_tag.strip()
                        if t not in cur_tags:
                            cur_tags.append(t)
                            db.update_transaction(tid, tags=cur_tags)
                            st.rerun()
                with ti2:
                    new_notes = st.text_input("note", value=cur_notes,
                                              placeholder="📝 note…",
                                              key=f"ti_note_{tid}",
                                              label_visibility="collapsed")
                    if new_notes != cur_notes:
                        db.update_transaction(tid, notes=new_notes)

            # ── Category / Split bar ──
            cur_cat = txn.get("category") or "Uncategorized"
            cidx    = find_cat_index(cats_flat, cur_cat)
            clr     = _cat_color(cur_cat, _cats())

            if txn.get("is_split"):
                splits = split_map.get(tid, [])
                if splits:
                    tot_abs = sum(abs(float(s["amount"])) for s in splits) or 1
                    bar_segs = ""
                    lbl_segs = ""
                    for i, s in enumerate(splits):
                        sc  = SPLIT_COLORS[i % len(SPLIT_COLORS)]
                        pct = abs(float(s["amount"])) / tot_abs * 100
                        nm  = (s.get("category") or "?")[:14]
                        amt = fmt(abs(float(s["amount"])))
                        bar_segs += (
                            f"<div style='flex:{pct:.2f};background:{sc};min-width:2px'></div>")
                        lbl_segs += (
                            f"<div style='flex:{pct:.2f};overflow:hidden;padding:0 2px;"
                            f"min-width:0'>"
                            f"<div style='font-size:.6rem;font-weight:700;color:{sc};"
                            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>"
                            f"{nm}</div>"
                            f"<div style='font-size:.57rem;color:#8892a4;white-space:nowrap'>"
                            f"{amt}</div>"
                            f"</div>")
                    # Bar (8px) + labels (28px) = ~36px total ≈ selectbox height
                    cols[2].markdown(
                        f"<div style='width:100%'>"
                        f"<div style='display:flex;border-radius:3px;overflow:hidden;"
                        f"height:8px;gap:1px'>{bar_segs}</div>"
                        f"<div style='display:flex;margin-top:3px;height:28px'>{lbl_segs}</div>"
                        f"</div>",
                        unsafe_allow_html=True)
                else:
                    cols[2].markdown(
                        f"<span class='cat-badge' style='background:{clr}22;"
                        f"border:1px solid {clr}55;color:{clr}'>{cur_cat}</span>",
                        unsafe_allow_html=True)
            else:
                # Color-tinted selectbox: inject border color via targeted CSS
                cols[2].markdown(
                    f"<style>div[data-testid='stSelectbox']:has(> label + div "
                    f"[data-baseweb='select']) {{ border-color:{clr}55 }}</style>",
                    unsafe_allow_html=True)
                new_cat_raw = cols[2].selectbox(
                    "cat", cats_flat, index=cidx,
                    key=f"cat_{tid}",
                    label_visibility="collapsed",
                    format_func=child_from_display)
                new_cat = child_from_display(new_cat_raw)
                if new_cat != cur_cat:
                    db.update_transaction(tid, category=new_cat)
                    cat_engine.learn_from_correction(txn["description"], new_cat, cur_cat)
                    st.toast("✓ Category saved")

            # ── Amount ──
            ac = "amt-pos" if float(txn["amount"]) >= 0 else "amt-neg"
            cols[3].markdown(f"<span class='{ac}'>{fmt(txn['amount'])}</span>",
                             unsafe_allow_html=True)

            # ── Account ──
            cols[4].markdown(
                f"<span style='font-size:.73rem;color:#8892a4'>"
                f"{(txn.get('account_name') or '')[:20]}</span>",
                unsafe_allow_html=True)

            # ── Split button ──
            if cols[5].button("✂", key=f"split_{tid}_{cur_page}",
                              help="Split transaction", type="secondary"):
                split_dialog(txn)

            st.markdown("<hr style='border-color:#1e2a3d;margin:1px 0'>",
                        unsafe_allow_html=True)

        # ── Pagination ──
        if total_pages > 1:
            pcols = st.columns([1, 0.5, 0.7, 0.5, 1])
            with pcols[1]:
                if cur_page > 1:
                    if st.button("← Prev", key="pg_prev"):
                        st.session_state["txn_page"] = cur_page - 1; st.rerun()
            with pcols[2]:
                st.markdown(
                    f"<div style='text-align:center;font-size:.8rem;color:#8892a4;"
                    f"padding:.4rem 0'>{cur_page} / {total_pages}</div>",
                    unsafe_allow_html=True)
            with pcols[3]:
                if cur_page < total_pages:
                    if st.button("Next →", key="pg_next"):
                        st.session_state["txn_page"] = cur_page + 1; st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# BUDGETS  — Performance tab only, with inline edit icon
# ═══════════════════════════════════════════════════════════════════════════════
elif selected == "Budgets":
    st.markdown("<h1>Budgets</h1>", unsafe_allow_html=True)

    mo_opts = []
    for yr in [today.year-1, today.year, today.year+1]:
        for mo in range(1,13):
            mo_opts.append(f"{yr}-{mo:02d}")
    # default to current month
    default_idx = mo_opts.index(f"{today.year}-{today.month:02d}") if f"{today.year}-{today.month:02d}" in mo_opts else 0
    mo_key  = st.selectbox("Month", mo_opts, index=default_idx)
    my, mm  = int(mo_key[:4]), int(mo_key[5:])
    ms, me  = mrange(my, mm)

    sp   = db.get_spending_by_category(ms, me)
    smap = {s["category"]: float(s["total"]) for s in sp}
    bmap_raw = db.get_budgets(mo_key)
    bmap = {b["category"]: b for b in bmap_raw}

    cats  = _cats()
    exp_c = [c for c in cats if not c["is_income"] and c["parent"]]
    tb    = sum(b["amount"] for b in bmap.values())
    ts    = sum(smap.get(c["name"],0) for c in exp_c if c["name"] in bmap)
    tr    = tb - ts

    b1,b2,b3 = st.columns(3)
    with b1: kpi("Budgeted",  tb, "b")
    with b2: kpi("Spent",     ts, "r")
    with b3: kpi("Remaining", tr, "g" if tr>=0 else "r")

    st.markdown('<div class="sh">📊 Budget Performance  <span style="font-size:.7rem;color:#8892a4;font-weight:400">(click ✏️ to edit any budget)</span></div>',
                unsafe_allow_html=True)

    items = []
    for c in exp_c:
        b_info = bmap.get(c["name"])
        budgeted = b_info["amount"] if b_info else 0
        spent    = smap.get(c["name"], 0)
        if budgeted > 0 or spent > 0:
            cft = b_info.get("carry_forward_type","none") if b_info else "none"
            items.append({"cat": c["name"], "icon": c.get("icon",""),
                          "budgeted": budgeted, "spent": spent, "cft": cft})
    items.sort(key=lambda x: (x["spent"]/x["budgeted"]*100) if x["budgeted"] else 100, reverse=True)

    for it in items:
        pct = (it["spent"]/it["budgeted"]*100) if it["budgeted"] else 100
        bc  = "#ff4f6d" if pct>100 else "#f5a623" if pct>75 else "#00c896"
        rem = it["budgeted"] - it["spent"]
        cft_badge = ""
        if it["cft"] != "none":
            cft_badge = f" <span style='font-size:.65rem;color:#9b6dff;background:#9b6dff22;padding:1px 7px;border-radius:10px'>⟳ {it['cft']}</span>"

        r1,r2,r3,r4,r5,r6 = st.columns([3.5,1.5,1.5,1.3,0.4,0.4])
        with r1:
            st.markdown(
                f"<div style='margin:3px 0'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"font-size:.83rem;margin-bottom:3px'>"
                f"<span>{'🔴 ' if pct>100 else ''}{it['icon']} {it['cat']}{cft_badge}</span>"
                f"<span style='color:{bc};font-weight:600'>{min(pct,999):.0f}%</span></div>"
                f"<div class='bb'><div class='bbf' style='width:{min(pct,100):.1f}%;"
                f"background:{bc}'></div></div></div>",
                unsafe_allow_html=True)
        with r2:
            st.markdown(f"<div style='font-size:.78rem;color:#8892a4;text-align:right'>Budget<br><b style='color:#e8edf5'>{fmt(it['budgeted'])}</b></div>",unsafe_allow_html=True)
        with r3:
            st.markdown(f"<div style='font-size:.78rem;color:#8892a4;text-align:right'>Spent<br><b style='color:#ff4f6d'>{fmt(it['spent'])}</b></div>",unsafe_allow_html=True)
        with r4:
            rc = "#00c896" if rem>=0 else "#ff4f6d"
            st.markdown(f"<div style='font-size:.78rem;color:#8892a4;text-align:right'>Left<br><b style='color:{rc}'>{fmt(rem)}</b></div>",unsafe_allow_html=True)
        with r5:
            if st.button("✏️", key=f"bgt_edit_{it['cat']}", help=f"Edit budget",
                         type="secondary"):
                budget_edit_dialog(it["cat"], it["budgeted"], mo_key)
        with r6:
            if st.button("🗑", key=f"bgt_del_{it['cat']}", help=f"Delete budget",
                         type="secondary"):
                db.delete_budget(it["cat"], mo_key)
                st.toast(f"✓ Deleted {it['cat']} budget")
                st.rerun()
        st.markdown("<hr style='border-color:#1e2a3d;margin:2px 0'>", unsafe_allow_html=True)

    # Show categories with no budget yet
    no_budget = [c for c in exp_c if c["name"] not in bmap and smap.get(c["name"],0) > 0]
    if no_budget:
        with st.expander(f"➕ {len(no_budget)} categories with spending but no budget"):
            for c in no_budget:
                rb1, rb2 = st.columns([4,1])
                with rb1:
                    st.markdown(f"<span style='font-size:.83rem'>{c.get('icon','')} {c['name']} — spent {fmt(smap.get(c['name'],0))}</span>",
                                unsafe_allow_html=True)
                with rb2:
                    if st.button("Set Budget", key=f"set_bgt_{c['name']}", type="secondary"):
                        budget_edit_dialog(c["name"], 0, mo_key)

    if not items:
        st.info("No budget data yet. Click ✏️ next to any category to set a budget.")

    st.markdown("---")
    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("📋 Copy Budgets from Last Month"):
            prev = (date(my,mm,1)-timedelta(days=1))
            pb = db.get_budgets(prev.strftime("%Y-%m"))
            for b in pb:
                db.upsert_budget(b["category"], mo_key, b["amount"])
            st.success(f"Copied {len(pb)} budgets"); st.rerun()
    with bc2:
        # Delete all — guarded by confirm checkbox
        if st.checkbox("☑ Enable delete", key="bgt_del_confirm"):
            if st.button("🗑️ Delete ALL Budgets", type="secondary"):
                db.delete_all_budgets()
                st.success("All budgets deleted."); st.rerun()
        else:
            st.markdown(
                "<span style='font-size:.75rem;color:#8892a4'>"
                "Tick checkbox to unlock delete.</span>",
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# GOALS
# ═══════════════════════════════════════════════════════════════════════════════
elif selected == "Goals":
    st.markdown("<h1>Goals 🎯</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8892a4'>Set savings goals as a total target or a monthly contribution.</p>",
                unsafe_allow_html=True)

    goals   = db.get_goals()
    accts   = db.get_accounts()
    acc_map = {a["name"]: a["id"] for a in accts}

    # Show existing goals
    if goals:
        st.markdown('<div class="sh">Active Goals</div>', unsafe_allow_html=True)
        for g in goals:
            # Compute simple progress: if monthly goal, estimate from account balance
            target  = g["target_amount"]
            monthly = g["monthly_amount"] or 0
            acc_bal = 0
            if g.get("account_id"):
                for a in accts:
                    if a["id"] == g["account_id"]:
                        acc_bal = max(a["balance"], 0); break

            # Progress = account balance vs target (or months × monthly)
            if g["goal_type"] == "monthly":
                # Show monthly progress bar
                pct = min((monthly / target * 100) if target else 0, 100)
                progress_label = f"{fmt(monthly)}/mo towards {fmt(target)}"
            else:
                pct = min((acc_bal / target * 100) if target else 0, 100)
                progress_label = f"{fmt(acc_bal)} saved of {fmt(target)}"

            bar_color = "#00c896" if pct >= 100 else "#f5a623" if pct >= 50 else "#4f8ef7"

            with st.container():
                gc1, gc2, gc3 = st.columns([4,2,0.6])
                with gc1:
                    st.markdown(
                        f"<div class='goal-card'>"
                        f"<div style='display:flex;justify-content:space-between;align-items:center'>"
                        f"<div style='font-weight:600;font-size:.9rem'>🎯 {g['name']}</div>"
                        f"<div style='font-size:.75rem;color:#8892a4'>{g.get('account_name','Any Account')}</div>"
                        f"</div>"
                        f"<div style='font-size:.78rem;color:#8892a4;margin:.3rem 0'>{progress_label}</div>"
                        f"<div class='goal-progress'><div class='goal-pf' style='width:{pct:.1f}%;background:{bar_color}'></div></div>"
                        f"<div style='display:flex;justify-content:space-between;font-size:.73rem;color:#8892a4;margin-top:.3rem'>"
                        f"<span>Target: <b style='color:#e8edf5'>{fmt(target)}</b></span>"
                        f"{'<span>Monthly: <b style=color:#e8edf5>' + fmt(monthly) + '</b></span>' if monthly else ''}"
                        f"{'<span>By: <b style=color:#e8edf5>' + str(g['target_date']) + '</b></span>' if g.get('target_date') else ''}"
                        f"</div>"
                        f"<div style='font-size:.8rem;color:{bar_color};font-weight:700;margin-top:.3rem'>{pct:.0f}% complete</div>"
                        f"</div>",
                        unsafe_allow_html=True)
                with gc3:
                    if st.button("🗑", key=f"del_goal_{g['id']}", help="Delete goal",
                                 type="secondary"):
                        db.delete_goal(g["id"]); st.rerun()

    st.markdown("---")
    st.markdown('<div class="sh">➕ Add New Goal</div>', unsafe_allow_html=True)

    ng1, ng2 = st.columns(2)
    with ng1:
        goal_name = st.text_input("Goal Name", placeholder="e.g. Emergency Fund, Vacation")
        goal_type = st.radio("Goal Type", ["Total Target", "Monthly Savings"],
                             horizontal=True)
        target_amount = st.number_input("Target Amount ($)", value=10000.0, min_value=0.0, step=500.0)

    with ng2:
        monthly_amount = None
        if goal_type == "Monthly Savings":
            monthly_amount = st.number_input("Monthly Savings ($)", value=500.0, min_value=0.0, step=50.0)

        target_date = st.date_input("Target Date (optional)", value=None)
        acc_options = ["(None)"] + list(acc_map.keys())
        sel_acc = st.selectbox("Linked Account", acc_options,
                               help="The account where savings are deposited")
        account_id = acc_map.get(sel_acc) if sel_acc != "(None)" else None

    if st.button("🎯 Add Goal", type="primary") and goal_name:
        gt = "monthly" if goal_type == "Monthly Savings" else "total"
        db.add_goal(goal_name, gt, target_amount, monthly_amount, target_date, account_id)
        st.success(f"Goal '{goal_name}' created!"); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# ACCOUNTS
# ═══════════════════════════════════════════════════════════════════════════════
elif selected == "Accounts":
    st.markdown("<h1>Accounts</h1>", unsafe_allow_html=True)
    accts  = db.get_account_balances()
    assets = sum(a["balance"] for a in accts if a["type"] in ("checking","investment") and a["balance"]>0)
    liabs  = sum(abs(a["balance"]) for a in accts if a["type"] in ("credit","mortgage"))
    nw     = assets - liabs

    n1,n2,n3 = st.columns(3)
    with n1: kpi("Total Assets",      assets, "g")
    with n2: kpi("Total Liabilities", liabs,  "r")
    with n3: kpi("Net Worth",         nw,     "t")

    for group, gtype in [("💵 Checking","checking"),("💳 Credit Cards","credit"),
                         ("📈 Investments","investment"),("🏠 Mortgage","mortgage")]:
        ga = [a for a in accts if a["type"]==gtype]
        if not ga: continue
        st.markdown(f'<div class="sh">{group}</div>', unsafe_allow_html=True)
        for a in ga:
            bc = "#00c896" if a["balance"]>=0 else "#ff4f6d"
            r1,r2,r3,r4,r5 = st.columns([2.5,1.2,1,1.5,1])
            with r1:
                num_str = (f" · <span style='color:#8892a4;font-size:.75rem'>{a['account_number']}</span>"
                           if a.get("account_number") else "")
                st.markdown(
                    f"<div style='padding:.35rem 0'>"
                    f"<div style='font-weight:600'>{a['name']}{num_str}</div>"
                    f"<div style='color:#8892a4;font-size:.76rem'>{a['institution']} · {a['currency']}</div>"
                    f"</div>", unsafe_allow_html=True)
            with r2:
                st.markdown(
                    f"<div style='font-size:1.05rem;font-weight:700;color:{bc};padding:.45rem 0'>"
                    f"{fmt(a['balance'])}</div>", unsafe_allow_html=True)
            with r3:
                new_name = st.text_input("Name", value=a["name"], key=f"an_{a['id']}",
                                         label_visibility="collapsed")
            with r4:
                nb = st.number_input("Bal", value=float(a["balance"]), step=100.0,
                                     key=f"ab_{a['id']}", label_visibility="collapsed")
            with r5:
                if st.button("Update", key=f"upd_{a['id']}"):
                    if new_name != a["name"]: db.update_account_name(a["id"], new_name)
                    db.update_account_balance(a["id"], nb)
                    st.success("✓"); st.rerun()
        st.markdown("<hr style='border-color:#1e2a3d'>", unsafe_allow_html=True)

    with st.expander("➕ Add Account Manually"):
        na1,na2,na3,na4,na5 = st.columns(5)
        with na1: nn  = st.text_input("Name")
        with na2: ni  = st.selectbox("Institution",
                         ["Wealthsimple","Rogers Bank","Questrade","CIBC","TD","RBC","BMO","Scotiabank","Other"])
        with na3: nt  = st.selectbox("Type", ["checking","credit","investment","mortgage"])
        with na4: nc  = st.selectbox("Currency", ["CAD","USD"])
        with na5: num = st.text_input("Account # (optional)", placeholder="****1234")
        if st.button("Add") and nn:
            db.upsert_account(nn, ni, nt, nc, account_number=num or None)
            st.success(f"Added: {nn}"); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ═══════════════════════════════════════════════════════════════════════════════
elif selected == "Reports":
    st.markdown("<h1 style='margin-bottom:.2rem'>Reports</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='display:inline-flex;align-items:center;gap:6px;"
        f"background:#161d2e;border:1px solid #2a3650;border-radius:20px;"
        f"padding:3px 12px;font-size:.74rem;color:#8892a4;margin-bottom:.5rem'>"
        f"📅 {d_start.strftime('%b %d, %Y')} — {d_end.strftime('%b %d, %Y')}</div>",
        unsafe_allow_html=True)

    txns  = db.get_transactions(start_date=d_start, end_date=d_end)
    VIVID = px.colors.qualitative.Vivid

    def stat_badge(label, value, color="#e8edf5"):
        return (f"<div style='background:#161d2e;border:1px solid #2a3650;border-radius:10px;"
                f"padding:.55rem .85rem;text-align:center'>"
                f"<div style='font-size:.63rem;color:#8892a4;text-transform:uppercase;"
                f"letter-spacing:.08em;margin-bottom:.15rem'>{label}</div>"
                f"<div style='font-size:1.2rem;font-weight:700;color:{color}'>{value}</div>"
                f"</div>")

    def hbar(label, value, max_val, color, sub=""):
        pct = min(value / max_val * 100, 100) if max_val else 0
        return (f"<div style='margin-bottom:.45rem'>"
                f"<div style='display:flex;justify-content:space-between;font-size:.78rem;margin-bottom:2px'>"
                f"<span style='font-weight:500;color:#e8edf5'>{label}</span>"
                f"<span style='font-weight:700;color:{color}'>{sub or fmt(value)}</span></div>"
                f"<div style='background:#1c2438;border-radius:3px;height:5px;overflow:hidden'>"
                f"<div style='width:{pct:.1f}%;height:100%;background:{color};border-radius:3px'>"
                f"</div></div></div>")

    tab_spend, tab_income, tab_ie, tab_save, tab_nw, tab_monthly, tab_tax = st.tabs(
        ["💸 Spending", "💵 Income", "📊 Inc & Exp",
         "🏦 Savings", "📈 Net Worth", "📅 Monthly", "🧾 Taxes"])

    # ── SPENDING ──────────────────────────────────────────────────────────────
    with tab_spend:
        sp        = db.get_spending_by_category(d_start, d_end)
        total_exp = sum(s["total"] for s in sp)
        if not sp:
            st.info("No expense data for this period.")
        else:
            k1, k2, k3, k4 = st.columns(4)
            top_cat   = sp[0]["category"] if sp else "—"
            avg_daily = total_exp / max((d_end - d_start).days, 1)
            k1.markdown(stat_badge("Total Expenses", fmt(total_exp), "#ff4f6d"), unsafe_allow_html=True)
            k2.markdown(stat_badge("Top Category",   top_cat,       "#f5a623"), unsafe_allow_html=True)
            k3.markdown(stat_badge("Categories",     str(len(sp)),  "#4f8ef7"), unsafe_allow_html=True)
            k4.markdown(stat_badge("Avg / Day",      fmt(avg_daily),"#9b6dff"), unsafe_allow_html=True)

            chart_col, break_col = st.columns([1.3, 1])
            with chart_col:
                fig_pie = go.Figure(go.Pie(
                    labels=[s["category"] for s in sp[:10]],
                    values=[s["total"]    for s in sp[:10]],
                    hole=.6, textinfo="none",
                    marker=dict(colors=VIVID, line=dict(color="#080c14",width=2)),
                    hovertemplate="<b>%{label}</b><br>%{value:$,.2f}<extra></extra>"))
                fig_pie.add_annotation(text=f"<b>{fmt(total_exp)}</b>",
                                       x=.5, y=.5, showarrow=False,
                                       font=dict(size=13, color="#e8edf5"))
                fig_pie.update_layout(showlegend=False, height=280,
                                      **pb_base(margin=dict(l=5,r=5,t=5,b=5)))
                st.plotly_chart(fig_pie, use_container_width=True, key="rpt_spend_pie")
            with break_col:
                for i, s in enumerate(sp[:12]):
                    clr = VIVID[i % len(VIVID)]
                    pct = s["total"] / total_exp * 100 if total_exp else 0
                    st.markdown(hbar(s["category"], s["total"], total_exp, clr,
                                     f"{fmt(s['total'])} · {pct:.1f}%"), unsafe_allow_html=True)
            parent_groups: dict = {}
            for s in sp:
                par = s.get("parent_category","Other")
                parent_groups.setdefault(par, []).append(s)
            for par_name, children in sorted(parent_groups.items()):
                par_total = sum(c["total"] for c in children)
                with st.expander(f"{par_name}  —  {fmt(par_total)}", expanded=False):
                    for child in children:
                        cat_txns = [t for t in txns if t.get("category")==child["category"] and float(t["amount"])<0]
                        if not cat_txns: continue
                        st.markdown(f"<div style='font-weight:600;font-size:.8rem;color:#f5a623;margin:.4rem 0 .2rem'>{child['category']}  {fmt(child['total'])}</div>", unsafe_allow_html=True)
                        st.dataframe(pd.DataFrame([{"Date":t["date"],"Payee":t["description"][:38],"Tags":", ".join(t.get("tags") or []),"Amount":abs(float(t["amount"]))} for t in cat_txns]),
                                     use_container_width=True, hide_index=True,
                                     column_config={"Amount": st.column_config.NumberColumn(format="$%.2f")})

    # ── INCOME ────────────────────────────────────────────────────────────────
    with tab_income:
        inc_sp    = db.get_income_by_category(d_start, d_end)
        total_inc = sum(s["total"] for s in inc_sp)
        GREEN_PAL = ["#22c55e","#4ade80","#16a34a","#86efac","#15803d","#34d399","#059669"]
        if not inc_sp:
            st.info("No income data for this period.")
        else:
            k1, k2, k3 = st.columns(3)
            k1.markdown(stat_badge("Total Income",   fmt(total_inc),     "#00c896"), unsafe_allow_html=True)
            k2.markdown(stat_badge("Sources",        str(len(inc_sp)),   "#4f8ef7"), unsafe_allow_html=True)
            k3.markdown(stat_badge("Avg / Day",      fmt(total_inc/max((d_end-d_start).days,1)), "#9b6dff"), unsafe_allow_html=True)
            c_chart, c_list = st.columns([1.2, 1])
            with c_chart:
                fig_pie = go.Figure(go.Pie(
                    labels=[s["category"] for s in inc_sp], values=[s["total"] for s in inc_sp],
                    hole=.6, textinfo="none",
                    marker=dict(colors=GREEN_PAL, line=dict(color="#080c14",width=2)),
                    hovertemplate="<b>%{label}</b><br>%{value:$,.2f}<extra></extra>"))
                fig_pie.add_annotation(text=f"<b>{fmt(total_inc)}</b>", x=.5, y=.5, showarrow=False,
                                       font=dict(size=13, color="#00c896"))
                fig_pie.update_layout(showlegend=False, height=260,
                                      **pb_base(margin=dict(l=5,r=5,t=5,b=5)))
                st.plotly_chart(fig_pie, use_container_width=True, key="rpt_inc_pie")
            with c_list:
                for i, s in enumerate(inc_sp):
                    clr = GREEN_PAL[i % len(GREEN_PAL)]
                    pct = s["total"] / total_inc * 100 if total_inc else 0
                    st.markdown(hbar(s["category"], s["total"], total_inc, clr, f"{fmt(s['total'])} · {pct:.1f}%"), unsafe_allow_html=True)
            for s in inc_sp:
                cat_txns = [t for t in txns if t.get("category")==s["category"] and float(t["amount"])>0]
                if not cat_txns: continue
                with st.expander(f"{s['category']}  —  {fmt(s['total'])}", expanded=False):
                    st.dataframe(pd.DataFrame([{"Date":t["date"],"Payee":t["description"][:40],"Amount":float(t["amount"])} for t in cat_txns]),
                                 use_container_width=True, hide_index=True,
                                 column_config={"Amount": st.column_config.NumberColumn(format="$%.2f")})

    # ── INCOME & EXPENSE ──────────────────────────────────────────────────────
    with tab_ie:
        cf = db.get_monthly_cash_flow(12)
        cat_monthly = db.get_category_monthly_summary(d_start, d_end)
        if not cf:
            st.info("No data yet.")
        else:
            df_cf = pd.DataFrame(cf); df_cf["net"] = df_cf["income"] - df_cf["expenses"]
            k1, k2, k3 = st.columns(3)
            total_net = df_cf["net"].sum()
            k1.markdown(stat_badge("Net", fmt(total_net), "#00c896" if total_net>=0 else "#ff4f6d"), unsafe_allow_html=True)
            k2.markdown(stat_badge("Income",   fmt(df_cf["income"].sum()),   "#00c896"), unsafe_allow_html=True)
            k3.markdown(stat_badge("Expenses", fmt(df_cf["expenses"].sum()), "#ff4f6d"), unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_bar(x=df_cf["month"], y=df_cf["income"],   name="Income",  marker_color="#00c896", opacity=.85, marker_line_width=0)
            fig.add_bar(x=df_cf["month"], y=df_cf["expenses"], name="Expenses",marker_color="#ff4f6d", opacity=.85, marker_line_width=0)
            fig.add_scatter(x=df_cf["month"], y=df_cf["net"], name="Net",
                            line=dict(color="#f5a623",width=2.5), mode="lines+markers",
                            marker=dict(size=7,color="#f5a623",line=dict(color="#080c14",width=1.5)))
            fig.update_layout(barmode="group", xaxis=dict(gridcolor="#1e2a3d"),
                              yaxis=dict(gridcolor="#1e2a3d"),
                              legend=dict(orientation="h",y=1.12,bgcolor="rgba(0,0,0,0)"),
                              **pb_base(), height=300)
            st.plotly_chart(fig, use_container_width=True, key="rpt_ie_bar")
            if cat_monthly:
                df_cm = pd.DataFrame(cat_monthly)
                months_sorted = sorted(df_cm["month"].unique())
                pivot_rows = []
                for par in df_cm["parent_category"].unique():
                    par_df  = df_cm[df_cm["parent_category"]==par]
                    par_row = {"Category": f"▸ {par}"}
                    par_total = 0
                    for m in months_sorted:
                        v = par_df[par_df["month"]==m]["total"].sum()
                        par_row[m] = v; par_total += v
                    par_row["Total"] = par_total
                    pivot_rows.append(par_row)
                    for cat in par_df["category"].unique():
                        cat_df  = par_df[par_df["category"]==cat]
                        cat_row = {"Category": f"   {cat}"}; cat_total = 0
                        for m in months_sorted:
                            v = cat_df[cat_df["month"]==m]["total"].sum()
                            cat_row[m] = v; cat_total += v
                        cat_row["Total"] = cat_total; pivot_rows.append(cat_row)
                pivot_df = pd.DataFrame(pivot_rows).fillna(0)
                disp_cols = ["Category"] + months_sorted + ["Total"]
                st.dataframe(pivot_df[disp_cols], use_container_width=True, hide_index=True,
                             column_config={c: st.column_config.NumberColumn(format="$,.2f") for c in months_sorted+["Total"]})

    # ── SAVINGS ───────────────────────────────────────────────────────────────
    with tab_save:
        cf = db.get_monthly_cash_flow(12)
        if not cf:
            st.info("No data yet.")
        else:
            df = pd.DataFrame(cf)
            df["net"]          = df["income"] - df["expenses"]
            df["savings_rate"] = (df["net"] / df["income"].replace(0,1)*100).round(1)
            df["cumulative"]   = df["net"].cumsum()
            k1,k2,k3,k4 = st.columns(4)
            k1.markdown(stat_badge("Total Saved",   fmt(df["net"].sum()),       "#00c896"), unsafe_allow_html=True)
            k2.markdown(stat_badge("Avg/Month",     fmt(df["net"].mean()),      "#4f8ef7"), unsafe_allow_html=True)
            k3.markdown(stat_badge("Avg Rate",      f"{df['savings_rate'].mean():.1f}%","#f5a623"), unsafe_allow_html=True)
            k4.markdown(stat_badge("Peak Rate",     f"{df['savings_rate'].max():.1f}%","#9b6dff"), unsafe_allow_html=True)
            fig = go.Figure()
            bar_colors = ["#00c896" if v>=0 else "#ff4f6d" for v in df["net"]]
            fig.add_bar(x=df["month"], y=df["net"], name="Monthly", marker_color=bar_colors, opacity=.85, marker_line_width=0)
            fig.add_scatter(x=df["month"], y=df["cumulative"], name="Cumulative",
                            line=dict(color="#f5a623",width=2.5), mode="lines+markers",
                            marker=dict(size=7,color="#f5a623"), yaxis="y2")
            fig.update_layout(yaxis=dict(gridcolor="#1e2a3d",title="Monthly"),
                              yaxis2=dict(overlaying="y",side="right",title="Cumulative",showgrid=False,color="#f5a623"),
                              legend=dict(orientation="h",y=1.12,bgcolor="rgba(0,0,0,0)"),
                              **pb_base(), height=300)
            st.plotly_chart(fig, use_container_width=True, key="rpt_save_bar")
            st.dataframe(df[["month","income","expenses","net","savings_rate","cumulative"]].rename(
                columns={"month":"Month","income":"Income","expenses":"Expenses","net":"Net","savings_rate":"Rate %","cumulative":"Cumulative"}),
                use_container_width=True, hide_index=True,
                column_config={c: st.column_config.NumberColumn(format="$,.2f") for c in ["Income","Expenses","Net","Cumulative"]})

    # ── NET WORTH ─────────────────────────────────────────────────────────────
    with tab_nw:
        accts  = db.get_account_balances()
        assets = sum(a["balance"] for a in accts if a["type"] in ("checking","investment") and a["balance"]>0)
        liabs  = sum(abs(a["balance"]) for a in accts if a["type"] in ("credit","mortgage"))
        nw     = assets - liabs
        k1,k2,k3 = st.columns(3)
        k1.markdown(stat_badge("Assets",      fmt(assets), "#00c896"), unsafe_allow_html=True)
        k2.markdown(stat_badge("Liabilities", fmt(liabs),  "#ff4f6d"), unsafe_allow_html=True)
        k3.markdown(stat_badge("Net Worth",   fmt(nw), "#00c896" if nw>=0 else "#ff4f6d"), unsafe_allow_html=True)
        if accts:
            all_items = ([(a["name"],a["balance"],"#00c896") for a in accts if a["type"] in ("checking","investment") and a["balance"]>0]
                        +[(a["name"],-abs(a["balance"]),"#ff4f6d") for a in accts if a["type"] in ("credit","mortgage")])
            names  = [x[0] for x in all_items]+["Net Worth"]
            values = [x[1] for x in all_items]+[nw]
            colors = [x[2] for x in all_items]+["#f5a623"]
            fig = go.Figure(go.Bar(x=names, y=values, marker_color=colors,
                                   text=[fmt(v) for v in values], textposition="outside",
                                   textfont=dict(size=11,color="#8892a4")))
            fig.update_layout(xaxis=dict(gridcolor="#1e2a3d"),
                              yaxis=dict(gridcolor="#1e2a3d",zeroline=True,zerolinecolor="#2a3650"),
                              **pb_base(), height=280, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, key="rpt_nw_bar")
        col_a, col_l = st.columns(2)
        asset_accts = [a for a in accts if a["type"] in ("checking","investment") and a["balance"]>0]
        liab_accts  = [a for a in accts if a["type"] in ("credit","mortgage")]
        with col_a:
            st.markdown('<div class="sh">Assets</div>', unsafe_allow_html=True)
            for a in asset_accts:
                st.markdown(f"<div style='display:flex;justify-content:space-between;font-size:.82rem;padding:.35rem .2rem;border-bottom:1px solid #1e2a3d'><span>{a['name']}<br><span style='font-size:.7rem;color:#8892a4'>{a['institution']}</span></span><span style='color:#00c896;font-weight:700'>{fmt(a['balance'])}</span></div>", unsafe_allow_html=True)
        with col_l:
            st.markdown('<div class="sh">Liabilities</div>', unsafe_allow_html=True)
            for a in liab_accts:
                st.markdown(f"<div style='display:flex;justify-content:space-between;font-size:.82rem;padding:.35rem .2rem;border-bottom:1px solid #1e2a3d'><span>{a['name']}<br><span style='font-size:.7rem;color:#8892a4'>{a['institution']}</span></span><span style='color:#ff4f6d;font-weight:700'>{fmt(abs(a['balance']))}</span></div>", unsafe_allow_html=True)
        if not accts:
            st.info("Add accounts to track net worth.")

    # ── MONTHLY SUMMARY ───────────────────────────────────────────────────────
    with tab_monthly:
        cf = db.get_monthly_cash_flow(12)
        if not cf:
            st.info("No data yet.")
        else:
            df = pd.DataFrame(cf)
            df["net"]          = df["income"] - df["expenses"]
            df["savings_rate"] = (df["net"]/df["income"].replace(0,1)*100).round(1)
            k1,k2,k3,k4 = st.columns(4)
            best_mo  = df.loc[df["net"].idxmax(),"month"] if not df.empty else "—"
            k1.markdown(stat_badge("12mo Income",   fmt(df["income"].sum()),  "#00c896"), unsafe_allow_html=True)
            k2.markdown(stat_badge("12mo Expenses", fmt(df["expenses"].sum()),  "#ff4f6d"), unsafe_allow_html=True)
            k3.markdown(stat_badge("Best Month",    best_mo,                    "#f5a623"), unsafe_allow_html=True)
            k4.markdown(stat_badge("Avg Net",       fmt(df["net"].mean()),      "#4f8ef7"), unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_bar(x=df["month"], y=df["income"],   name="Income",  marker_color="#00c896", opacity=.85, marker_line_width=0)
            fig.add_bar(x=df["month"], y=df["expenses"], name="Expenses",marker_color="#ff4f6d", opacity=.85, marker_line_width=0)
            fig.add_scatter(x=df["month"], y=df["net"], name="Net",
                            line=dict(color="#f5a623",width=2.5), mode="lines+markers",
                            marker=dict(size=7,color="#f5a623",line=dict(color="#080c14",width=1.5)))
            fig.update_layout(barmode="group", xaxis=dict(gridcolor="#1e2a3d"), yaxis=dict(gridcolor="#1e2a3d"),
                              legend=dict(orientation="h",y=1.12,bgcolor="rgba(0,0,0,0)"),
                              **pb_base(), height=300)
            st.plotly_chart(fig, use_container_width=True, key="rpt_monthly_bar")
            fig2 = go.Figure(go.Scatter(x=df["month"], y=df["savings_rate"],
                             fill="tozeroy", line=dict(color="#9b6dff",width=2),
                             fillcolor="rgba(155,109,255,0.1)",
                             hovertemplate="%{x}: %{y:.1f}%<extra></extra>"))
            fig2.update_layout(title="Savings Rate %", xaxis=dict(gridcolor="#1e2a3d"), yaxis=dict(gridcolor="#1e2a3d"),
                               height=150, **pb_base(margin=dict(l=8,r=8,t=28,b=8)))
            st.plotly_chart(fig2, use_container_width=True, key="rpt_monthly_sparkline")
            st.dataframe(df[["month","income","expenses","net","savings_rate"]].rename(columns={"month":"Month","income":"Income","expenses":"Expenses","net":"Net","savings_rate":"Rate %"}),
                         use_container_width=True, hide_index=True,
                         column_config={c: st.column_config.NumberColumn(format="$,.2f") for c in ["Income","Expenses","Net"]})

    # ── TAXES ─────────────────────────────────────────────────────────────────
    with tab_tax:
        inc_sp = db.get_income_by_category(d_start, d_end)
        exp_sp = db.get_spending_by_category(d_start, d_end)
        TAX_KW = ["tax","donation","charitable","rrsp","resp","business","tuition","education"]
        tax_cats     = [s for s in exp_sp if any(k in s["category"].lower() for k in TAX_KW)]
        income_total = sum(s["total"] for s in inc_sp)
        tax_total    = sum(s["total"] for s in tax_cats)
        ded_rate     = tax_total/income_total*100 if income_total else 0
        k1,k2,k3 = st.columns(3)
        k1.markdown(stat_badge("Total Income",      fmt(income_total), "#00c896"), unsafe_allow_html=True)
        k2.markdown(stat_badge("Tax-Related Spend", fmt(tax_total),    "#ff4f6d"), unsafe_allow_html=True)
        k3.markdown(stat_badge("Deductible Rate",   f"{ded_rate:.1f}%","#f5a623"), unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1:
            st.markdown('<div class="sh">💵 Income Sources</div>', unsafe_allow_html=True)
            for s in inc_sp:
                pct = s["total"]/income_total*100 if income_total else 0
                st.markdown(hbar(s["category"],s["total"],income_total,"#00c896",f"{fmt(s['total'])}  {pct:.1f}%"), unsafe_allow_html=True)
            if not inc_sp: st.info("No income data.")
        with tc2:
            st.markdown('<div class="sh">🧾 Deductions & Tax Payments</div>', unsafe_allow_html=True)
            for s in tax_cats:
                pct = s["total"]/tax_total*100 if tax_total else 0
                st.markdown(hbar(s["category"],s["total"],tax_total,"#f5a623",f"{fmt(s['total'])}  {pct:.1f}%"), unsafe_allow_html=True)
            if not tax_cats: st.info("No tax-related expenses.")
        st.markdown("---")
        st.markdown("<div style='background:#1c2438;border:1px solid #2a3650;border-radius:10px;padding:.7rem 1rem;font-size:.8rem;color:#8892a4'>💡 <b style='color:#f5a623'>Tax tip:</b> Export a CSV from the Import page and share with your accountant.</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# INVESTMENTS
# ═══════════════════════════════════════════════════════════════════════════════
elif selected == "Investments":
    st.markdown("<h1>Investments</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8892a4'>Track contributions & allocations across all investment accounts.</p>",
                unsafe_allow_html=True)

    accts     = db.get_account_balances()
    inv_accts = [a for a in accts if a["type"] == "investment"]

    if not inv_accts:
        st.info("No investment accounts yet. Import a Questrade or Wealthsimple CSV to create one.")
    else:
        cols_inv = st.columns(min(len(inv_accts), 4))
        for i, a in enumerate(inv_accts[:4]):
            with cols_inv[i]:
                kpi(f"📈 {a['name'][:20]}", a["balance"], "g",
                    f"{a['institution']} {a.get('account_number') or ''}")

    transfers     = db.get_investment_transfers(d_start, d_end)
    all_transfers = db.get_investment_transfers()

    st.markdown(f'<div class="sh">💸 Investment Contributions — {d_start} to {d_end}</div>',
                unsafe_allow_html=True)

    if all_transfers:
        cat_totals = {}
        for t in all_transfers:
            ic = t.get("inv_category") or t.get("to_account") or "General"
            cat_totals[ic] = cat_totals.get(ic, 0) + abs(float(t["amount"]))

        if cat_totals:
            fig = go.Figure(go.Pie(
                labels=list(cat_totals.keys()), values=list(cat_totals.values()),
                hole=.5, textinfo="percent+label", textfont_size=11,
                marker=dict(colors=px.colors.qualitative.Set2,
                            line=dict(color="#080c14", width=2))))
            fig.update_layout(title="Contributions by Category (All Time)", **pb_base())
            st.plotly_chart(fig, use_container_width=True, key="inv_contributions_pie")

        inv_transfers = [t for t in transfers if
                         next((a["type"] for a in accts if a["id"]==t.get("transfer_to_account_id")),"")=="investment"
                         or t.get("inv_category")]
        if inv_transfers:
            rows_d = [{"Date":t["date"],"Description":t["description"][:40],
                       "From":t.get("from_account","?"),"To":t.get("to_account","?"),
                       "Category":t.get("inv_category") or "General",
                       "Amount":abs(float(t["amount"])),"Currency":t.get("currency","CAD")}
                      for t in inv_transfers]
            st.dataframe(pd.DataFrame(rows_d), use_container_width=True, hide_index=True,
                         column_config={"Amount":st.column_config.NumberColumn(format="$%.2f")})
    else:
        st.info("No investment transfers yet.")


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORT
# ═══════════════════════════════════════════════════════════════════════════════
elif selected == "Import":
    st.markdown("<h1>Import Transactions</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8892a4'>Upload one or more CSV files at once. "
                "Account numbers are auto-detected for deduplication.</p>",
                unsafe_allow_html=True)

    HINTS = {
        "Wealthsimple Cash":   "Date · Description · Withdrawals ($) · Deposits ($) · Balance ($)",
        "Rogers Mastercard":   "Transaction Date · Description · Transaction Amount · Type",
        "Questrade":           "Transaction Date · Action · Symbol · Description · Net Amount · Currency",
        "Wealthsimple Invest": "Date · Type · Symbol · Description · Net Amount · Currency",
        "CIBC Mortgage":       "Date · Description · Debit ($) · Credit ($) · Balance ($)",
    }

    col_i, col_h = st.columns([2,3])
    with col_i:
        institution = st.selectbox("Institution", list(p.INSTITUTION_PARSERS.keys()))
    with col_h:
        st.markdown(
            f"<div style='background:var(--elev);border:1px solid var(--bdr2);"
            f"border-radius:10px;padding:.75rem;font-size:.77rem;color:#8892a4;"
            f"margin-top:1.7rem'>"
            f"<b style='color:#f5a623'>Expected columns:</b><br>{HINTS[institution]}</div>",
            unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        f"Upload {institution} CSV(s)",
        type=["csv"],
        accept_multiple_files=True)

    if uploaded_files:
        total_inserted = total_skipped = 0
        for uploaded in uploaded_files:
            with st.expander(f"📄 {uploaded.name}", expanded=(len(uploaded_files)==1)):
                try:
                    raw = uploaded.read().decode("utf-8", errors="replace")
                    detected_name, detected_num = p.extract_account_info(
                        io.StringIO(raw), institution)

                    preview_df = pd.read_csv(io.StringIO(raw))
                    st.markdown(f'<div class="sh">Preview — {len(preview_df)} rows</div>',
                                unsafe_allow_html=True)
                    st.dataframe(preview_df.head(5), use_container_width=True, hide_index=True)

                    card_html = ("  ·  Card #: <b style='color:#00c896'>" + detected_num + "</b>"
                                 if detected_num else "")
                    st.markdown(
                        f"<div style='background:#00c89611;border:1px solid #00c89644;"
                        f"border-radius:8px;padding:.65rem;font-size:.83rem;margin:.5rem 0'>"
                        f"🔍 Detected: <b style='color:#00c896'>{detected_name}</b>"
                        f"{card_html}"
                        f"</div>", unsafe_allow_html=True)

                    custom_name = st.text_input("Account display name",
                                                value=detected_name,
                                                key=f"imp_name_{uploaded.name}")

                    if st.button(f"📥 Import {len(preview_df)} rows from {uploaded.name}",
                                 type="primary", key=f"imp_btn_{uploaded.name}"):
                        inst_name, acc_type = p.ACCOUNT_TYPES[institution]
                        acct_id = db.upsert_account(custom_name, inst_name, acc_type,
                                                    account_number=detected_num)
                        with st.spinner("Parsing…"):
                            transactions = p.parse_csv(
                                io.StringIO(raw), institution, acct_id,
                                account_name=custom_name, account_number=detected_num)
                        with st.spinner("Categorizing…"):
                            transactions = cat_engine.categorize_batch(transactions)
                        with st.spinner("Saving…"):
                            ins, skp = db.insert_transactions(transactions)
                        total_inserted += ins; total_skipped += skp
                        rc1, rc2, rc3 = st.columns(3)
                        rc1.success(f"✅ {ins} imported")
                        rc2.warning(f"⏭ {skp} skipped")
                        rc3.info(f"📄 {len(transactions)} parsed")
                except Exception as e:
                    st.error(f"Failed to parse {uploaded.name}: {e}")
                    import traceback
                    st.code(traceback.format_exc(), language="python")

        if len(uploaded_files) > 1 and (total_inserted + total_skipped) > 0:
            st.markdown("---")
            st.markdown(
                f"<div style='background:var(--elev2);border:1px solid var(--bdr2);"
                f"border-radius:10px;padding:1rem;font-size:.9rem'>"
                f"<b>Combined total:</b> "
                f"<span style='color:#00c896'>{total_inserted} imported</span>  ·  "
                f"<span style='color:#f5a623'>{total_skipped} duplicates skipped</span>"
                f"</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**⬇️ Export**")
    exp_txns = db.get_transactions(start_date=d_start, end_date=d_end)
    if exp_txns:
        exp_df = pd.DataFrame(exp_txns)
        keep   = [c for c in ["date","description","category","amount",
                               "currency","account_name","memo","tags","is_split"]
                  if c in exp_df.columns]
        st.download_button("Export CSV", data=exp_df[keep].to_csv(index=False),
                           file_name=f"financeiq_{d_start}_{d_end}.csv", mime="text/csv")


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
elif selected == "Settings":
    st.markdown("<h1>Settings</h1>", unsafe_allow_html=True)

    tab_c, tab_r, tab_d = st.tabs(["🏷️ Categories","📋 Rules","🗃️ Data"])

    with tab_c:
        cats    = _cats()
        parents = [c for c in cats if not c["parent"]]
        st.markdown(f"### Categories  ({len(cats)} defined)")
        for par in parents:
            children = [c for c in cats if c["parent"]==par["name"]]
            with st.expander(f"{par.get('icon','')} **{par['name']}** "
                             f"({'Income' if par['is_income'] else str(len(children))+' subcategories'})",
                             expanded=False):
                if children:
                    rows_d = [{"Icon":c.get("icon",""),"Name":c["name"],
                               "Type":"Income" if c["is_income"] else "Expense"}
                              for c in children]
                    st.dataframe(pd.DataFrame(rows_d), use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("### Add Category")
        nc1,nc2,nc3,nc4 = st.columns(4)
        with nc1: cn = st.text_input("Name", key="cn")
        with nc2:
            plist = ["(none)"] + [c["name"] for c in cats if not c["parent"]]
            cp    = st.selectbox("Parent", plist)
        with nc3: ci = st.text_input("Icon", value="💰", max_chars=4)
        with nc4: cm = st.checkbox("Income?")
        if st.button("Add") and cn:
            db.add_category(cn, None if cp=="(none)" else cp, icon=ci, is_income=int(cm))
            st.cache_data.clear(); st.success(f"Added: {cn}"); st.rerun()

    with tab_r:
        st.markdown("### Categorization Rules")
        rules = db.get_rules()
        if rules:
            rd = pd.DataFrame(rules)[["pattern","category","match_type","priority","use_count"]]
            rd.columns = ["Pattern","Category","Match Type","Priority","Uses"]
            st.dataframe(rd, use_container_width=True, hide_index=True)
        else:
            st.info("No rules yet — auto-created when you change a category.")
        st.markdown("---")
        st.markdown("### Add Rule")
        mr1,mr2,mr3,mr4 = st.columns(4)
        with mr1: rp   = st.text_input("Pattern", placeholder="e.g. starbucks")
        with mr2: rcat = st.selectbox("Category", [c["name"] for c in _cats()], key="rc")
        with mr3: rmt  = st.selectbox("Match", ["contains","startswith","exact","regex"])
        with mr4: rpr  = st.number_input("Priority", value=5, min_value=0, max_value=100)
        if st.button("Add Rule") and rp:
            db.add_rule(rp, rcat, match_type=rmt, priority=rpr)
            st.success("Added"); st.rerun()

    with tab_d:
        st.markdown("### Database")
        try:
            conn = db.get_connection()
            cur  = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM transactions");            tc  = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM accounts");               ac  = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM categorization_rules");   rc  = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM goals");                  gc  = cur.fetchone()[0]
            conn.close()
            d1,d2,d3,d4 = st.columns(4)
            d1.metric("Transactions", tc); d2.metric("Accounts", ac)
            d3.metric("Custom Rules", rc); d4.metric("Goals", gc)
        except Exception as e:
            st.error(f"DB error: {e}")
        st.markdown(f"**Connection:** `{db.DB_PATH}`")
        st.markdown("---")
        st.markdown("### ⚠️ Danger Zone")
        with st.expander("Delete all transactions"):
            confirm = st.text_input("Type DELETE ALL to confirm")
            if st.button("🗑 Delete") and confirm == "DELETE ALL":
                conn = db.get_connection()
                cur  = conn.cursor()
                cur.execute("DELETE FROM split_transactions")
                cur.execute("DELETE FROM transactions")
                conn.commit(); conn.close()
                st.success("Deleted."); st.rerun()
