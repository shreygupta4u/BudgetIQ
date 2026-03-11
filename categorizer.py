"""
categorizer.py — Rule-based transaction categorization (no AI).
Applies fast regex patterns first, then user-saved DB rules.
Auto-learns from manual corrections.
"""
from __future__ import annotations

import re
from typing import Optional
import database as db

# ─── Built-in Canadian merchant patterns ─────────────────────────────────────
FAST_RULES = [
    (r"netflix",                                    "Streaming Services"),
    (r"spotify",                                    "Streaming Services"),
    (r"apple\.com/bill|itunes",                     "Streaming Services"),
    (r"disney\+|disneyplus",                        "Streaming Services"),
    (r"crave|cravetv",                              "Streaming Services"),
    (r"amazon prime|prime video",                   "Streaming Services"),
    (r"youtube premium",                            "Streaming Services"),
    (r"hbo|paramount\+",                            "Streaming Services"),
    (r"tim hortons|tims\b",                         "Coffee & Cafes"),
    (r"starbucks",                                  "Coffee & Cafes"),
    (r"second cup",                                 "Coffee & Cafes"),
    (r"\bcoffee\b|\bcafe\b",                        "Coffee & Cafes"),
    (r"mcdonalds|mcdonald",                         "Fast Food"),
    (r"burger king",                                "Fast Food"),
    (r"\bwendy",                                    "Fast Food"),
    (r"\bsubway\b",                                 "Fast Food"),
    (r"\bkfc\b|kentucky fried",                     "Fast Food"),
    (r"pizza hut|dominos|pizza pizza",              "Fast Food"),
    (r"\ba&w\b|harveys|mary brown|popeyes",         "Fast Food"),
    (r"five guys|chipotle|taco bell",               "Fast Food"),
    (r"loblaws|no frills",                          "Groceries"),
    (r"sobeys|safeway",                             "Groceries"),
    (r"\bmetro\b(?!.*transit)",                     "Groceries"),
    (r"\biga\b",                                    "Groceries"),
    (r"costco",                                     "Groceries"),
    (r"walmart",                                    "Groceries"),
    (r"food basics",                                "Groceries"),
    (r"t&t supermarket",                            "Groceries"),
    (r"whole foods",                                "Groceries"),
    (r"fortinos|zehrs|valumart|freshco",            "Groceries"),
    (r"farm boy|highland farms|independence grocer","Groceries"),
    (r"esso|exxon",                                 "Gas & Fuel"),
    (r"petro.canada|petrocan",                      "Gas & Fuel"),
    (r"\bshell\b",                                  "Gas & Fuel"),
    (r"\bhusky\b",                                  "Gas & Fuel"),
    (r"pioneer gas|ultramar|circle k",              "Gas & Fuel"),
    (r"\bsunoco\b|chevron",                         "Gas & Fuel"),
    (r"\bttc\b|toronto transit",                    "Public Transit"),
    (r"oc transpo",                                 "Public Transit"),
    (r"via rail",                                   "Public Transit"),
    (r"go transit|metrolinx",                       "Public Transit"),
    (r"\bpresto\b",                                 "Public Transit"),
    (r"\buber\b",                                   "Public Transit"),
    (r"\blyft\b",                                   "Public Transit"),
    (r"\btaxi\b|taxicab|beck taxi",                "Public Transit"),
    (r"hydro one|ontario hydro|toronto hydro",      "Utilities"),
    (r"enbridge",                                   "Utilities"),
    (r"union gas|atco gas",                         "Utilities"),
    (r"\bbell\b",                                   "Utilities"),
    (r"\brogers\b(?!.*mastercard|.*bank|.*visa)",   "Utilities"),
    (r"\btelus\b|\bfido\b|\bkoodo\b",               "Utilities"),
    (r"freedom mobile|virgin mobile",               "Utilities"),
    (r"\bshaw\b|videotron",                         "Utilities"),
    (r"shoppers drug|shoppers",                     "Pharmacy"),
    (r"rexall",                                     "Pharmacy"),
    (r"pharma",                                     "Pharmacy"),
    (r"drug mart|guardian|jean coutu",              "Pharmacy"),
    (r"goodlife|anytime fitness|planet fitness",    "Gym & Fitness"),
    (r"\bymca\b|equinox|crossfit|crunch fitness",   "Gym & Fitness"),
    (r"amazon\.(ca|com)",                           "Amazon"),
    (r"\bh&m\b|\bzara\b|\bgap\b",                  "Clothing"),
    (r"old navy|lululemon|sport chek|roots\b",      "Clothing"),
    (r"\bwinners\b|homesense|marshalls",            "Clothing"),
    (r"best buy|canada computers|memory express",   "Electronics"),
    (r"restaurant|bistro",                          "Restaurants"),
    (r"sushi|ramen|pho|thai|indian|chinese|vietnamese|noodle", "Restaurants"),
    (r"\bpub\b|\btavern\b",                         "Restaurants"),
    (r"the keg|east side mario|boston pizza",       "Restaurants"),
    (r"swiss chalet|kelsey|montana|jack astor",     "Restaurants"),
    (r"\blcbo\b|beer store|wine rack|liquor",       "Restaurants"),
    (r"hotel|marriott|hilton|hyatt|airbnb",         "Travel"),
    (r"expedia|booking\.com|trivago|priceline",     "Travel"),
    (r"air canada|westjet|porter air|swoop",        "Travel"),
    (r"doctor|dentist|clinic|hospital",             "Doctor & Dentist"),
    (r"physiotherapy|physio|chiropractic|optometrist", "Doctor & Dentist"),
    (r"cibc mortgage|rbc mortgage|td mortgage|mortgage payment", "Mortgage"),
    (r"e.?transfer|interac",                        "Transfer"),
    (r"bill payment|bpay|credit card payment",      "Credit Card Payment"),
    (r"service fee|account fee|annual fee|late fee|\bnsf\b", "Fees & Charges"),
    (r"\binterest charge\b|\binterest accrued\b",   "Interest"),
    (r"\brrsp\b|registered retirement",             "RRSP"),
    (r"\btfsa\b|tax.free savings",                  "TFSA"),
    (r"\bresp\b|education savings",                 "RESP"),
    (r"dividend|dividende|capital gain",            "Investment Income"),
    (r"payroll|direct deposit|salary",              "Salary"),
    (r"government of canada|canada revenue|\bcra\b", "Other Income"),
    (r"\bccb\b|child benefit|\bei\b",               "Other Income"),
    (r"dollarama|\bdollar store\b",                 "Shopping"),
    (r"chapters|indigo",                            "Hobbies"),
    (r"\bcineplex\b|imax|ticketmaster",             "Entertainment"),
    (r"parking|impark",                             "Parking"),
    (r"car insurance|auto insurance|intact insurance|desjardins", "Car Insurance"),
    (r"canadian tire|napa auto|midas|mr lube|jiffy lube", "Car Maintenance"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), c) for p, c in FAST_RULES]


def _fast_rule_match(description: str) -> Optional[str]:
    for pattern, category in _COMPILED:
        if pattern.search(description):
            return category
    return None


def _db_rule_match(description: str) -> Optional[tuple[str, int]]:
    rules = db.get_rules()
    desc_lower = description.lower()
    for rule in rules:
        p = rule["pattern"].lower()
        mt = rule["match_type"]
        matched = False
        if mt == "contains":
            matched = p in desc_lower
        elif mt == "startswith":
            matched = desc_lower.startswith(p)
        elif mt == "exact":
            matched = desc_lower == p
        elif mt == "regex":
            matched = bool(re.search(p, desc_lower, re.IGNORECASE))
        if matched:
            return rule["category"], rule["id"]
    return None


def categorize_transaction(description: str) -> tuple[str, float]:
    db_result = _db_rule_match(description)
    if db_result:
        cat, rule_id = db_result
        db.increment_rule_use(rule_id)
        return cat, 0.90
    fast = _fast_rule_match(description)
    if fast:
        return fast, 0.75
    return "Uncategorized", 0.0


def categorize_batch(transactions: list[dict]) -> list[dict]:
    for t in transactions:
        if not t.get("category") or t.get("category") == "Uncategorized":
            cat, conf = categorize_transaction(t.get("description", ""))
            t["category"] = cat
            t["ai_confidence"] = conf
        else:
            t.setdefault("ai_confidence", 0.80)
    return transactions


def suggest_categories(description: str, amount: float = 0.0) -> list[tuple[str, float]]:
    suggestions = []
    seen = set()
    db_result = _db_rule_match(description)
    if db_result:
        cat, _ = db_result
        suggestions.append((cat, 0.90))
        seen.add(cat)
    fast = _fast_rule_match(description)
    if fast and fast not in seen:
        suggestions.append((fast, 0.75))
        seen.add(fast)
    if not suggestions:
        suggestions.append(("Uncategorized", 0.0))
    return suggestions[:3]


def learn_from_correction(description: str, new_category: str, old_category: str):
    if not description or not new_category or new_category == old_category:
        return
    STOP = {"the", "and", "for", "inc", "ltd", "llc", "co", "ca", "purchase",
            "payment", "pos", "debit", "credit", "card", "transaction", "via",
            "ref", "from", "with", "des", "cad", "usd"}
    words = re.findall(r"[a-zA-Z]{3,}", description.lower())
    keywords = [w for w in words if w not in STOP]
    if not keywords:
        return
    best = max(keywords, key=len)
    for rule in db.get_rules():
        if rule["pattern"].lower() == best and rule["category"] == new_category:
            db.increment_rule_use(rule["id"])
            return
    db.add_rule(pattern=best, category=new_category, match_type="contains", priority=10)
