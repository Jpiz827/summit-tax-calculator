"""
Summit Tax Services — Personalized PDF Report Generator
Generates branded PDF reports for each calculator type plus a personalized guide.
Uses HTML → WeasyPrint pipeline with Summit brand design system.
"""

import os
import re
from datetime import datetime
from weasyprint import HTML

# ─── Constants ──────────────────────────────────────────────────────────────
REPORTS_DIR = '/home/joe/summit-calculator/reports'
GUIDE_SOURCE = '/mnt/c/Users/Joe/Desktop/Hermes/MaxSS-Guide-Redesigned-v3-06-14-2026.html'

# Summit brand colors
NAVY = '#1a2744'
NAVY_DEEP = '#0f1629'
NAVY_MID = '#29344f'
NAVY_LIGHT = '#354a6e'
RED = '#c0392b'
RED_BRIGHT = '#e74c3c'
GOLD = '#c9a84c'
GOLD_BRIGHT = '#d4a843'
GOLD_LIGHT = '#f0d78c'
GREEN = '#27ae60'
GREEN_LIGHT = '#4eca7f'
CREAM = '#f5f0e7'
CREAM_DARK = '#e8e0d0'
WHITE = '#ffffff'
OFF_WHITE = '#faf8f4'
GRAY_LIGHT = '#848893'
GRAY_MID = '#6b7080'
TEXT_BODY = '#2c3345'
TEXT_MUTED = '#5a6070'


# ─── Shared CSS ─────────────────────────────────────────────────────────────
SHARED_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Georgia&family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
  --navy: {NAVY};
  --navy-deep: {NAVY_DEEP};
  --navy-mid: {NAVY_MID};
  --navy-light: {NAVY_LIGHT};
  --red: {RED};
  --red-bright: {RED_BRIGHT};
  --gold: {GOLD};
  --gold-bright: {GOLD_BRIGHT};
  --gold-light: {GOLD_LIGHT};
  --green: {GREEN};
  --green-light: {GREEN_LIGHT};
  --cream: {CREAM};
  --cream-dark: {CREAM_DARK};
  --white: {WHITE};
  --off-white: {OFF_WHITE};
  --gray-light: {GRAY_LIGHT};
  --gray-mid: {GRAY_MID};
  --gray-dark: #4a4f5c;
  --text-body: {TEXT_BODY};
  --text-muted: {TEXT_MUTED};
}}

@page {{
  size: letter;
  margin: 0.75in 0.85in;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: 'Georgia', 'Times New Roman', serif;
  background: var(--white);
  color: var(--text-body);
  line-height: 1.6;
  font-size: 11pt;
  -webkit-font-smoothing: antialiased;
}}

/* =================== PAGE SECTIONS =================== */
.page {{
  page-break-after: always;
  padding: 0;
  position: relative;
}}
.page:last-child {{
  page-break-after: auto;
}}

/* =================== TYPOGRAPHY =================== */
.label-spread {{
  font-family: 'Inter', sans-serif;
  font-size: 8pt;
  font-weight: 700;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 10px;
  display: block;
}}
.label-spread.white {{ color: var(--white); }}
.label-spread.red {{ color: var(--red); }}
.label-spread.cream {{ color: var(--cream); }}
.label-spread.navy {{ color: var(--navy); }}

h1 {{
  font-family: 'Georgia', serif;
  font-size: 26pt;
  font-weight: 700;
  line-height: 1.15;
  color: var(--white);
  margin-bottom: 16px;
}}
h1 .highlight {{ color: var(--gold); }}
h1 .redline {{ color: var(--red-bright); }}

h2 {{
  font-family: 'Georgia', serif;
  font-size: 18pt;
  font-weight: 700;
  line-height: 1.25;
  color: var(--white);
  margin-bottom: 12px;
}}
h2 .highlight {{ color: var(--gold); }}
h2 .redline {{ color: var(--red-bright); }}

h3 {{
  font-family: 'Georgia', serif;
  font-size: 14pt;
  font-weight: 700;
  line-height: 1.3;
  color: var(--cream);
  margin-bottom: 10px;
}}

p {{ margin-bottom: 12px; font-size: 11pt; line-height: 1.65; }}

.strong {{ font-weight: 700; }}
.em {{ font-style: italic; }}
.gold {{ color: var(--gold); }}
.red {{ color: var(--red-bright); }}
.green {{ color: var(--green-light); }}

/* =================== COVER / DARK / LIGHT PAGES =================== */
.cover-page {{
  background: linear-gradient(170deg, var(--navy-deep) 0%, var(--navy) 50%);
  color: var(--white);
  padding: 48px 40px 40px;
  margin: -0.75in -0.85in;
  min-height: calc(11in - 1.5in);
  display: flex;
  flex-direction: column;
}}

.dark-page {{
  background: var(--navy);
  color: var(--cream);
  padding: 44px 40px;
  margin: -0.75in -0.85in;
  min-height: calc(11in - 1.5in);
}}
.dark-page h1, .dark-page h2, .dark-page h3 {{ color: var(--white); }}
.dark-page p {{ color: var(--cream); }}

.light-page {{
  background: var(--off-white);
  color: var(--text-body);
  padding: 44px 40px;
  margin: -0.75in -0.85in;
  min-height: calc(11in - 1.5in);
}}
.light-page h1, .light-page h2, .light-page h3 {{ color: var(--navy); }}
.light-page p {{ color: var(--text-body); }}
.light-page .label-spread {{ color: var(--gold); }}

/* =================== BANNER =================== */
.top-banner {{
  background: {RED};
  padding: 8px 16px;
  text-align: center;
  font-family: 'Inter', sans-serif;
  font-size: 7.5pt;
  font-weight: 700;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--white);
  margin: -44px -40px 28px -40px;
}}

/* =================== STAT CARDS =================== */
.stat-row {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 24px 0;
}}
.stat-row.two-col {{
  grid-template-columns: repeat(2, 1fr);
}}
.stat-card {{
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(201,168,76,0.25);
  border-radius: 6px;
  padding: 20px 16px;
  text-align: center;
}}
.light-page .stat-card {{
  background: var(--white);
  border: 1px solid var(--cream-dark);
}}
.stat-card .number {{
  font-family: 'Georgia', serif;
  font-size: 32pt;
  font-weight: 700;
  color: var(--gold);
  display: block;
  margin-bottom: 6px;
  line-height: 1.1;
}}
.stat-card .number.red-num {{ color: var(--red-bright); }}
.stat-card .number.green-num {{ color: var(--green-light); }}
.stat-card .label {{
  font-family: 'Inter', sans-serif;
  font-size: 7.5pt;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--gray-light);
  line-height: 1.4;
}}

/* =================== CALLOUT BOXES =================== */
.callout {{
  border-radius: 6px;
  padding: 20px 24px;
  margin: 24px 0;
  position: relative;
}}
.callout-red {{
  background: rgba(192,57,43,0.08);
  border-left: 4px solid var(--red);
}}
.dark-page .callout-red {{
  background: rgba(192,57,43,0.15);
  border-left: 4px solid var(--red-bright);
  color: var(--cream);
}}
.callout-gold {{
  background: rgba(201,168,76,0.08);
  border-left: 4px solid var(--gold);
}}
.callout-green {{
  background: rgba(78,202,127,0.06);
  border-left: 4px solid var(--green);
}}
.callout-navy {{
  background: rgba(26,39,68,0.06);
  border: 1px solid rgba(201,168,76,0.15);
  border-left: 4px solid var(--navy);
}}
.callout .callout-label {{
  font-family: 'Inter', sans-serif;
  font-size: 8pt;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 8px;
  display: block;
}}
.callout-red .callout-label {{ color: var(--red); }}
.callout-green .callout-label {{ color: var(--green); }}
.callout p {{ margin-bottom: 8px; font-size: 10.5pt; }}
.callout p:last-child {{ margin-bottom: 0; }}

/* =================== PULL QUOTE =================== */
.pull-quote {{
  background: rgba(255,255,255,0.04);
  border-radius: 6px;
  padding: 22px 28px;
  margin: 24px 0;
  border: 1px solid rgba(201,168,76,0.15);
  text-align: center;
}}
.pull-quote p {{
  font-family: 'Georgia', serif;
  font-style: italic;
  font-size: 14pt;
  color: var(--cream);
  line-height: 1.5;
  margin-bottom: 0;
}}

/* =================== COMPARISON TABLE =================== */
.comparison-table {{
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-size: 10pt;
}}
.comparison-table th {{
  font-family: 'Inter', sans-serif;
  font-size: 7.5pt;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 10px 12px;
  text-align: left;
  border-bottom: 2px solid rgba(201,168,76,0.3);
}}
.comparison-table th.col-green {{ color: var(--green); }}
.comparison-table th.col-gold {{ color: var(--gold); }}
.comparison-table th.col-red {{ color: var(--red-bright); }}
.comparison-table td {{
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  vertical-align: top;
  line-height: 1.45;
}}
.light-page .comparison-table td {{
  border-bottom-color: var(--cream-dark);
}}
.comparison-table tr:last-child td {{ border-bottom: none; }}
.comparison-table td.label-cell {{
  font-weight: 700;
  font-size: 10pt;
}}
.comparison-table td.green-cell {{ color: var(--green); }}
.comparison-table td.gold-cell {{ color: var(--gold); }}
.comparison-table td.red-cell {{ color: var(--red-bright); }}

/* =================== DIVIDER =================== */
.section-divider {{
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(201,168,76,0.3), transparent);
  margin: 32px 0;
}}

/* =================== CONSIDER THIS =================== */
.consider-this {{
  background: linear-gradient(135deg, rgba(201,168,76,0.06) 0%, rgba(201,168,76,0.02) 100%);
  border-left: 3px solid var(--gold);
  border-radius: 0 6px 6px 0;
  padding: 18px 22px;
  margin: 24px 0;
  font-style: italic;
  font-size: 11pt;
  line-height: 1.65;
}}
.consider-this .ct-label {{
  font-family: 'Inter', sans-serif;
  font-style: normal;
  font-size: 8pt;
  font-weight: 700;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 8px;
  display: block;
}}

/* =================== CTA BOXES =================== */
.cta-box {{
  background: var(--cream);
  border-radius: 6px;
  padding: 28px 32px;
  text-align: center;
  margin: 28px 0;
}}
.cta-box h3 {{
  color: var(--navy);
  font-size: 16pt;
  margin-bottom: 10px;
}}
.cta-box p {{
  color: var(--navy);
  font-size: 10.5pt;
  margin-bottom: 16px;
}}

.cta-box-dark {{
  background: var(--navy);
  border: 2px solid var(--gold);
  border-radius: 6px;
  padding: 28px 32px;
  text-align: center;
  margin: 28px 0;
}}
.cta-box-dark h3 {{ color: var(--gold); font-size: 16pt; margin-bottom: 10px; }}
.cta-box-dark p {{ color: var(--cream); font-size: 10.5pt; margin-bottom: 16px; }}

/* =================== CHECK LIST =================== */
.check-list {{
  list-style: none;
  padding: 0;
  margin: 18px 0;
}}
.check-list li {{
  padding: 10px 0 10px 30px;
  position: relative;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 10.5pt;
  line-height: 1.55;
}}
.check-list li::before {{
  content: '\\2713';
  position: absolute;
  left: 0;
  font-family: 'Inter', sans-serif;
  font-size: 12pt;
  font-weight: 700;
  color: var(--green);
}}
.check-list li:last-child {{ border-bottom: none; }}

/* =================== PERSONALIZED HEADER =================== */
.client-header {{
  font-family: 'Inter', sans-serif;
  font-size: 9pt;
  font-weight: 600;
  letter-spacing: 1px;
  color: var(--gold-light);
  margin-bottom: 4px;
}}
.client-name-display {{
  font-family: 'Georgia', serif;
  font-size: 14pt;
  font-weight: 700;
  color: var(--white);
  margin-bottom: 12px;
}}
.client-meta {{
  font-family: 'Inter', sans-serif;
  font-size: 7.5pt;
  color: var(--gray-light);
  letter-spacing: 1px;
}}

.light-page .client-header {{ color: var(--gold); }}
.light-page .client-name-display {{ color: var(--navy); }}
.light-page .client-meta {{ color: var(--gray-mid); }}

/* =================== DISCLAIMER FOOTER =================== */
.disclaimer {{
  font-family: 'Inter', sans-serif;
  font-size: 7pt;
  color: var(--gray-light);
  line-height: 1.5;
  margin-top: 32px;
  padding-top: 12px;
  border-top: 1px solid rgba(201,168,76,0.15);
}}

/* =================== TWO-PATH GRID =================== */
.two-paths {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 24px 0;
}}
.path-card {{
  border-radius: 6px;
  padding: 24px 20px;
}}
.path-bad {{
  background: rgba(192,57,43,0.06);
  border: 1px solid rgba(192,57,43,0.25);
}}
.path-good {{
  background: rgba(78,202,127,0.06);
  border: 1px solid rgba(78,202,127,0.25);
}}
.path-card h4 {{
  font-family: 'Inter', sans-serif;
  font-size: 8pt;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 12px;
}}
.path-bad h4 {{ color: var(--red-bright); }}
.path-good h4 {{ color: var(--green); }}
.path-card p {{ font-size: 10.5pt; margin-bottom: 8px; }}
.path-card p:last-child {{ margin-bottom: 0; }}

/* =================== PRINT =================== */
@media print {{
  .page {{ page-break-after: always; }}
  .page:last-child {{ page-break-after: auto; }}
  body {{ background: white; }}
  .cover-page, .dark-page {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .stat-card, .callout, .cta-box, .cta-box-dark,
  .path-card, .consider-this, .pull-quote {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .callout, .stat-card, .consider-this, .pull-quote {{ break-inside: avoid; }}
}}
"""


# ─── Helper functions ───────────────────────────────────────────────────────

def _fmt_dollar(val):
    """Format a number as a dollar string with commas."""
    try:
        n = float(val)
        return f"${n:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def _fmt_pct(val):
    """Format a number as a percentage string."""
    try:
        n = float(val)
        return f"{n:.1f}%"
    except (ValueError, TypeError):
        return str(val)


def _fmt_dollar_precise(val):
    """Format a number as a dollar string with commas and 2 decimal places."""
    try:
        n = float(val)
        return f"${n:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def _today_str():
    """Return today's date as a formatted string."""
    return datetime.now().strftime('%B %d, %Y')


def _first_name(client_name):
    """Extract first name from full client name."""
    return client_name.split()[0] if client_name else 'Client'


def _render_pdf(html_content, output_path):
    """Render HTML string to PDF via WeasyPrint."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    html_doc = HTML(string=html_content)
    html_doc.write_pdf(output_path)
    return output_path


def _disclaimer_footer():
    """Standard disclaimer for all reports."""
    return f"""
    <div class="disclaimer">
      <strong>Disclaimer:</strong> This report is prepared for educational and informational purposes only and does not constitute tax, legal, or financial advice. 
      Calculations are based on 2024 federal tax brackets and Social Security rules; actual results may vary based on your complete tax situation, state taxes, 
      and future law changes. Consult a qualified tax professional before making any financial decisions. Summit Tax Services is not liable for any actions taken 
      based on this report. Client ID reference is for internal tracking only.
    </div>
    """


def _client_header_html(client_name, client_id, is_dark=True):
    """Generate the personalized client header block."""
    fname = _first_name(client_name)
    return f"""
    <div style="margin-bottom: 20px;">
      <div class="client-header">PREPARED FOR</div>
      <div class="client-name-display">{fname}</div>
      <div class="client-meta">Client ID: {client_id} &nbsp;|&nbsp; {_today_str()}</div>
    </div>
    """


def _cta_box_dark():
    """Standard dark CTA box for all reports."""
    return f"""
    <div class="cta-box-dark">
      <h3>Ready to Take Action?</h3>
      <p>Don't let another year go by leaving money on the table. Book a complimentary strategy session with Summit Tax Services and get a personalized plan.</p>
      <p style="font-family: 'Inter', sans-serif; font-size: 12pt; font-weight: 700; color: var(--gold); margin-bottom: 8px;">taxesrx.com/maxss</p>
      <p style="font-family: 'Inter', sans-serif; font-size: 9pt; color: var(--cream);">Call [PHONE NUMBER] to speak with a specialist today</p>
    </div>
    """


def _cta_box_light():
    """Standard light CTA box for all reports."""
    return f"""
    <div class="cta-box">
      <h3>Ready to Take Action?</h3>
      <p>Don't let another year go by leaving money on the table. Book a complimentary strategy session with Summit Tax Services and get a personalized plan.</p>
      <p style="font-family: 'Inter', sans-serif; font-size: 12pt; font-weight: 700; color: var(--navy); margin-bottom: 8px;">taxesrx.com/maxss</p>
      <p style="font-family: 'Inter', sans-serif; font-size: 9pt; color: var(--text-muted);">Call [PHONE NUMBER] to speak with a specialist today</p>
    </div>
    """


# ═══════════════════════════════════════════════════════════════════════════
# 1. SOCIAL SECURITY CLAIMING REPORT
# ═══════════════════════════════════════════════════════════════════════════

def ss_report(client_name, client_id, inputs_dict, results_dict):
    """
    Generate a personalized Social Security Claiming Strategy Report PDF.
    
    inputs: {pia_monthly, birth_year, filing, life_expectancy}
    results: {scenarios: [{claim_age, annual_benefit, monthly_benefit, lifetime_benefit}],
              fra, optimal_age, optimal_lifetime}
    
    Returns the PDF file path.
    """
    fname = _first_name(client_name)
    pia_monthly = inputs_dict.get('pia_monthly', 0)
    birth_year = inputs_dict.get('birth_year', 1960)
    filing = inputs_dict.get('filing', 'MFJ')
    life_expectancy = inputs_dict.get('life_expectancy', 85)
    
    scenarios = results_dict.get('scenarios', [])
    # Filter out survivor note entries
    claim_scenarios = [s for s in scenarios if 'claim_age' in s]
    fra = results_dict.get('fra', 67)
    optimal_age = results_dict.get('optimal_age', 67)
    optimal_lifetime = results_dict.get('optimal_lifetime', 0)
    
    # Find key scenarios
    age62 = next((s for s in claim_scenarios if s['claim_age'] == 62), None)
    age_fra = next((s for s in claim_scenarios if abs(s['claim_age'] - fra) < 0.5), None)
    age70 = next((s for s in claim_scenarios if s['claim_age'] == 70), None)
    
    fra_display = f"{int(fra)}" if fra == int(fra) else f"{fra}"
    
    # Build scenarios table rows
    table_rows = ""
    for s in claim_scenarios:
        age = s.get('claim_age', 0)
        monthly = _fmt_dollar_precise(s.get('monthly_benefit', 0))
        annual = _fmt_dollar(s.get('annual_benefit', 0))
        lifetime = _fmt_dollar(s.get('lifetime_benefit', 0))
        is_optimal = age == optimal_age
        row_class = ' style="background: rgba(201,168,76,0.08);"' if is_optimal else ''
        opt_star = ' &#9733;' if is_optimal else ''
        age_label = f"Age {int(age)}{opt_star}"
        
        if age == 62:
            age_cell_class = 'red-cell'
        elif is_optimal:
            age_cell_class = 'gold-cell'
        elif age == 70:
            age_cell_class = 'green-cell'
        else:
            age_cell_class = ''
        
        table_rows += f"""
        <tr{row_class}>
          <td class="label-cell {age_cell_class}">{age_label}</td>
          <td>{monthly}</td>
          <td>{annual}</td>
          <td class="{'gold-cell' if is_optimal else ''}">{lifetime}</td>
        </tr>"""
    
    # Build the comparison between early vs optimal
    early_benefit = age62['lifetime_benefit'] if age62 else 0
    gain_vs_62 = optimal_lifetime - early_benefit
    
    # Filing status display
    filing_display = "Married Filing Jointly" if filing == 'MFJ' else "Single"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Social Security Claiming Strategy Report — {fname}</title>
    <style>{SHARED_CSS}</style>
    </head>
    <body>
    
    <!-- PAGE 1: COVER -->
    <div class="page">
    <div class="cover-page">
      <div class="top-banner">
        SUMMIT TAX SERVICES &nbsp;|&nbsp; PERSONALIZED ANALYSIS
      </div>
      
      {_client_header_html(client_name, client_id)}
      
      <span class="label-spread" style="margin-bottom: 20px;">SOCIAL SECURITY ANALYSIS</span>
      
      <h1 style="font-size: 30pt; line-height: 1.1; margin-bottom: 24px;">
        Your <span class="highlight">Social Security</span><br>
        Claiming Strategy<br>
        <span class="redline">Report</span>
      </h1>
      
      <p style="font-size: 12pt; color: var(--cream); font-style: italic; max-width: 540px; margin-bottom: 32px; line-height: 1.6;">
        A personalized analysis of your claiming options — showing how the age you file can mean tens of thousands of dollars in lifetime benefits.
      </p>
      
      <div class="stat-row" style="max-width: 600px;">
        <div class="stat-card">
          <span class="number">{_fmt_dollar(optimal_lifetime)}</span>
          <span class="label">MAXIMUM LIFETIME<br>BENEFIT</span>
        </div>
        <div class="stat-card">
          <span class="number">Age {int(optimal_age)}</span>
          <span class="label">OPTIMAL<br>CLAIMING AGE</span>
        </div>
        <div class="stat-card">
          <span class="number green-num">{_fmt_dollar(gain_vs_62)}</span>
          <span class="label">GAIN VS.<br>FILING AT 62</span>
        </div>
      </div>
      
      <div class="callout callout-gold" style="max-width: 560px;">
        <span class="callout-label">YOUR INPUTS</span>
        <p><strong>PIA (monthly):</strong> {_fmt_dollar_precise(pia_monthly)} &nbsp;|&nbsp; <strong>Birth Year:</strong> {birth_year} &nbsp;|&nbsp; <strong>FRA:</strong> {fra_display}</p>
        <p><strong>Filing Status:</strong> {filing_display} &nbsp;|&nbsp; <strong>Life Expectancy:</strong> {life_expectancy}</p>
      </div>
    </div>
    </div>
    
    <!-- PAGE 2: SCENARIO COMPARISON -->
    <div class="page">
    <div class="light-page">
      {_client_header_html(client_name, client_id, is_dark=False)}
      
      <span class="label-spread" style="color: var(--navy);">CLAIMING SCENARIOS</span>
      
      <h2 style="color: var(--navy); margin-bottom: 20px; font-size: 22pt;">
        Every Year You Wait <span style="color: var(--gold);">Changes the Math</span>
      </h2>
      
      <p style="color: var(--text-body); margin-bottom: 16px;">
        Below is a year-by-year comparison of your Social Security claiming options. Each row shows the monthly benefit, annual benefit, and projected lifetime benefit based on your life expectancy of <strong>{life_expectancy}</strong> years.
      </p>
      
      <p style="color: var(--text-body); margin-bottom: 20px;">
        The <strong style="color: var(--gold);">&#9733; star</strong> marks your <strong>optimal claiming age</strong> — the age that maximizes your total lifetime benefits.
      </p>
      
      <table class="comparison-table">
        <thead>
          <tr>
            <th>Claim Age</th>
            <th>Monthly Benefit</th>
            <th>Annual Benefit</th>
            <th class="col-gold">Lifetime Benefit</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
      
      <div class="callout callout-gold" style="background: #fdf8e8;">
        <span class="callout-label">KEY INSIGHT</span>
        <p style="color: var(--text-body);">By claiming at <strong>Age {int(optimal_age)}</strong> instead of Age 62, your projected lifetime benefit increases by <strong style="color: var(--green);">{_fmt_dollar(gain_vs_62)}</strong>. That's real money that stays in your pocket over your retirement.</p>
      </div>
      
      <div class="consider-this" style="background: linear-gradient(135deg, rgba(201,168,76,0.1) 0%, rgba(201,168,76,0.03) 100%);">
        <span class="ct-label">CONSIDER THIS</span>
        The breakeven analysis above shows <em>gross</em> benefits. But after taxes, the picture shifts — because a bigger Social Security check pushes more of it into the taxable zone. The real breakeven includes the tax torpedo. This is why a Roth conversion strategy paired with the right claiming age is so powerful.
      </div>
      
      {_disclaimer_footer()}
    </div>
    </div>
    
    <!-- PAGE 3: STRATEGY & EXPLANATION -->
    <div class="page">
    <div class="dark-page">
      <span class="label-spread">STRATEGY RECOMMENDATIONS</span>
      
      <h1 style="margin-bottom: 20px; font-size: 24pt;">
        What This Means<br>for <span class="highlight">{fname}</span>
      </h1>
      
      <div class="callout callout-red">
        <span class="callout-label" style="color: var(--red);">THE $100K MISTAKE</span>
        <p><strong>96% of retirees do not optimize their Social Security claiming strategy.</strong> According to the Government Accountability Office, the average retiree leaves between $50,000 and $150,000 on the table by filing at the wrong time. Your analysis shows a potential gain of <strong>{_fmt_dollar(gain_vs_62)}</strong> by choosing the right age.</p>
      </div>
      
      <hr class="section-divider">
      
      <h2><span class="highlight">Three Strategies</span> to Consider</h2>
      
      <ul class="check-list">
        <li><strong>Delay to {int(optimal_age)} for maximum lifetime benefits.</strong> Each year you wait past {fra_display} (your FRA), your benefit grows by approximately 8%. If your health and cash flow allow it, this is the mathematical optimum.</li>
        <li><strong>Pair your claiming decision with a Roth conversion.</strong> A larger Social Security check pushes more of it into the taxable zone. A Roth conversion reduces your RMDs, lowers your provisional income, and can permanently un-tax more of your Social Security.</li>
        <li><strong>Consider the "go-go" years.</strong> If you need income now — for travel, healthcare, or living expenses — claiming earlier isn't "wrong." But you should know the cost: {_fmt_dollar(gain_vs_62)} in lifetime benefits.</li>
      </ul>
      
      <div class="pull-quote">
        <p>Delaying Social Security without a Roth conversion is like buying a bigger house without checking if you can afford the property tax. <strong>The real breakeven isn't about what you receive — it's about what you keep.</strong></p>
      </div>
      
      {_cta_box_dark()}
      
      {_disclaimer_footer()}
    </div>
    </div>
    
    </body>
    </html>
    """
    
    output_path = os.path.join(REPORTS_DIR, f"{client_id}_ss_claiming_report.pdf")
    return _render_pdf(html, output_path)


# ═══════════════════════════════════════════════════════════════════════════
# 2. TAX TORPEDO REPORT
# ═══════════════════════════════════════════════════════════════════════════

def torpedo_report(client_name, client_id, inputs_dict, results_dict):
    """
    Generate a personalized Tax Torpedo Report PDF.
    
    inputs: {ss_benefit_annual, other_income, filing}
    results: {provisional_income, ss_taxable_pct, federal_tax, effective_marginal_rate, irmaa_surcharge}
    
    Returns the PDF file path.
    """
    fname = _first_name(client_name)
    ss_benefit_annual = inputs_dict.get('ss_benefit_annual', 0)
    other_income = inputs_dict.get('other_income', 0)
    filing = inputs_dict.get('filing', 'MFJ')
    
    provisional_income = results_dict.get('provisional_income', 0)
    ss_taxable_pct = results_dict.get('ss_taxable_pct', 0)
    federal_tax = results_dict.get('federal_tax', 0)
    effective_marginal_rate = results_dict.get('effective_marginal_rate', 0)
    irmaa_surcharge = results_dict.get('irmaa_surcharge', 0)
    
    # Additional fields that may come from calc_full_scenario
    ss_taxable_amount = results_dict.get('ss_taxable', results_dict.get('ss_taxable_no_roth', 0))
    total_income = results_dict.get('total_income', results_dict.get('total_income_no_roth', 0))
    base_rate = results_dict.get('base_rate', results_dict.get('base_rate_no_roth', 0))
    torpedo_surcharge = results_dict.get('torpedo_surcharge', results_dict.get('torpedo_no_roth', 0))
    
    # Determine torpedo zone
    if filing == 'MFJ':
        if provisional_income <= 32000:
            zone = "Below 50% threshold"
            zone_color = GREEN
        elif provisional_income <= 44000:
            zone = "50% taxation zone"
            zone_color = GOLD
        else:
            zone = "85% taxation zone"
            zone_color = RED
        thresh_50, thresh_85 = 32000, 44000
    else:
        if provisional_income <= 25000:
            zone = "Below 50% threshold"
            zone_color = GREEN
        elif provisional_income <= 34000:
            zone = "50% taxation zone"
            zone_color = GOLD
        else:
            zone = "85% taxation zone"
            zone_color = RED
        thresh_50, thresh_85 = 25000, 34000
    
    filing_display = "Married Filing Jointly" if filing == 'MFJ' else "Single"
    
    # Calculate torpedo penalty (effective - base)
    torpedo_penalty = effective_marginal_rate - base_rate if effective_marginal_rate and base_rate else 0
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Tax Torpedo Report — {fname}</title>
    <style>{SHARED_CSS}</style>
    </head>
    <body>
    
    <!-- PAGE 1: COVER -->
    <div class="page">
    <div class="cover-page">
      <div class="top-banner">
        SUMMIT TAX SERVICES &nbsp;|&nbsp; PERSONALIZED ANALYSIS
      </div>
      
      {_client_header_html(client_name, client_id)}
      
      <span class="label-spread" style="margin-bottom: 20px;">TAX TORPEDO ANALYSIS</span>
      
      <h1 style="font-size: 30pt; line-height: 1.1; margin-bottom: 24px;">
        How Your Savings<br>
        <span class="redline">Tax Your Social Security</span><br>
        at <span class="highlight">85%</span>
      </h1>
      
      <p style="font-size: 12pt; color: var(--cream); font-style: italic; max-width: 540px; margin-bottom: 32px; line-height: 1.6;">
        Up to 85% of your Social Security can be taxed — triggered by the very money you saved. This report reveals your torpedo zone and what you can do about it.
      </p>
      
      <div class="stat-row" style="max-width: 600px;">
        <div class="stat-card">
          <span class="number">{_fmt_pct(ss_taxable_pct)}</span>
          <span class="label">OF YOUR SS<br>IS TAXABLE</span>
        </div>
        <div class="stat-card">
          <span class="number red-num">{_fmt_pct(effective_marginal_rate)}</span>
          <span class="label">EFFECTIVE<br>MARGINAL RATE</span>
        </div>
        <div class="stat-card">
          <span class="number">{_fmt_dollar(irmaa_surcharge)}/yr</span>
          <span class="label">IRMAA<br>SURCHARGE</span>
        </div>
      </div>
      
      <div class="callout callout-gold" style="max-width: 560px;">
        <span class="callout-label">YOUR INPUTS</span>
        <p><strong>SS Benefit (annual):</strong> {_fmt_dollar(ss_benefit_annual)} &nbsp;|&nbsp; <strong>Other Income:</strong> {_fmt_dollar(other_income)}</p>
        <p><strong>Filing Status:</strong> {filing_display}</p>
      </div>
    </div>
    </div>
    
    <!-- PAGE 2: YOUR TORPEDO ZONE -->
    <div class="page">
    <div class="light-page">
      {_client_header_html(client_name, client_id, is_dark=False)}
      
      <span class="label-spread" style="color: var(--navy);">YOUR TORPEDO ZONE</span>
      
      <h2 style="color: var(--navy); margin-bottom: 20px; font-size: 22pt;">
        Your Numbers, <span style="color: var(--gold);">Your Zone</span>
      </h2>
      
      <p style="color: var(--text-body); margin-bottom: 16px;">
        The IRS uses <strong>provisional income</strong> to determine how much of your Social Security is taxable. Your provisional income is calculated as:
      </p>
      
      <div class="callout callout-navy" style="background: #f0f3f8; border: 1px solid var(--navy-light); border-left: 4px solid var(--navy);">
        <p style="font-family: 'Inter', sans-serif; font-size: 11pt; text-align: center; margin-bottom: 0; color: var(--navy);">
          <strong style="color: var(--gold);">Provisional Income</strong> = AGI + 50% of SS + Tax-Exempt Interest
        </p>
      </div>
      
      <div class="stat-row" style="max-width: 500px; margin: 24px auto;">
        <div class="stat-card">
          <span class="number" style="font-size: 28pt;">{_fmt_dollar(provisional_income)}</span>
          <span class="label">YOUR PROVISIONAL<br>INCOME</span>
        </div>
        <div class="stat-card">
          <span class="number {'red-num' if zone_color == RED else ''}" style="font-size: 28pt; {'color: var(--green);' if zone_color == GREEN else ''}">{zone}</span>
          <span class="label">YOUR CURRENT<br>TAXATION ZONE</span>
        </div>
      </div>
      
      <table class="comparison-table" style="margin-bottom: 20px;">
        <thead>
          <tr>
            <th>Metric</th>
            <th class="col-gold">Your Value</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="label-cell">Social Security Benefit</td>
            <td>{_fmt_dollar(ss_benefit_annual)}</td>
          </tr>
          <tr>
            <td class="label-cell">Other Income (AGI)</td>
            <td>{_fmt_dollar(other_income)}</td>
          </tr>
          <tr>
            <td class="label-cell">Provisional Income</td>
            <td>{_fmt_dollar(provisional_income)}</td>
          </tr>
          <tr>
            <td class="label-cell">SS Taxable Percentage</td>
            <td class="{'red-cell' if ss_taxable_pct > 50 else 'gold-cell'}">{_fmt_pct(ss_taxable_pct)}</td>
          </tr>
          <tr>
            <td class="label-cell">Estimated Federal Tax</td>
            <td class="red-cell">{_fmt_dollar(federal_tax)}</td>
          </tr>
          <tr>
            <td class="label-cell">Effective Marginal Rate</td>
            <td class="red-cell">{_fmt_pct(effective_marginal_rate)}</td>
          </tr>
          <tr>
            <td class="label-cell">IRMAA Surcharge (annual)</td>
            <td class="red-cell">{_fmt_dollar(irmaa_surcharge)}</td>
          </tr>
        </tbody>
      </table>
      
      {_disclaimer_footer()}
    </div>
    </div>
    
    <!-- PAGE 3: THREE HITS & STRATEGY -->
    <div class="page">
    <div class="dark-page">
      <span class="label-spread">THE THREE HITS</span>
      
      <h1 style="margin-bottom: 20px; font-size: 24pt;">
        One Trigger,<br><span class="redline">Three Tax Hits</span>
      </h1>
      
      <div class="callout callout-red">
        <span class="callout-label" style="color: var(--red);">THE TAX TORPEDO — THREE HITS, ONE TRIGGER</span>
        <p><strong>Hit #1: Direct Income Tax.</strong> Every dollar of your RMD is taxed as ordinary income. For a $1M IRA at 73, that's approximately $37,736 in year one — growing every year.</p>
        <p><strong>Hit #2: Social Security Becomes Taxable.</strong> Your RMD increases provisional income. Once above {_fmt_dollar(thresh_85)} ({filing_display}), up to 85% of your SS becomes taxable income.</p>
        <p><strong>Hit #3: Medicare Premiums Spike.</strong> IRMAA surcharges based on your tax return from two years ago. Your current surcharge: <strong>{_fmt_dollar(irmaa_surcharge)}/year</strong>. No warning. No appeal.</p>
      </div>
      
      <hr class="section-divider">
      
      <h2><span class="highlight">Your Strategy Options</span></h2>
      
      <ul class="check-list">
        <li><strong>Roth Conversion:</strong> Convert Traditional IRA funds to Roth now while the 12% and 24% brackets are permanent (2025 tax law). Every dollar converted is a dollar that will never trigger SS taxation again.</li>
        <li><strong>QCD Strategy:</strong> A Qualified Charitable Distribution from your IRA directly to charity is excluded from AGI — reducing provisional income without itemizing deductions.</li>
        <li><strong>Income Timing:</strong> Manage when you realize income to stay below the {_fmt_dollar(thresh_85)} threshold. Even small reductions can make a big difference.</li>
      </ul>
      
      <div class="pull-quote">
        <p>Your effective marginal rate of <strong>{_fmt_pct(effective_marginal_rate)}</strong> means that for every additional dollar of income, you're paying that rate — <em>including</em> the cascading effect on Social Security taxation. A Roth conversion is the most powerful way to lower it permanently.</p>
      </div>
      
      {_cta_box_dark()}
      
      {_disclaimer_footer()}
    </div>
    </div>
    
    </body>
    </html>
    """
    
    output_path = os.path.join(REPORTS_DIR, f"{client_id}_tax_torpedo_report.pdf")
    return _render_pdf(html, output_path)


# ═══════════════════════════════════════════════════════════════════════════
# 3. CAPITAL GAINS BUMP ZONE REPORT
# ═══════════════════════════════════════════════════════════════════════════

def capital_gains_report(client_name, client_id, inputs_dict, results_dict):
    """
    Generate a personalized Capital Gains Bump Zone Report PDF.
    
    inputs: {ss_benefit_annual, other_income, capital_gain, filing}
    results: {provisional_income_before, provisional_income_after, ss_taxable_before, 
              ss_taxable_after, effective_rate_on_gain}
    
    Returns the PDF file path.
    """
    fname = _first_name(client_name)
    ss_benefit_annual = inputs_dict.get('ss_benefit_annual', 0)
    other_income = inputs_dict.get('other_income', 0)
    capital_gain = inputs_dict.get('capital_gain', 0)
    filing = inputs_dict.get('filing', 'MFJ')
    
    pi_before = results_dict.get('provisional_income_before', results_dict.get('pi_before', 0))
    pi_after = results_dict.get('provisional_income_after', results_dict.get('pi_after', 0))
    ss_taxable_before = results_dict.get('ss_taxable_before', 0)
    ss_taxable_after = results_dict.get('ss_taxable_after', 0)
    effective_rate_on_gain = results_dict.get('effective_rate_on_gain', 
                          results_dict.get('effective_cg_rate', 0))
    
    # Additional fields from calc_capital_gains_bump
    additional_ss_taxable = results_dict.get('additional_ss_taxable', 0)
    nominal_cg_rate = results_dict.get('nominal_cg_rate', 15)
    bump_zone_penalty = results_dict.get('bump_zone_penalty', 0)
    tax_increase = results_dict.get('tax_increase', 0)
    ss_pct_before = results_dict.get('ss_pct_before', 0)
    ss_pct_after = results_dict.get('ss_pct_after', 0)
    agi_before = results_dict.get('agi_before', other_income)
    agi_after = results_dict.get('agi_after', other_income + capital_gain)
    fed_tax_before = results_dict.get('fed_tax_before', 0)
    fed_tax_after = results_dict.get('fed_tax_after', results_dict.get('fed_tax_no_roth', 0))
    
    filing_display = "Married Filing Jointly" if filing == 'MFJ' else "Single"
    
    # Determine if bump zone is significant
    is_bumped = bump_zone_penalty > 5
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>Capital Gains Bump Zone Report — {fname}</title>
    <style>{SHARED_CSS}</style>
    </head>
    <body>
    
    <!-- PAGE 1: COVER -->
    <div class="page">
    <div class="cover-page">
      <div class="top-banner">
        SUMMIT TAX SERVICES &nbsp;|&nbsp; PERSONALIZED ANALYSIS
      </div>
      
      {_client_header_html(client_name, client_id)}
      
      <span class="label-spread" style="margin-bottom: 20px;">CAPITAL GAINS BUMP ZONE</span>
      
      <h1 style="font-size: 28pt; line-height: 1.1; margin-bottom: 24px;">
        The Hidden Tax on<br>
        Your <span class="highlight">Capital Gains</span><br>
        <span class="redline">Nobody Tells You About</span>
      </h1>
      
      <p style="font-size: 12pt; color: var(--cream); font-style: italic; max-width: 540px; margin-bottom: 32px; line-height: 1.6;">
        When you sell an asset, the capital gains tax seems straightforward. But for retirees receiving Social Security, a capital gain can trigger a second, hidden tax torpedo — making your effective rate far higher than the nominal rate.
      </p>
      
      <div class="stat-row" style="max-width: 600px;">
        <div class="stat-card">
          <span class="number">{_fmt_pct(nominal_cg_rate)}</span>
          <span class="label">NOMINAL<br>CG RATE</span>
        </div>
        <div class="stat-card">
          <span class="number red-num">{_fmt_pct(effective_rate_on_gain)}</span>
          <span class="label">EFFECTIVE RATE<br>ON YOUR GAIN</span>
        </div>
        <div class="stat-card">
          <span class="number red-num">{_fmt_pct(bump_zone_penalty)}</span>
          <span class="label">BUMP ZONE<br>PENALTY</span>
        </div>
      </div>
      
      <div class="callout callout-gold" style="max-width: 560px;">
        <span class="callout-label">YOUR INPUTS</span>
        <p><strong>SS Benefit (annual):</strong> {_fmt_dollar(ss_benefit_annual)} &nbsp;|&nbsp; <strong>Other Income:</strong> {_fmt_dollar(other_income)}</p>
        <p><strong>Capital Gain:</strong> {_fmt_dollar(capital_gain)} &nbsp;|&nbsp; <strong>Filing Status:</strong> {filing_display}</p>
      </div>
    </div>
    </div>
    
    <!-- PAGE 2: BEFORE vs AFTER -->
    <div class="page">
    <div class="light-page">
      {_client_header_html(client_name, client_id, is_dark=False)}
      
      <span class="label-spread" style="color: var(--navy);">BEFORE vs. AFTER THE GAIN</span>
      
      <h2 style="color: var(--navy); margin-bottom: 20px; font-size: 22pt;">
        How a {_fmt_dollar(capital_gain)} Gain<br><span style="color: var(--gold);">Cascades Into Your Taxes</span>
      </h2>
      
      <p style="color: var(--text-body); margin-bottom: 20px;">
        When you take a capital gain, it increases your AGI, which increases your provisional income, which increases the percentage of your Social Security that's taxable. This "double tax" effect is the <strong>capital gains bump zone</strong>.
      </p>
      
      <div class="two-paths">
        <div class="path-card path-good">
          <h4>BEFORE THE GAIN</h4>
          <p><strong>AGI:</strong> {_fmt_dollar(agi_before)}</p>
          <p><strong>Provisional Income:</strong> {_fmt_dollar(pi_before)}</p>
          <p><strong>SS Taxable:</strong> {_fmt_dollar(ss_taxable_before)} ({_fmt_pct(ss_pct_before)})</p>
          <p><strong>Federal Tax:</strong> {_fmt_dollar(fed_tax_before)}</p>
        </div>
        <div class="path-card path-bad">
          <h4>AFTER THE GAIN</h4>
          <p><strong>AGI:</strong> {_fmt_dollar(agi_after)}</p>
          <p><strong>Provisional Income:</strong> {_fmt_dollar(pi_after)}</p>
          <p><strong>SS Taxable:</strong> {_fmt_dollar(ss_taxable_after)} ({_fmt_pct(ss_pct_after)})</p>
          <p><strong>Federal Tax:</strong> {_fmt_dollar(fed_tax_after)}</p>
        </div>
      </div>
      
      <div class="callout callout-red" style="background: #fdf2f0;">
        <span class="callout-label" style="color: var(--red);">THE BUMP ZONE EFFECT</span>
        <p style="color: var(--text-body);">Your capital gain of <strong>{_fmt_dollar(capital_gain)}</strong> caused an additional <strong>{_fmt_dollar(additional_ss_taxable)}</strong> of Social Security to become taxable. Your total tax increased by <strong style="color: var(--red-bright);">{_fmt_dollar(tax_increase)}</strong>.</p>
        <p style="color: var(--text-body); margin-bottom: 0;">That means your <strong>effective rate on the gain is {_fmt_pct(effective_rate_on_gain)}</strong> — not the nominal {_fmt_pct(nominal_cg_rate)} you might expect. The difference ({_fmt_pct(bump_zone_penalty)}) is the <strong>hidden bump zone penalty</strong>.</p>
      </div>
      
      <div class="consider-this" style="background: linear-gradient(135deg, rgba(201,168,76,0.1) 0%, rgba(201,168,76,0.03) 100%);">
        <span class="ct-label">CONSIDER THIS</span>
        A capital gain that appears to be taxed at 15% can actually cost you 25%, 30%, or more once you include the cascading effect on Social Security. This is why timing capital gains — and pairing them with a Roth conversion strategy — matters so much.
      </div>
      
      {_disclaimer_footer()}
    </div>
    </div>
    
    <!-- PAGE 3: STRATEGY -->
    <div class="page">
    <div class="dark-page">
      <span class="label-spread">STRATEGY RECOMMENDATIONS</span>
      
      <h1 style="margin-bottom: 20px; font-size: 24pt;">
        How to Avoid the<br><span class="highlight">Bump Zone Penalty</span>
      </h1>
      
      <div class="callout callout-red">
        <span class="callout-label" style="color: var(--red);">YOUR BUMP ZONE IS {'ACTIVE' if is_bumped else 'LOW'}</span>
        <p>{'Your effective rate on capital gains is significantly higher than the nominal rate. This means every time you sell an asset, the government takes a hidden bonus — through your Social Security.' if is_bumped else 'Your current capital gain has a modest bump zone effect, but larger gains or additional income could push you deeper into the zone.'}</p>
      </div>
      
      <hr class="section-divider">
      
      <h2><span class="highlight">Three Strategies</span> to Minimize the Bump</h2>
      
      <ul class="check-list">
        <li><strong>Spread gains across multiple years.</strong> Instead of realizing a large gain in one year, sell assets incrementally to stay below the bump zone threshold. Each year, calculate how much gain you can take before triggering additional SS taxation.</li>
        <li><strong>Offset gains with Roth conversions.</strong> If you're already doing Roth conversions, coordinate capital gains timing so you don't stack both in the same year. A Roth conversion and a capital gain in the same year can create a double torpedo.</li>
        <li><strong>Use tax-loss harvesting proactively.</strong> Realize losses in the same year as gains to offset the bump zone. This is especially powerful in the years between 60 and 73 when you control your income most flexibly.</li>
      </ul>
      
      <div class="pull-quote">
        <p>A {_fmt_pct(nominal_cg_rate)} capital gains rate sounds reasonable. But when the bump zone is active, you could be paying <strong>{_fmt_pct(effective_rate_on_gain)} effective</strong> — nearly double. The right strategy can shrink or eliminate this hidden tax.</p>
      </div>
      
      {_cta_box_dark()}
      
      {_disclaimer_footer()}
    </div>
    </div>
    
    </body>
    </html>
    """
    
    output_path = os.path.join(REPORTS_DIR, f"{client_id}_capital_gains_report.pdf")
    return _render_pdf(html, output_path)


# ═══════════════════════════════════════════════════════════════════════════
# 4. TAX BILL / RETIREMENT TAX ANALYSIS REPORT
# ═══════════════════════════════════════════════════════════════════════════

# IRS Uniform Lifetime Table (for RMD calculations)
_RMD_FACTORS = {
    72: 27.4, 73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
    78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7,
    84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4, 88: 13.7, 89: 12.9,
    90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1, 94:  9.5, 95:  8.9,
    96:  8.4, 97:  7.8, 98:  7.3, 99:  6.8, 100: 6.4, 101: 6.0,
    102: 5.6, 103: 5.3, 104: 5.0, 105: 4.7, 106: 4.4, 107: 4.1,
    108: 3.9, 109: 3.7, 110: 3.5, 111: 3.3, 112: 3.1, 113: 2.9,
    114: 2.8, 115: 2.6, 116: 2.5, 117: 2.4, 118: 2.3, 119: 2.2,
    120: 2.1,
}


def _calc_rmd_schedule(ira_balance, growth_rate, tax_rate, start_age, end_age=95):
    """
    Calculate year-by-year RMD schedule for the 'current approach' scenario.
    Returns list of dicts: {year, age, rmd_factor, rmd, after_tax_rmd, remaining_ira, taxable_acct}
    """
    rows = []
    balance = ira_balance
    taxable_acct = 0.0

    for age in range(start_age, end_age + 1):
        # Growth
        balance = balance * (1 + growth_rate)

        # RMD
        if age >= 73:
            factor = _RMD_FACTORS.get(age, 2.0)
            rmd = balance / factor
        else:
            rmd = 0.0

        # After-tax RMD (distributed and taxed)
        after_tax_rmd = rmd * (1 - tax_rate)
        # Taxable account grows after-tax RMDs
        if rmd > 0:
            taxable_acct = (taxable_acct + after_tax_rmd) * (1 + growth_rate * (1 - tax_rate * 0.5))
        else:
            taxable_acct = taxable_acct  # No new deposits, but growth already applied via balance

        balance = max(0, balance - rmd)

        rows.append({
            'age': age,
            'rmd_factor': _RMD_FACTORS.get(age, 0) if age >= 73 else 0,
            'rmd': rmd,
            'after_tax_rmd': after_tax_rmd,
            'remaining_ira': balance,
            'taxable_acct': taxable_acct,
        })

    return rows


def tax_bill_report(client_name, client_id, inputs_dict, results_dict):
    """
    Generate a Retirement Tax Bill Analysis PDF report.

    inputs: {ira_balance, tax_rate, age, filing, growth_rate}
    results: {total_taxes_current, total_taxes_conversion, tax_savings,
              ira_after_distributions, taxable_acct_value, roth_value}

    Returns the PDF file path.
    """
    fname = _first_name(client_name)
    ira_balance = inputs_dict.get('ira_balance', 500000)
    tax_rate = inputs_dict.get('tax_rate', 0.25)
    age = inputs_dict.get('age', 65)
    filing = inputs_dict.get('filing', 'MFJ')
    growth_rate = inputs_dict.get('growth_rate', 0.05)

    total_taxes_current = results_dict.get('total_taxes_current', ira_balance * tax_rate)
    total_taxes_conversion = results_dict.get('total_taxes_conversion', ira_balance * tax_rate)
    tax_savings = results_dict.get('tax_savings', 0)
    ira_after = results_dict.get('ira_after_distributions', 0)
    taxable_acct = results_dict.get('taxable_acct_value', 0)
    roth_value = results_dict.get('roth_value', 0)

    filing_label = 'Married Filing Jointly' if filing == 'MFJ' else 'Single'

    # Calculate RMD schedule
    rmd_schedule = _calc_rmd_schedule(ira_balance, growth_rate, tax_rate, age, min(age + 30, 95))

    # Build RMD table rows (show condensed: pre-RMD summary + key RMD years)
    rmd_rows_html = ""
    for row in rmd_schedule:
        if row['rmd'] > 0 or row['age'] <= age + 2:
            rmd_rows_html += f"""
            <tr>
              <td style="text-align:center; padding: 4px 8px; border-bottom: 1px solid {CREAM_DARK}; font-size: 9pt;">{row['age']}</td>
              <td style="text-align:center; padding: 4px 8px; border-bottom: 1px solid {CREAM_DARK}; font-size: 9pt;">{row['rmd_factor'] if row['rmd_factor'] else '—'}</td>
              <td style="text-align:right; padding: 4px 8px; border-bottom: 1px solid {CREAM_DARK}; font-size: 9pt;">{_fmt_dollar(row['rmd'])}</td>
              <td style="text-align:right; padding: 4px 8px; border-bottom: 1px solid {CREAM_DARK}; font-size: 9pt;">{_fmt_dollar(row['after_tax_rmd'])}</td>
              <td style="text-align:right; padding: 4px 8px; border-bottom: 1px solid {CREAM_DARK}; font-size: 9pt;">{_fmt_dollar(row['remaining_ira'])}</td>
              <td style="text-align:right; padding: 4px 8px; border-bottom: 1px solid {CREAM_DARK}; font-size: 9pt;">{_fmt_dollar(row['taxable_acct'])}</td>
            </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        {SHARED_CSS}
        .comparison-grid {{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin: 24px 0;
        }}
        .approach-card {{
          background: {WHITE};
          border-radius: 10px;
          padding: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .approach-card.current {{ border-top: 4px solid {RED}; }}
        .approach-card.adjusted {{ border-top: 4px solid {GREEN}; }}
        .shock-number {{
          font-family: 'Inter', sans-serif;
          font-size: 42pt;
          font-weight: 800;
          color: {GOLD};
          text-align: center;
          margin: 16px 0;
        }}
        .data-table {{
          width: 100%;
          border-collapse: collapse;
          margin: 16px 0;
        }}
        .data-table th {{
          font-family: 'Inter', sans-serif;
          font-size: 8pt;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          color: {GRAY_MID};
          text-align: right;
          padding: 6px 8px;
          border-bottom: 2px solid {NAVY};
        }}
        .data-table th:first-child {{ text-align: center; }}
        .data-table th:nth-child(2) {{ text-align: center; }}
        .summary-row {{
          font-weight: 700;
          background: rgba(201,168,76,0.08);
        }}
        .input-tag {{
          display: inline-block;
          background: {CREAM};
          border-radius: 6px;
          padding: 4px 12px;
          margin: 2px 4px;
          font-size: 10pt;
          font-family: 'Inter', sans-serif;
        }}
      </style>
    </head>
    <body>

    <!-- PAGE 1: Cover -->
    <div class="page cover-page">
      <div style="flex: 1;"></div>
      <div>
        <div class="label-spread">Personalized Analysis</div>
        <h1>{fname}'s <span class="highlight">Tax Analysis</span></h1>
        <p style="font-size: 14pt; color: {CREAM}; line-height: 1.6; margin-top: 20px;">
          Approaches for Qualified Accounts
        </p>
        <p style="font-size: 10pt; color: {GRAY_LIGHT}; margin-top: 24px;">
          Many savers use a tax-deferred account, like a traditional IRA or 401(k), to save funds for retirement.
          Tax-deferred accounts are funded with pre-tax dollars. These accounts accumulate funds tax-deferred,
          meaning taxes are owed on the funds when they are distributed, not when contributed.
        </p>
        <p style="font-size: 10pt; color: {GRAY_LIGHT}; margin-top: 12px;">
          With an existing qualified account, there are two potential ways to manage your account and the tax
          status of your savings:
        </p>
        <div style="margin-top: 16px; padding-left: 16px; border-left: 3px solid {GOLD};">
          <p style="font-size: 10pt; color: {CREAM};"><span class="strong" style="color: {GOLD};">Current Approach:</span> Keep the account as-is and accumulate funds tax-deferred</p>
          <p style="font-size: 10pt; color: {CREAM}; margin-top: 6px;"><span class="strong" style="color: {GREEN_LIGHT};">Adjusted Approach:</span> Reallocate to a tax-free vehicle and accumulate funds tax-free</p>
        </div>
      </div>
      <div style="text-align: center; margin-top: 30px;">
        <p style="font-size: 8pt; color: {GRAY_LIGHT};">This report is © {datetime.now().year} Summit Tax Services</p>
      </div>
    </div>

    <!-- PAGE 2: Summary Comparison -->
    <div class="page dark-page">
      {_client_header_html(client_name, client_id, is_dark=True)}
      <div style="margin-bottom: 12px;">
        <div class="label-spread">Your Inputs</div>
        <span class="input-tag">IRA Value: <strong>{_fmt_dollar(ira_balance)}</strong></span>
        <span class="input-tag">Tax Rate: <strong>{_fmt_pct(tax_rate * 100)}</strong></span>
        <span class="input-tag">Age: <strong>{age}</strong></span>
        <span class="input-tag">Filing: <strong>{filing_label}</strong></span>
        <span class="input-tag">Growth: <strong>{_fmt_pct(growth_rate * 100)}</strong></span>
      </div>

      <div class="label-spread">Your Potential Retirement Tax Bill</div>
      <div class="shock-number">{_fmt_dollar(total_taxes_current)}</div>
      <p style="text-align: center; color: {CREAM}; font-size: 9pt; margin-top: -8px; margin-bottom: 24px;">
        Total potential taxes on your qualified account over your retirement
      </p>

      <div class="comparison-grid">
        <div class="approach-card current">
          <div style="font-family: 'Inter', sans-serif; font-size: 8pt; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: {RED}; margin-bottom: 12px;">Current Approach</div>
          <p style="font-size: 9pt; color: {TEXT_MUTED}; margin-bottom: 12px;">You keep your IRA/401(k), take Required Minimum Distributions, and pay taxes on every dollar withdrawn.</p>
          <div style="border-top: 1px solid {CREAM_DARK}; padding-top: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
              <span style="font-size: 9pt; color: {TEXT_MUTED};">Total Potential Taxes</span>
              <span style="font-family: 'Inter', sans-serif; font-weight: 700; color: {RED_BRIGHT};">{_fmt_dollar(total_taxes_current)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
              <span style="font-size: 9pt; color: {TEXT_MUTED};">Remaining IRA Value</span>
              <span style="font-family: 'Inter', sans-serif; font-weight: 600;">{_fmt_dollar(ira_after)}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="font-size: 9pt; color: {TEXT_MUTED};">Taxable Acct. Value</span>
              <span style="font-family: 'Inter', sans-serif; font-weight: 600;">{_fmt_dollar(taxable_acct)}</span>
            </div>
          </div>
        </div>

        <div class="approach-card adjusted">
          <div style="font-family: 'Inter', sans-serif; font-size: 8pt; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: {GREEN}; margin-bottom: 12px;">Adjusted Approach</div>
          <p style="font-size: 9pt; color: {TEXT_MUTED}; margin-bottom: 12px;">You convert to a Roth IRA. Withdrawals of principal and interest are distributed tax-free. No RMDs required.</p>
          <div style="border-top: 1px solid {CREAM_DARK}; padding-top: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
              <span style="font-size: 9pt; color: {TEXT_MUTED};">Taxes on Conversion</span>
              <span style="font-family: 'Inter', sans-serif; font-weight: 700; color: {GOLD};">{_fmt_dollar(total_taxes_conversion)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
              <span style="font-size: 9pt; color: {TEXT_MUTED};">Tax-Free Roth Value</span>
              <span style="font-family: 'Inter', sans-serif; font-weight: 600; color: {GREEN};">{_fmt_dollar(roth_value)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 10px; padding-top: 8px; border-top: 2px solid {GREEN};">
              <span style="font-size: 10pt; font-weight: 700; color: {GREEN};">Potential Tax Savings</span>
              <span style="font-family: 'Inter', sans-serif; font-size: 14pt; font-weight: 800; color: {GREEN_LIGHT};">{_fmt_dollar(tax_savings)}</span>
            </div>
          </div>
        </div>
      </div>

      {_cta_box_dark()}
    </div>

    <!-- PAGE 3: RMD Data Table -->
    <div class="page light-page">
      <div class="label-spread navy">Data: Qualified Account Analysis</div>
      <h2 style="color: {NAVY}; margin-bottom: 16px;">Year-by-Year RMD Schedule</h2>
      <p style="font-size: 9pt; color: {TEXT_MUTED}; margin-bottom: 12px;">
        Required Minimum Distributions begin at age 73. RMD factors are based on IRS Uniform Lifetime Table.
        Taxable account value assumes after-tax RMDs are reinvested at an equivalent after-tax rate.
      </p>

      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 30px;">Age</th>
            <th style="width: 55px;">RMD Factor</th>
            <th>RMD</th>
            <th>After-Tax RMD</th>
            <th>Remaining IRA</th>
            <th>Taxable Acct.</th>
          </tr>
        </thead>
        <tbody>
          {rmd_rows_html}
        </tbody>
      </table>

      {_cta_box_light()}
    </div>

    <!-- PAGE 4: Disclosures -->
    <div class="page light-page">
      <div class="label-spread navy" style="margin-bottom: 20px;">Important Disclosures</div>
      <div style="font-size: 9pt; color: {TEXT_MUTED}; line-height: 1.7;">
        <p style="margin-bottom: 12px;">
          These disclosures apply to this presentation in its entirety. Determining when (or if) you should
          convert to a Roth IRA is an individual decision based on factors such as your financial situation,
          age, tax bracket, current assets, and alternate sources of retirement income. Your unique
          circumstances help determine what's right for you.
        </p>
        <p style="margin-bottom: 12px;">
          The information contained herein is based on our understanding of current tax law. The tax and
          legislative information may be subject to change and different interpretations. We recommend that
          you seek professional legal advice for applicability to your personal situation.
        </p>
        <p style="margin-bottom: 12px;">
          This is not a complete list of features and benefits of a qualified account and Required Minimum
          Distributions (RMDs) at the designated age. This information is provided for informational purposes
          only and should not be considered investment advice for individuals or advice on withdrawing funds
          from your qualified account.
        </p>
        <p style="margin-bottom: 12px;">
          <strong>Circular 230 Disclosure:</strong> To ensure compliance with requirements imposed by the IRS,
          we inform you that any federal income tax information in this document is not intended to (and cannot)
          be used by anyone to avoid IRS penalties. Per the license limitations of the licensed professional
          presenting this material, this proposal is not intended to offer or provide, and no statement
          contained herein shall constitute tax or legal advice. See qualified professionals in these areas
          before making any decisions about your individual situation. Your financial professional is not
          permitted to offer, and no statement contained herein shall constitute, tax or legal advice.
        </p>
        <p style="margin-bottom: 12px;">
          This hypothetical example does not consider every product or feature of tax-deferred accounts,
          tax-free accounts, or Roth accounts and is for illustrative purposes only. It should not be deemed
          a representation of past or future results, and is no guarantee of return or future performance.
          Your tax bracket may be lower or higher in retirement, unlike this hypothetical example.
        </p>
        <p style="margin-bottom: 12px;">
          Examples of tax-free accounts include Roth IRAs and Roth 401(k) accounts. Roth accounts use
          post-tax dollars; withdrawals of principal and interest are distributed tax-free. Although qualified
          withdrawals from a Roth IRA are tax-free, when converting a Traditional IRA into a Roth IRA, the
          entire converted taxable amount is reportable as income in the year of conversion.
        </p>
      </div>
      <div style="text-align: center; margin-top: 30px; padding-top: 16px; border-top: 1px solid {CREAM_DARK};">
        <p style="font-size: 8pt; color: {GRAY_MID};">© {datetime.now().year} Summit Tax Services. All Rights Reserved.</p>
      </div>
    </div>

    </body>
    </html>
    """

    output_path = os.path.join(REPORTS_DIR, f'tax_bill_{client_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
    return _render_pdf(html, output_path)


# 5. PERSONALIZED GUIDE
# ═══════════════════════════════════════════════════════════════════════════

def generate_personalized_guide(client_name, client_id):
    """
    Generate a personalized MaxSS guide PDF with ?c=CLIENT_ID on every calculator link.
    
    Reads the source guide HTML, replaces every localhost:5002 link with
    localhost:5002?c=CLIENT_ID, adds a personalized cover note, and generates
    via WeasyPrint.
    
    Returns the PDF file path.
    """
    fname = _first_name(client_name)
    
    # Read the source guide HTML
    with open(GUIDE_SOURCE, 'r', encoding='utf-8') as f:
        guide_html = f.read()
    
    # Replace all localhost:5002 URLs with ?c=CLIENT_ID parameter
    # Match href="http://localhost:5002/..." and href="http://localhost:5002?..."
    # Also match plain text references to localhost:5002
    
    # Pattern 1: href links with full URLs
    guide_html = re.sub(
        r'href="http://localhost:5002(/[^"]*)?"',
        lambda m: f'href="http://localhost:5002{m.group(1) or ""}?c={client_id}"',
        guide_html
    )
    
    # Pattern 2: plain text references (in divs that show the URL)
    guide_html = re.sub(
        r'localhost:5002(/[^\s<]*)?',
        lambda m: f'localhost:5002{m.group(1) or ""}?c={client_id}',
        guide_html
    )
    
    # Clean up double question marks (if a URL already had ?c=)
    guide_html = guide_html.replace(f'?c={client_id}?c={client_id}', f'?c={client_id}')
    
    # Add personalized cover note at the top of the body
    # We insert it right after the <body> tag, before the first page
    personalized_note = f"""
    <!-- PERSONALIZED COVER NOTE -->
    <div style="
      background: linear-gradient(135deg, {NAVY} 0%, {NAVY_MID} 100%);
      color: {CREAM};
      padding: 32px 40px;
      margin: -0.75in -0.85in;
      min-height: calc(11in - 1.5in);
      page-break-after: always;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
    ">
      <div style="
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: {GOLD};
        margin-bottom: 16px;
      ">PERSONALLY PREPARED FOR</div>
      
      <div style="
        font-family: 'Georgia', serif;
        font-size: 36pt;
        font-weight: 700;
        color: {WHITE};
        margin-bottom: 24px;
        line-height: 1.2;
      ">{fname}</div>
      
      <div style="
        width: 80px;
        height: 3px;
        background: {GOLD};
        margin: 0 auto 24px;
      "></div>
      
      <div style="
        font-family: 'Georgia', serif;
        font-size: 16pt;
        font-style: italic;
        color: {CREAM};
        max-width: 500px;
        line-height: 1.6;
        margin-bottom: 32px;
      ">The Maximizer's Guide to Social Security — 2026 Edition</div>
      
      <div style="
        font-family: 'Inter', sans-serif;
        font-size: 9pt;
        color: {GRAY_LIGHT};
        letter-spacing: 1px;
        margin-bottom: 8px;
      ">Client ID: {client_id} &nbsp;|&nbsp; {_today_str()}</div>
      
      <div style="
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: {GRAY_LIGHT};
        letter-spacing: 1px;
        margin-bottom: 32px;
      ">Summit Tax Services</div>
      
      <div style="
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(201,168,76,0.25);
        border-radius: 6px;
        padding: 20px 28px;
        max-width: 480px;
        text-align: center;
      ">
        <div style="
          font-family: 'Georgia', serif;
          font-size: 12pt;
          color: {CREAM};
          font-style: italic;
          line-height: 1.65;
          margin-bottom: 0;
        ">
          {fname}, every calculator link in this guide is personalized for you. 
          When you click through, your results will be tracked so we can follow up with 
          a strategy tailored specifically to your situation.
        </div>
      </div>
      
      <div style="
        margin-top: 32px;
        font-family: 'Inter', sans-serif;
        font-size: 7.5pt;
        color: {GRAY_LIGHT};
        letter-spacing: 2px;
        text-transform: uppercase;
      ">TURN THE PAGE TO BEGIN →</div>
    </div>
    """
    
    # Insert personalized note right after <body>
    guide_html = guide_html.replace('<body>', f'<body>\n{personalized_note}', 1)
    
    # Generate the PDF
    output_path = os.path.join(REPORTS_DIR, f"{client_id}_maxss_guide.pdf")
    return _render_pdf(guide_html, output_path)


# ═══════════════════════════════════════════════════════════════════════════
# Convenience: generate all reports for a client
# ═══════════════════════════════════════════════════════════════════════════

def generate_all_reports(client_name, client_id, ss_inputs=None, ss_results=None,
                         torpedo_inputs=None, torpedo_results=None,
                         cg_inputs=None, cg_results=None,
                         include_guide=True):
    """
    Generate all available reports for a client.
    Returns a dict of report_type: file_path.
    """
    from tax_engine import (
        calc_ss_claiming_comparison, calc_full_scenario, calc_capital_gains_bump,
        get_fra, get_fra_display,
    )
    
    reports = {}
    
    # SS Claiming Report
    if ss_inputs and ss_results:
        try:
            path = ss_report(client_name, client_id, ss_inputs, ss_results)
            reports['ss_claiming'] = path
        except Exception as e:
            reports['ss_claiming_error'] = str(e)
    
    # Tax Torpedo Report
    if torpedo_inputs and torpedo_results:
        try:
            path = torpedo_report(client_name, client_id, torpedo_inputs, torpedo_results)
            reports['tax_torpedo'] = path
        except Exception as e:
            reports['tax_torpedo_error'] = str(e)
    
    # Capital Gains Report
    if cg_inputs and cg_results:
        try:
            path = capital_gains_report(client_name, client_id, cg_inputs, cg_results)
            reports['capital_gains'] = path
        except Exception as e:
            reports['capital_gains_error'] = str(e)
    
    # Personalized Guide
    if include_guide:
        try:
            path = generate_personalized_guide(client_name, client_id)
            reports['guide'] = path
        except Exception as e:
            reports['guide_error'] = str(e)
    
    return reports