#!/usr/bin/env python3
"""Build the final PDF report from the project documents (markdown -> HTML -> PDF with headless Chrome).
Usage: build_report.py out.pdf [--roll "24I-3166, 24I-3015, 24I-3106"]"""
import base64, mimetypes, os, re, subprocess, sys, tempfile
import markdown

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO_URL = 'https://github.com/IfBilal/inventree-stock-sqe-testing'
BLOB = REPO_URL + '/blob/main/'
ORDER = [  # (section title, file)
    ('1. Executive summary and release decision', 'docs/COMPLETION_REPORT.md'),
    ('2. Scope, baseline and test basis', 'docs/BASELINE.md'),
    ('2.1 Test basis (workflows, requirements, rules, roles)', 'docs/TEST_BASIS.md'),
    ('2.2 Use case specification', 'docs/USE_CASES.md'),
    ('3. Test plan, estimation, exit criteria', 'docs/TEST_PLAN.md'),
    ('3.1 Risk register', 'docs/RISK_REGISTER.md'),
    ('3.2 GQM metrics', 'docs/GQM.md'),
    ('3.3 Traceability matrix (generated from test results)', 'docs/TRACEABILITY.md'),
    ('4. Static analysis (SonarQube) and cyclomatic complexity', 'docs/STATIC_ANALYSIS.md'),
    ('5. White-box unit testing', 'docs/UNIT_TESTING.md'),
    ('5.1 Complete MCC and MC/DC', 'docs/MCC_MCDC.md'),
    ('5.2 In-scope coverage per function', 'docs/COVERAGE_SCOPE.md'),
    ('5.3 Coverage justification', 'docs/COVERAGE_JUSTIFICATION.md'),
    ('6. Automated test-data generation', 'docs/TEST_DATA_GENERATION.md'),
    ('7. API and integration testing', 'docs/API_TESTING.md'),
    ('7.1 API coverage criteria', 'docs/API_COVERAGE.md'),
    ('8. Use cases and browser end-to-end testing; usability', 'docs/USABILITY.md'),
    ('8.1 Accessibility (Lighthouse + axe-core)', 'docs/ACCESSIBILITY.md'),
    ('9. Defensive security', 'docs/SECURITY.md'),
    ('10. Performance and recovery', 'docs/PERFORMANCE.md'),
    ('11. Mutation analysis', 'docs/MUTATION.md'),
    ('12. CI quality gate', 'docs/CI_QUALITY_GATE.md'),
    ('13. Defect management and Pareto', 'docs/DEFECTS.md'),
    ('13.1 Root-cause analysis', 'docs/RCA.md'),
    ('13.2 Findings register (API, accessibility, security, performance)', 'docs/FINDINGS_REGISTER.md'),
    ('14. Weekly progress report 1 of 2', 'reports/weekly/week-1.md'),
    ('14.1 Weekly progress report 2 of 2', 'reports/weekly/week-2.md'),
    ('15. Area ownership', 'docs/AREA_OWNERSHIP.md'),
    ('16. AI-use record', 'docs/AI_USE_RECORD.md'),
    ('17. Tool versions', 'docs/TOOL_VERSIONS.md'),
    ('18. Final release / hold decision and evidence links', 'docs/FINAL_DECISION.md'),
]
CSS = """body{font-family:DejaVu Sans,Arial,sans-serif;font-size:9.5pt;line-height:1.35;margin:0}
h1{font-size:17pt;border-bottom:2px solid #333;padding-bottom:3px;margin-top:22px;page-break-before:always}
h2{font-size:13pt;margin-top:16px} h3{font-size:11pt} table{border-collapse:collapse;margin:6px 0;font-size:8pt;width:100%;table-layout:auto}
th,td{border:1px solid #999;padding:2px 4px;vertical-align:top;word-break:break-word} th{background:#e9ecef}
code{font-family:DejaVu Sans Mono,monospace;font-size:8pt;background:#f1f3f5;padding:0 2px;word-break:break-all} pre{background:#f1f3f5;padding:6px;overflow-wrap:anywhere;white-space:pre-wrap}
img{max-width:100%} a{color:#1c4fd6;text-decoration:none} .cover{text-align:center;margin-top:160px;page-break-after:always} .cover h1{border:0;page-break-before:avoid;font-size:24pt}
.toc li{margin:2px 0}"""


def fix_links(html, docdir):
    """Relative repository links -> absolute GitHub links (so evidence links stay clickable in the PDF)."""
    def rep(m):
        url = m.group(1)
        if url.startswith(('http', '#', 'mailto', 'data:')):
            return m.group(0)
        return 'href="%s%s"' % (BLOB, os.path.normpath(os.path.join(docdir, url)).replace(os.sep, '/'))
    return re.sub(r'href="([^"]+)"', rep, html)


def inline_images(html, base):
    def rep(m):
        src = m.group(1)
        if src.startswith('http') or src.startswith('data:'):
            return m.group(0)
        p = os.path.normpath(os.path.join(base, src))
        if os.path.exists(p):
            mime = mimetypes.guess_type(p)[0] or 'image/png'
            return 'src="data:%s;base64,%s"' % (mime, base64.b64encode(open(p, 'rb').read()).decode())
        return m.group(0)
    return re.sub(r'src="([^"]+)"', rep, html)


def main():
    out = sys.argv[1]
    rolls = '24I-3166, 24I-3015, 24I-3106'
    parts = [f'<div class="cover"><h1>SE3002 Software Quality Engineering — Final Project</h1><h2>Automated testing of an open-source management information system</h2>'
             f'<p><b>System under test:</b> InvenTree (Stock module: Add stock / Remove stock)<br><b>Upstream:</b> https://github.com/inventree/InvenTree — MIT — commit 1f51dfe64bf4717fd95df51f1055ffb7a991a01d</p>'
             f'<p><b>Group:</b> {rolls}</p><p><b>Repository:</b> <a href="{REPO_URL}">{REPO_URL}</a></p>'
             f'<p><b>Release / hold decision:</b> HOLD — see section 1</p></div>']
    toc = ['<h1 style="page-break-before:avoid">Contents</h1><ol class="toc">'] + [f'<li>{t}</li>' for t, _ in ORDER] + ['</ol>']
    parts += toc
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'sane_lists'])
    for title, f in ORDER:
        path = os.path.join(ROOT, f)
        if not os.path.exists(path):
            print('MISSING', f, file=sys.stderr); continue
        text = open(path, encoding='utf-8').read()
        text = re.sub(r'^(#{1,5}) ', r'\1# ', text, flags=re.M)          # demote headings: the section title is the only h1 (one page break per section)
        out_l, fence, prev = [], False, ''
        for ln in text.split('\n'):          # a table needs a blank line before it (otherwise it renders as raw pipes)
            if ln.lstrip().startswith('```'): fence = not fence
            if not fence and ln.startswith('|') and prev.strip() and not prev.startswith('|'): out_l.append('')
            out_l.append(ln); prev = ln
        text = '\n'.join(out_l)
        md.reset()
        body = md.convert(text)
        body = inline_images(body, os.path.dirname(path))
        body = fix_links(body, os.path.dirname(f))
        parts.append(f'<h1>{title}</h1>{body}')
    html = f'<!doctype html><html><head><meta charset="utf-8"><title>SE3002 SQE Final Project</title><style>{CSS}</style></head><body>{"".join(parts)}</body></html>'
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as t:
        t.write(html); hp = t.name
    chrome = 'google-chrome'
    subprocess.run([chrome, '--headless=new', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={out}', f'file://{hp}'], check=True, capture_output=True, timeout=300)
    print('wrote', out, os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    main()
