/**
 * JobRadar AI - Universal Job Portal Auto-Fill Assistant
 * Compatible with: Greenhouse, Lever, Workday, Ashby, SmartRecruiters & Generic Job Portals
 */
(async function() {
    console.log("⚡ [JobRadar AI] Universal Auto-Fill initializing...");

    // Remove existing HUD if present
    const oldHud = document.getElementById("jobradar-autofill-hud");
    if (oldHud) oldHud.remove();

    // Configuration & Server URL
    const SERVER_URL = "http://127.0.0.1:8765";

    // 1. Fetch user autofill profile from JobRadar local server
    let profile = null;
    try {
        const res = await fetch(`${SERVER_URL}/api/autofill/profile`, {
            method: "GET",
            headers: { "Accept": "application/json" }
        });
        if (res.ok) {
            const data = await res.json();
            profile = data.profile || data;
        }
    } catch (e) {
        console.warn("⚡ [JobRadar AI] Could not connect to local server, using cached session or fallback.", e);
    }

    // Default fallback if server not reachable or profile empty
    if (!profile) {
        profile = {
            name: "Sharanu",
            email: "sharanujm@gmail.com",
            phone: "+91 98765 43210",
            current_city: "Bengaluru, Karnataka, India",
            linkedin_url: "https://linkedin.com/in/sharanu",
            github_url: "https://github.com/sharanu",
            portfolio_url: "https://sharanu.dev",
            years_experience: "1",
            notice_period: "Immediate",
            expected_ctc: "Competitive / Market Standard",
            work_authorization: "Authorized to work in India (Citizen/Permanent Resident)",
            visa_sponsorship: "No",
            target_role: "Software Engineer",
            why_hire_me: "I bring strong foundations in software development with hands-on experience building scalable applications, clean architecture, and modern APIs. I adapt rapidly and deliver high-quality, production-tested solutions.",
            why_this_company: "I have been following your engineering culture and product innovation with great interest. The problems your team is tackling directly align with my technical interests and long-term career focus.",
            experience_summary: "Software Engineer with hands-on experience building scalable APIs, frontend workflows, and database optimizations. Strong focus on clean code, automated testing, and team collaboration."
        };
    }

    // Split name into first and last
    const nameParts = (profile.name || "Candidate").trim().split(/\s+/);
    const firstName = nameParts[0] || "";
    const lastName = nameParts.length > 1 ? nameParts.slice(1).join(" ") : nameParts[0];

    // Helper: Safely set value on React/Vue/Angular controlled inputs
    function setReactInputValue(el, value) {
        if (!el || value === undefined || value === null) return false;
        try {
            el.focus();
            const proto = el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
            const nativeSetter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
            if (nativeSetter) {
                nativeSetter.call(el, value);
            } else {
                el.value = value;
            }
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
            el.dispatchEvent(new Event("blur", { bubbles: true }));
            el.style.backgroundColor = "rgba(16, 185, 129, 0.12)";
            el.style.borderColor = "#10b981";
            return true;
        } catch (err) {
            el.value = value;
            return true;
        }
    }

    // Helper: Get label text associated with input
    function getAssociatedLabel(input) {
        let labelText = "";
        if (input.id) {
            const lbl = document.querySelector(`label[for="${input.id}"]`);
            if (lbl) labelText += " " + lbl.textContent;
        }
        const parentLbl = input.closest("label");
        if (parentLbl) labelText += " " + parentLbl.textContent;
        
        // Also check preceding sibling label or container heading
        const prevEl = input.previousElementSibling;
        if (prevEl && (prevEl.tagName === "LABEL" || prevEl.classList.contains("label") || prevEl.tagName === "SPAN")) {
            labelText += " " + prevEl.textContent;
        }
        const container = input.closest(".form-group, .field, .input-container, [data-qa], .application-question, [data-automation-id]");
        if (container) {
            const h = container.querySelector("label, .label, h3, h4, span, legend");
            if (h && h !== input) labelText += " " + h.textContent;
        }
        return labelText.toLowerCase();
    }

    // Detect Platform
    const url = window.location.href.toLowerCase();
    let platform = "Generic Job Portal";
    if (url.includes("greenhouse.io") || document.querySelector("#application_form, [data-qa='job-application']")) platform = "Greenhouse";
    else if (url.includes("lever.co") || document.querySelector(".application-form, .lever-job-title")) platform = "Lever";
    else if (url.includes("myworkdayjobs.com") || document.querySelector("[data-automation-id]")) platform = "Workday";
    else if (url.includes("ashbyhq.com") || document.querySelector("[data-ashby]")) platform = "Ashby";
    else if (url.includes("smartrecruiters.com")) platform = "SmartRecruiters";

    let filledCount = 0;
    const filledFields = [];

    // 2. Platform-Specific and General Form Fillers
    const inputs = Array.from(document.querySelectorAll("input:not([type='hidden']):not([type='submit']):not([type='button']), textarea, select"));

    inputs.forEach(input => {
        const name = (input.name || "").toLowerCase();
        const id = (input.id || "").toLowerCase();
        const placeholder = (input.placeholder || "").toLowerCase();
        const ariaLabel = (input.getAttribute("aria-label") || "").toLowerCase();
        const autoId = (input.getAttribute("data-automation-id") || "").toLowerCase();
        const autocomplete = (input.getAttribute("autocomplete") || "").toLowerCase();
        const type = (input.type || "text").toLowerCase();
        const label = getAssociatedLabel(input);

        const allMeta = `${name} ${id} ${placeholder} ${ariaLabel} ${autoId} ${autocomplete} ${label}`;

        // FIRST NAME
        if (
            (allMeta.includes("first") && (allMeta.includes("name") || allMeta.includes("given"))) ||
            allMeta.includes("firstname") ||
            autoId.includes("legalnamesection_firstname") ||
            name === "first_name" || id === "first_name"
        ) {
            if (setReactInputValue(input, firstName)) {
                filledCount++;
                filledFields.push("First Name");
            }
            return;
        }

        // LAST NAME
        if (
            (allMeta.includes("last") && (allMeta.includes("name") || allMeta.includes("surname") || allMeta.includes("family"))) ||
            allMeta.includes("lastname") ||
            autoId.includes("legalnamesection_lastname") ||
            name === "last_name" || id === "last_name"
        ) {
            if (setReactInputValue(input, lastName)) {
                filledCount++;
                filledFields.push("Last Name");
            }
            return;
        }

        // FULL NAME (when no separate first/last name)
        if (
            (allMeta.includes("full name") || allMeta.includes("candidate name") || name === "name" || id === "name") &&
            !allMeta.includes("first") && !allMeta.includes("last") && !allMeta.includes("company") && !allMeta.includes("college")
        ) {
            if (setReactInputValue(input, profile.name)) {
                filledCount++;
                filledFields.push("Full Name");
            }
            return;
        }

        // EMAIL
        if (
            type === "email" ||
            allMeta.includes("email") ||
            autoId.includes("email") ||
            name === "email" || id === "email"
        ) {
            if (setReactInputValue(input, profile.email)) {
                filledCount++;
                filledFields.push("Email");
            }
            return;
        }

        // PHONE / MOBILE
        if (
            type === "tel" ||
            allMeta.includes("phone") ||
            allMeta.includes("mobile") ||
            allMeta.includes("contact number") ||
            autoId.includes("phone-number") ||
            name === "phone" || id === "phone"
        ) {
            if (setReactInputValue(input, profile.phone)) {
                filledCount++;
                filledFields.push("Phone");
            }
            return;
        }

        // LINKEDIN
        if (
            allMeta.includes("linkedin") ||
            name.includes("[linkedin]") ||
            autoId.includes("linkedin")
        ) {
            if (setReactInputValue(input, profile.linkedin_url)) {
                filledCount++;
                filledFields.push("LinkedIn URL");
            }
            return;
        }

        // GITHUB
        if (
            allMeta.includes("github") ||
            name.includes("[github]") ||
            autoId.includes("github")
        ) {
            if (setReactInputValue(input, profile.github_url)) {
                filledCount++;
                filledFields.push("GitHub URL");
            }
            return;
        }

        // PORTFOLIO / WEBSITE
        if (
            (allMeta.includes("portfolio") || allMeta.includes("website") || allMeta.includes("personal site")) &&
            !allMeta.includes("linkedin") && !allMeta.includes("github")
        ) {
            if (setReactInputValue(input, profile.portfolio_url)) {
                filledCount++;
                filledFields.push("Portfolio URL");
            }
            return;
        }

        // LOCATION / CITY
        if (
            allMeta.includes("city") ||
            (allMeta.includes("location") && !allMeta.includes("relocation")) ||
            allMeta.includes("addresssection_city")
        ) {
            if (setReactInputValue(input, profile.current_city)) {
                filledCount++;
                filledFields.push("City/Location");
            }
            return;
        }

        // NOTICE PERIOD / AVAILABILITY
        if (
            allMeta.includes("notice period") ||
            allMeta.includes("how soon can you join") ||
            allMeta.includes("availability")
        ) {
            if (input.tagName === "SELECT") {
                for (let opt of input.options) {
                    if (opt.text.toLowerCase().includes("immediate") || opt.value.toLowerCase().includes("immediate") || opt.value.includes("0")) {
                        opt.selected = true;
                        input.dispatchEvent(new Event("change", { bubbles: true }));
                        filledCount++;
                        filledFields.push("Notice Period");
                        break;
                    }
                }
            } else {
                if (setReactInputValue(input, profile.notice_period || "Immediate (0 Days)")) {
                    filledCount++;
                    filledFields.push("Notice Period");
                }
            }
            return;
        }

        // YEARS OF EXPERIENCE
        if (
            (allMeta.includes("years of experience") || allMeta.includes("total experience")) &&
            !allMeta.includes("describe")
        ) {
            if (setReactInputValue(input, profile.years_experience || "1")) {
                filledCount++;
                filledFields.push("Years Experience");
            }
            return;
        }

        // EXPECTED SALARY / CTC
        if (
            allMeta.includes("expected ctc") ||
            allMeta.includes("expected salary") ||
            allMeta.includes("compensation expectation")
        ) {
            if (setReactInputValue(input, profile.expected_ctc || "Competitive / Market Standard")) {
                filledCount++;
                filledFields.push("Expected CTC");
            }
            return;
        }

        // WORK AUTHORIZATION (Radio / Checkbox / Select)
        if (
            (allMeta.includes("authorized to work") || allMeta.includes("legally authorized") || allMeta.includes("work authorization")) &&
            !allMeta.includes("sponsorship")
        ) {
            if (input.type === "radio" || input.type === "checkbox") {
                if (allMeta.includes("yes") || input.value.toLowerCase() === "yes" || input.value === "1") {
                    input.checked = true;
                    input.dispatchEvent(new Event("change", { bubbles: true }));
                    filledCount++;
                    filledFields.push("Work Authorization (Yes)");
                }
            } else if (input.tagName === "SELECT") {
                for (let opt of input.options) {
                    if (opt.text.toLowerCase().includes("yes") || opt.value.toLowerCase().includes("yes")) {
                        opt.selected = true;
                        input.dispatchEvent(new Event("change", { bubbles: true }));
                        filledCount++;
                        filledFields.push("Work Authorization");
                        break;
                    }
                }
            }
            return;
        }

        // VISA SPONSORSHIP (Typically answered "No" for domestic roles)
        if (
            allMeta.includes("require sponsorship") ||
            allMeta.includes("sponsorship for employment visa") ||
            allMeta.includes("visa sponsorship")
        ) {
            if (input.type === "radio" || input.type === "checkbox") {
                if (allMeta.includes("no") || input.value.toLowerCase() === "no" || input.value === "0") {
                    input.checked = true;
                    input.dispatchEvent(new Event("change", { bubbles: true }));
                    filledCount++;
                    filledFields.push("Visa Sponsorship (No)");
                }
            } else if (input.tagName === "SELECT") {
                for (let opt of input.options) {
                    if (opt.text.toLowerCase().includes("no") || opt.value.toLowerCase().includes("no")) {
                        opt.selected = true;
                        input.dispatchEvent(new Event("change", { bubbles: true }));
                        filledCount++;
                        filledFields.push("Visa Sponsorship (No)");
                        break;
                    }
                }
            }
            return;
        }

        // WHY WORK HERE / COVER LETTER
        if (
            input.tagName === "TEXTAREA" &&
            (allMeta.includes("why do you want to work") || allMeta.includes("why us") || allMeta.includes("cover letter") || allMeta.includes("comments") || allMeta.includes("additional info"))
        ) {
            if (!input.value.trim()) {
                if (setReactInputValue(input, profile.why_this_company)) {
                    filledCount++;
                    filledFields.push("Why This Company");
                }
            }
            return;
        }
    });

    // 3. Create Floating Modern Glassmorphism HUD Badge on the Page
    const hud = document.createElement("div");
    hud.id = "jobradar-autofill-hud";
    hud.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 2147483647;
        width: 340px;
        max-width: 90vw;
        background: #0f172a;
        color: #f8fafc;
        border: 1px solid rgba(99, 102, 241, 0.4);
        border-radius: 14px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(99, 102, 241, 0.25);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 13px;
        line-height: 1.4;
        box-sizing: border-box;
        overflow: hidden;
        animation: jobradarSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    `;

    hud.innerHTML = `
        <div style="background: linear-gradient(135deg, #1e1b4b, #312e81); padding: 12px 14px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">⚡</span>
                <span style="font-weight: 800; font-size: 13px; letter-spacing: -0.2px; color: #fff;">JobRadar Auto-Fill</span>
                <span style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(52, 211, 153, 0.3);">${platform}</span>
            </div>
            <button id="jr-btn-close-hud" style="background: none; border: none; color: #94a3b8; font-size: 16px; cursor: pointer; padding: 0 4px; line-height: 1;">✕</button>
        </div>
        <div style="padding: 14px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <div style="width: 28px; height: 28px; border-radius: 50%; background: rgba(16, 185, 129, 0.2); color: #10b981; display: flex; align-items: center; justify-content: center; font-weight: bold;">✓</div>
                <div>
                    <div style="font-weight: 700; color: #fff; font-size: 13px;">${filledCount > 0 ? `${filledCount} Fields Auto-Filled!` : "Form Inspected"}</div>
                    <div style="font-size: 11px; color: #94a3b8;">${filledFields.slice(0, 3).join(", ") + (filledFields.length > 3 ? ` +${filledFields.length - 3} more` : "")}</div>
                </div>
            </div>

            <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px; margin-top: 6px;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #818cf8; margin-bottom: 6px;">1-Click Snippet Copy:</div>
                <div style="display: flex; flex-direction: column; gap: 6px;">
                    <button class="jr-copy-btn" data-val="${encodeURIComponent(profile.why_hire_me)}" style="background: #1e293b; color: #e2e8f0; border: 1px solid #334155; padding: 6px 10px; border-radius: 6px; font-size: 11px; text-align: left; cursor: pointer; display: flex; justify-content: space-between;">
                        <span>💼 Why Hire Me?</span>
                        <span style="color: #38bdf8;">Copy</span>
                    </button>
                    <button class="jr-copy-btn" data-val="${encodeURIComponent(profile.why_this_company)}" style="background: #1e293b; color: #e2e8f0; border: 1px solid #334155; padding: 6px 10px; border-radius: 6px; font-size: 11px; text-align: left; cursor: pointer; display: flex; justify-content: space-between;">
                        <span>🏢 Why This Company?</span>
                        <span style="color: #38bdf8;">Copy</span>
                    </button>
                    <button class="jr-copy-btn" data-val="${encodeURIComponent(profile.experience_summary)}" style="background: #1e293b; color: #e2e8f0; border: 1px solid #334155; padding: 6px 10px; border-radius: 6px; font-size: 11px; text-align: left; cursor: pointer; display: flex; justify-content: space-between;">
                        <span>🚀 Experience Summary</span>
                        <span style="color: #38bdf8;">Copy</span>
                    </button>
                </div>
            </div>

            <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #64748b;">
                <span>User: ${profile.name}</span>
                <a href="${SERVER_URL}" target="_blank" style="color: #6366f1; text-decoration: none; font-weight: 600;">Open JobRadar →</a>
            </div>
        </div>
    `;

    document.body.appendChild(hud);

    // Event listeners
    document.getElementById("jr-btn-close-hud").onclick = () => hud.remove();

    hud.querySelectorAll(".jr-copy-btn").forEach(btn => {
        btn.onclick = function() {
            const val = decodeURIComponent(this.getAttribute("data-val"));
            navigator.clipboard.writeText(val);
            const originalSpan = this.querySelector("span:last-child");
            const oldText = originalSpan.textContent;
            originalSpan.textContent = "Copied!";
            originalSpan.style.color = "#34d399";
            setTimeout(() => {
                originalSpan.textContent = oldText;
                originalSpan.style.color = "#38bdf8";
            }, 1800);
        };
    });

    // Auto-dismiss HUD after 15 seconds
    setTimeout(() => {
        if (document.getElementById("jobradar-autofill-hud")) {
            hud.style.opacity = "0.7";
        }
    }, 15000);

    console.log(`⚡ [JobRadar AI] Auto-fill completed: ${filledCount} fields filled.`);
})();

