"""Generate LaTeX tables for the Phase 2 document from the real artefacts:
   - column dictionary  <- information_schema of a database loaded from schema.sql
   - endpoint catalogue <- openapi.yaml
Run:  python3 gen_tables.py <out_dir>
"""
import subprocess, sys, yaml, re, os
out = sys.argv[1]
def esc(s):
    s = str(s)
    for a, b in [('\\', '\\textbackslash{}'), ('&', '\\&'), ('%', '\\%'), ('#', '\\#'), ('_', '\\_'), ('$', '\\$'), ('{', '\\{'), ('}', '\\}'), ('~', '\\textasciitilde{}'), ('^', '\\^{}')]:
        s = s.replace(a, b)
    return s
def q(sql):
    r = subprocess.run(['mariadb', 'idp_db', '-B', '-N', '-e', sql], capture_output=True, text=True, check=True)
    return [l.split('\t') for l in r.stdout.rstrip('\n').split('\n') if l]

# ---------- column dictionary ----------
cols = q("SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_KEY FROM information_schema.COLUMNS "
         "WHERE TABLE_SCHEMA='idp_db' ORDER BY TABLE_NAME,ORDINAL_POSITION")
fks = {(t, c): rt for t, c, rt in q("SELECT TABLE_NAME,COLUMN_NAME,REFERENCED_TABLE_NAME FROM information_schema.KEY_COLUMN_USAGE "
                                    "WHERE TABLE_SCHEMA='idp_db' AND REFERENCED_TABLE_NAME IS NOT NULL")}
JSONCOLS = {'preproc_config', 'bbox', 'before_json', 'after_json'}
order = ['organizations', 'users', 'documents', 'processing_runs', 'extracted_fields', 'extracted_line_items', 'validation_findings',
         'reviews', 'field_corrections', 'erp_attempts', 'audit_events', 'system_settings',
         'listings', 'listing_documents', 'applications', 'application_documents']
by = {}
for t, c, ty, nl, k in cols:
    ty = 'json' if c in JSONCOLS else ty.replace('utf8mb4_unicode_ci', '')
    ty = re.sub(r'^(int|bigint)\(\d+\)', r'\1', ty)
    key = []
    if k == 'PRI': key.append('PK')
    if k == 'UNI': key.append('UNIQUE')
    if (t, c) in fks: key.append('FK $\\rightarrow$ ' + esc(fks[(t, c)]))
    by.setdefault(t, []).append((c, ty, 'yes' if nl == 'YES' else 'no', ', '.join(key)))
assert set(by) == set(order), set(by) ^ set(order)
lines = ['{\\tblstart\\footnotesize', '\\begin{longtable}{L{4.2cm}L{3.4cm}L{1.1cm}L{5.0cm}}',
         '\\hdrrow \\hdr{Column} & \\hdr{Type} & \\hdr{Null} & \\hdr{Key}\\\\ \\endhead']
ncols = 0
for t in order:
    lines.append('\\rowcolor{teal!18}\\multicolumn{4}{l}{\\textbf{\\texttt{%s}}}\\\\' % esc(t))
    for c, ty, nl, key in by[t]:
        ncols += 1
        lines.append('\\texttt{%s} & %s & %s & %s\\\\' % (esc(c), esc(ty), nl, key))
lines += ['\\hline', '\\end{longtable}}']
open(os.path.join(out, 'p2_gen_dict.tex'), 'w').write('\n'.join(lines) + '\n')

# ---------- endpoint catalogue ----------
spec = yaml.safe_load(open('openapi.yaml'))
ab = {'OPERATOR': 'Op', 'REVIEWER': 'Rev', 'ADMIN': 'Adm', 'COMPANY': 'Co', 'APPLICANT': 'App', 'public': 'all'}
rows = []
for path, p in spec['paths'].items():
    for m, o in p.items():
        if m not in ('get', 'post', 'put', 'patch', 'delete'): continue
        roles = o.get('x-roles')
        rtxt = 'public' if path.startswith('/health') or roles == ['public'] else ', '.join(ab[r] for r in roles)
        impl = 'implemented' if o.get('x-status') == 'implemented' else ''
        codes = ', '.join(c for c in o['responses'])
        rows.append((m.upper(), path, rtxt, o['summary'], codes, impl))
def pathtex(p):
    return '\\texttt{' + esc(p).replace('/', '/\\allowbreak ') + '}'
L = ['{\\tblstart\\footnotesize', '\\begin{longtable}{L{1.3cm}L{5.0cm}L{1.6cm}L{4.4cm}L{1.9cm}}',
     '\\hdrrow \\hdr{Method} & \\hdr{Path (after \\texttt{/api/v1})} & \\hdr{Roles} & \\hdr{Purpose} & \\hdr{Status codes}\\\\ \\endhead']
for m, path, r, s, codes, impl in rows:
    L.append('%s & %s & %s & %s%s & %s\\\\' % (m, pathtex(path), esc(r), esc(s), ' \\emph{(exists)}' if impl else '', esc(codes)))
L += ['\\hline', '\\end{longtable}}']
open(os.path.join(out, 'p2_gen_api.tex'), 'w').write('\n'.join(L) + '\n')
open(os.path.join(out, 'p2_gen_counts.tex'), 'w').write(
    '\\newcommand{\\nTables}{%d}\\newcommand{\\nColumns}{%d}\\newcommand{\\nOps}{%d}\\newcommand{\\nPaths}{%d}\\newcommand{\\nSchemas}{%d}\n'
    % (len(order), ncols, len(rows), len(spec['paths']), len(spec['components']['schemas'])))
print('tables', len(order), 'columns', ncols, 'operations', len(rows))
