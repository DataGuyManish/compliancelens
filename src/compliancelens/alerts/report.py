"""Per-run HTML report rendered with a plain Python string template - no
templating dependency, easy to audit. Saved to a UC volume in production."""
from __future__ import annotations

import html

DISCLAIMER = ("Indicative engineering signals only - not legal advice, "
              "not a compliance certification.")

_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>ComplianceLens run {run_id_short}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }}
table {{ border-collapse: collapse; margin: 1rem 0; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: .4rem .6rem; text-align: left; }}
th {{ background: #f0f4f8; }}
.badge {{ display: inline-block; padding: .15rem .5rem; border-radius: .6rem; font-size: .85rem; }}
.sev-critical {{ background: #7f1d1d; color: #fff; }} .sev-high {{ background: #dc2626; color: #fff; }}
.sev-medium {{ background: #f59e0b; }} .sev-low {{ background: #2563eb; color: #fff; }}
.score {{ font-size: 2.5rem; font-weight: 700; }} .up {{ color: #16a34a; }}
.disc {{ background: #fffbeb; border: 1px solid #f59e0b; padding: .8rem; border-radius: .5rem; }}
</style></head><body>
<h1>ComplianceLens run report</h1>
<p>run_id: <code>{run_id}</code> &middot; generated {generated_at}</p>
<h2>Compliance score</h2>
<p><span class="score">{score_after}</span> / 100
&nbsp;(before remediation: <b>{score_before}</b> &rarr; after: <b class="up">{score_after}</b>)</p>
<h2>Findings</h2>
<table><tr><th>Severity</th><th>Finding</th><th>Table</th><th>Column</th><th>Failed</th><th>Total</th></tr>
{findings_rows}
</table>
<h2>Schema drift</h2>
<table><tr><th>Table</th><th>Change</th><th>Column</th><th>From</th><th>To</th></tr>
{drift_rows}
</table>
<h2>Indicative controls triggered</h2>
<ul>{controls_list}</ul>
<h2>Actions taken</h2>
<ul>{actions_list}</ul>
<p class="disc"><b>Disclaimer:</b> {disclaimer}</p>
</body></html>
"""


def _esc(v) -> str:
    return html.escape(str(v))


def render_html_report(run_id: str, generated_at: str, score_before: float,
                       score_after: float, findings: list[dict],
                       drift_events: list[dict], controls: list[dict],
                       actions: list[dict]) -> str:
    f_rows = "\n".join(
        f"<tr><td><span class='badge sev-{_esc(f.get('severity','info'))}'>{_esc(f.get('severity'))}</span></td>"
        f"<td>{_esc(f.get('finding'))}</td><td>{_esc(f.get('table'))}</td>"
        f"<td>{_esc(f.get('column','-'))}</td><td>{_esc(f.get('failed','-'))}</td>"
        f"<td>{_esc(f.get('total','-'))}</td></tr>"
        for f in findings) or "<tr><td colspan='6'>none</td></tr>"
    d_rows = "\n".join(
        f"<tr><td>{_esc(d.get('table'))}</td><td>{_esc(d.get('change_type'))}</td>"
        f"<td>{_esc(d.get('column'))}</td><td>{_esc(d.get('old_type') or '-')}</td>"
        f"<td>{_esc(d.get('new_type') or '-')}</td></tr>"
        for d in drift_events) or "<tr><td colspan='5'>none</td></tr>"
    c_list = "\n".join(f"<li><b>{_esc(c.get('ref'))}</b> - {_esc(c.get('note'))}</li>"
                       for c in controls) or "<li>none</li>"
    a_list = "\n".join(f"<li><b>{_esc(a.get('action'))}</b> ({_esc(a.get('rule'))}): {_esc(a.get('detail'))}</li>"
                       for a in actions) or "<li>none</li>"
    return _HTML.format(run_id=_esc(run_id), run_id_short=_esc(run_id[:8]),
                        generated_at=_esc(generated_at), score_before=score_before,
                        score_after=score_after, findings_rows=f_rows,
                        drift_rows=d_rows, controls_list=c_list,
                        actions_list=a_list, disclaimer=DISCLAIMER)
