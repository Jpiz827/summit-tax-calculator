"""
Summit Tax Services — Automated Check-Up Follow-Up Sequence
Runs the multi-touch nurture emails that go out after someone completes the
Tax & Retirement Check-Up tool. Step 0 (the instant "here are your results"
email) is handled by the Check-Up tool's own lead-capture flow — this module
covers the drip steps that follow.

Wiring: call `send_due_sequence_emails()` once a day from an external
scheduler (Railway cron job, or any free service like cron-job.org) hitting
the protected `/cron/send-sequence-emails` route in app.py. Kept out-of-process
on purpose — a single gunicorn worker could restart or scale at any time, and
an external trigger is simpler to reason about than an in-process scheduler.
"""

import client_db
import email_sender

# Day offsets for each drip step, measured from when the sequence started
# (i.e. from their first Check-Up submission). Step 0 (instant) is not
# listed here — it's sent synchronously by the Check-Up tool itself.
SEQUENCE_DAYS = [3, 7, 12, 18, 25, 40]

WRAP_OPEN = """
<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #2c3345;">
  <div style="background: #1a2744; padding: 24px; border-radius: 8px 8px 0 0; text-align: center;">
    <h1 style="color: #f5f0e7; margin: 0; font-size: 20pt;">Summit Tax Services</h1>
  </div>
  <div style="padding: 28px 24px; background: #faf8f4; border-radius: 0 0 8px 8px;">
"""

WRAP_CLOSE = """
    <hr style="border: none; height: 1px; background: #e8e0d0; margin: 20px 0;">
    <p style="font-size: 9pt; color: #5a6070;">Summit Tax Services | taxesrx.com | myrothrx.com<br>
    Roth conversions. Tax strategy. Retirement confidence.</p>
  </div>
</div>
"""

CTA = """
<div style="background: #1a2744; border: 2px solid #c9a84c; border-radius: 6px; padding: 18px; text-align: center; margin: 20px 0;">
  <a href="https://taxesrx.com/maxss" style="display: inline-block; background: #c9a84c; color: #1a2744; font-family: Arial, sans-serif; font-size: 10pt; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; padding: 12px 28px; border-radius: 4px; text-decoration: none;">Schedule Your Free Strategy Session</a>
</div>
"""


def _step_3_torpedo(name):
    subject = "What is the “Social Security tax torpedo”?"
    body = WRAP_OPEN + f"""
    <p style="font-size: 14pt;">{name},</p>
    <p style="font-size: 11pt; line-height: 1.7;">A few days ago you ran your numbers on our Tax &amp; Retirement Check-Up. One phrase came up that deserves a plain-English explanation: the <strong>Social Security tax torpedo</strong>.</p>
    <p style="font-size: 11pt; line-height: 1.7;">Here's the short version: withdrawals from a Traditional IRA or 401(k) count as income. As that income rises, it can push <strong>up to 85% of your Social Security benefit</strong> into taxable territory &mdash; on top of the tax you already owe on the withdrawal itself. That's the "torpedo."</p>
    <p style="font-size: 11pt; line-height: 1.7;">The good news: for most people, there's a window &mdash; usually the years before RMDs begin &mdash; where a modest, planned Roth conversion can reduce that exposure permanently instead of watching it grow every year.</p>
    {CTA}
    """ + WRAP_CLOSE
    return subject, body


def _step_7_irmaa(name):
    subject = "The hidden Medicare surcharge nobody warns you about"
    body = WRAP_OPEN + f"""
    <p style="font-size: 14pt;">{name},</p>
    <p style="font-size: 11pt; line-height: 1.7;">Most people have never heard of <strong>IRMAA</strong> (Income-Related Monthly Adjustment Amount) until the year it hits them.</p>
    <p style="font-size: 11pt; line-height: 1.7;">Here's what it is: if your income crosses certain thresholds, Medicare charges you <em>more</em> for Part B and Part D &mdash; sometimes hundreds of dollars more per month, for both spouses. And because it's based on your tax return from <strong>two years earlier</strong>, a single large withdrawal today can raise your Medicare premium two years from now, seemingly out of nowhere.</p>
    <p style="font-size: 11pt; line-height: 1.7;">Your Check-Up already gave you a directional read on where you stand. A full review shows the exact bracket, the exact dollar impact, and how to plan withdrawals so you don't cross a line you didn't know was there.</p>
    {CTA}
    """ + WRAP_CLOSE
    return subject, body


def _step_12_case_study(name):
    subject = "What a real before/after looks like"
    body = WRAP_OPEN + f"""
    <p style="font-size: 14pt;">{name},</p>
    <p style="font-size: 11pt; line-height: 1.7;">A married couple came to us with about $310,000 in a Traditional IRA. Doing nothing, our projection showed their Required Minimum Distributions would eventually push them into a Medicare surcharge bracket &mdash; costing them roughly $1,800&ndash;$2,400 more per year, every year, for both of them.</p>
    <p style="font-size: 11pt; line-height: 1.7;">By converting a modest amount to Roth each year &mdash; while their income was still low &mdash; the projection showed they could stay under that threshold indefinitely, even after RMDs began.</p>
    <p style="font-size: 11pt; line-height: 1.7;">Every household's numbers are different. That's exactly what a full review is for.</p>
    {CTA}
    """ + WRAP_CLOSE
    return subject, body


def _step_18_social_proof(name):
    subject = "Still thinking it over? Here's what others found"
    body = WRAP_OPEN + f"""
    <p style="font-size: 14pt;">{name},</p>
    <p style="font-size: 11pt; line-height: 1.7;">Most people who complete a full review tell us the same thing: they wish they'd done it sooner, simply because it clarified decisions they'd been putting off &mdash; when to claim Social Security, how much to convert, whether they're on the right Medicare plan.</p>
    <p style="font-size: 11pt; line-height: 1.7;">There's no cost and no obligation. It's a conversation about your numbers, not a sales pitch.</p>
    {CTA}
    """ + WRAP_CLOSE
    return subject, body


def _step_25_direct_nudge(name):
    subject = "Quick question"
    body = WRAP_OPEN + f"""
    <p style="font-size: 14pt;">{name},</p>
    <p style="font-size: 11pt; line-height: 1.7;">Just checking in &mdash; would it help to get 20 minutes on the calendar to walk through your Check-Up results together?</p>
    {CTA}
    <p style="font-size: 11pt; line-height: 1.7;">No pressure either way &mdash; just here when you're ready.</p>
    """ + WRAP_CLOSE
    return subject, body


def _step_40_reengage(name):
    subject = "One more tool you might find useful"
    body = WRAP_OPEN + f"""
    <p style="font-size: 14pt;">{name},</p>
    <p style="font-size: 11pt; line-height: 1.7;">If taxes and Social Security timing are still on your mind, you might like our <strong>Tax Torpedo Calculator</strong> &mdash; it lets you test a Roth conversion amount yourself and see the effect in real time, no appointment needed.</p>
    <div style="text-align:center; margin: 16px 0;">
      <a href="https://taxesrx.com/torpedo-calculator" style="color:#1a5276; font-weight:700;">Try the Tax Torpedo Calculator &rarr;</a>
    </div>
    <p style="font-size: 11pt; line-height: 1.7;">And whenever you're ready for the full picture on your own numbers, we're here.</p>
    {CTA}
    """ + WRAP_CLOSE
    return subject, body


# Ordered to match SEQUENCE_DAYS — index 0 -> day 3, index 1 -> day 7, etc.
STEP_BUILDERS = [
    _step_3_torpedo,
    _step_7_irmaa,
    _step_12_case_study,
    _step_18_social_proof,
    _step_25_direct_nudge,
    _step_40_reengage,
]


def send_due_sequence_emails():
    """Send whichever drip step is due for each lead. Returns a summary dict
    for logging/inspection. Safe to call repeatedly (idempotent per lead per
    step, since last_step_sent only advances forward)."""
    due = client_db.get_leads_due_for_sequence_email(SEQUENCE_DAYS)
    sent, failed = [], []
    for lead in due:
        step_index = lead['next_step'] - 1  # SEQUENCE_DAYS / STEP_BUILDERS are 0-indexed
        if step_index >= len(STEP_BUILDERS):
            continue
        subject, body = STEP_BUILDERS[step_index](lead['first_name'] or 'there')
        ok = email_sender.send_email(lead['email'], lead['first_name'] or 'there', subject, body)
        if ok:
            client_db.mark_sequence_step_sent(lead['client_id'], lead['next_step'])
            client_db.log_action(lead['client_id'], 'sequence_email_sent',
                                  f"Step {lead['next_step']} (day {SEQUENCE_DAYS[step_index]}): {subject}")
            sent.append({'client_id': lead['client_id'], 'step': lead['next_step'], 'subject': subject})
        else:
            failed.append({'client_id': lead['client_id'], 'step': lead['next_step']})
    return {'sent': sent, 'failed': failed}
