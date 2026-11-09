"""Shared helpers: error responses and a generic search/filter/sort/paginate query."""
from flask import jsonify, request

from .db import get_db

MAX_PER_PAGE = 100


def error(status, message, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def get_json():
    """Parse the JSON body; returns None if it is missing or malformed."""
    return request.get_json(silent=True)


def paginated_query(base_sql, params, *, search_cols, sort_fields, default_sort,
                    filters=None):
    """Run a list query with ?search, filters, ?sort=field|-field, ?page, ?per_page.

    base_sql  - SELECT ... FROM ... (no WHERE/ORDER/LIMIT)
    filters   - {query_param: sql_column} for exact-match filtering
    sort_fields - whitelist {api_name: sql_column} (prevents SQL injection)
    Returns (response_dict, None) or (None, error_response).
    """
    where, args = [], list(params)

    term = request.args.get("search", "").strip()
    if term and search_cols:
        where.append("(" + " OR ".join(f"{c} LIKE ?" for c in search_cols) + ")")
        args.extend([f"%{term}%"] * len(search_cols))

    for qp, col in (filters or {}).items():
        val = request.args.get(qp)
        if val not in (None, ""):
            where.append(f"{col} = ?")
            args.append(val)

    sort = request.args.get("sort", default_sort)
    desc = sort.startswith("-")
    field = sort.lstrip("-")
    if field not in sort_fields:
        return None, error(400, "Invalid sort field.",
                           {"allowed": sorted(sort_fields)})

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or not 1 <= per_page <= MAX_PER_PAGE:
            raise ValueError
    except ValueError:
        return None, error(400, f"page must be >= 1 and per_page 1-{MAX_PER_PAGE}.")

    clause = (" WHERE " + " AND ".join(where)) if where else ""
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM ({base_sql}{clause})", args).fetchone()[0]
    order = f" ORDER BY {sort_fields[field]} {'DESC' if desc else 'ASC'}"
    rows = db.execute(
        f"{base_sql}{clause}{order} LIMIT ? OFFSET ?",
        args + [per_page, (page - 1) * per_page],
    ).fetchall()

    return {
        "data": [dict(r) for r in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }, None
