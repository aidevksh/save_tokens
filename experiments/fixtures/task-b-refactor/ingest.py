"""Ingest three CSV-ish record feeds into normalized dictionaries.

Each loader repeats the same parse / validate / coerce sequence.
"""


def load_users(lines):
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if line.strip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            raise ValueError("row %d: expected 3 fields, got %d" % (i, len(parts)))
        for p in parts:
            if p == "":
                raise ValueError("row %d: empty field" % i)
        rec = {}
        rec["id"] = int(parts[0])
        rec["name"] = parts[1]
        rec["email"] = parts[2].lower()
        out.append(rec)
    return out


def load_orders(lines):
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if line.strip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            raise ValueError("row %d: expected 4 fields, got %d" % (i, len(parts)))
        for p in parts:
            if p == "":
                raise ValueError("row %d: empty field" % i)
        rec = {}
        rec["id"] = int(parts[0])
        rec["user_id"] = int(parts[1])
        rec["sku"] = parts[2].upper()
        rec["qty"] = int(parts[3])
        out.append(rec)
    return out


def load_products(lines):
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if line.strip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            raise ValueError("row %d: expected 3 fields, got %d" % (i, len(parts)))
        for p in parts:
            if p == "":
                raise ValueError("row %d: empty field" % i)
        rec = {}
        rec["sku"] = parts[0].upper()
        rec["title"] = parts[1]
        rec["price_cents"] = int(round(float(parts[2]) * 100))
        out.append(rec)
    return out
