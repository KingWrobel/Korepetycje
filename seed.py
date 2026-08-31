from datetime import date, timedelta

from app import (
    app, db, User, Assignment, Tip, Video
)


with app.app_context():
    db.create_all()

    teacher = User.query.filter_by(
        email="nauczyciel@example.com"
    ).first()

    if not teacher:
        teacher = User(
            name="Jakub",
            email="nauczyciel@example.com",
            role="teacher"
        )
        teacher.set_password("Admin123!")
        db.session.add(teacher)

    student = User.query.filter_by(
        email="uczen@example.com"
    ).first()

    if not student:
        student = User(
            name="Uczeń Demo",
            email="uczen@example.com",
            role="student"
        )
        student.set_password("Uczen123!")
        db.session.add(student)
        db.session.flush()

    db.session.commit()

    if not Assignment.query.filter_by(student_id=student.id).first():
        db.session.add(
            Assignment(
                subject="Matematyka",
                title="Równania kwadratowe – zadania 1–5",
                description=(
                    "Rozwiąż zadania i prześlij zdjęcie albo PDF "
                    "z rozwiązaniem."
                ),
                due_date=date.today() + timedelta(days=7),
                student_id=student.id
            )
        )

    if not Tip.query.filter_by(student_id=student.id).first():
        db.session.add(
            Tip(
                subject="Matematyka",
                title="Zanim zaczniesz liczyć",
                content=(
                    "Najpierw uporządkuj równanie do postaci ogólnej, "
                    "a dopiero potem wyznacz a, b i c."
                ),
                student_id=student.id
            )
        )

    if not Video.query.filter_by(student_id=student.id).first():
        db.session.add(
            Video(
                subject="Geografia",
                title="Przykładowy film",
                description="Tu możesz później wkleić własny film.",
                url="https://www.youtube.com/",
                embed_url=None,
                student_id=student.id
            )
        )

    db.session.commit()

    print()
    print("==============================================")
    print("GOTOWE - WERSJA 3")
    print("==============================================")
    print("Nauczyciel:")
    print("  e-mail: nauczyciel@example.com")
    print("  hasło:  Admin123!")
    print()
    print("Uczeń demo:")
    print("  e-mail: uczen@example.com")
    print("  hasło:  Uczen123!")
    print("==============================================")
