"""Shared helpers: error responses and the list-query builder."""
from flask import jsonify, request

from .db import get_db

MAX_PER_PAGE = 100


def error(status, message, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def list_query(base_sql, *, scope_sql, scope_args, search_cols, sort_fields,
               default_sort, filters=None, ranges=None):
    """Build and run a list query.

    scope_sql/scope_args - mandatory WHERE part (e.g. "user_id = ?"), so one
                           user can never see another user's rows.
    filters  - {param: column} exact, case-insensitive match
    ranges   - {param: (column, operator)} for <= / >= comparisons
    Everything user-supplied is a bound parameter or checked against a whitelist.
    Returns (payload, None) or (None, error_response).
    """
    where, args = [scope_sql], list(scope_args)

    term = request.args.get("search", "").strip()
    if term:
        where.append("(" + " OR ".join(f"{c} LIKE ?" for c in search_cols) + ")")
        args.extend([f"%{term}%"] * len(search_cols))

    for param, col in (filters or {}).items():
        val = request.args.get(param)
        if val:
            where.append(f"{col} = ? COLLATE NOCASE")
            args.append(val)

    for param, (col, op) in (ranges or {}).items():
        val = request.args.get(param)
        if val:
            where.append(f"{col} {op} ?")
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

    clause = " WHERE " + " AND ".join(where)
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
