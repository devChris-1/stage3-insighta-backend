import io
import csv
import httpx
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response
from app.models import Profile
from app import db
from app.middleware import require_auth, admin_required

bp = Blueprint('main', __name__)


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


def apply_sort(query, args):
    sort_by = args.get("sort_by")
    order = args.get("order", "asc")
    if sort_by:
        column = getattr(Profile, sort_by, None)
        if column is not None:
            query = query.order_by(column.desc() if order == "desc" else column.asc())
    return query


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


def paginate_response(query, args, base_url):
    page = int(args.get("page", 1))
    limit = min(int(args.get("limit", 10)), 50)
    total = query.count()
    total_pages = (total + limit - 1) // limit

    results = query.offset((page - 1) * limit).limit(limit).all()

    def build_link(p):
        params = request.args.to_dict()
        params["page"] = p
        params["limit"] = limit
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{qs}"

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": {
            "self": build_link(page),
            "next": build_link(page + 1) if page < total_pages else None,
            "prev": build_link(page - 1) if page > 1 else None
        },
        "data": [serialize(p) for p in results]
    }


# -------- GET PROFILES --------
@bp.route('/api/profiles', methods=['GET'])
@require_auth
def get_profiles():
    query = Profile.query
    query = apply_filters(query, request.args)
    query = apply_sort(query, request.args)
    return jsonify(paginate_response(query, request.args, "/api/profiles"))


# -------- SEARCH PROFILES --------
def parse_query(q):
    q = q.lower()
    filters = {}
    if "female" in q:
        filters["gender"] = "female"
    elif "male" in q:
        filters["gender"] = "male"
    if "young" in q:
        filters["min_age"] = 16
        filters["max_age"] = 24
    if "adult" in q:
        filters["age_group"] = "adult"
    if "teenager" in q:
        filters["age_group"] = "teenager"
    if "senior" in q:
        filters["age_group"] = "senior"
    if "above" in q:
        import re
        match = re.search(r"above (\d+)", q)
        if match:
            filters["min_age"] = int(match.group(1))
    for name, code in {"nigeria": "NG", "kenya": "KE", "angola": "AO", "uganda": "UG", "united states": "US"}.items():
        if name in q:
            filters["country_id"] = code
    return filters if filters else None


@bp.route('/api/profiles/search', methods=['GET'])
@require_auth
def search_profiles():
    q = request.args.get("q")
    if not q:
        return jsonify({"status": "error", "message": "Missing query"}), 400
    filters = parse_query(q)
    if not filters:
        return jsonify({"status": "error", "message": "Unable to interpret query"}), 400
    query = apply_filters(Profile.query, filters)
    return jsonify(paginate_response(query, request.args, "/api/profiles/search"))


# -------- CREATE PROFILE (admin only) --------
@bp.route('/api/profiles', methods=['POST'])
@admin_required
def create_profile():
    data = request.get_json()
    name = data.get("name") if data else None
    if not name:
        return jsonify({"status": "error", "message": "Name is required"}), 400

    if Profile.query.filter_by(name=name).first():
        return jsonify({"status": "error", "message": "Profile already exists"}), 409

    gender_resp = httpx.get(f"https://api.genderize.io/?name={name}").json()
    age_resp = httpx.get(f"https://api.agify.io/?name={name}").json()
    country_resp = httpx.get(f"https://api.nationalize.io/?name={name}").json()

    top_country = max(country_resp.get("country", []), key=lambda c: c["probability"], default={})

    age = age_resp.get("age") or 0
    if age <= 17:
        age_group = "teenager"
    elif age <= 35:
        age_group = "adult"
    elif age <= 60:
        age_group = "middle-aged"
    else:
        age_group = "senior"

    profile = Profile(
        name=name,
        gender=gender_resp.get("gender"),
        gender_probability=gender_resp.get("probability"),
        age=age,
        age_group=age_group,
        country_id=top_country.get("country_id"),
        country_probability=top_country.get("probability"),
    )
    db.session.add(profile)
    db.session.commit()

    return jsonify({"status": "success", "data": serialize(profile)}), 201


# -------- EXPORT CSV --------
@bp.route('/api/profiles/export', methods=['GET'])
@require_auth
def export_profiles():
    if request.args.get("format") != "csv":
        return jsonify({"status": "error", "message": "Only format=csv is supported"}), 400

    query = Profile.query
    query = apply_filters(query, request.args)
    query = apply_sort(query, request.args)
    profiles = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "gender", "gender_probability", "age", "age_group",
                     "country_id", "country_name", "country_probability", "created_at"])
    for p in profiles:
        writer.writerow([p.id, p.name, p.gender, p.gender_probability, p.age, p.age_group,
                         p.country_id, p.country_name, p.country_probability,
                         p.created_at.isoformat() + "Z"])

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = f'attachment; filename="profiles_{timestamp}.csv"'
    return response
