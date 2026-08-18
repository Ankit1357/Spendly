import random
from datetime import datetime

from werkzeug.security import generate_password_hash

from database.db import get_db, init_db

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Rohan", "Rahul", "Arjun", "Karan", "Ankit",
    "Siddharth", "Nikhil", "Manish", "Pranav", "Aryan", "Harsh", "Vikram",
    "Ananya", "Priya", "Sneha", "Neha", "Pooja", "Kavya", "Divya", "Riya",
    "Meera", "Ishita", "Aishwarya", "Shruti", "Nandini", "Deepika", "Tara",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Iyer", "Nair", "Reddy", "Rao", "Menon",
    "Patel", "Desai", "Joshi", "Kulkarni", "Chatterjee", "Banerjee", "Das",
    "Mukherjee", "Kapoor", "Malhotra", "Bhat", "Pillai", "Naidu", "Sinha",
    "Chaudhary", "Agarwal", "Mehta", "Shetty", "Bose", "Dutta", "Ghosh",
]


def generate_user():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    suffix = random.randint(10, 999)
    email = f"{first.lower()}.{last.lower()}{suffix}@gmail.com"
    return name, email


def email_exists(conn, email):
    return (
        conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        is not None
    )


def main():
    init_db()
    conn = get_db()
    try:
        name, email = generate_user()
        while email_exists(conn, email):
            name, email = generate_user()

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (
                name,
                email,
                generate_password_hash("password123"),
                datetime.now().isoformat(sep=" ", timespec="seconds"),
            ),
        )
        conn.commit()

        print("User created successfully:")
        print(f"  id:    {cur.lastrowid}")
        print(f"  name:  {name}")
        print(f"  email: {email}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
