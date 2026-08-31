import os

from dotenv import load_dotenv

load_dotenv()

from app import app, db, User


def main():
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    name = os.environ.get("ADMIN_NAME", "Nauczyciel").strip()

    if not email or not password:
        print(
            "ADMIN_EMAIL / ADMIN_PASSWORD nie są ustawione. "
            "Pomijam tworzenie administratora."
        )
        return

    if len(password) < 10:
        raise SystemExit(
            "ADMIN_PASSWORD powinno mieć co najmniej 10 znaków."
        )

    with app.app_context():
        admin = User.query.filter_by(email=email).first()

        if admin:
            if admin.role != "teacher":
                admin.role = "teacher"
                db.session.commit()
            print(f"Administrator już istnieje: {email}")
            return

        admin = User(
            name=name,
            email=email,
            role="teacher"
        )
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        print(f"Utworzono administratora: {email}")


if __name__ == "__main__":
    main()
