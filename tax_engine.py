"""
Summit Tax Services — Retirement Tax Engine
Calculates Social Security taxation, IRMAA surcharges, tax torpedo effects,
Roth conversion scenarios, and claiming strategy comparisons.
"""

# ============================================================
# 2024 Federal Tax Brackets (MFJ)
# ============================================================
FED_BRACKETS_MFJ = [
    (23200, 0.10),
    (94300, 0.12),
    (201050, 0.22),
    (383900, 0.24),
    (487450, 0.32),
    (731200, 0.35),
    (float('inf'), 0.37),
]

FED_BRACKETS_SINGLE = [
    (11600, 0.10),
    (47150, 0.12),
    (100525, 0.22),
    (191950, 0.24),
    (243725, 0.32),
    (609350, 0.35),
    (float('inf'), 0.37),
]

STD_DEDUCTION_MFJ = 29200
STD_DEDUCTION_SINGLE = 14600

# Social Security taxation thresholds
SS_THRESHOLDS_MFJ = (32000, 44000)  # (50% threshold, 85% threshold)
SS_THRESHOLDS_SINGLE = (25000, 34000)

# IRMAA brackets (2024, based on 2022 MAGI)
IRMAA_MFJ = [
    (212000, 0),       # standard premium
    (266000, 74.00),   # IRMAA tier 1
    (334000, 185.00),   # IRMAA tier 2
    (750000, 370.00),   # IRMAA tier 3
    (float('inf'), 444.00),  # IRMAA tier 4
]

IRMAA_SINGLE = [
    (106000, 0),
    (133000, 74.00),
    (167000, 185.00),
    (400000, 370.00),
    (float('inf'), 444.00),
]

# Capital gains brackets (2024, MFJ)
CG_BRACKETS_MFJ = [
    (94050, 0.00),   # 0% rate
    (583750, 0.15),  # 15% rate
    (float('inf'), 0.20),  # 20% rate
]

CG_BRACKETS_SINGLE = [
    (47025, 0.00),
    (518900, 0.15),
    (float('inf'), 0.20),
]

# Full Retirement Age by birth year
FRA_TABLE = {
    1943: 66, 1944: 66, 1945: 66, 1946: 66,
    1947: 66, 1948: 66, 1949: 66, 1950: 66,
    1951: 66, 1952: 66, 1953: 66, 1954: 66,
    1955: 66 + 2/12, 1956: 66 + 4/12, 1957: 66 + 6/12,
    1958: 66 + 8/12, 1959: 66 + 10/12,
}
# 1960+ = 67


def get_fra(birth_year):
    """Get Full Retirement Age in years (decimal)."""
    if birth_year <= 1937:
        return 65
    elif birth_year <= 1942:
        return 65 + (birth_year - 1937) * (2/12)
    elif birth_year <= 1954:
        return 66
    elif birth_year <= 1959:
        return FRA_TABLE.get(birth_year, 66)
    else:
        return 67


def get_fra_display(birth_year):
    """Get FRA as human-readable string."""
    fra = get_fra(birth_year)
    years = int(fra)
    months = round((fra - years) * 12)
    if months == 0:
        return f"{years}"
    return f"{years} and {months} month{'s' if months != 1 else ''}"


def calc_ss_benefit_at_age(pia, claim_age, birth_year):
    """
    Calculate Social Security benefit at a given claim age.
    PIA = Primary Insurance Amount (benefit at FRA).
    Returns annual benefit amount.
    """
    fra = get_fra(birth_year)
    
    if claim_age >= 70:
        # Maximum: FRA benefit + delayed retirement credits
        drc_months = (70 - fra) * 12
        return pia * (1 + drc_months * (2/3) / 100)
    elif claim_age >= fra:
        # Delayed retirement credits (2/3 of 1% per month)
        drc_months = (claim_age - fra) * 12
        return pia * (1 + drc_months * (2/3) / 100)
    elif claim_age >= 62:
        # Early filing reduction
        months_early = int((fra - claim_age) * 12)
        if months_early <= 36:
            reduction = months_early * (5/9) / 100
        else:
            reduction = (36 * 5/9 + (months_early - 36) * 5/12) / 100
        return pia * (1 - reduction)
    else:
        return 0


def calc_provisional_income(agi, ss_benefit, tax_exempt_interest=0, filing='MFJ'):
    """
    Calculate provisional income for SS taxation.
    Provisional Income = AGI + 50% of SS + Tax-Exempt Interest
    """
    return agi + (ss_benefit * 0.5) + tax_exempt_interest


def calc_ss_taxable(ss_benefit, provisional_income, filing='MFJ'):
    """
    Calculate how much of Social Security is taxable.
    Returns (taxable_amount, percentage).
    """
    if filing == 'MFJ':
        thresh_50, thresh_85 = SS_THRESHOLDS_MFJ
    else:
        thresh_50, thresh_85 = SS_THRESHOLDS_SINGLE
    
    if provisional_income <= thresh_50:
        return 0, 0.0
    elif provisional_income <= thresh_85:
        # 50% threshold bracket
        taxable = min(
            ss_benefit * 0.50,
            (provisional_income - thresh_50) * 0.50
        )
        return taxable, (taxable / ss_benefit * 100) if ss_benefit > 0 else 0
    else:
        # 85% threshold bracket
        taxable_50 = min(
            ss_benefit * 0.50,
            (thresh_85 - thresh_50) * 0.50
        )
        taxable_85 = min(
            ss_benefit * 0.85 - taxable_50,
            (provisional_income - thresh_85) * 0.85
        )
        taxable = min(ss_benefit * 0.85, taxable_50 + taxable_85)
        return taxable, (taxable / ss_benefit * 100) if ss_benefit > 0 else 0


def calc_marginal_rate(income, filing='MFJ'):
    """Calculate marginal federal tax rate for a given income level."""
    brackets = FED_BRACKETS_MFJ if filing == 'MFJ' else FED_BRACKETS_SINGLE
    deduction = STD_DEDUCTION_MFJ if filing == 'MFJ' else STD_DEDUCTION_SINGLE
    
    taxable = max(0, income - deduction)
    
    tax = 0
    prev_bracket = 0
    marginal_rate = 0
    
    for bracket_top, rate in brackets:
        if taxable <= prev_bracket:
            break
        bracket_income = min(taxable, bracket_top) - prev_bracket
        tax += bracket_income * rate
        marginal_rate = rate
        prev_bracket = bracket_top
    
    return marginal_rate, tax


def calc_effective_marginal_rate(base_income, ss_benefit, filing='MFJ'):
    """
    Calculate the EFFECTIVE marginal rate including the SS tax torpedo.
    This is the rate that applies to each additional dollar of income,
    including the cascading effect on SS taxation.
    
    Returns (effective_rate, base_rate, torpedo_surcharge)
    """
    brackets = FED_BRACKETS_MFJ if filing == 'MFJ' else FED_BRACKETS_SINGLE
    thresholds = SS_THRESHOLDS_MFJ if filing == 'MFJ' else SS_THRESHOLDS_SINGLE
    
    # Calculate base marginal rate
    base_rate, _ = calc_marginal_rate(base_income, filing)
    
    # Calculate SS taxation at current income
    pi_current = calc_provisional_income(base_income, ss_benefit, filing=filing)
    ss_taxable_current, _ = calc_ss_taxable(ss_benefit, pi_current, filing)
    
    # Calculate SS taxation with $1 more income
    pi_next = calc_provisional_income(base_income + 1, ss_benefit, filing=filing)
    ss_taxable_next, _ = calc_ss_taxable(ss_benefit, pi_next, filing)
    
    # Additional SS taxable per additional dollar
    additional_ss_taxable = ss_taxable_next - ss_taxable_current
    
    # Effective rate = base rate + (base_rate * additional_ss_taxable)
    # Because each additional dollar of income taxes more SS, which is also taxed at base_rate
    torpedo_surcharge = base_rate * additional_ss_taxable
    effective_rate = base_rate + torpedo_surcharge
    
    return effective_rate, base_rate, torpedo_surcharge


def calc_irmaa(magi, filing='MFJ'):
    """Calculate IRMAA surcharge based on MAGI."""
    brackets = IRMAA_MFJ if filing == 'MFJ' else IRMAA_SINGLE
    
    for threshold, surcharge in brackets:
        if magi <= threshold:
            return surcharge * 12  # Annual amount (surcharge is monthly)
    
    return brackets[-1][1] * 12


def calc_irmaa_tier(magi, filing='MFJ'):
    """Return the IRMAA tier number and monthly surcharge."""
    brackets = IRMAA_MFJ if filing == 'MFJ' else IRMAA_SINGLE
    
    for i, (threshold, surcharge) in enumerate(brackets):
        if magi <= threshold:
            return i, surcharge
    return len(brackets) - 1, brackets[-1][1]


def calc_full_scenario(
    ss_benefit_annual,
    other_income,
    ira_balance=0,
    roth_conversion_amount=0,
    birth_year=1960,
    claim_age=67,
    filing='MFJ',
    tax_exempt_interest=0,
    state_tax_rate=0.0,
):
    """
    Calculate a complete retirement tax scenario.
    
    Returns dict with all calculated values.
    """
    fra = get_fra(birth_year)
    ss_at_claim = calc_ss_benefit_at_age(ss_benefit_annual, claim_age, birth_year)
    
    # Current scenario (no Roth conversion)
    current_agi = other_income + roth_conversion_amount  # Roth conversion adds to AGI
    if roth_conversion_amount == 0:
        current_agi = other_income
    
    # RMD estimate (simplified - uses uniform lifetime table factor)
    rmd_age = 73 if birth_year <= 1959 else 75
    if birth_year <= 1950:
        rmd_age = 72
    rmd_divisor = 26.5 if rmd_age == 73 else 24.7 if rmd_age == 75 else 27.4  # simplified
    rmd_amount = ira_balance / rmd_divisor if ira_balance > 0 else 0
    
    # === WITHOUT Roth conversion ===
    agi_no_roth = other_income + rmd_amount
    pi_no_roth = calc_provisional_income(agi_no_roth, ss_at_claim, tax_exempt_interest, filing)
    ss_taxable_no_roth, ss_pct_no_roth = calc_ss_taxable(ss_at_claim, pi_no_roth, filing)
    total_income_no_roth = agi_no_roth + ss_taxable_no_roth
    marginal_rate_no_roth, fed_tax_no_roth = calc_marginal_rate(total_income_no_roth, filing)
    effective_rate_no_roth, base_rate_no_roth, torpedo_no_roth = calc_effective_marginal_rate(
        agi_no_roth, ss_at_claim, filing
    )
    irmaa_no_roth = calc_irmaa(agi_no_roth, filing)
    
    # === WITH Roth conversion (no RMDs on Roth money) ===
    # After conversion, IRA balance is reduced, so RMDs are lower
    ira_after_roth = max(0, ira_balance - roth_conversion_amount)
    rmd_after_roth = ira_after_roth / rmd_divisor if ira_after_roth > 0 else 0
    
    # The year of conversion: pay tax on conversion amount
    agi_conversion_year = other_income + rmd_amount + roth_conversion_amount
    pi_conversion = calc_provisional_income(agi_conversion_year, ss_at_claim, tax_exempt_interest, filing)
    ss_taxable_conversion, ss_pct_conversion = calc_ss_taxable(ss_at_claim, pi_conversion, filing)
    
    # Ongoing years after conversion (lower RMDs)
    agi_with_roth = other_income + rmd_after_roth
    pi_with_roth = calc_provisional_income(agi_with_roth, ss_at_claim, tax_exempt_interest, filing)
    ss_taxable_with_roth, ss_pct_with_roth = calc_ss_taxable(ss_at_claim, pi_with_roth, filing)
    total_income_with_roth = agi_with_roth + ss_taxable_with_roth
    marginal_rate_with_roth, fed_tax_with_roth = calc_marginal_rate(total_income_with_roth, filing)
    effective_rate_with_roth, base_rate_with_roth, torpedo_with_roth = calc_effective_marginal_rate(
        agi_with_roth, ss_at_claim, filing
    )
    irmaa_with_roth = calc_irmaa(agi_with_roth, filing)
    
    # Tax savings from Roth conversion (annual, ongoing)
    annual_tax_savings = fed_tax_no_roth - fed_tax_with_roth
    ss_tax_savings = ss_taxable_no_roth - ss_taxable_with_roth
    irmaa_savings = irmaa_no_roth - irmaa_with_roth
    total_annual_savings = annual_tax_savings + ss_tax_savings * marginal_rate_with_roth + irmaa_savings
    
    return {
        # Social Security
        'fra': fra,
        'fra_display': get_fra_display(birth_year),
        'ss_benefit_at_fra': ss_benefit_annual,
        'ss_benefit_at_claim': round(ss_at_claim, 2),
        'claim_age': claim_age,
        'birth_year': birth_year,
        
        # RMD
        'rmd_age': rmd_age,
        'rmd_amount': round(rmd_amount, 2),
        'ira_balance': ira_balance,
        
        # Without Roth conversion
        'agi_no_roth': round(agi_no_roth, 2),
        'pi_no_roth': round(pi_no_roth, 2),
        'ss_taxable_no_roth': round(ss_taxable_no_roth, 2),
        'ss_pct_no_roth': round(ss_pct_no_roth, 1),
        'fed_tax_no_roth': round(fed_tax_no_roth, 2),
        'marginal_rate_no_roth': round(marginal_rate_no_roth * 100, 1),
        'effective_rate_no_roth': round(effective_rate_no_roth * 100, 1),
        'base_rate_no_roth': round(base_rate_no_roth * 100, 1),
        'torpedo_no_roth': round(torpedo_no_roth * 100, 1),
        'irmaa_no_roth': round(irmaa_no_roth, 2),
        'total_income_no_roth': round(total_income_no_roth, 2),
        
        # With Roth conversion
        'roth_conversion_amount': roth_conversion_amount,
        'ira_after_roth': round(ira_after_roth, 2),
        'rmd_after_roth': round(rmd_after_roth, 2),
        'agi_with_roth': round(agi_with_roth, 2),
        'pi_with_roth': round(pi_with_roth, 2),
        'ss_taxable_with_roth': round(ss_taxable_with_roth, 2),
        'ss_pct_with_roth': round(ss_pct_with_roth, 1),
        'fed_tax_with_roth': round(fed_tax_with_roth, 2),
        'marginal_rate_with_roth': round(marginal_rate_with_roth * 100, 1),
        'effective_rate_with_roth': round(effective_rate_with_roth * 100, 1),
        'torpedo_with_roth': round(torpedo_with_roth * 100, 1),
        'irmaa_with_roth': round(irmaa_with_roth, 2),
        'total_income_with_roth': round(total_income_with_roth, 2),
        
        # Conversion year
        'agi_conversion_year': round(agi_conversion_year, 2),
        'ss_taxable_conversion': round(ss_taxable_conversion, 2),
        'ss_pct_conversion': round(ss_pct_conversion, 1),
        
        # Savings
        'annual_tax_savings': round(annual_tax_savings, 2),
        'ss_tax_savings': round(ss_tax_savings, 2),
        'irmaa_savings': round(irmaa_savings, 2),
        'total_annual_savings': round(total_annual_savings, 2),
    }


def calc_ss_claiming_comparison(
    pia_annual,
    birth_year,
    filing='MFJ',
    spouse_pia=0,
    spouse_birth_year=None,
    life_expectancy=85,
):
    """
    Compare Social Security claiming strategies.
    Returns a list of scenarios showing lifetime benefits at each claim age.
    """
    results = []
    
    for age in range(62, 71):
        annual_benefit = calc_ss_benefit_at_age(pia_annual, age, birth_year)
        years_collecting = max(0, life_expectancy - age)
        lifetime_benefit = annual_benefit * years_collecting
        
        # Monthly benefit for display
        monthly_benefit = annual_benefit / 12
        
        results.append({
            'claim_age': age,
            'annual_benefit': round(annual_benefit, 2),
            'monthly_benefit': round(monthly_benefit, 2),
            'years_collecting': years_collecting,
            'lifetime_benefit': round(lifetime_benefit, 2),
            'reduction_or_increase': round((annual_benefit / pia_annual - 1) * 100, 1) if pia_annual > 0 else 0,
        })
    
    # Add survivor scenario if married
    if spouse_pia > 0 and spouse_birth_year:
        spouse_fra = get_fra(spouse_birth_year)
        # Survivor gets the higher of their own or their spouse's benefit
        # This is simplified - just shows the drop
        higher_benefit = max(pia_annual, spouse_pia)
        lower_benefit = min(pia_annual, spouse_pia)
        survivor_income = higher_benefit  # Only one check
        couple_income = pia_annual + spouse_pia
        income_drop = couple_income - survivor_income
        
        results.append({
            'note': 'survivor',
            'couple_income': round(couple_income, 2),
            'survivor_income': round(survivor_income, 2),
            'income_drop': round(income_drop, 2),
            'income_drop_pct': round(income_drop / couple_income * 100, 1) if couple_income > 0 else 0,
        })
    
    return results


def calc_torpedo_chart_data(
    ss_benefit_annual,
    other_income_range,
    filing='MFJ',
    tax_exempt_interest=0,
):
    """
    Generate data for the tax torpedo chart.
    Shows effective marginal rate as income increases, revealing the torpedo zones.
    
    Returns list of (income, effective_rate, base_rate, ss_taxable_pct) tuples.
    """
    data = []
    
    for other_income in other_income_range:
        pi = calc_provisional_income(other_income, ss_benefit_annual, tax_exempt_interest, filing)
        ss_taxable, ss_pct = calc_ss_taxable(ss_benefit_annual, pi, filing)
        effective_rate, base_rate, torpedo = calc_effective_marginal_rate(
            other_income, ss_benefit_annual, filing
        )
        
        data.append({
            'income': other_income,
            'effective_rate': round(effective_rate * 100, 1),
            'base_rate': round(base_rate * 100, 1),
            'torpedo': round(torpedo * 100, 1),
            'ss_taxable_pct': round(ss_pct, 1),
            'ss_taxable_amount': round(ss_taxable, 2),
            'provisional_income': round(pi, 2),
        })
    
    return data


# ============================================================
# Capital Gains Bump Zone Calculator
# (from Bruce Larsen Ch 3)
# Shows how capital gains cascade into higher SS taxation
# ============================================================

def calc_capital_gains_bump(
    ss_benefit_annual,
    other_income,
    capital_gain,
    filing='MFJ',
    tax_exempt_interest=0,
):
    """
    Calculate the 'capital gains bump zone' effect.
    
    When a retiree takes a capital gain, it increases AGI, which increases
    the percentage of SS that's taxable. This 'double tax' effect can make
    the effective rate on the gain much higher than the nominal capital gains rate.
    
    Based on Bruce Larsen's analysis in Chapter 3 of his book.
    
    Returns dict with before/after comparison.
    """
    # --- BEFORE the capital gain ---
    agi_before = other_income
    pi_before = calc_provisional_income(agi_before, ss_benefit_annual, tax_exempt_interest, filing)
    ss_taxable_before, ss_pct_before = calc_ss_taxable(ss_benefit_annual, pi_before, filing)
    
    total_income_before = agi_before + ss_taxable_before
    deductions = STD_DEDUCTION_MFJ if filing == 'MFJ' else STD_DEDUCTION_SINGLE
    taxable_before = max(0, total_income_before - deductions)
    
    # Calculate tax before (ordinary income only, no CG)
    base_rate_before, fed_tax_before = calc_marginal_rate(total_income_before, filing)
    effective_rate_before = (fed_tax_before / other_income * 100) if other_income > 0 else 0
    
    # --- AFTER the capital gain ---
    agi_after = other_income + capital_gain
    pi_after = calc_provisional_income(agi_after, ss_benefit_annual, tax_exempt_interest, filing)
    ss_taxable_after, ss_pct_after = calc_ss_taxable(ss_benefit_annual, pi_after, filing)
    
    total_income_after = agi_after + ss_taxable_after
    taxable_after = max(0, total_income_after - deductions)
    
    # Calculate total tax after (with CG)
    # Need to separate ordinary income and CG for proper tax calculation
    # CG rates apply to the gain, but AGI determines which CG bracket
    cg_brackets = CG_BRACKETS_MFJ if filing == 'MFJ' else CG_BRACKETS_SINGLE
    
    # Ordinary income portion
    ordinary_income = other_income + ss_taxable_after
    cg_amount = capital_gain
    
    # Tax on ordinary income
    ord_tax = 0
    prev_bracket = 0
    remaining_ordinary = ordinary_income
    brackets = FED_BRACKETS_MFJ if filing == 'MFJ' else FED_BRACKETS_SINGLE
    
    for bracket_top, rate in brackets:
        if taxable_after <= 0:
            break
        bracket_width = bracket_top - prev_bracket
        if remaining_ordinary <= 0:
            break
        taxed_in_bracket = min(remaining_ordinary, bracket_width)
        # Check if CG fills this bracket first
        ordinary_in_bracket = max(0, min(taxed_in_bracket, taxable_after - cg_amount))
        cg_in_bracket = taxed_in_bracket - ordinary_in_bracket
        # Determine CG rate based on total income
        income_threshold = prev_bracket + ordinary_in_bracket
        if income_threshold <= cg_brackets[0][0]:
            cg_rate = 0.0
        elif income_threshold <= cg_brackets[1][0]:
            cg_rate = 0.15
        else:
            cg_rate = 0.20
        
        ord_tax += ordinary_in_bracket * rate
        ord_tax += cg_in_bracket * cg_rate
        remaining_ordinary -= taxed_in_bracket
        prev_bracket = bracket_top
    
    # Simplified: calculate total tax with and without the gain
    # Total tax after gain
    _, total_tax_after = calc_marginal_rate(total_income_after, filing)
    
    # Additional SS that became taxable due to the gain
    additional_ss_taxable = ss_taxable_after - ss_taxable_before
    additional_agi = capital_gain + additional_ss_taxable
    
    # Effective rate on the capital gain itself
    tax_increase = total_tax_after - fed_tax_before
    if capital_gain > 0:
        effective_cg_rate = (tax_increase / capital_gain) * 100
    else:
        effective_cg_rate = 0
    
    # Nominal CG rate based on taxable income
    if taxable_after <= 0:
        nominal_cg_rate = 0
    elif taxable_after <= cg_brackets[0][0]:
        nominal_cg_rate = 0
    elif taxable_after <= cg_brackets[1][0]:
        nominal_cg_rate = 15
    else:
        nominal_cg_rate = 20
    
    # Net cash flow comparison
    net_cash_flow_before = other_income + ss_benefit_annual - fed_tax_before
    net_cash_flow_after = other_income + capital_gain + ss_benefit_annual - total_tax_after
    
    return {
        # Before
        'agi_before': round(agi_before, 2),
        'pi_before': round(pi_before, 2),
        'ss_taxable_before': round(ss_taxable_before, 2),
        'ss_pct_before': round(ss_pct_before, 1),
        'total_income_before': round(total_income_before, 2),
        'fed_tax_before': round(fed_tax_before, 2),
        'effective_rate_before': round(effective_rate_before, 1),
        
        # After
        'agi_after': round(agi_after, 2),
        'pi_after': round(pi_after, 2),
        'ss_taxable_after': round(ss_taxable_after, 2),
        'ss_pct_after': round(ss_pct_after, 1),
        'total_income_after': round(total_income_after, 2),
        'fed_tax_after': round(total_tax_after, 2),
        
        # The bump zone effect
        'capital_gain': round(capital_gain, 2),
        'additional_ss_taxable': round(additional_ss_taxable, 2),
        'additional_agi': round(additional_agi, 2),
        'tax_increase': round(tax_increase, 2),
        'effective_cg_rate': round(effective_cg_rate, 1),
        'nominal_cg_rate': round(nominal_cg_rate, 1),
        'bump_zone_penalty': round(effective_cg_rate - nominal_cg_rate, 1),
        
        # Net cash flow
        'net_cash_flow_before': round(net_cash_flow_before, 2),
        'net_cash_flow_after': round(net_cash_flow_after, 2),
        'net_gain_after_tax': round(net_cash_flow_after - net_cash_flow_before, 2),
    }


def calc_cg_bump_chart_data(
    ss_benefit_annual,
    other_income,
    cg_range,
    filing='MFJ',
    tax_exempt_interest=0,
):
    """
    Generate chart data showing effective CG rate as capital gain increases.
    Reveals the 'bump zones' where effective rate spikes due to SS cascading.
    """
    data = []
    
    for cg_amount in cg_range:
        result = calc_capital_gains_bump(
            ss_benefit_annual, other_income, cg_amount, filing, tax_exempt_interest
        )
        data.append({
            'capital_gain': round(cg_amount, 0),
            'effective_rate': result['effective_cg_rate'],
            'nominal_rate': result['nominal_cg_rate'],
            'bump_penalty': result['bump_zone_penalty'],
            'additional_ss_taxable': result['additional_ss_taxable'],
            'tax_increase': result['tax_increase'],
        })
    
    return data


# ============================================================
# Widow Tax Hit Calculator
# (from Bruce Larsen Ch 10)
# Shows the tax increase when a spouse dies
# ============================================================

def calc_widow_tax_hit(
    ss_benefit_husband,
    ss_benefit_wife,
    other_income_joint,
    ira_balance=0,
    birth_year_husband=1955,
    birth_year_wife=1957,
    filing='MFJ',
    tax_exempt_interest=0,
):
    """
    Calculate the tax impact of losing a spouse.
    
    When one spouse passes:
    1. Standard deduction is cut in half
    2. SS thresholds drop to single ($25K/$34K vs $32K/$44K)
    3. Tax brackets compress to single
    4. One SS benefit is lost (survivor keeps higher)
    5. IRA RMDs may increase if inherited
    
    Returns comparison of joint vs survivor scenarios.
    """
    # === JOINT FILING (both alive) ===
    ss_joint = ss_benefit_husband + ss_benefit_wife
    agi_joint = other_income_joint
    pi_joint = calc_provisional_income(agi_joint, ss_joint, tax_exempt_interest, 'MFJ')
    ss_taxable_joint, ss_pct_joint = calc_ss_taxable(ss_joint, pi_joint, 'MFJ')
    
    total_income_joint = agi_joint + ss_taxable_joint
    _, fed_tax_joint = calc_marginal_rate(total_income_joint, 'MFJ')
    effective_rate_joint = (fed_tax_joint / (ss_joint + other_income_joint) * 100) if (ss_joint + other_income_joint) > 0 else 0
    
    # RMD estimate
    rmd_age = 73
    rmd_divisor = 26.5
    rmd_joint = ira_balance / rmd_divisor if ira_balance > 0 else 0
    
    # Cash flow
    cash_flow_joint = ss_joint + other_income_joint
    net_joint = cash_flow_joint - fed_tax_joint
    
    # === SURVIVOR FILING (one spouse passes) ===
    # Survivor keeps the higher SS benefit
    survivor_ss = max(ss_benefit_husband, ss_benefit_wife)
    lost_ss = min(ss_benefit_husband, ss_benefit_wife)
    
    # RMD may stay the same (or increase if inherited)
    # Assuming IRA stays with survivor
    agi_survivor = other_income_joint  # Same other income (pensions, etc.)
    pi_survivor = calc_provisional_income(agi_survivor, survivor_ss, tax_exempt_interest, 'Single')
    ss_taxable_survivor, ss_pct_survivor = calc_ss_taxable(survivor_ss, pi_survivor, 'Single')
    
    total_income_survivor = agi_survivor + ss_taxable_survivor
    _, fed_tax_survivor = calc_marginal_rate(total_income_survivor, 'Single')
    effective_rate_survivor = (fed_tax_survivor / (survivor_ss + other_income_joint) * 100) if (survivor_ss + other_income_joint) > 0 else 0
    
    cash_flow_survivor = survivor_ss + other_income_joint
    net_survivor = cash_flow_survivor - fed_tax_survivor
    
    # === THE WIDOW TAX HIT ===
    tax_increase = fed_tax_survivor - fed_tax_joint
    income_drop = cash_flow_joint - cash_flow_survivor
    net_income_drop = net_joint - net_survivor
    pct_of_original = (net_survivor / net_joint * 100) if net_joint > 0 else 0
    
    # === WITH ROTH CONVERSION MITIGATION ===
    # Show how a Roth conversion before death reduces the hit
    # (reduces RMDs, which reduces AGI and SS taxation for survivor)
    rmd_with_roth = max(0, ira_balance - 100000) / rmd_divisor if ira_balance > 100000 else 0
    agi_survivor_roth = other_income_joint + rmd_with_roth
    pi_survivor_roth = calc_provisional_income(agi_survivor_roth, survivor_ss, tax_exempt_interest, 'Single')
    ss_taxable_survivor_roth, _ = calc_ss_taxable(survivor_ss, pi_survivor_roth, 'Single')
    total_income_survivor_roth = agi_survivor_roth + ss_taxable_survivor_roth
    _, fed_tax_survivor_roth = calc_marginal_rate(total_income_survivor_roth, 'Single')
    tax_increase_with_roth = fed_tax_survivor_roth - fed_tax_joint
    roth_savings = fed_tax_survivor - fed_tax_survivor_roth
    
    return {
        # Joint (both alive)
        'ss_joint': round(ss_joint, 2),
        'ss_taxable_joint': round(ss_taxable_joint, 2),
        'ss_pct_joint': round(ss_pct_joint, 1),
        'agi_joint': round(agi_joint, 2),
        'total_income_joint': round(total_income_joint, 2),
        'fed_tax_joint': round(fed_tax_joint, 2),
        'effective_rate_joint': round(effective_rate_joint, 1),
        'cash_flow_joint': round(cash_flow_joint, 2),
        'net_joint': round(net_joint, 2),
        
        # Survivor
        'survivor_ss': round(survivor_ss, 2),
        'lost_ss': round(lost_ss, 2),
        'ss_taxable_survivor': round(ss_taxable_survivor, 2),
        'ss_pct_survivor': round(ss_pct_survivor, 1),
        'agi_survivor': round(agi_survivor, 2),
        'total_income_survivor': round(total_income_survivor, 2),
        'fed_tax_survivor': round(fed_tax_survivor, 2),
        'effective_rate_survivor': round(effective_rate_survivor, 1),
        'cash_flow_survivor': round(cash_flow_survivor, 2),
        'net_survivor': round(net_survivor, 2),
        
        # The hit
        'tax_increase': round(tax_increase, 2),
        'income_drop': round(income_drop, 2),
        'net_income_drop': round(net_income_drop, 2),
        'pct_of_original': round(pct_of_original, 1),
        
        # Roth conversion mitigation
        'fed_tax_survivor_roth': round(fed_tax_survivor_roth, 2),
        'tax_increase_with_roth': round(tax_increase_with_roth, 2),
        'roth_savings': round(roth_savings, 2),
        
        # Key insight labels
        'standard_deduction_joint': STD_DEDUCTION_MFJ,
        'standard_deduction_single': STD_DEDUCTION_SINGLE,
        'deduction_lost': STD_DEDUCTION_MFJ - STD_DEDUCTION_SINGLE,
    }


# ============================================================
# QCD Strategy Calculator
# (from Bruce Larsen Ch 11)
# Qualified Charitable Distribution from IRA directly to charity
# Excluded from AGI → reduces SS taxation
# ============================================================

def calc_qcd_benefit(
    ss_benefit_annual,
    other_income,
    rmd_amount,
    qcd_amount,
    filing='MFJ',
    tax_exempt_interest=0,
):
    """
    Calculate the tax benefit of a Qualified Charitable Distribution (QCD).
    
    A QCD sends RMD directly to charity, excluding it from AGI.
    This is better than taking the RMD and itemizing the deduction because:
    - QCD is EXCLUDED from AGI (not a deduction)
    - Lower AGI means less SS is taxable
    - May avoid IRMAA brackets
    
    Returns comparison of taking RMD vs QCD.
    """
    # Ensure QCD doesn't exceed RMD or $105,000 annual limit (2024)
    qcd_annual_limit = 105000
    qcd_actual = min(qcd_amount, rmd_amount, qcd_annual_limit)
    
    # === WITHOUT QCD (take full RMD) ===
    agi_no_qcd = other_income + rmd_amount
    pi_no_qcd = calc_provisional_income(agi_no_qcd, ss_benefit_annual, tax_exempt_interest, filing)
    ss_taxable_no_qcd, ss_pct_no_qcd = calc_ss_taxable(ss_benefit_annual, pi_no_qcd, filing)
    total_income_no_qcd = agi_no_qcd + ss_taxable_no_qcd
    _, fed_tax_no_qcd = calc_marginal_rate(total_income_no_qcd, filing)
    irmaa_no_qcd = calc_irmaa(agi_no_qcd, filing)
    
    # === WITH QCD (send portion directly to charity) ===
    # QCD is excluded from AGI
    remaining_rmd = rmd_amount - qcd_actual  # what you still receive
    agi_with_qcd = other_income + remaining_rmd
    pi_with_qcd = calc_provisional_income(agi_with_qcd, ss_benefit_annual, tax_exempt_interest, filing)
    ss_taxable_with_qcd, ss_pct_with_qcd = calc_ss_taxable(ss_benefit_annual, pi_with_qcd, filing)
    total_income_with_qcd = agi_with_qcd + ss_taxable_with_qcd
    _, fed_tax_with_qcd = calc_marginal_rate(total_income_with_qcd, filing)
    irmaa_with_qcd = calc_irmaa(agi_with_qcd, filing)
    
    # === THE QCD ADVANTAGE ===
    tax_savings = fed_tax_no_qcd - fed_tax_with_qcd
    ss_tax_savings = ss_taxable_no_qcd - ss_taxable_with_qcd
    irmaa_savings = irmaa_no_qcd - irmaa_with_qcd
    
    # Compare to itemized deduction approach (less beneficial)
    # With itemized deduction, the QCD amount is still in AGI
    agi_itemized = other_income + rmd_amount  # Same as no QCD
    # But you get a charitable deduction (limited to 60% of AGI for cash)
    charitable_deduction = min(qcd_actual, agi_itemized * 0.60)
    # SALT cap at $10,000 already limits itemizers; QCD avoids this entirely
    # For simplicity, show that QCD reduces AGI while deduction only reduces taxable income
    
    return {
        # Without QCD
        'agi_no_qcd': round(agi_no_qcd, 2),
        'ss_taxable_no_qcd': round(ss_taxable_no_qcd, 2),
        'ss_pct_no_qcd': round(ss_pct_no_qcd, 1),
        'total_income_no_qcd': round(total_income_no_qcd, 2),
        'fed_tax_no_qcd': round(fed_tax_no_qcd, 2),
        'irmaa_no_qcd': round(irmaa_no_qcd, 2),
        
        # With QCD
        'qcd_amount': round(qcd_actual, 2),
        'remaining_rmd': round(remaining_rmd, 2),
        'agi_with_qcd': round(agi_with_qcd, 2),
        'ss_taxable_with_qcd': round(ss_taxable_with_qcd, 2),
        'ss_pct_with_qcd': round(ss_pct_with_qcd, 1),
        'total_income_with_qcd': round(total_income_with_qcd, 2),
        'fed_tax_with_qcd': round(fed_tax_with_qcd, 2),
        'irmaa_with_qcd': round(irmaa_with_qcd, 2),
        
        # Benefits
        'tax_savings': round(tax_savings, 2),
        'ss_tax_savings': round(ss_tax_savings, 2),
        'irmaa_savings': round(irmaa_savings, 2),
        'total_savings': round(tax_savings + irmaa_savings, 2),
        'effective_savings_rate': round((tax_savings / qcd_actual * 100) if qcd_actual > 0 else 0, 1),
        
        # Key insight
        'qcd_vs_deduction_advantage': round(ss_tax_savings, 2),  # The SS savings that a deduction wouldn't give
    }