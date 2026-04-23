import json
from app import create_app, db
from app.models import Profile

app = create_app()

def safe_get(item, *keys):
    for key in keys:
        if isinstance(item, dict) and key in item:
            return item[key]
    return None

with app.app_context():
    db.drop_all()
    db.create_all()
    with open("data.json") as f:
        data = json.load(f)

    # 🔥 FIXED HERE
    records = data["profiles"]

    inserted = 0

    for item in records:
        if not isinstance(item, dict):
            continue

        name = safe_get(item, "name")
        if not name:
         continue

        exists = Profile.query.filter_by(name=name).first()
        if exists:
            continue

        profile = Profile(
            name=safe_get(item, "name"),
            gender=safe_get(item, "gender"),
            gender_probability=safe_get(item, "gender_probability"),
            age=safe_get(item, "age"),
            age_group=safe_get(item, "age_group"),
            country_id=safe_get(item, "country_id"),
            country_name=safe_get(item, "country_name"),
            country_probability=safe_get(item, "country_probability")
        )

        db.session.add(profile)
        inserted += 1

    db.session.commit()

    print("Inserted:", inserted)