import asyncio
import csv
import json
from typing import Dict, List, Any

import config
from monarchmoney import MonarchMoney, RequireMFAException
from utils.logger import log


OUTPUT_CSV = "monarch_piano_income.csv"
CATEGORY_NAME = "Piano Income"


async def login_client() -> MonarchMoney:
    email = config.MONARCH_EMAIL
    password = config.MONARCH_PASSWORD

    if not email or not password:
        raise SystemExit(
            "Please set MONARCH_EMAIL and MONARCH_PASSWORD in config.py for Monarch login."
        )

    mm = MonarchMoney()
    log("Attempting to load saved Monarch session (non-interactive)...")
    try:
        mm.load_session()
        # Quick probe to ensure session works
        await mm.get_subscription_details()
        log("Loaded saved session successfully.")
        return mm
    except Exception as e:
        log("Saved session not available/valid; attempting password login (may require MFA)...")

    log("Logging into Monarch Money with credentials...")
    try:
        await mm.login(email=email, password=password)
        log("Login successful.")
        try:
            mm.save_session()
        except Exception as e:
            log(f"Warning: could not save session after login: {e}")
        return mm
    except RequireMFAException:
        log("Monarch requires MFA. Please enter the current MFA code from your authenticator/email.")
        mfa_code = input("Enter MFA code: ").strip()
        # multi_factor_authenticate(email, password, code)
        await mm.multi_factor_authenticate(email, password, mfa_code)
        log("MFA successful.")
        try:
            mm.save_session()
            log("Saved session for future non-MFA runs.")
        except Exception as se:
            log(f"Warning: could not save session after MFA: {se}")
        return mm

    return mm


async def get_piano_category_id(mm: MonarchMoney) -> str:
    log(f"Locating category '{CATEGORY_NAME}'...")
    data: Dict[str, Any] = await mm.get_transaction_categories()
    categories: List[Dict[str, Any]] = data.get("categories", [])

    match = next((c for c in categories if c.get("name") == CATEGORY_NAME), None)
    if not match:
        match = next(
            (c for c in categories if c.get("name", "").lower() == CATEGORY_NAME.lower()),
            None,
        )

    if not match:
        raise SystemExit(f"Category '{CATEGORY_NAME}' not found in Monarch Money.")

    category_id = match["id"]
    log(f"Found category id: {category_id}")
    return category_id


async def fetch_all_transactions(mm: MonarchMoney, category_id: str) -> List[Dict[str, Any]]:
    limit = 500
    offset = 0
    all_results: List[Dict[str, Any]] = []

    while True:
        log(f"Fetching transactions offset {offset} limit {limit}...")
        resp: Dict[str, Any] = await mm.get_transactions(
            limit=limit,
            offset=offset,
            category_ids=[category_id],
        )

        container = resp.get("allTransactions", {})
        batch = container.get("results", []) or []
        total = container.get("totalCount", 0)

        all_results.extend(batch)
        offset += len(batch)

        if offset >= total or not batch:
            break

    log(f"Fetched {len(all_results)} transactions (totalCount reported: {total}).")
    return all_results


def normalize_row(tx: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in tx.items():
        if isinstance(value, (dict, list)):
            normalized[key] = json.dumps(value, ensure_ascii=True)
        else:
            normalized[key] = value
    return normalized


def write_csv(transactions: List[Dict[str, Any]]) -> None:
    if not transactions:
        log("No transactions to write.")
        return

    fieldnames = sorted({k for tx in transactions for k in tx.keys()})
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tx in transactions:
            writer.writerow(normalize_row(tx))

    log(f"Wrote {len(transactions)} rows to {OUTPUT_CSV}.")


async def main() -> None:
    mm = await login_client()
    category_id = await get_piano_category_id(mm)
    transactions = await fetch_all_transactions(mm, category_id)
    write_csv(transactions)


if __name__ == "__main__":
    asyncio.run(main())

