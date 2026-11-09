"""Shared helpers: error responses and the search/filter/sort/paginate query."""
from flask import jsonify, request

from .db import get_db

MAX_PER_PAGE = 100


def error(status, message, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def paginated_query(base_sql, *, search_terms, sort_fields, default_sort, filters=None):
    """Handle search, filter params, ?sort=field|-field, ?page, ?per_page.

    search_terms: list of (column, term) pairs, OR-ed together with LIKE
    (empty list = no search). Sort fields are whitelisted, and all values
    are bound parameters, so user input never reaches the SQL text.
    """
    where, args = [], []

    if search_terms:
        where.append("(" + " OR ".join(f"{c} LIKE ?" for c, _ in search_terms) + ")")
        args.extend(f"%{t}%" for _, t in search_terms)

    for param, col in (filters or {}).items():
        val = request.args.get(param)
        if val:
            where.append(f"{col} = ? COLLATE NOCASE")
            args.append(val)

    sort = request.args.get("sort", default_sort)
    field = sort.lstrip("-")
    if field not in sort_fields:
        return None, error(400, "Invalid sort field.", {"allowed": sorted(sort_fields)})

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        if page < 1 or not 1 <= per_page <= MAX_PER_PAGE:
            raise ValueError
    except ValueError:
        return None, error(400, f"page must be >= 1 and per_page between 1 and {MAX_PER_PAGE}.")

    clause = (" WHERE " + " AND ".join(where)) if where else ""
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM ({base_sql}{clause})", args).fetchone()[0]
    direction = "DESC" if sort.startswith("-") else "ASC"
    rows = db.execute(
        f"{base_sql}{clause} ORDER BY {sort_fields[field]} {direction}, id ASC LIMIT ? OFFSET ?",
        args + [per_page, (page - 1) * per_page],
    ).fetchall()

    return {
        "data": [dict(r) for r in rows],
        "pagination": {"page": page, "per_page": per_page, "total": total,
                       "pages": (total + per_page - 1) // per_page},
    }, None
