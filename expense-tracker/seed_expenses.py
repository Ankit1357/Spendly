import random
import sys
from datetime import datetime, timedelta

from database.db import get_db, init_db

# Category -> (min_amount, max_amount, weight, [descriptions])
CATEGORIES = {
    "Food": (50, 800, 30, [
        "Groceries", "Lunch at office", "Zomato order", "Swiggy dinner",
        "Vegetables from mandi", "Chai and snacks", "Restaurant dinner",
        "Milk and bread", "Street food", "Coffee",
    ]),
    "Transport": (20, 500, 18, [
        "Auto rickshaw", "Ola cab", "Uber ride", "Metro recharge",
        "Petrol", "Bus ticket", "Local train pass", "Parking fee",
    ]),
    "Bills": (200, 3000, 15, [
        "Electricity bill", "Mobile recharge", "Broadband bill",
        "DTH recharge", "Water bill", "Gas cylinder", "Society maintenance",
    ]),
    "Health": (100, 2000, 6, [
        "Pharmacy", "Doctor consultation", "Medical tests", "Gym membership",
        "Dentist visit", "Vitamins",
    ]),
    "Entertainment": (100, 1500, 6, [
        "Movie tickets", "Netflix subscription", "Spotify", "Concert tickets",
        "Amusement park", "Gaming",
    ]),
    "Shopping": (200, 5000, 15, [
        "Myntra order", "New shoes", "Amazon purchase", "Clothes from mall",
        "Flipkart order", "Home decor", "Electronics accessory",
    ]),
    "Other": (50, 1000, 10, [
        "Miscellaneous", "Gift", "Donation", "Stationery", "Salon",
        "Repair charges",
    ]),
}


def generate_expenses(user_id, count, months):
    names = list(CATEGORIES.keys())
    weights = [CATEGORIES[n][2] for n in names]
    today = datetime.now().date()
    earliest = today - timedelta(days=months * 30)
    span_days = (today - earliest).days

    rows = []
    for _ in range(count):
        category = random.choices(names, weights=weights, k=1)[0]
        low, high, _weight, descriptions = CATEGORIES[category]
        amount = round(random.uniform(low, high), 2)
        date = (earliest + timedelta(days=random.randint(0, span_days))).isoformat()
        description = random.choice(descriptions)
        rows.append((user_id, amount, category, date, description))
    return rows


def main():
    user_id, count, months = 2, 5, 3

    init_db()
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if user is None:
            print(f"No user found with id {user_id}.")
            sys.exit(1)

        rows = generate_expenses(user_id, count, months)

        # Single transaction: roll back everything if any insert fails.
        try:
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        dates = sorted(r[3] for r in rows)
        print(f"Inserted {len(rows)} expenses for user {user_id}.")
        print(f"Date range: {dates[0]} to {dates[-1]}")
        print("\nSample of inserted records:")
        sample = conn.execute(
            "SELECT id, amount, category, date, description FROM expenses "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (user_id,),
        ).fetchall()
        for r in reversed(sample):
            print(
                f"  #{r['id']}  {r['date']}  {r['category']:<13} "
                f"Rs.{r['amount']:>8.2f}  {r['description']}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
