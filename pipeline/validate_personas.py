"""
Seed-time persona validator — run BEFORE any persona/theme data is written.

Closes the gap documented in guardrails.test.js Test 10: guardrails.js can
never see a persona whose always_orders and never_tried contradict each
other (its context only carries neverTriedCategories), so that class of bad
data must be caught here, at the seed layer, not at recommendation time.

Checks, per persona:
  1. OVERLAP — always_orders and never_tried must share zero categories.
     Compared case-insensitively: "Pet Supplies" vs "pet supplies" is still
     a contradiction.
  2. UNKNOWN/DRIFTED CATEGORY — every category must exactly match the
     canonical 11-category taxonomy (CATEGORY_KEYWORDS keys in
     ingest_themes.py). A case-insensitive match with wrong casing is
     flagged separately as CASING_DRIFT, because recommend.js's Supabase
     .in('category', ...) filters are case-sensitive at the SQL level even
     though guardrails.js now tolerates casing.
  3. DUPLICATE — a category listed twice within the same array.

Plus one cross-source check: supabase/02_seed.sql and
mvp-shell/src/data/mockPersonas.js are documented as "kept in sync
manually" — this verifies they actually are (same persona IDs, same
always_orders/never_tried per persona), since drift means the frontend
fallback shows different personas than the live DB.

Any violation fails loudly (nonzero exit, per-persona detail) — never
silently accepted.

Usage:
  python validate_personas.py               # validate both seed sources + sync
  python validate_personas.py --self-check  # synthetic good/bad cases, no files needed
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ingest_themes import CATEGORY_KEYWORDS

CANONICAL_CATEGORIES = list(CATEGORY_KEYWORDS.keys())

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_SQL_PATH = REPO_ROOT / 'supabase' / '02_seed.sql'
MOCK_JS_PATH = REPO_ROOT / 'mvp-shell' / 'src' / 'data' / 'mockPersonas.js'


def _norm(s):
    return s.strip().lower()


def validate_personas(personas, source_label):
    """personas: list of dicts with id, always_orders, never_tried.
    Returns a list of violation strings (empty = clean)."""
    violations = []
    canonical_by_norm = {_norm(c): c for c in CANONICAL_CATEGORIES}

    for p in personas:
        pid = p.get('id', '<missing id>')
        always = p.get('always_orders') or []
        never = p.get('never_tried') or []

        # 1. Overlap — the check this validator exists for.
        overlap = {_norm(a) for a in always} & {_norm(n) for n in never}
        if overlap:
            violations.append(
                f'[{source_label}] persona "{pid}": OVERLAP — categories in BOTH '
                f'always_orders and never_tried: {sorted(overlap)}'
            )

        # 2. Unknown or casing-drifted categories.
        for field_name, values in (('always_orders', always), ('never_tried', never)):
            for cat in values:
                if cat in CANONICAL_CATEGORIES:
                    continue
                if _norm(cat) in canonical_by_norm:
                    violations.append(
                        f'[{source_label}] persona "{pid}": CASING_DRIFT — {field_name} has '
                        f'"{cat}", canonical is "{canonical_by_norm[_norm(cat)]}" '
                        f'(breaks case-sensitive SQL .in() filters in recommend.js)'
                    )
                else:
                    violations.append(
                        f'[{source_label}] persona "{pid}": UNKNOWN_CATEGORY — {field_name} has '
                        f'"{cat}", not in the canonical 11-category taxonomy'
                    )

        # 3. Duplicates within one array.
        for field_name, values in (('always_orders', always), ('never_tried', never)):
            normed = [_norm(v) for v in values]
            dupes = {v for v in normed if normed.count(v) > 1}
            if dupes:
                violations.append(
                    f'[{source_label}] persona "{pid}": DUPLICATE — {field_name} lists '
                    f'{sorted(dupes)} more than once'
                )

    return violations


def parse_seed_sql(path):
    """Targeted parser for 02_seed.sql's personas insert. Not a general SQL
    parser — it fails loudly (raises) if it can't extract what it expects,
    rather than returning an empty list that would vacuously pass."""
    sql = path.read_text(encoding='utf-8')

    m = re.search(r'insert into personas[^;]+;', sql, re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError(f'{path}: could not locate the "insert into personas" statement')
    block = m.group(0)

    tuples = re.findall(
        r"\(\s*'([^']+)',.*?array\[([^\]]*)\]\s*,\s*array\[([^\]]*)\]\s*\)",
        block,
        re.DOTALL,
    )
    if not tuples:
        raise ValueError(f'{path}: personas insert found but no rows parsed — update parse_seed_sql()')

    def split_array(raw):
        return [s.strip().strip("'") for s in re.findall(r"'([^']*)'", raw)]

    return [
        {'id': pid, 'always_orders': split_array(always_raw), 'never_tried': split_array(never_raw)}
        for pid, always_raw, never_raw in tuples
    ]


def parse_mock_js(path):
    """Real parse of the ESM module via node — not a regex guess at JS.
    Returns None (with a warning) if node isn't available."""
    node = shutil.which('node')
    if not node:
        print('[warn] node not found — skipping mockPersonas.js validation and the '
              'SQL<->JS sync check (SQL seed still validated)', file=sys.stderr)
        return None

    script = (
        f'const m = await import({json.dumps(path.as_uri())}); '
        'console.log(JSON.stringify(m.mockPersonas));'
    )
    result = subprocess.run(
        [node, '--input-type=module', '-e', script],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise ValueError(f'{path}: node failed to import module: {result.stderr.strip()}')
    return json.loads(result.stdout)


def check_source_sync(sql_personas, js_personas):
    """Verifies the manually-synced mirror actually matches the SQL seed."""
    violations = []
    sql_by_id = {p['id']: p for p in sql_personas}
    js_by_id = {p['id']: p for p in js_personas}

    only_sql = set(sql_by_id) - set(js_by_id)
    only_js = set(js_by_id) - set(sql_by_id)
    if only_sql:
        violations.append(f'[sync] personas only in 02_seed.sql, missing from mockPersonas.js: {sorted(only_sql)}')
    if only_js:
        violations.append(f'[sync] personas only in mockPersonas.js, missing from 02_seed.sql: {sorted(only_js)}')

    for pid in set(sql_by_id) & set(js_by_id):
        for field in ('always_orders', 'never_tried'):
            if sql_by_id[pid].get(field) != js_by_id[pid].get(field):
                violations.append(
                    f'[sync] persona "{pid}": {field} differs — '
                    f'SQL={sql_by_id[pid].get(field)} vs JS={js_by_id[pid].get(field)}'
                )
    return violations


def run_self_check():
    ok = True

    def expect(name, violations, want_codes):
        nonlocal ok
        got = all(any(code in v for v in violations) for code in want_codes) if want_codes \
            else len(violations) == 0
        status = 'PASS' if got else 'FAIL'
        print(f'  [{status}] {name}')
        if not got:
            for v in violations:
                print(f'          {v}')
            ok = False

    clean = [{'id': 'ok', 'always_orders': ['Baby Care'], 'never_tried': ['Pet Supplies']}]
    expect('clean persona produces zero violations', validate_personas(clean, 't'), [])

    overlapping = [{'id': 'bad1', 'always_orders': ['Baby Care', 'Pet Supplies'], 'never_tried': ['Pet Supplies']}]
    expect('direct overlap caught', validate_personas(overlapping, 't'), ['OVERLAP'])

    case_overlap = [{'id': 'bad2', 'always_orders': ['Pet Supplies'], 'never_tried': ['pet supplies']}]
    expect('case-insensitive overlap caught ("Pet Supplies" vs "pet supplies")',
           validate_personas(case_overlap, 't'), ['OVERLAP', 'CASING_DRIFT'])

    unknown = [{'id': 'bad3', 'always_orders': ['Baby Care'], 'never_tried': ['Groceries & Produce']}]
    expect('unknown/typo category caught', validate_personas(unknown, 't'), ['UNKNOWN_CATEGORY'])

    dupes = [{'id': 'bad4', 'always_orders': ['Baby Care', 'Baby Care'], 'never_tried': ['Pet Supplies']}]
    expect('duplicate within one array caught', validate_personas(dupes, 't'), ['DUPLICATE'])

    drifted = check_source_sync(
        [{'id': 'p1', 'always_orders': ['Baby Care'], 'never_tried': ['Pet Supplies']}],
        [{'id': 'p1', 'always_orders': ['Baby Care'], 'never_tried': ['Toys & Gifting']}],
    )
    expect('SQL<->JS sync drift caught', drifted, ['[sync]'])

    print('Self-check passed.' if ok else 'Self-check FAILED.')
    sys.exit(0 if ok else 1)


def fetch_live_personas():
    """Same query ingest_themes.py's write-time gate uses — this lets you
    run that exact check standalone, without needing real theme/review
    input files just to validate the live personas table."""
    import os

    try:
        from supabase import create_client
    except ImportError:
        print('[error] supabase package not installed. Run: pip install -r requirements.txt', file=sys.stderr)
        sys.exit(1)

    supabase_url = os.getenv('SUPABASE_URL')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not supabase_url or not service_role_key:
        print('[error] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must both be set '
              '(the anon key can still read personas, but use the service role key '
              'for consistency with the ingest-time gate)', file=sys.stderr)
        sys.exit(1)

    supabase = create_client(supabase_url, service_role_key)
    rows = supabase.table('personas').select('id, always_orders, never_tried').execute().data or []
    return rows


def main():
    parser = argparse.ArgumentParser(description='Validate persona seed data before it is written anywhere')
    parser.add_argument('--self-check', action='store_true', help='Run synthetic good/bad cases, no files needed')
    parser.add_argument('--live', action='store_true',
                         help='Validate the LIVE Supabase personas table instead of the local seed files '
                              '(requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)')
    args = parser.parse_args()

    if args.self_check:
        run_self_check()
        return

    violations = []

    if args.live:
        live_personas = fetch_live_personas()
        if not live_personas:
            print('[note] live personas table is empty — nothing to validate')
            return
        print(f'Fetched {len(live_personas)} personas from the live Supabase personas table')
        violations += validate_personas(live_personas, 'supabase.personas (live)')

        if violations:
            print(f'\nFAILED — {len(violations)} violation(s) in the LIVE personas table:', file=sys.stderr)
            for v in violations:
                print(f'  {v}', file=sys.stderr)
            sys.exit(1)
        print('\nLive personas table valid: no overlaps, no unknown categories, no duplicates.')
        return

    sql_personas = parse_seed_sql(SEED_SQL_PATH)
    print(f'Parsed {len(sql_personas)} personas from {SEED_SQL_PATH.relative_to(REPO_ROOT)}')
    violations += validate_personas(sql_personas, '02_seed.sql')

    js_personas = parse_mock_js(MOCK_JS_PATH)
    if js_personas is not None:
        print(f'Parsed {len(js_personas)} personas from {MOCK_JS_PATH.relative_to(REPO_ROOT)}')
        violations += validate_personas(js_personas, 'mockPersonas.js')
        violations += check_source_sync(sql_personas, js_personas)

    if violations:
        print(f'\nFAILED — {len(violations)} violation(s), fix the seed data before writing anything:', file=sys.stderr)
        for v in violations:
            print(f'  {v}', file=sys.stderr)
        sys.exit(1)

    print('\nAll persona seed data valid: no overlaps, no unknown categories, sources in sync.')


if __name__ == '__main__':
    main()
