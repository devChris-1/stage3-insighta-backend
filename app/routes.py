from flask import Blueprint, request, jsonify
from app.models import Profile
from app import db

bp = Blueprint('main', __name__)

# -------- FILTER LOGIC --------
def apply_filters(query, args):
    if args.get("gender"):
        query = query.filter(Profile.gender == args.get("gender"))

    if args.get("age_group"):
        query = query.filter(Profile.age_group == args.get("age_group"))

    if args.get("country_id"):
        query = query.filter(Profile.country_id == args.get("country_id"))

    if args.get("min_age"):
        query = query.filter(Profile.age >= int(args.get("min_age")))

    if args.get("max_age"):
        query = query.filter(Profile.age <= int(args.get("max_age")))

    if args.get("min_gender_probability"):
        query = query.filter(Profile.gender_probability >= float(args.get("min_gender_probability")))

    if args.get("min_country_probability"):
        query = query.filter(Profile.country_probability >= float(args.get("min_country_probability")))

    return query

# -------- SORT --------
def apply_sort(query, args):
    sort_by = args.get("sort_by")
    order = args.get("order", "asc")

    if sort_by:
        column = getattr(Profile, sort_by, None)
        if column is not None:
            if order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
    return query

# -------- RESPONSE FORMAT --------
def serialize(profile):
    return {
        "id": profile.id,
        "name": profile.name,
        "gender": profile.gender,
        "gender_probability": profile.gender_probability,
        "age": profile.age,
        "age_group": profile.age_group,
        "country_id": profile.country_id,
        "country_name": profile.country_name,
        "country_probability": profile.country_probability,
        "created_at": profile.created_at.isoformat() + "Z"
    }

# -------- MAIN ENDPOINT --------
@bp.route('/api/profiles', methods=['GET'])
def get_profiles():
    args = request.args

    page = int(args.get("page", 1))
    limit = min(int(args.get("limit", 10)), 50)

    query = Profile.query
    query = apply_filters(query, args)

    total = query.count()

    query = apply_sort(query, args)

    results = query.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize(p) for p in results]
    })

# -------- NLP PARSER --------
def parse_query(q):
    q = q.lower()
    filters = {}

    if "male" in q:
        filters["gender"] = "male"
    if "female" in q:
        filters["gender"] = "female"

    if "young" in q:
        filters["min_age"] = 16
        filters["max_age"] = 24

    if "adult" in q:
        filters["age_group"] = "adult"

    if "teenager" in q:
        filters["age_group"] = "teenager"

    if "above" in q:
        import re
        match = re.search(r"above (\d+)", q)
        if match:
            filters["min_age"] = int(match.group(1))

    country_map = {
        "nigeria": "NG",
        "kenya": "KE",
        "angola": "AO"
    }

    for name, code in country_map.items():
        if name in q:
            filters["country_id"] = code

    return filters if filters else None

# -------- NLP ENDPOINT --------
@bp.route('/api/profiles/search', methods=['GET'])
def search_profiles():
    q = request.args.get("q")

    if not q:
        return jsonify({"status": "error", "message": "Missing query"}), 400

    filters = parse_query(q)

    if not filters:
        return jsonify({"status": "error", "message": "Unable to interpret query"}), 400

    query = Profile.query
    query = apply_filters(query, filters)

    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 10)), 50)

    total = query.count()

    results = query.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [serialize(p) for p in results]
    })
