import math
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("SalaryStudio")

# Baseline annual compensation in Lakhs INR (LPA) for Tier-1 Product Companies
# Structure: {role: {exp_level: {"p25": float, "median": float, "p75": float, "p90": float}}}
BENCHMARK_BASE_LPA: Dict[str, Dict[str, Dict[str, float]]] = {
    "software_engineer": {
        "fresher": {"p25": 4.5, "median": 8.0, "p75": 14.0, "p90": 22.0},
        "junior": {"p25": 8.0, "median": 13.5, "p75": 20.0, "p90": 28.0},
        "mid": {"p25": 16.0, "median": 24.0, "p75": 34.0, "p90": 45.0},
        "senior": {"p25": 28.0, "median": 40.0, "p75": 55.0, "p90": 75.0},
        "lead": {"p25": 45.0, "median": 65.0, "p75": 85.0, "p90": 120.0},
    },
    "full_stack": {
        "fresher": {"p25": 4.5, "median": 8.5, "p75": 14.5, "p90": 23.0},
        "junior": {"p25": 8.5, "median": 14.0, "p75": 21.0, "p90": 30.0},
        "mid": {"p25": 17.0, "median": 25.0, "p75": 36.0, "p90": 48.0},
        "senior": {"p25": 30.0, "median": 42.0, "p75": 58.0, "p90": 80.0},
        "lead": {"p25": 48.0, "median": 68.0, "p75": 90.0, "p90": 125.0},
    },
    "backend": {
        "fresher": {"p25": 5.0, "median": 9.0, "p75": 15.0, "p90": 24.0},
        "junior": {"p25": 9.0, "median": 15.0, "p75": 22.0, "p90": 32.0},
        "mid": {"p25": 18.0, "median": 26.5, "p75": 38.0, "p90": 52.0},
        "senior": {"p25": 32.0, "median": 45.0, "p75": 62.0, "p90": 85.0},
        "lead": {"p25": 50.0, "median": 70.0, "p75": 95.0, "p90": 130.0},
    },
    "frontend": {
        "fresher": {"p25": 4.0, "median": 7.5, "p75": 13.0, "p90": 20.0},
        "junior": {"p25": 7.5, "median": 12.5, "p75": 19.0, "p90": 27.0},
        "mid": {"p25": 15.0, "median": 22.5, "p75": 32.0, "p90": 44.0},
        "senior": {"p25": 26.0, "median": 38.0, "p75": 52.0, "p90": 70.0},
        "lead": {"p25": 42.0, "median": 60.0, "p75": 80.0, "p90": 110.0},
    },
    "python_dev": {
        "fresher": {"p25": 4.2, "median": 8.0, "p75": 14.0, "p90": 22.0},
        "junior": {"p25": 8.0, "median": 14.0, "p75": 21.0, "p90": 29.0},
        "mid": {"p25": 17.0, "median": 25.0, "p75": 36.0, "p90": 50.0},
        "senior": {"p25": 30.0, "median": 42.0, "p75": 60.0, "p90": 80.0},
        "lead": {"p25": 48.0, "median": 66.0, "p75": 92.0, "p90": 125.0},
    },
    "ai_ml": {
        "fresher": {"p25": 6.5, "median": 11.0, "p75": 18.0, "p90": 28.0},
        "junior": {"p25": 11.0, "median": 18.0, "p75": 26.0, "p90": 38.0},
        "mid": {"p25": 22.0, "median": 32.0, "p75": 46.0, "p90": 65.0},
        "senior": {"p25": 38.0, "median": 54.0, "p75": 75.0, "p90": 105.0},
        "lead": {"p25": 60.0, "median": 85.0, "p75": 120.0, "p90": 160.0},
    },
    "devops_cloud": {
        "fresher": {"p25": 4.5, "median": 8.0, "p75": 13.5, "p90": 21.0},
        "junior": {"p25": 8.5, "median": 14.0, "p75": 21.0, "p90": 30.0},
        "mid": {"p25": 18.0, "median": 26.0, "p75": 37.0, "p90": 50.0},
        "senior": {"p25": 32.0, "median": 44.0, "p75": 60.0, "p90": 82.0},
        "lead": {"p25": 50.0, "median": 70.0, "p75": 92.0, "p90": 125.0},
    },
    "data_engineer": {
        "fresher": {"p25": 5.0, "median": 8.5, "p75": 14.5, "p90": 22.0},
        "junior": {"p25": 9.0, "median": 15.0, "p75": 22.0, "p90": 31.0},
        "mid": {"p25": 18.0, "median": 26.0, "p75": 37.0, "p90": 50.0},
        "senior": {"p25": 32.0, "median": 44.0, "p75": 60.0, "p90": 82.0},
        "lead": {"p25": 48.0, "median": 68.0, "p75": 92.0, "p90": 125.0},
    }
}

# Multipliers by Company Type
COMPANY_TIER_MULTIPLIERS: Dict[str, float] = {
    "it_services": 0.55,       # TCS, Infosys, Wipro, Cognizant, TechM, etc.
    "funded_startup": 0.95,    # Series A/B/C Startups (strong base + ESOPs)
    "product_unicorn": 1.15,   # Swiggy, Zomato, Razorpay, Flipkart, Zerodha
    "big_tech_faang": 1.50,    # Google, Microsoft, Amazon, Uber, Atlassian, Adobe
    "global_remote": 2.20      # US / EU remote paid in USD/EUR
}

# Multipliers by City/Location
LOCATION_MULTIPLIERS: Dict[str, float] = {
    "bangalore": 1.15,
    "hyderabad": 1.05,
    "delhi_ncr": 1.05,
    "pune": 1.00,
    "mumbai": 1.05,
    "chennai": 0.95,
    "tier_2": 0.85,
    "remote_india": 1.00,
    "remote_global": 2.20
}

# Tech Stack Premium Add-ons (+percentage boost for high demand skills)
TECH_STACK_PREMIUMS: Dict[str, float] = {
    "system_design": 0.08,
    "fastapi": 0.05,
    "docker_kubernetes": 0.07,
    "react_nextjs": 0.05,
    "aws_cloud": 0.06,
    "distributed_systems": 0.10,
    "ai_llms": 0.15,
    "golang": 0.08,
    "rust": 0.12,
    "graphql": 0.04,
    "microservices": 0.06
}

def normalize_role(role_name: str) -> str:
    r = (role_name or "").lower().strip()
    if "ai" in r or "ml" in r or "machine learning" in r or "data scien" in r:
        return "ai_ml"
    if "data eng" in r or "big data" in r:
        return "data_engineer"
    if "devops" in r or "cloud" in r or "sre" in r or "platform eng" in r:
        return "devops_cloud"
    if "front" in r or "react" in r or "angular" in r or "vue" in r or "ui developer" in r:
        return "frontend"
    if "back" in r or "api" in r or "django" in r or "fastapi" in r or "node" in r:
        return "backend"
    if "full" in r or "mern" in r or "mean" in r:
        return "full_stack"
    if "python" in r:
        return "python_dev"
    return "software_engineer"

def calculate_monthly_take_home(annual_ctc_lpa: float, fixed_pct: float = 0.85) -> Dict[str, Any]:
    """
    Estimates monthly in-hand salary under India's New Tax Regime (FY 2025-26 rules).
    Takes into account Standard Deduction (₹75,000), Employee PF contribution (~₹21,600/yr),
    and progressive tax slabs.
    """
    fixed_ctc = annual_ctc_lpa * (fixed_pct / 100.0) * 100000.0  # In INR
    
    # Standard Deduction
    std_deduction = 75000.0
    
    # Employee PF estimate (~1800/mo standard capped or 12% basic)
    annual_pf = min(fixed_ctc * 0.40 * 0.12, 1800.0 * 12)
    
    taxable_income = max(0.0, fixed_ctc - std_deduction - annual_pf)
    
    # New Tax Regime Slabs
    # Up to 3L: 0%
    # 3L - 7L: 5%
    # 7L - 10L: 10%
    # 10L - 12L: 15%
    # 12L - 15L: 20%
    # Above 15L: 30%
    tax = 0.0
    if taxable_income > 1500000:
        tax += (taxable_income - 1500000) * 0.30
        taxable_income = 1500000
    if taxable_income > 1200000:
        tax += (taxable_income - 1200000) * 0.20
        taxable_income = 1200000
    if taxable_income > 1000000:
        tax += (taxable_income - 1000000) * 0.15
        taxable_income = 1000000
    if taxable_income > 700000:
        tax += (taxable_income - 700000) * 0.10
        taxable_income = 700000
    if taxable_income > 300000:
        tax += (taxable_income - 300000) * 0.05

    # Section 87A rebate: zero tax if taxable income <= 7,00,000
    if fixed_ctc - std_deduction <= 700000:
        tax = 0.0
    else:
        # Add 4% Health & Education Cess
        tax = tax * 1.04

    # Professional Tax (~₹2,400/yr in Karnataka / Telangana / Maharashtra)
    prof_tax = 2400.0

    net_annual_in_hand = max(0.0, fixed_ctc - tax - annual_pf - prof_tax)
    monthly_in_hand = round(net_annual_in_hand / 12.0)

    return {
        "monthly_in_hand_inr": monthly_in_hand,
        "monthly_formatted": f"₹{monthly_in_hand:,.0f}",
        "annual_tax_inr": round(tax),
        "annual_pf_inr": round(annual_pf),
        "annual_fixed_inr": round(fixed_ctc)
    }

def estimate_compensation(
    role: str = "software_engineer",
    experience: str = "fresher",
    location: str = "bangalore",
    company_tier: str = "product_unicorn",
    skills: Optional[List[str]] = None,
    current_offered_lpa: Optional[float] = None
) -> Dict[str, Any]:
    norm_role = normalize_role(role)
    norm_exp = experience.lower().strip()
    if norm_exp not in ["fresher", "junior", "mid", "senior", "lead"]:
        norm_exp = "fresher"

    base_matrix = BENCHMARK_BASE_LPA.get(norm_role, BENCHMARK_BASE_LPA["software_engineer"]).get(
        norm_exp, BENCHMARK_BASE_LPA["software_engineer"]["fresher"]
    )

    tier_mult = COMPANY_TIER_MULTIPLIERS.get(company_tier, 1.0)
    loc_mult = LOCATION_MULTIPLIERS.get(location, 1.0)

    # Tech stack premium
    skill_bonus_pct = 0.0
    active_premiums = []
    if skills:
        for s in skills:
            s_clean = s.lower().replace(" ", "_").replace(".", "").replace("-", "_")
            for prem_key, prem_val in TECH_STACK_PREMIUMS.items():
                if prem_key in s_clean or s_clean in prem_key:
                    if prem_key not in active_premiums:
                        skill_bonus_pct += prem_val
                        active_premiums.append(prem_key)

    skill_mult = 1.0 + min(skill_bonus_pct, 0.35)  # Cap premium at 35%
    combined_mult = tier_mult * loc_mult * skill_mult

    p25 = round(base_matrix["p25"] * combined_mult, 1)
    median = round(base_matrix["median"] * combined_mult, 1)
    p75 = round(base_matrix["p75"] * combined_mult, 1)
    p90 = round(base_matrix["p90"] * combined_mult, 1)

    # Structure breakdown: Fixed Base (~75-85%), Performance Variable (~10-15%), ESOPs/Stock (remaining)
    fixed_ratio = 0.82
    variable_ratio = 0.12
    equity_ratio = 0.06

    median_fixed = round(median * fixed_ratio, 1)
    median_variable = round(median * variable_ratio, 1)
    median_equity = round(median * equity_ratio, 1)

    take_home_data = calculate_monthly_take_home(median, fixed_pct=fixed_ratio * 100)

    # Assess where current offered CTC sits (if provided)
    percentile_assessment = None
    if current_offered_lpa and current_offered_lpa > 0:
        if current_offered_lpa < p25:
            pct_label = "Below 25th Percentile (Below Market Average)"
            status_color = "#ef4444"
            advice = "High negotiation leverage! This offer is below fair market value. Counter immediately using our data benchmarks."
        elif current_offered_lpa < median:
            pct_label = "25th - 50th Percentile (Fair Entry Market)"
            status_color = "#f59e0b"
            advice = "Good baseline, but there is room for a 15-25% bump. Counter with specific skill achievements and competing opportunities."
        elif current_offered_lpa < p75:
            pct_label = "50th - 75th Percentile (Competitive Top Tier)"
            status_color = "#10b981"
            advice = "Strong, competitive compensation! You can negotiate non-salary perks like a joining bonus, faster performance reviews, or remote flexibility."
        else:
            pct_label = "Top 10% (Exceptional Tier-1 Package)"
            status_color = "#6366f1"
            advice = "Outstanding offer at the top tier of the market! Ensure vesting schedule and title trajectory match your long-term goals."

        percentile_assessment = {
            "offered_lpa": current_offered_lpa,
            "label": pct_label,
            "status_color": status_color,
            "advice": advice
        }

    return {
        "role": norm_role,
        "experience": norm_exp,
        "location": location,
        "company_tier": company_tier,
        "benchmarks": {
            "p25": p25,
            "median": median,
            "p75": p75,
            "p90": p90,
            "currency": "LPA (Lakhs INR / Year)"
        },
        "median_breakdown": {
            "total_ctc": median,
            "fixed_base": median_fixed,
            "performance_bonus": median_variable,
            "equity_esops": median_equity
        },
        "in_hand_estimate": take_home_data,
        "premiums_applied": {
            "active_skills": active_premiums,
            "total_bonus_percentage": round(skill_bonus_pct * 100, 1)
        },
        "percentile_assessment": percentile_assessment
    }

def generate_counter_offer_scripts(
    candidate_name: str,
    company_name: str,
    role_title: str,
    current_offered_lpa: float,
    target_lpa: float,
    competing_offer_lpa: Optional[float] = None,
    competing_company: Optional[str] = None,
    key_skills: Optional[List[str]] = None,
    negotiation_focus: str = "polite_counter"
) -> Dict[str, Any]:
    """
    Generates 3 battle-tested, high-conversion negotiation email scripts:
    1. The Respectful Data-Driven Counter (Standard & highly professional)
    2. The Competing Offer Leverage Counter (Uses alternative options to maximize speed & package)
    3. The Total Rewards & Signing Bonus Pivot (When fixed base is tight but company has budget for joining bonus or perks)
    """
    skills_str = ", ".join(key_skills[:4]) if key_skills else "Python, System Design, and modern backend architecture"
    gap_lpa = round(target_lpa - current_offered_lpa, 1) if target_lpa > current_offered_lpa else 2.0

    # Script 1: Polite Data-Backed Counter
    script_polite = f"""Subject: Regarding the Offer for {role_title} - {candidate_name}

Hi [Hiring Manager / Recruiter Name],

Thank you so much for extending the offer to join {company_name} as a {role_title}! I am genuinely excited about the team's vision and the technical roadmap we discussed during our interviews.

After thoroughly reviewing the offer and comparing it against current market benchmarks for someone with hands-on experience in {skills_str}, I would like to discuss the compensation package.

Given the scope of the position and my ability to hit the ground running from Day 1, I was hoping we could explore an annual base of ₹{target_lpa:.1f} LPA (currently offered at ₹{current_offered_lpa:.1f} LPA).

I believe this reflects fair market alignment for the impact I plan to deliver to the team. If we can reach closer to this number, I would be thrilled to sign the offer immediately and begin onboarding.

Please let me know if we can schedule a quick 5-minute call to discuss this.

Best regards,
{candidate_name}
[Phone Number] | [LinkedIn Profile]"""

    # Script 2: Competing Offer Leverage
    comp_comp = competing_company or "another respected tech company"
    comp_num = f"₹{competing_offer_lpa:.1f} LPA" if competing_offer_lpa else f"₹{target_lpa + 1.5:.1f} LPA"

    script_competing = f"""Subject: Update Regarding {role_title} Offer - {candidate_name}

Hi [Hiring Manager / Recruiter Name],

First, I want to reiterate how much I enjoyed speaking with the team at {company_name}. You are my top choice for where I want to take the next step in my career.

To be completely transparent with you, I have recently received a concurrent offer from {comp_comp} for {comp_num}. 

That said, {company_name}'s product direction, team culture, and engineering challenges are far more aligned with where I want to be. If you are able to adjust the current compensation to ₹{target_lpa:.1f} LPA, I am ready to decline the other opportunity today and formally commit to joining {company_name}.

I deeply respect your time and wanted to provide full clarity so we can find a mutually exciting agreement.

Warm regards,
{candidate_name}
[Phone Number] | [LinkedIn Profile]"""

    # Script 3: Total Rewards / Joining Bonus Pivot
    script_signing_bonus = f"""Subject: Exploring Total Compensation Structure for {role_title} - {candidate_name}

Hi [Hiring Manager / Recruiter Name],

Thank you again for the offer! I am very grateful for the opportunity and eager to contribute to {company_name}.

I understand that internal compensation bands may place constraints on base salary at ₹{current_offered_lpa:.1f} LPA. To help bridge the gap towards my target of ₹{target_lpa:.1f} LPA, I would love to explore flexible components such as:

1. A one-time Joining / Sign-on Bonus of ₹{min(gap_lpa * 100000, 300000):,.0f}
2. Accelerated 6-month performance review with an opportunity for an early compensation revision
3. Flexibility with remote work setup allowances or equity grant allocation

I am confident in my ability to drive measurable results quickly with my background in {skills_str}, and I am eager to make this partnership work.

Looking forward to hearing your thoughts.

Sincerely,
{candidate_name}
[Phone Number] | [LinkedIn Profile]"""

    # Tactical Negotiation Playbook Advice
    tips = [
        "Never reject an offer outright—always anchor on enthusiasm first before naming your counter-number.",
        f"Anchoring psychology: Aim for ₹{target_lpa:.1f} LPA so even if the recruiter meets you in the middle at ₹{round((current_offered_lpa + target_lpa)/2, 1)} LPA, you come out significantly ahead.",
        "Recruiters expect counter-offers: Standard industry surveys show over 80% of companies have a 10-15% negotiation buffer reserved in their hiring budget.",
        "If base salary is fixed by band, always pivot to a one-time sign-on bonus or an accelerated 6-month performance appraisal clause."
    ]

    return {
        "status": "ok",
        "scripts": {
            "polite_counter": {
                "title": "Data-Driven Professional Counter",
                "badge": "Standard & High Success Rate",
                "email_text": script_polite.strip()
            },
            "competing_offer": {
                "title": "Competing Offer Leverage",
                "badge": "Fast Resolution & Maximum Leverage",
                "email_text": script_competing.strip()
            },
            "signing_bonus_pivot": {
                "title": "Signing Bonus & Total Rewards Pivot",
                "badge": "Overcomes Fixed Base Bands",
                "email_text": script_signing_bonus.strip()
            }
        },
        "tactical_tips": tips
    }

def get_job_salary_radar_insight(job_title: str, company: str, location: str = "") -> Dict[str, Any]:
    """
    Given a scraped job posting title, company, and location, analyzes market value
    and generates an automated compensation estimate with recruiter bargaining tips.
    """
    norm_role = normalize_role(job_title)
    
    # Infer company tier based on company name
    comp_lower = (company or "").lower()
    if any(m in comp_lower for m in ["google", "microsoft", "amazon", "uber", "atlassian", "meta", "adobe", "apple", "salesforce"]):
        c_tier = "big_tech_faang"
    elif any(m in comp_lower for m in ["tcs", "infosys", "wipro", "cognizant", "tech mahindra", "accenture", "hcl", "capgemini"]):
        c_tier = "it_services"
    elif any(m in comp_lower for m in ["swiggy", "zomato", "razorpay", "cred", "flipkart", "paytm", "ola", "zerodha", "zepto"]):
        c_tier = "product_unicorn"
    else:
        c_tier = "funded_startup"

    # Infer location
    loc_lower = (location or "").lower()
    if "bangalore" in loc_lower or "bengaluru" in loc_lower:
        loc = "bangalore"
    elif "hyderabad" in loc_lower:
        loc = "hyderabad"
    elif "pune" in loc_lower:
        loc = "pune"
    elif "remote" in loc_lower:
        loc = "remote_india"
    else:
        loc = "bangalore"

    fresher_est = estimate_compensation(norm_role, "fresher", loc, c_tier)
    junior_est = estimate_compensation(norm_role, "junior", loc, c_tier)
    mid_est = estimate_compensation(norm_role, "mid", loc, c_tier)

    return {
        "job_title": job_title,
        "company": company,
        "inferred_company_tier": c_tier.replace("_", " ").title(),
        "inferred_location": loc.replace("_", " ").title(),
        "expected_ranges": {
            "fresher_0_1_yrs": f"₹{fresher_est['benchmarks']['p25']} - ₹{fresher_est['benchmarks']['p75']} LPA (Median: ₹{fresher_est['benchmarks']['median']} LPA)",
            "junior_1_3_yrs": f"₹{junior_est['benchmarks']['p25']} - ₹{junior_est['benchmarks']['p75']} LPA (Median: ₹{junior_est['benchmarks']['median']} LPA)",
            "mid_3_5_yrs": f"₹{mid_est['benchmarks']['p25']} - ₹{mid_est['benchmarks']['p75']} LPA (Median: ₹{mid_est['benchmarks']['median']} LPA)"
        },
        "monthly_take_home_entry": fresher_est["in_hand_estimate"]["monthly_formatted"],
        "negotiation_tip": (
            f"When interviewing with {company}, ask for the salary range during the first HR screen: "
            "'To make sure we're mutually aligned, what is the budgeted compensation band for this role?' "
            "Never state your current salary first."
        )
    }
