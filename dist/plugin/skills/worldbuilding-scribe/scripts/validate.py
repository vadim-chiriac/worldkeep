#!/usr/bin/env python3
"""KERNEL §11 validator for a canon folder. Aligned with KERNEL v0.17.

Usage: python3 validate.py <world-folder>

ERRORS   duplicate IDs; dangling references; missing/invalid `kind`; relation
         with empty/missing `members`; `from`/`to` instead of `members`;
         violation of declared `constraints:` inherited down the type path —
         downgraded to NOTICES on artifacts carrying `fiat: true`.
WARNINGS type with no file anywhere on its path; `applies_to_kind` mismatch;
         declared `suggested_fields` absent; `weight` not a number in 0..1;
         `amount` without `unit` and without `of`; bare "now" as `when`;
         `status` outside the closed set; id != path; (scribe-managed worlds
         only) missing scribe provenance.
Ordering is derived (§6 `precedes`), so a missing `sort` is never a warning.
"""
import sys, os, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIRS = (
    os.path.join(SCRIPT_DIR, "_vendor"),
    os.path.abspath(os.path.join(
        SCRIPT_DIR, "..", "..", "..", "runtime", "_vendor")),
)
for vendor_dir in VENDOR_DIRS:
    if os.path.isdir(vendor_dir):
        sys.path.insert(0, vendor_dir)
        break

try:
    import yaml
except ImportError:
    print("pyyaml required"); sys.exit(2)

KINDS = {"entity", "idea", "relation", "type"}
#: Kinds removed from the closed set, and what replaced them. Naming the fix in
#: the error is the cheapest migration aid there is, and there is no other.
RETIRED_KINDS = {"action": "kind: entity with type: action (KERNEL v0.17)"}
STATUSES = {"canon", "draft", "deprecated"}

root = sys.argv[1].rstrip("/\\")
arts = {}
errors, warnings, notices = [], [], []

for dirpath, _, files in os.walk(root):
    for fn in files:
        if not fn.endswith(".md"):
            continue
        p = os.path.join(dirpath, fn)
        rel = os.path.relpath(p, root)[:-3].replace(os.sep, "/")
        with open(p, encoding="utf-8") as handle:
            text = handle.read()
        m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
        if not m:
            if rel.upper().startswith(("FRICTION", "README", "MANIFEST", "INDEX")):
                continue
            errors.append(f"{rel}: no YAML frontmatter")
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception as e:
            errors.append(f"{rel}: YAML parse error: {e}")
            continue
        aid = fm.get("id", rel)
        if aid in arts:
            errors.append(f"duplicate id {aid}: {arts[aid][0]} and {rel}")
        arts[aid] = (rel, fm)
        if aid != rel:
            warnings.append(f"{rel}: id '{aid}' does not match path")

scribe_world = any("scribe.origin" in fm or (fm.get("scribe") or {}).get("origin")
                   for _, fm in arts.values())
#: Artifacts with no provenance in a world that has some. Collected rather than
#: warned about one by one: the flag is all-or-nothing, so capturing a single
#: artifact into a hand-written world lights up every file the author never
#: touched. One line says the same thing without burying the real warnings.
unstamped = []


def ancestors(t):
    """types/a/b/c -> [a/b/c, a/b, a] (most specific first)."""
    parts = t.split("/")
    return ["/".join(parts[:i]) for i in range(len(parts), 0, -1)]


def inherited_constraints(t):
    """Merge constraints down the path; children tighten (override) parents."""
    merged = {
        "roles_required": [],
        "roles_unique": [],
        "role_kinds": {},
        "role_types": {},
        "suggested_fields": [],
    }
    found = False
    for path in reversed(ancestors(t)):          # root first, leaf last
        tf = arts.get(f"types/{path}")
        if not tf:
            continue
        found = True
        cons = tf[1].get("constraints")
        if not isinstance(cons, dict):
            cons = {}
        for r in cons.get("roles_required") or []:
            if r not in merged["roles_required"]:
                merged["roles_required"].append(r)
        for r in cons.get("roles_unique") or []:
            if r not in merged["roles_unique"]:
                merged["roles_unique"].append(r)
        merged["role_kinds"].update(cons.get("role_kinds") or {})
        merged["role_types"].update(cons.get("role_types") or {})
        for f in tf[1].get("suggested_fields") or []:
            if f not in merged["suggested_fields"]:
                merged["suggested_fields"].append(f)
    return (merged if found else None)


def type_owner(t):
    """The nearest defined ancestor type file, or None."""
    for path in ancestors(t):
        tf = arts.get(f"types/{path}")
        if tf:
            return path, tf[1]
    return None


def member_ids(fm):
    return [m["id"] if isinstance(m, dict) else m for m in (fm.get("members") or [])]


AMOUNT_KEYS = {"value", "unit", "per", "of"}


def check_amount(rel, a):
    for one in (a if isinstance(a, list) else [a]):
        if not isinstance(one, dict):
            warnings.append(f"{rel}: amount {one!r} is not an object")
            continue
        if "unit" not in one and "of" not in one:
            warnings.append(f"{rel}: amount has neither 'unit' nor 'of'")
        if "value" not in one:
            warnings.append(f"{rel}: amount has no 'value'")
        for k in set(one) - AMOUNT_KEYS:
            warnings.append(f"{rel}: unknown key '{k}' inside amount")


def check_constraint_declarations():
    """Validate the small formal-constraint vocabulary on type artifacts."""
    for _, (rel, fm) in sorted(arts.items()):
        if fm.get("kind") != "type":
            continue
        constraints = fm.get("constraints")
        if constraints is None:
            continue
        if not isinstance(constraints, dict):
            errors.append(f"{rel}: constraints must be a mapping")
            continue
        for field in ("role_kinds", "role_types"):
            table = constraints.get(field)
            if table is None:
                continue
            if not isinstance(table, dict) or any(
                not isinstance(role, str)
                or not role
                or not isinstance(allowed, list)
                or not allowed
                or any(not isinstance(v, str) or not v for v in allowed)
                for role, allowed in table.items()
            ):
                errors.append(
                    f"{rel}: {field} must map role names to non-empty lists of strings"
                )
        unique = constraints.get("roles_unique")
        if unique is None:
            continue
        if (
            not isinstance(unique, list)
            or any(not isinstance(role, str) or not role for role in unique)
            or len(set(unique)) != len(unique)
        ):
            errors.append(
                f"{rel}: roles_unique must be a list of distinct non-empty role strings"
            )


check_constraint_declarations()


for aid, (rel, fm) in sorted(arts.items()):
    kind, t = fm.get("kind"), fm.get("type")
    fiat = fm.get("fiat") is True
    bucket = notices if fiat else errors

    if not kind:
        errors.append(f"{rel}: missing kind")
    elif kind in RETIRED_KINDS:
        errors.append(f"{rel}: kind '{kind}' was retired; use {RETIRED_KINDS[kind]}")
    elif kind not in KINDS:
        errors.append(f"{rel}: kind '{kind}' outside closed set")
    if "from" in fm or "to" in fm:
        errors.append(f"{rel}: uses from/to instead of members")
    if kind == "relation" and not fm.get("members"):
        errors.append(f"{rel}: relation with empty/missing members")

    refs = list(member_ids(fm))
    for key in ("where", "when"):
        v = fm.get(key)
        if isinstance(v, str) and "/" in v:
            refs.append(v)
        elif isinstance(v, list):
            refs += [x for x in v if isinstance(x, str) and "/" in x]
    for r in refs:
        if r not in arts:
            errors.append(f"{rel}: dangling reference '{r}'")

    w = fm.get("when")
    if isinstance(w, str) and w.strip().lower() in {"now", "the present", "today"}:
        warnings.append(f"{rel}: bare \"{w}\" as when — point at the present period (§9)")

    st = fm.get("status")
    if st is not None and st not in STATUSES:
        warnings.append(f"{rel}: status '{st}' outside closed set")

    def chkw(x, where):
        if x is None:
            return
        if not isinstance(x, (int, float)) or not (0.0 <= x <= 1.0):
            warnings.append(f"{rel}: weight {x!r} not a number in 0..1 ({where})")
    chkw(fm.get("weight"), "relation")
    for mem in fm.get("members") or []:
        if isinstance(mem, dict):
            chkw(mem.get("weight"), f"member {mem.get('id')}")

    if "amount" in fm:
        check_amount(rel, fm["amount"])
    for stray in ("per", "unit", "of"):
        if stray in fm:
            warnings.append(
                f"{rel}: '{stray}' at top level — it belongs inside amount")

    if scribe_world and kind != "type":
        sc = fm.get("scribe") or {}
        if not (("scribe.origin" in fm or sc.get("origin")) and
                ("scribe.session" in fm or sc.get("session"))):
            unstamped.append(rel)

    if t and kind != "type":
        owner = type_owner(t)
        if not owner:
            warnings.append(f"{rel}: type '{t}' has no file anywhere on its path")
        else:
            owner_path, owner_fm = owner
            ak = owner_fm.get("applies_to_kind")
            if ak and kind and kind != ak:
                warnings.append(
                    f"{rel}: type '{t}' (defined at {owner_path}) applies_to_kind "
                    f"'{ak}' but artifact kind is '{kind}'")
            cons = inherited_constraints(t) or {}
            for f in cons.get("suggested_fields") or []:
                if f not in fm:
                    warnings.append(f"{rel}: type '{t}' suggests field '{f}' (absent)")
            roles = {}
            for mem in fm.get("members") or []:
                if isinstance(mem, dict) and mem.get("role"):
                    roles.setdefault(mem["role"], []).append(mem["id"])
            for req in cons.get("roles_required") or []:
                if req not in roles:
                    bucket.append(f"{rel}: type {t} requires role '{req}' (absent)")
            for role in cons.get("roles_unique") or []:
                count = len(roles.get(role, []))
                if count > 1:
                    bucket.append(
                        f"{rel}: type {t} allows role '{role}' at most once (found {count})"
                    )
            for role, kinds_ok in (cons.get("role_kinds") or {}).items():
                for mid in roles.get(role, []):
                    mk = arts.get(mid, (None, {}))[1].get("kind")
                    if mk and mk not in kinds_ok:
                        bucket.append(
                            f"{rel}: role '{role}' bound to kind '{mk}', requires {kinds_ok}")
            # role_types pins a role to a type path rather than a kind. It is
            # what lets a std relation say "this member is an event" now that
            # events are a type; inheritance means `action/practice` satisfies
            # a requirement for `action`, exactly as type paths do everywhere.
            for role, types_ok in (cons.get("role_types") or {}).items():
                for mid in roles.get(role, []):
                    mt = arts.get(mid, (None, {}))[1].get("type")
                    if not mt:
                        bucket.append(
                            f"{rel}: role '{role}' bound to an untyped artifact, "
                            f"requires type {types_ok}")
                        continue
                    if not any(a in types_ok for a in ancestors(mt)):
                        bucket.append(
                            f"{rel}: role '{role}' bound to type '{mt}', requires {types_ok}")

if unstamped:
    shown = ", ".join(sorted(unstamped)[:3])
    more = f", +{len(unstamped) - 3} more" if len(unstamped) > 3 else ""
    warnings.append(
        f"{len(unstamped)} artifact(s) have no scribe.origin/scribe.session "
        f"in a world that stamps provenance ({shown}{more})"
    )

print(f"artifacts: {len(arts)}")
for label, xs in (("ERROR", errors), ("WARNING", warnings), ("NOTICE (fiat)", notices)):
    print(f"\n{label}S: {len(xs)}")
    for x in xs:
        print(f"  {label}: {x}")
sys.exit(1 if errors else 0)
