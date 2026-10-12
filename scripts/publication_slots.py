"""Validate Cairo stock dates/hours and expand them into serial episode jobs."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def stock_matrix(date_text: str, hour_text: str, *, today: date | None = None) -> dict:
    today = today or datetime.now(ZoneInfo("Africa/Cairo")).date()
    digits = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    date_text = date_text.translate(digits).strip().replace("،", ",")
    hour_text = hour_text.translate(digits).strip().replace("،", ",")
    if not date_text and not hour_text:
        return {"include": [{"date": "", "hour": ""}]}
    if not date_text or not hour_text:
        raise ValueError("Provide both stock_date and stock_hour, or leave both empty")
    compact = re.fullmatch(r"(\d{1,2}(?:\s*,\s*\d{1,2})*)-(\d{1,2})-(\d{4})", date_text)
    try:
        if compact:
            days, month, year = compact.groups()
            dates = [date(int(year), int(month), int(day)) for day in days.split(",")]
        else:
            dates = [date.fromisoformat(item.strip()) for item in date_text.split(",")]
    except ValueError as exc:
        raise ValueError("Invalid stock_date: use YYYY-MM-DD, ISO dates separated by commas, or 13,14,15-10-2026") from exc
    hours = [item.strip() for item in hour_text.split(",")]
    if any(hour not in {"12", "18"} for hour in hours):
        raise ValueError("stock_hour accepts 12, 18, or 12,18 (Cairo)")
    dates = sorted(set(dates))
    hours = sorted(set(hours), key=int)
    if any(not today <= day <= today + timedelta(days=4) for day in dates):
        raise ValueError("Each stock date must be between today and four days ahead (Cairo)")
    return {"include": [{"date": day.isoformat(), "hour": hour} for day in dates for hour in hours]}


def main() -> None:
    try:
        matrix = stock_matrix(os.getenv("STOCK_DATE", ""), os.getenv("STOCK_HOUR", ""))
    except ValueError as exc:
        raise SystemExit(f"Publication input error: {exc}") from exc
    encoded = json.dumps(matrix, separators=(",", ":"))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"matrix={encoded}\n")
    print(f"Validated {len(matrix['include'])} serial episode slot(s): {encoded}")


if __name__ == "__main__":
    main()
