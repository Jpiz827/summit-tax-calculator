"""
Summit Tax Services — Social Security & Tax Torpedo Calculator
Flask web application with Plotly.js interactive charts and client tracking.
"""

from flask import Flask, render_template, request, jsonify, url_for, send_from_directory
from tax_engine import (
    calc_full_scenario, calc_ss_claiming_comparison, calc_torpedo_chart_data,
    get_fra, get_fra_display, calc_ss_benefit_at_age,
    calc_provisional_income, calc_ss_taxable, calc_effective_marginal_rate,
    calc_irmaa, calc_irmaa_tier,
    calc_marginal_rate, IRMAA_MFJ, IRMAA_SINGLE,
    calc_capital_gains_bump, calc_cg_bump_chart_data,
    calc_widow_tax_hit,
    calc_qcd_benefit,
)
import client_db
import email_sender
import report_generator
import json
import threading

app = Flask(__name__)


@app.route('/maxss')
def guide_request():
    """Guide request landing page — where ads send traffic."""
    return render_template('guide_request.html')


@app.route('/checkup')
def checkup():
    """Tax & Retirement Check-Up tool (self-contained static page)."""
    return send_from_directory(app.static_folder, 'checkup.html')


@app.route('/')
def index():
    """Landing page — choose calculator."""
    client_id = request.args.get('c')
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_db.log_action(client_id, 'visit', 'Landing page')
    return render_template('index.html', client_id=client_id)


@app.route('/ss-calculator')
def ss_calculator():
    """Social Security claiming strategy calculator."""
    client_id = request.args.get('c')
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_db.log_action(client_id, 'visit', 'SS Calculator')
    return render_template('ss_calculator.html', client_id=client_id)


@app.route('/torpedo-calculator')
def torpedo_calculator():
    """Tax torpedo calculator."""
    client_id = request.args.get('c')
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_db.log_action(client_id, 'visit', 'Torpedo Calculator')
    return render_template('torpedo_calculator.html', client_id=client_id)


@app.route('/capital-gains')
def capital_gains():
    """Capital gains bump zone calculator."""
    client_id = request.args.get('c')
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_db.log_action(client_id, 'visit', 'Capital Gains Calculator')
    return render_template('capital_gains.html', client_id=client_id)


@app.route('/widow-tax-hit')
def widow_tax_hit():
    """Widow/survivor tax hit calculator."""
    client_id = request.args.get('c')
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_db.log_action(client_id, 'visit', 'Widow Tax Hit Calculator')
    return render_template('widow_tax_hit.html', client_id=client_id)


@app.route('/qcd-benefit')
def qcd_benefit():
    """QCD (Qualified Charitable Distribution) benefit calculator."""
    client_id = request.args.get('c')
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_db.log_action(client_id, 'visit', 'QCD Benefit Calculator')
    return render_template('qcd_benefit.html', client_id=client_id)


@app.route('/irmaa')
def irmaa():
    """IRMAA surcharge calculator."""
    client_id = request.args.get('c')
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_db.log_action(client_id, 'visit', 'IRMAA Calculator')
    return render_template('irmaa.html', client_id=client_id)


@app.route('/tax-bill')
def tax_bill():
    """Retirement Tax Bill Calculator — 3-step lead generation funnel."""
    client_id = request.args.get('c')
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_db.log_action(client_id, 'visit', 'Tax Bill Calculator')
    return render_template('tax_bill.html', client_id=client_id)


@app.route('/rothrx')
def rothrx():
    """RothRx Blueprint Calculator (self-contained)."""
    return render_template('rothrx.html')



@app.route('/api/tax-bill-calculate', methods=['POST'])
def api_tax_bill_calculate():
    """Calculate retirement tax bill comparison (current vs adjusted approach).
    Accepts: {ira_balance, tax_rate, age, filing, growth_rate?}
    Returns: {total_taxes_current, total_taxes_conversion, tax_savings,
              ira_after_distributions, taxable_acct_value, roth_value, rmd_schedule}
    """
    data = request.json
    ira_balance = float(data.get('ira_balance', 0))
    tax_rate = float(data.get('tax_rate', 0.25))
    age = int(data.get('age', 65))
    filing = data.get('filing', 'MFJ')
    growth_rate = float(data.get('growth_rate', 0.05))

    if ira_balance <= 0:
        return jsonify({'error': 'IRA balance must be greater than 0'}), 400
    if not (0.15 <= tax_rate <= 0.40):
        return jsonify({'error': 'Tax rate must be between 15% and 40%'}), 400
    if not (55 <= age <= 80):
        return jsonify({'error': 'Age must be between 55 and 80'}), 400

    # Calculate RMD schedule (current approach)
    from report_generator import _calc_rmd_schedule
    rmd_schedule = _calc_rmd_schedule(ira_balance, growth_rate, tax_rate, age, min(age + 30, 95))

    # Total taxes under current approach = sum of (RMD * tax_rate) for all RMD years
    total_taxes_current = sum(row['rmd'] * tax_rate for row in rmd_schedule)

    # IRA remaining after all distributions
    ira_after_distributions = rmd_schedule[-1]['remaining_ira'] if rmd_schedule else 0

    # Taxable account value (after-tax RMDs reinvested)
    taxable_acct_value = rmd_schedule[-1]['taxable_acct'] if rmd_schedule else 0

    # Adjusted approach: Convert entire IRA to Roth
    # Tax on conversion = IRA balance * tax_rate
    total_taxes_conversion = ira_balance * tax_rate

    # Roth value after growth (tax-free)
    years = min(age + 30, 95) - age
    roth_value = ira_balance * (1 + growth_rate) ** years * (1 - tax_rate)  # after paying conversion tax

    # Actually, the Roth value should just be the IRA balance growing tax-free
    # The conversion tax is paid from outside (or from the IRA itself)
    # For simplicity: Roth = (IRA - taxes) * growth^years if taxes paid from IRA
    # Or Roth = IRA * growth^years if taxes paid from outside
    # Stonewood shows: taxes paid separately, Roth = full IRA balance growing tax-free
    roth_value = ira_balance * (1 + growth_rate) ** years  # full balance, tax-free growth

    # Tax savings = current approach total taxes - conversion taxes
    tax_savings = total_taxes_current - total_taxes_conversion

    # Format RMD schedule for response
    rmd_data = []
    for row in rmd_schedule:
        if row['rmd'] > 0 or row['age'] <= age + 2:
            rmd_data.append({
                'age': row['age'],
                'rmd_factor': row['rmd_factor'],
                'rmd': round(row['rmd'], 2),
                'after_tax_rmd': round(row['after_tax_rmd'], 2),
                'remaining_ira': round(row['remaining_ira'], 2),
                'taxable_acct': round(row['taxable_acct'], 2),
            })

    return jsonify({
        'total_taxes_current': round(total_taxes_current, 2),
        'total_taxes_conversion': round(total_taxes_conversion, 2),
        'tax_savings': round(max(0, tax_savings), 2),
        'ira_after_distributions': round(ira_after_distributions, 2),
        'taxable_acct_value': round(taxable_acct_value, 2),
        'roth_value': round(roth_value, 2),
        'rmd_schedule': rmd_data,
    })


@app.route('/api/tax-bill-lead', methods=['POST'])
def api_tax_bill_lead():
    """Capture lead from tax bill funnel and generate/send PDF report.
    Accepts: {first_name, last_name, email, phone, ira_balance, tax_rate, age, filing, growth_rate?}
    """
    data = request.json
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    ira_balance = float(data.get('ira_balance', 0))
    tax_rate = float(data.get('tax_rate', 0.25))
    age = int(data.get('age', 65))
    filing = data.get('filing', 'MFJ')
    growth_rate = float(data.get('growth_rate', 0.05))

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    client_name = f"{first_name} {last_name}".strip() or 'Friend'

    # Find or create client
    client = client_db.find_or_create_client(client_name, email, phone=phone)
    client_id = client['id']

    # Calculate results
    from report_generator import _calc_rmd_schedule
    rmd_schedule = _calc_rmd_schedule(ira_balance, growth_rate, tax_rate, age, min(age + 30, 95))

    total_taxes_current = sum(row['rmd'] * tax_rate for row in rmd_schedule)
    total_taxes_conversion = ira_balance * tax_rate
    years = min(age + 30, 95) - age
    roth_value = ira_balance * (1 + growth_rate) ** years
    tax_savings = max(0, total_taxes_current - total_taxes_conversion)
    ira_after = rmd_schedule[-1]['remaining_ira'] if rmd_schedule else 0
    taxable_acct = rmd_schedule[-1]['taxable_acct'] if rmd_schedule else 0

    inputs_dict = {
        'ira_balance': ira_balance,
        'tax_rate': tax_rate,
        'age': age,
        'filing': filing,
        'growth_rate': growth_rate,
    }
    results_dict = {
        'total_taxes_current': total_taxes_current,
        'total_taxes_conversion': total_taxes_conversion,
        'tax_savings': tax_savings,
        'ira_after_distributions': ira_after,
        'taxable_acct_value': taxable_acct,
        'roth_value': roth_value,
    }

    # Generate and send report in background
    def send_report_async():
        try:
            from report_generator import tax_bill_report
            report_path = tax_bill_report(client_name, client_id, inputs_dict, results_dict)
            email_sender.send_report_email(email, client_name, 'tax-bill', report_path)
            client_db.log_action(client_id, 'report_sent', f'Tax Bill report emailed to {email}')
        except Exception as e:
            client_db.log_action(client_id, 'report_send_error', str(e))

    client_db.log_action(client_id, 'lead_captured', f'Tax Bill lead: {email}')
    report_id = client_db.log_report(client_id, 'tax-bill', json.dumps(inputs_dict))

    thread = threading.Thread(target=send_report_async)
    thread.start()

    return jsonify({
        'status': 'queued',
        'report_id': report_id,
        'client_id': client_id,
        'results': results_dict,
    })


# ─── Client Registration & Tracking Routes ───────────────────────────

@app.route('/register', methods=['POST'])
def register():
    """Register a new client. Accepts {first_name, email, phone?}."""
    data = request.json or request.form
    first_name = data.get('first_name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip() or None

    if not first_name or not email:
        return jsonify({'error': 'first_name and email are required'}), 400
    try:
        client = client_db.find_or_create_client(first_name, email, phone)
        is_new = client.get('created_at') == client.get('guide_sent_at') or not client.get('guide_sent_at')
        client_db.log_action(client['id'], 'registered', f'Email: {email}')
        
        # Generate and send personalized guide in background
        def send_guide_async():
            try:
                guide_pdf = report_generator.generate_personalized_guide(
                    client['first_name'], client['id']
                )
                email_sender.send_guide_email(
                    client['email'], client['first_name'], guide_pdf
                )
                # Mark guide as sent
                import sqlite3
                conn = sqlite3.connect(client_db.DB_PATH)
                conn.execute(
                    "UPDATE clients SET guide_sent_at = datetime('now') WHERE id = ?",
                    (client['id'],)
                )
                conn.commit()
                conn.close()
                client_db.log_action(client['id'], 'guide_sent', 'Personalized guide emailed')
            except Exception as e:
                client_db.log_action(client['id'], 'guide_send_error', str(e))
        
        thread = threading.Thread(target=send_guide_async)
        thread.start()
        
        return jsonify({
            'client_id': client['id'],
            'first_name': client['first_name'],
            'email': client['email'],
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 409


@app.route('/api/log-visit', methods=['POST'])
def api_log_visit():
    """Log a calculator visit action. Accepts {client_id, page, details?}."""
    data = request.json
    client_id = data.get('client_id', '').strip()
    page = data.get('page', '').strip()
    details = data.get('details', '').strip()

    if not client_id or not page:
        return jsonify({'error': 'client_id and page are required'}), 400

    client = client_db.get_client(client_id)
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    client_db.log_action(client_id, 'visit', f'{page}{": " + details if details else ""}')
    return jsonify({'status': 'logged'})


@app.route('/api/request-report', methods=['POST'])
def api_request_report():
    """Generate and email a personalized calculator report. Accepts {client_id?, calculator, inputs, results, email?}."""
    data = request.json
    client_id = data.get('client_id', '').strip() if data.get('client_id') else None
    calculator = data.get('calculator', '').strip()
    inputs = data.get('inputs', {})
    results = data.get('results', {})
    email = data.get('email', '').strip()
    
    if not calculator:
        return jsonify({'error': 'calculator is required'}), 400
    
    if not email:
        return jsonify({'error': 'email is required to send the report'}), 400
    
    # Find or create client by email if no client_id
    client_name = 'Friend'
    if client_id:
        client = client_db.get_client(client_id)
        if client:
            client_name = client['first_name']
        else:
            client_id = None
    
    if not client_id and email:
        client = client_db.find_or_create_client(email.split('@')[0].title(), email)
        client_id = client['id']
        client_name = client['first_name']
    
    # Generate and send report in background
    def send_report_async():
        try:
            # Generate the PDF report
            report_path = None
            if calculator == 'ss-calculator':
                report_path = report_generator.ss_report(client_name, client_id, inputs, results)
            elif calculator == 'torpedo-calculator':
                report_path = report_generator.torpedo_report(client_name, client_id, inputs, results)
            elif calculator == 'capital-gains':
                report_path = report_generator.capital_gains_report(client_name, client_id, inputs, results)
            
            if report_path:
                email_sender.send_report_email(email, client_name, calculator, report_path)
                client_db.log_action(client_id, 'report_sent', f'{calculator} report emailed to {email}')
            else:
                client_db.log_action(client_id, 'report_error', f'Unknown calculator: {calculator}')
        except Exception as e:
            client_db.log_action(client_id, 'report_send_error', str(e))
    
    # Log the report request
    inputs_json = json.dumps(inputs) if isinstance(inputs, dict) else str(inputs)
    report_id = client_db.log_report(client_id, calculator, inputs_json)
    client_db.log_action(client_id, 'report_requested', f'{calculator} (report #{report_id})')
    
    thread = threading.Thread(target=send_report_async)
    thread.start()
    
    return jsonify({'status': 'queued', 'report_id': report_id, 'client_id': client_id})


@app.route('/admin')
def admin():
    """Admin dashboard — renders client list."""
    clients = client_db.get_dashboard_data()
    return render_template('admin.html', clients=clients)


@app.route('/api/clients')
def api_clients():
    """Return JSON list of all clients with action history."""
    clients = client_db.get_all_clients()
    for c in clients:
        c['actions'] = client_db.get_client_actions(c['id'])
    return jsonify(clients)


@app.route('/api/client/<client_id>')
def api_client_detail(client_id):
    """Return single client detail with full action history."""
    client = client_db.get_client(client_id)
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    client['actions'] = client_db.get_client_actions(client_id)
    return jsonify(client)


# ─── Existing API Endpoints ──────────────────────────────────────────

@app.route('/api/ss-scenarios', methods=['POST'])
def api_ss_scenarios():
    """Calculate Social Security claiming scenarios."""
    data = request.json
    
    pia_monthly = float(data.get('pia_monthly', 2000))
    pia_annual = pia_monthly * 12
    birth_year = int(data.get('birth_year', 1960))
    filing = data.get('filing', 'MFJ')
    life_expectancy = int(data.get('life_expectancy', 85))
    spouse_pia_monthly = float(data.get('spouse_pia_monthly', 0))
    spouse_birth_year = int(data.get('spouse_birth_year', 1960)) if data.get('spouse_birth_year') else None
    
    spouse_pia_annual = spouse_pia_monthly * 12 if spouse_pia_monthly > 0 else 0
    
    results = calc_ss_claiming_comparison(
        pia_annual=pia_annual,
        birth_year=birth_year,
        filing=filing,
        spouse_pia=spouse_pia_annual,
        spouse_birth_year=spouse_birth_year,
        life_expectancy=life_expectancy,
    )
    
    fra = get_fra(birth_year)
    optimal = max(results[:-1] if results[-1].get('note') == 'survivor' else results, 
                  key=lambda x: x.get('lifetime_benefit', 0))
    
    return jsonify({
        'scenarios': results,
        'fra': fra,
        'fra_display': get_fra_display(birth_year),
        'optimal_age': optimal['claim_age'],
        'optimal_lifetime': optimal['lifetime_benefit'],
    })


@app.route('/api/torpedo', methods=['POST'])
def api_torpedo():
    """Calculate full tax torpedo scenario."""
    data = request.json
    
    ss_benefit_monthly = float(data.get('ss_benefit_monthly', 2500))
    ss_benefit_annual = ss_benefit_monthly * 12
    other_income = float(data.get('other_income', 40000))
    ira_balance = float(data.get('ira_balance', 300000))
    roth_conversion = float(data.get('roth_conversion', 0))
    birth_year = int(data.get('birth_year', 1960))
    claim_age = int(data.get('claim_age', 67))
    filing = data.get('filing', 'MFJ')
    tax_exempt_interest = float(data.get('tax_exempt_interest', 0))
    state_tax_rate = float(data.get('state_tax_rate', 0))
    
    result = calc_full_scenario(
        ss_benefit_annual=ss_benefit_annual,
        other_income=other_income,
        ira_balance=ira_balance,
        roth_conversion_amount=roth_conversion,
        birth_year=birth_year,
        claim_age=claim_age,
        filing=filing,
        tax_exempt_interest=tax_exempt_interest,
        state_tax_rate=state_tax_rate,
    )
    
    # Generate torpedo chart data
    income_range = list(range(0, 201000, 1000))
    chart_data = calc_torpedo_chart_data(
        ss_benefit_annual=ss_benefit_annual,
        other_income_range=income_range,
        filing=filing,
        tax_exempt_interest=tax_exempt_interest,
    )
    
    result['chart_data'] = chart_data
    
    return jsonify(result)


@app.route('/api/torpedo-chart', methods=['POST'])
def api_torpedo_chart():
    """Get torpedo chart data only (for dynamic updates)."""
    data = request.json
    
    ss_benefit_monthly = float(data.get('ss_benefit_monthly', 2500))
    ss_benefit_annual = ss_benefit_monthly * 12
    filing = data.get('filing', 'MFJ')
    tax_exempt_interest = float(data.get('tax_exempt_interest', 0))
    
    income_range = list(range(0, 201000, 1000))
    chart_data = calc_torpedo_chart_data(
        ss_benefit_annual=ss_benefit_annual,
        other_income_range=income_range,
        filing=filing,
        tax_exempt_interest=tax_exempt_interest,
    )
    
    return jsonify({'chart_data': chart_data})


@app.route('/api/capital-gains', methods=['POST'])
def api_capital_gains():
    """Calculate capital gains bump zone effect."""
    data = request.json
    
    ss_benefit_annual = float(data.get('ss_benefit_annual', 48000))
    other_income = float(data.get('other_income', 40000))
    capital_gain = float(data.get('capital_gain', 50000))
    filing = data.get('filing', 'MFJ')
    tax_exempt_interest = float(data.get('tax_exempt_interest', 0))
    
    result = calc_capital_gains_bump(
        ss_benefit_annual=ss_benefit_annual,
        other_income=other_income,
        capital_gain=capital_gain,
        filing=filing,
        tax_exempt_interest=tax_exempt_interest,
    )
    
    return jsonify(result)


@app.route('/api/cg-bump-chart', methods=['POST'])
def api_cg_bump_chart():
    """Get capital gains bump zone chart data."""
    data = request.json
    
    ss_benefit_annual = float(data.get('ss_benefit_annual', 48000))
    other_income = float(data.get('other_income', 40000))
    filing = data.get('filing', 'MFJ')
    tax_exempt_interest = float(data.get('tax_exempt_interest', 0))
    
    cg_range = list(range(0, 301000, 5000))
    chart_data = calc_cg_bump_chart_data(
        ss_benefit_annual=ss_benefit_annual,
        other_income=other_income,
        cg_range=cg_range,
        filing=filing,
        tax_exempt_interest=tax_exempt_interest,
    )
    
    return jsonify({'chart_data': chart_data})


@app.route('/api/widow-tax-hit', methods=['POST'])
def api_widow_tax_hit():
    """Calculate the widow/survivor tax hit."""
    data = request.json
    
    result = calc_widow_tax_hit(
        ss_benefit_husband=float(data.get('ss_benefit_husband', 30000)),
        ss_benefit_wife=float(data.get('ss_benefit_wife', 20000)),
        other_income_joint=float(data.get('other_income_joint', 30000)),
        ira_balance=float(data.get('ira_balance', 300000)),
        birth_year_husband=int(data.get('birth_year_husband', 1955)),
        birth_year_wife=int(data.get('birth_year_wife', 1957)),
        filing=data.get('filing', 'MFJ'),
        tax_exempt_interest=float(data.get('tax_exempt_interest', 0)),
    )
    
    # Reshape flat result into nested objects the frontend expects:
    reshaped = {
        'joint': {
            'net_cash_flow': result.get('net_joint', 0),
            'ss_benefits': result.get('ss_joint', 0),
            'ss_pct_taxable': result.get('ss_pct_joint', 0),
            'agi': result.get('agi_joint', 0),
            'total_income': result.get('total_income_joint', 0),
            'federal_tax': result.get('fed_tax_joint', 0),
            'effective_rate': result.get('effective_rate_joint', 0),
        },
        'survivor': {
            'net_cash_flow': result.get('net_survivor', 0),
            'ss_benefits': result.get('survivor_ss', 0),
            'ss_pct_taxable': result.get('ss_pct_survivor', 0),
            'agi': result.get('agi_survivor', 0),
            'total_income': result.get('total_income_survivor', 0),
            'federal_tax': result.get('fed_tax_survivor', 0),
            'effective_rate': result.get('effective_rate_survivor', 0),
        },
        # Pass through top-level summary fields
        'income_drop': result.get('income_drop', 0),
        'lost_ss': result.get('lost_ss', 0),
        'tax_increase': result.get('tax_increase', 0),
        'deduction_lost': result.get('deduction_lost', 0),
        'pct_of_original': result.get('pct_of_original', 0),
    }
    
    # If Roth conversion data exists, add it
    if result.get('fed_tax_survivor_roth') is not None:
        roth_tax_savings = result.get('fed_tax_survivor', 0) - result.get('fed_tax_survivor_roth', 0)
        reshaped['with_roth_conversion'] = {
            'net_cash_flow': result.get('net_survivor', 0) + roth_tax_savings,
            'ss_benefits': result.get('survivor_ss', 0),
            'ss_pct_taxable': result.get('ss_pct_survivor', 0),  # simplified
            'agi': result.get('agi_survivor', 0),
            'total_income': result.get('total_income_survivor', 0) - result.get('deduction_lost', 0) + roth_tax_savings,
            'federal_tax': result.get('fed_tax_survivor_roth', 0),
            'effective_rate': result.get('effective_rate_survivor', 0),  # simplified
        }
    
    return jsonify(reshaped)


@app.route('/api/qcd-benefit', methods=['POST'])
def api_qcd_benefit():
    """Calculate QCD (Qualified Charitable Distribution) benefit."""
    data = request.json
    
    result = calc_qcd_benefit(
        ss_benefit_annual=float(data.get('ss_benefit_annual', 48000)),
        other_income=float(data.get('other_income', 40000)),
        rmd_amount=float(data.get('rmd_amount', 20000)),
        qcd_amount=float(data.get('qcd_amount', 10000)),
        filing=data.get('filing', 'MFJ'),
        tax_exempt_interest=float(data.get('tax_exempt_interest', 0)),
    )
    
    return jsonify(result)


@app.route('/api/irmaa', methods=['POST'])
def api_irmaa():
    """Calculate IRMAA surcharge and show bracket position."""
    data = request.json
    
    # Income inputs
    ss_benefit = float(data.get('ss_benefit_annual', 48000))
    other_income = float(data.get('other_income', 40000))
    rmd_amount = float(data.get('rmd_amount', 20000))
    tax_exempt_interest = float(data.get('tax_exempt_interest', 0))
    filing = data.get('filing', 'MFJ')
    
    # Optional Roth conversion
    roth_conversion = float(data.get('roth_conversion', 0))
    
    # Current MAGI (all income + taxable SS + tax-exempt interest)
    ss_taxable, ss_pct = calc_ss_taxable(
        ss_benefit,
        calc_provisional_income(other_income + rmd_amount, ss_benefit, tax_exempt_interest, filing),
        filing
    )
    current_magi = other_income + rmd_amount + ss_taxable + tax_exempt_interest
    
    # With Roth conversion: RMD reduced by conversion amount for future years,
    # but this year conversion ADDS to MAGI
    # Show: current MAGI vs what happens if you convert X (one-time spike)
    # vs ongoing lower MAGI after conversion reduces future RMDs
    magi_with_roth = current_magi + roth_conversion  # conversion adds to MAGI this year
    
    # Future year: lower RMDs from smaller IRA balance
    ira_balance = float(data.get('ira_balance', 300000))
    future_ira = ira_balance - roth_conversion
    future_rmd = future_ira / 26.5 if future_ira > 0 else 0  # age 73 divisor
    future_ss_taxable, future_ss_pct = calc_ss_taxable(
        ss_benefit,
        calc_provisional_income(other_income + future_rmd, ss_benefit, tax_exempt_interest, filing),
        filing
    )
    future_magi = other_income + future_rmd + future_ss_taxable + tax_exempt_interest
    
    # IRMAA calculations
    current_irmaa = calc_irmaa(current_magi, filing)
    current_tier, current_surcharge = calc_irmaa_tier(current_magi, filing)
    future_irmaa = calc_irmaa(future_magi, filing)
    future_tier, future_surcharge = calc_irmaa_tier(future_magi, filing)
    spike_irmaa = calc_irmaa(magi_with_roth, filing)
    spike_tier, spike_surcharge = calc_irmaa_tier(magi_with_roth, filing)
    
    # Federal tax on current scenario
    _, fed_tax_current = calc_marginal_rate(current_magi, filing)
    _, fed_tax_future = calc_marginal_rate(future_magi, filing)
    _, fed_tax_spike = calc_marginal_rate(magi_with_roth, filing)
    
    # IRMAA bracket boundaries for visualization
    brackets = IRMAA_MFJ if filing == 'MFJ' else IRMAA_SINGLE
    
    result = {
        'filing': filing,
        
        # Current situation
        'current_magi': round(current_magi, 2),
        'current_ss_taxable': round(ss_taxable, 2),
        'current_ss_pct': round(ss_pct, 1),
        'current_irmaa_annual': round(current_irmaa, 2),
        'current_irmaa_monthly': round(current_surcharge, 2),
        'current_tier': current_tier,
        'current_fed_tax': round(fed_tax_current, 2),
        'current_total_cost': round(fed_tax_current + current_irmaa, 2),
        
        # With Roth conversion (this year - spike)
        'spike_magi': round(magi_with_roth, 2),
        'spike_irmaa_annual': round(spike_irmaa, 2),
        'spike_irmaa_monthly': round(spike_surcharge, 2),
        'spike_tier': spike_tier,
        'spike_fed_tax': round(fed_tax_spike, 2),
        'spike_total_cost': round(fed_tax_spike + spike_irmaa, 2),
        
        # After Roth conversion (future years - ongoing)
        'future_magi': round(future_magi, 2),
        'future_ss_taxable': round(future_ss_taxable, 2),
        'future_ss_pct': round(future_ss_pct, 1),
        'future_irmaa_annual': round(future_irmaa, 2),
        'future_irmaa_monthly': round(future_surcharge, 2),
        'future_tier': future_tier,
        'future_fed_tax': round(fed_tax_future, 2),
        'future_total_cost': round(fed_tax_future + future_irmaa, 2),
        
        # Savings
        'annual_irmaa_savings': round(current_irmaa - future_irmaa, 2),
        'annual_tax_savings': round(fed_tax_current - fed_tax_future, 2),
        'total_annual_savings': round((current_irmaa - future_irmaa) + (fed_tax_current - fed_tax_future), 2),
        'five_year_savings': round(((current_irmaa - future_irmaa) + (fed_tax_current - fed_tax_future)) * 5, 2),
        
        # Bracket table for visualization
        'brackets': [{'threshold': b[0], 'surcharge': b[1]} for b in brackets],
    }
    
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)