/* ==============================================================================
   JOBRADAR AI - CLIENT APPLICATION LOGIC
   ============================================================================== */

function getInitialUser() {
    try {
        const saved = localStorage.getItem("jobradar_active_user");
        if (saved) {
            const parsed = JSON.parse(saved);
            if (parsed && parsed.email) {
                return parsed;
            }
        }
    } catch (e) {
        console.error("Error reading saved user:", e);
    }
    return null;
}

let state = {
    currentUser: getInitialUser(),
    jobs: [],
    totalJobs: 0,
    offset: 0,
    limit: 30,
    filters: {
        search: "",
        experience: "all",
        site: "all",
        location: "all",
        is_remote: null,
        min_score: 0,
        status_filter: "",
        posted_within: "",
        skill_tag: ""
    },
    activeView: "jobs",
    debounceTimer: null,
    profileModalSkills: [],
    trackerItems: [],
    selectedDetailJobId: null,
    currentAutofill: null,
    resources: [],
    activeResourceCategory: "all",
    resourceSearchTerm: "",
    activeReadingResourceId: null
};

// Initialize Application
initTheme(); // Immediate theme setup to prevent flash

document.addEventListener("DOMContentLoaded", async () => {
    initTheme();
    checkFirstTimeOnboarding();
    setupNavigation();
    setupDropZone();

    // Immediately restore flexible schedule time and recipient email from localStorage
    const savedTime = localStorage.getItem("jobradar_scheduled_time");
    const savedEmail = localStorage.getItem("jobradar_user_email");
    if (savedTime) {
        const inpTime = document.getElementById("input-schedule-time");
        if (inpTime) inpTime.value = savedTime;
        const sideTime = document.getElementById("sidebar-schedule-display");
        if (sideTime) sideTime.textContent = `Daily Digest: ${formatTimeTo12h(savedTime)}`;
        const profTime = document.getElementById("profile-modal-time");
        if (profTime) profTime.value = savedTime;
    }
    if (savedEmail) {
        const inpEmail = document.getElementById("auto-email-input");
        if (inpEmail && !inpEmail.value) inpEmail.value = savedEmail;
    }

    await loadUserProfile();
    await fetchStats();
    await fetchJobs(true);
    await analyzeResumeATS();
    loadStudyResources(); // Pre-load vault count
    loadPipelineStatus();
    loadEmailSettings();
});

// First-Time Sign Up / Login Onboarding
function checkFirstTimeOnboarding() {
    const overlay = document.getElementById("auth-onboarding-screen");
    if (!state.currentUser) {
        if (overlay) overlay.style.display = "flex";
        switchOnboardTab("login");
    } else {
        if (overlay) overlay.style.display = "none";
    }
}

function dismissOnboarding() {
    const overlay = document.getElementById("auth-onboarding-screen");
    if (overlay) overlay.style.display = "none";
    hideAuthAlert();
    if (!state.currentUser) {
        showToast("Browsing dashboard as Guest. Sign in anytime to sync alerts and saved jobs!");
    }
    renderUserHeader();
}

function switchOnboardTab(tab) {
    const btnSignup = document.getElementById("onboard-tab-signup");
    const btnLogin = document.getElementById("onboard-tab-login");
    const pnlSignup = document.getElementById("onboard-signup-panel");
    const pnlLogin = document.getElementById("onboard-login-panel");
    const pnlForgot = document.getElementById("onboard-forgot-panel");

    hideAuthAlert();
    if (pnlForgot) pnlForgot.style.display = "none";

    if (tab === "signup") {
        btnSignup?.classList.add("active");
        btnLogin?.classList.remove("active");
        if (pnlSignup) pnlSignup.style.display = "block";
        if (pnlLogin) pnlLogin.style.display = "none";
        document.getElementById("ob-signup-name")?.focus();
    } else {
        btnLogin?.classList.add("active");
        btnSignup?.classList.remove("active");
        if (pnlLogin) pnlLogin.style.display = "block";
        if (pnlSignup) pnlSignup.style.display = "none";
        document.getElementById("ob-login-email")?.focus();
    }
}

function openForgotPasswordPanel() {
    hideAuthAlert();
    const loginEmail = document.getElementById("ob-login-email")?.value.trim() || "";
    const resetEmailInp = document.getElementById("ob-reset-email");
    if (resetEmailInp && loginEmail) {
        resetEmailInp.value = loginEmail;
    }
    const pnlLogin = document.getElementById("onboard-login-panel");
    const pnlSignup = document.getElementById("onboard-signup-panel");
    const pnlForgot = document.getElementById("onboard-forgot-panel");

    if (pnlLogin) pnlLogin.style.display = "none";
    if (pnlSignup) pnlSignup.style.display = "none";
    if (pnlForgot) pnlForgot.style.display = "block";

    document.getElementById("onboard-tab-login")?.classList.remove("active");
    document.getElementById("onboard-tab-signup")?.classList.remove("active");

    if (!loginEmail) {
        resetEmailInp?.focus();
    } else {
        document.getElementById("ob-reset-new-password")?.focus();
    }
}

async function safeParseResponse(res) {
    try {
        const text = await res.text();
        return text ? JSON.parse(text) : {};
    } catch (_) {
        return {};
    }
}

async function handlePasswordReset() {
    hideAuthAlert();
    const email = (document.getElementById("ob-reset-email")?.value || "").trim().toLowerCase();
    const newPw = (document.getElementById("ob-reset-new-password")?.value || "").trim();
    const confirmPw = (document.getElementById("ob-reset-confirm-password")?.value || "").trim();

    if (!email || !email.includes("@")) {
        showAuthAlert("Please enter a valid email address.", "error");
        return;
    }
    if (!newPw || newPw.length < 4) {
        showAuthAlert("Password must be at least 4 characters long.", "error");
        return;
    }
    if (newPw !== confirmPw) {
        showAuthAlert("Passwords do not match. Please re-enter carefully.", "error");
        return;
    }

    const btn = document.getElementById("btn-ob-reset-submit");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = "<span>Resetting Password...</span>";
    }

    try {
        const res = await fetch("/api/auth/reset-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, new_password: newPw })
        });
        const data = await safeParseResponse(res);
        if (!res.ok) {
            showAuthAlert(data.detail || (res.status >= 500 ? "Server is waking up. Please retry in 5 seconds." : "Failed to reset password."), "error");
            return;
        }

        if (data.user) {
            state.currentUser = data.user;
            localStorage.setItem("jobradar_active_user", JSON.stringify(data.user));
            const overlay = document.getElementById("auth-onboarding-screen");
            if (overlay) overlay.style.display = "none";
            showToast("🎉 Password updated successfully! You are now logged in.");
            renderUserHeader();
            fetchJobs(true);
            fetchStats();
            loadTrackerJobs();
        }
    } catch (e) {
        showAuthAlert("Error resetting password: " + e.message, "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = "<span>Reset Password &amp; Sign In &rarr;</span>";
        }
    }
}

function showAuthAlert(msg, type = "error") {
    const banner = document.getElementById("auth-alert-banner");
    if (!banner) return;
    banner.style.display = "block";
    if (type === "error") {
        banner.style.backgroundColor = "rgba(239, 68, 68, 0.12)";
        banner.style.color = "#ef4444";
        banner.style.border = "1px solid rgba(239, 68, 68, 0.3)";
    } else if (type === "warning") {
        banner.style.backgroundColor = "rgba(245, 158, 11, 0.12)";
        banner.style.color = "#f59e0b";
        banner.style.border = "1px solid rgba(245, 158, 11, 0.3)";
    } else {
        banner.style.backgroundColor = "rgba(16, 185, 129, 0.12)";
        banner.style.color = "#10b981";
        banner.style.border = "1px solid rgba(16, 185, 129, 0.3)";
    }
    banner.innerHTML = msg;
}

function hideAuthAlert() {
    const banner = document.getElementById("auth-alert-banner");
    if (banner) banner.style.display = "none";
}

function switchToLoginWithEmail(email) {
    switchOnboardTab("login");
    const el = document.getElementById("ob-login-email");
    if (el) el.value = email;
    document.getElementById("ob-login-password")?.focus();
}

function switchToSignupWithEmail(email) {
    switchOnboardTab("signup");
    const el = document.getElementById("ob-signup-email");
    if (el) el.value = email;
    document.getElementById("ob-signup-name")?.focus();
}

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === "password") {
        input.type = "text";
        btn.textContent = "🙈";
        btn.title = "Hide Password";
    } else {
        input.type = "password";
        btn.textContent = "👁️";
        btn.title = "Show Password";
    }
}

async function handleOnboardSignup() {
    hideAuthAlert();
    const nameInput = document.getElementById("ob-signup-name");
    const emailInput = document.getElementById("ob-signup-email");
    const passwordInput = document.getElementById("ob-signup-password");
    const expInput = document.getElementById("ob-signup-exp");
    const timeInput = document.getElementById("ob-signup-time");
    const roleInput = document.getElementById("ob-signup-role");

    const name = (nameInput?.value || "").trim();
    const email = (emailInput?.value || "").trim().toLowerCase();
    const password = (passwordInput?.value || "").trim();
    const exp = expInput?.value || "fresher";
    const time = timeInput?.value || "20:00";
    const role = (roleInput?.value || "").trim() || "Software Engineer";

    if (!name) {
        showAuthAlert("Please enter your full name.", "error");
        nameInput?.focus();
        return;
    }
    if (!email || !email.includes("@")) {
        showAuthAlert("Please enter a valid email address.", "error");
        emailInput?.focus();
        return;
    }
    if (!password || password.length < 4) {
        showAuthAlert("Please enter a password with at least 4 characters.", "error");
        passwordInput?.focus();
        return;
    }

    const submitBtn = document.getElementById("btn-ob-signup-submit");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = "<span>Creating Account...</span>";
    }

    try {
        const res = await fetch("/api/auth/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                email,
                password,
                experience_level: exp,
                target_role: role,
                skills: ["Python", "JavaScript", "SQL", "Git", "REST API"],
                email_time: time,
                daily_email: true
            })
        });

        const data = await safeParseResponse(res);

        if (!res.ok) {
            const detail = data.detail || (res.status >= 500 ? "Server is waking up. Please retry in 5 seconds." : "Failed to create account.");
            if (res.status === 409) {
                showAuthAlert(`${detail} <a href="javascript:void(0)" onclick="switchToLoginWithEmail('${escapeHtml(email)}')" style="color:var(--primary); font-weight:700; text-decoration:underline; margin-left:6px;">Sign In Now</a>`, "warning");
            } else {
                showAuthAlert(detail, "error");
            }
            return;
        }

        if (data.user) {
            state.currentUser = data.user;
            localStorage.setItem("jobradar_active_user", JSON.stringify(data.user));
            const overlay = document.getElementById("auth-onboarding-screen");
            if (overlay) overlay.style.display = "none";
            showToast(`Welcome ${data.user.name}! Your account is active.`);
            renderUserHeader();
            fetchJobs(true);
            fetchStats();
            loadTrackerJobs();
        }
    } catch (e) {
        showAuthAlert("Sign up failed: " + e.message, "error");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>Create Account &amp; Open Dashboard &rarr;</span>";
        }
    }
}

async function handleOnboardLogin() {
    hideAuthAlert();
    const emailInput = document.getElementById("ob-login-email");
    const passwordInput = document.getElementById("ob-login-password");
    const email = (emailInput?.value || "").trim().toLowerCase();
    const password = (passwordInput?.value || "").trim();

    if (!email || !email.includes("@")) {
        showAuthAlert("Please enter a valid email address.", "error");
        emailInput?.focus();
        return;
    }
    if (!password) {
        showAuthAlert("Please enter your password.", "error");
        passwordInput?.focus();
        return;
    }

    const submitBtn = document.getElementById("btn-ob-login-submit");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = "<span>Signing In...</span>";
    }

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await safeParseResponse(res);

        if (!res.ok) {
            const detail = data.detail || (res.status >= 500 ? "Server is waking up or deploying. Please try again in 5 seconds." : "Invalid login credentials. Please try again.");
            if (res.status === 404) {
                showAuthAlert(`${detail} <a href="javascript:void(0)" onclick="switchToSignupWithEmail('${escapeHtml(email)}')" style="color:var(--primary); font-weight:700; text-decoration:underline; margin-left:6px;">Create Account</a>`, "error");
            } else {
                showAuthAlert(detail, "error");
            }
            return;
        }

        if (data.user) {
            state.currentUser = data.user;
            // Respect and preserve schedule time across logins
            const localSavedTime = localStorage.getItem("jobradar_scheduled_time");
            if (data.user.email_time) {
                localStorage.setItem("jobradar_scheduled_time", data.user.email_time);
            } else if (localSavedTime) {
                state.currentUser.email_time = localSavedTime;
                fetch("/api/automation/schedule", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: data.user.email, email_time: localSavedTime, daily_email: true })
                }).catch(() => {});
            }
            localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
            const overlay = document.getElementById("auth-onboarding-screen");
            if (overlay) overlay.style.display = "none";
            showToast(`Welcome back, ${data.user.name || "User"}!`);
            renderUserHeader();
            loadPipelineStatus();
            fetchJobs(true);
            fetchStats();
            loadTrackerJobs();
            analyzeResumeATS();
        }
    } catch (e) {
        showAuthAlert("Network or server error during login: " + e.message, "error");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = "<span>Sign In &rarr;</span>";
        }
    }
}

function handleAuthAction() {
    if (state.currentUser && state.currentUser.email) {
        handleLogout();
    } else {
        openAuthModal("login");
    }
}

function openAuthModal(tab = "login") {
    hideAuthAlert();
    const overlay = document.getElementById("auth-onboarding-screen");
    if (overlay) {
        overlay.style.display = "flex";
        switchOnboardTab(tab);
    }
}

function handleLogout() {
    closeProfileModal();
    // Preserve the user's scheduled time so logged-out view never resets or shows a different time
    const currentScheduleTime = state.currentUser?.email_time || localStorage.getItem("jobradar_scheduled_time") || "20:00";
    state.currentUser = null;
    localStorage.removeItem("jobradar_active_user");
    localStorage.setItem("jobradar_scheduled_time", currentScheduleTime);
    renderUserHeader();
    openAuthModal("login");
    showToast("You have been signed out.");
}

// ------------------------------------------------------------------------------
// Navigation Handling
// ------------------------------------------------------------------------------
function setupNavigation() {
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", () => {
            const view = item.getAttribute("data-view");
            if (!view) return;
            switchView(view);
        });
    });
}

function toggleSidebar(forceState) {
    const sidebar = document.querySelector(".sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (!sidebar) return;
    if (typeof forceState === "boolean") {
        sidebar.classList.toggle("open", forceState);
        if (backdrop) backdrop.classList.toggle("active", forceState);
    } else {
        const isOpen = sidebar.classList.toggle("open");
        if (backdrop) backdrop.classList.toggle("active", isOpen);
    }
}

function switchView(viewName) {
    state.activeView = viewName;
    toggleSidebar(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
    document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
    const activeNav = document.getElementById(`nav-${viewName}`);
    if (activeNav) activeNav.classList.add("active");

    // Toggle view containers
    document.getElementById("view-jobs").style.display = viewName === "jobs" ? "block" : "none";
    document.getElementById("view-resume").style.display = viewName === "resume" ? "block" : "none";
    document.getElementById("view-tracker").style.display = viewName === "tracker" ? "block" : "none";
    document.getElementById("view-automation").style.display = viewName === "automation" ? "block" : "none";
    const resView = document.getElementById("view-resources");
    if (resView) resView.style.display = viewName === "resources" ? "block" : "none";
    const salView = document.getElementById("view-salary");
    if (salView) salView.style.display = viewName === "salary" ? "block" : "none";
    const intView = document.getElementById("view-interview");
    if (intView) intView.style.display = viewName === "interview" ? "block" : "none";
    const afView = document.getElementById("view-autofill");
    if (afView) afView.style.display = viewName === "autofill" ? "block" : "none";

    const headingMap = {
        jobs: "Live Opportunities",
        resume: "AI Resume & Skills Studio",
        tracker: "Application Pipeline & CRM",
        automation: "Daily Mail Agent",
        resources: "Study Vault & Preparation Hub",
        salary: "Salary Studio & Offer Negotiator",
        interview: "AI Mock Technical & HR Interview Simulator",
        autofill: "Universal Job Portal Auto-Fill Assistant"
    };
    document.getElementById("page-heading").textContent = headingMap[viewName] || "JobRadar AI";

    if (viewName === "tracker") loadTrackerJobs();
    if (viewName === "resume") analyzeResumeATS();
    if (viewName === "automation") { loadPipelineStatus(); loadEmailSettings(); }
    if (viewName === "resources") loadStudyResources();
    if (viewName === "salary") runSalaryBenchmark();
    if (viewName === "interview") initInterviewView();
    if (viewName === "autofill") initAutofillView();
}

// ------------------------------------------------------------------------------
// User Profile & Authentication Logic
// ------------------------------------------------------------------------------
async function loadUserProfile() {
    if (!state.currentUser || !state.currentUser.email) {
        renderUserHeader();
        return;
    }
    try {
        const res = await fetch(`/api/user/profile?email=${encodeURIComponent(state.currentUser.email)}`);
        if (res.ok) {
            const data = await res.json();
            if (data && data.user) {
                state.currentUser = data.user;
                localStorage.setItem("jobradar_active_user", JSON.stringify(data.user));
            }
        }
    } catch (e) {
        console.error("Error loading profile:", e);
    } finally {
        renderUserHeader();
        analyzeResumeATS();
    }
}

function renderUserHeader() {
    const u = state.currentUser;
    const userNameEl = document.getElementById("user-display-name");
    const heroNameEl = document.getElementById("hero-username");
    const userRoleEl = document.getElementById("user-display-role");
    const userAvatarEl = document.getElementById("user-avatar");
    const sidebarEmailEl = document.getElementById("sidebar-email-preview");
    const autoEmailInput = document.getElementById("auto-email-input");
    const sidebarScheduleEl = document.getElementById("sidebar-schedule-display");
    const inputScheduleTime = document.getElementById("input-schedule-time");
    const autoEmailExp = document.getElementById("auto-email-exp-filter");
    const autoEmailRoles = document.getElementById("auto-email-roles-input");
    const autoEmailLangs = document.getElementById("auto-email-languages-input");
    const autoEmailLocations = document.getElementById("auto-email-locations-input");
    const sidebarSkillsCount = document.getElementById("sidebar-skills-count");
    const chipsContainer = document.getElementById("active-skills-chips");
    const studioSkills = document.getElementById("studio-skills-list");
    const expBtn = document.getElementById("btn-toggle-exp");
    const sidebarAuthBtn = document.getElementById("btn-sidebar-auth");
    const sidebarAuthIcon = document.getElementById("btn-sidebar-auth-icon");
    const sidebarAuthText = document.getElementById("btn-sidebar-auth-text");
    const headerUserBtn = document.getElementById("header-user-btn");
    const headerUserName = document.getElementById("header-user-name");
    const headerUserAvatar = document.getElementById("header-user-avatar");

    if (u && u.email) {
        const displayName = u.name || u.email.split("@")[0];
        if (userNameEl) userNameEl.textContent = displayName;
        if (heroNameEl) heroNameEl.textContent = displayName;
        if (userAvatarEl) userAvatarEl.textContent = (displayName[0] || "U").toUpperCase();
        if (headerUserName) headerUserName.textContent = displayName;
        if (headerUserAvatar) headerUserAvatar.textContent = (displayName[0] || "U").toUpperCase();

        const expLabel = u.experience_level === "fresher" ? "🎓 Fresher" : 
                        (u.experience_level === "junior" ? "💼 Junior" : 
                        (u.experience_level === "mid" ? "🚀 Mid-Level" : "⭐ Senior"));
        if (userRoleEl) userRoleEl.textContent = `${expLabel} • ${u.target_role || "Software Eng"}`;
        if (sidebarEmailEl) sidebarEmailEl.textContent = u.email;
        if (autoEmailInput) autoEmailInput.value = u.email;

        const emailTime = u.email_time || localStorage.getItem("jobradar_scheduled_time") || "20:00";
        localStorage.setItem("jobradar_scheduled_time", emailTime);
        if (sidebarScheduleEl) sidebarScheduleEl.textContent = `Daily Digest: ${formatTimeTo12h(emailTime)}`;
        if (inputScheduleTime) inputScheduleTime.value = emailTime;
        const profileTimeInput = document.getElementById("profile-modal-time");
        if (profileTimeInput) profileTimeInput.value = emailTime;

        if (autoEmailExp) autoEmailExp.value = u.email_experience_filter || "1_year";
        if (autoEmailRoles) {
            const rolesArr = Array.isArray(u.email_roles) ? u.email_roles : (u.email_roles ? [u.email_roles] : ["Software Engineer", "Full Stack Developer", "Backend Developer", "Python Developer"]);
            autoEmailRoles.value = rolesArr.join(", ");
        }
        if (autoEmailLangs) {
            const langsArr = Array.isArray(u.email_languages) ? u.email_languages : (u.email_languages ? [u.email_languages] : ["Python", "JavaScript", "SQL"]);
            autoEmailLangs.value = langsArr.join(", ");
        }
        if (autoEmailLocations) {
            const locsArr = Array.isArray(u.email_locations) ? u.email_locations : (u.email_locations ? [u.email_locations] : []);
            autoEmailLocations.value = locsArr.join(", ");
        }

        const skills = u.skills || [];
        if (chipsContainer) chipsContainer.innerHTML = skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join("");
        if (studioSkills) {
            studioSkills.innerHTML = skills.map(s => 
                `<span class="skill-tag">${escapeHtml(s)} <button onclick="removeUserSkill('${escapeHtml(s)}')" style="background:none; border:none; color:inherit; opacity:0.75; cursor:pointer; font-size:12px; margin-left:4px;" title="Remove skill">&times;</button></span>`
            ).join("");
        }
        if (sidebarSkillsCount) sidebarSkillsCount.textContent = skills.length;
        const studioSkillsCount = document.getElementById("studio-skills-count");
        if (studioSkillsCount) studioSkillsCount.textContent = `${skills.length} Skills`;

        if (expBtn) {
            expBtn.innerHTML = u.experience_level === "fresher" 
                ? `<span>💼</span> Switch to Professional Mode` 
                : `<span>🎓</span> Switch to Fresher Mode`;
        }

        if (sidebarAuthIcon) sidebarAuthIcon.textContent = "🚪";
        if (sidebarAuthText) sidebarAuthText.textContent = "Exit";
        if (sidebarAuthBtn) {
            sidebarAuthBtn.style.color = "#ef4444";
            sidebarAuthBtn.title = "Sign Out";
        }
        if (headerUserBtn) {
            headerUserBtn.title = `Signed in as ${u.email}. Click to manage account.`;
        }

        // Show Admin Email Server Configuration only for the owner/admin
        const isAdmin = u && (u.email.toLowerCase() === 'sharanujm@gmail.com' || u.email.toLowerCase() === 'sharanujm10@gmail.com');
        const adminBtn = document.getElementById("btn-admin-config-toggle");
        if (adminBtn) adminBtn.style.display = isAdmin ? "inline-flex" : "none";
    } else {
        // Guest / Signed Out State
        const adminBtn = document.getElementById("btn-admin-config-toggle");
        if (adminBtn) adminBtn.style.display = "none";
        const adminCard = document.getElementById("card-cloud-email-settings");
        if (adminCard) adminCard.style.display = "none";
        if (userNameEl) userNameEl.textContent = "Guest";
        if (heroNameEl) heroNameEl.textContent = "Guest";
        if (userAvatarEl) userAvatarEl.textContent = "👤";
        if (headerUserName) headerUserName.textContent = "Sign In";
        if (headerUserAvatar) headerUserAvatar.textContent = "🔑";

        if (userRoleEl) userRoleEl.textContent = "Not signed in • Click to login";
        if (sidebarEmailEl) sidebarEmailEl.textContent = "guest@jobradar.ai";
        if (autoEmailInput) autoEmailInput.value = "";
        if (autoEmailLocations) autoEmailLocations.value = "";
        const preservedTime = localStorage.getItem("jobradar_scheduled_time") || "20:00";
        if (sidebarScheduleEl) sidebarScheduleEl.textContent = `Daily Digest: ${formatTimeTo12h(preservedTime)}`;
        if (inputScheduleTime) inputScheduleTime.value = preservedTime;
        const profileTimeInput = document.getElementById("profile-modal-time");
        if (profileTimeInput) profileTimeInput.value = preservedTime;
        if (sidebarSkillsCount) sidebarSkillsCount.textContent = "0";
        const studioSkillsCount = document.getElementById("studio-skills-count");
        if (studioSkillsCount) studioSkillsCount.textContent = "0 Skills";

        if (chipsContainer) chipsContainer.innerHTML = `<span class="skill-tag" style="opacity:0.6;">Sign in to save skills</span>`;
        if (studioSkills) studioSkills.innerHTML = `<span class="skill-tag" style="opacity:0.6;">Sign in to customize skills</span>`;

        if (expBtn) expBtn.innerHTML = `<span>💼</span> Switch Mode`;

        if (sidebarAuthIcon) sidebarAuthIcon.textContent = "🔑";
        if (sidebarAuthText) sidebarAuthText.textContent = "Sign In";
        if (sidebarAuthBtn) {
            sidebarAuthBtn.style.color = "var(--primary)";
            sidebarAuthBtn.title = "Click to Sign In or Create Free Account";
        }
        if (headerUserBtn) {
            headerUserBtn.title = "Click to Sign In or Create Free Account";
        }
    }
}

function formatTimeTo12h(timeStr) {
    if (!timeStr) return "8:00 PM";
    const parts = timeStr.split(":");
    let h = parseInt(parts[0], 10);
    const m = parts[1] || "00";
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return `${h}:${m} ${ampm}`;
}

async function toggleExperienceMode() {
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in to switch experience modes.");
        return;
    }
    const nextExp = state.currentUser.experience_level === "fresher" ? "mid" : "fresher";
    state.currentUser.experience_level = nextExp;

    await fetch("/api/auth/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: state.currentUser.email, experience_level: nextExp })
    });

    localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
    renderUserHeader();
    fetchJobs(true);
    showToast(`Switched to ${nextExp === 'fresher' ? 'Fresher' : 'Professional'} mode!`);
}

// ------------------------------------------------------------------------------
// Profile Settings Modal
// ------------------------------------------------------------------------------
function openProfileModal() {
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in or create an account to view and edit your profile.");
        return;
    }
    const u = state.currentUser;
    document.getElementById("profile-modal-name").value = u.name || "";
    document.getElementById("profile-modal-email").value = u.email || "";
    document.getElementById("profile-modal-password").value = "";
    document.getElementById("profile-modal-role").value = u.target_role || "Software Engineer";
    document.getElementById("profile-modal-exp").value = u.experience_level || "fresher";
    const yrsExpInp = document.getElementById("profile-modal-years-exp");
    if (yrsExpInp) yrsExpInp.value = u.years_experience || "1";
    const emailExpInp = document.getElementById("profile-modal-email-exp");
    if (emailExpInp) emailExpInp.value = u.email_experience_filter || "1_year";
    const modalEmailRoles = document.getElementById("profile-modal-email-roles");
    if (modalEmailRoles) {
        const rolesArr = Array.isArray(u.email_roles) ? u.email_roles : (u.email_roles ? [u.email_roles] : ["Software Engineer", "Full Stack Developer", "Backend Developer", "Python Developer"]);
        modalEmailRoles.value = rolesArr.join(", ");
    }
    const modalEmailLangs = document.getElementById("profile-modal-email-languages");
    if (modalEmailLangs) {
        const langsArr = Array.isArray(u.email_languages) ? u.email_languages : (u.email_languages ? [u.email_languages] : ["Python", "JavaScript", "SQL"]);
        modalEmailLangs.value = langsArr.join(", ");
    }
    const modalEmailLocs = document.getElementById("profile-modal-email-locations");
    if (modalEmailLocs) {
        const locsArr = Array.isArray(u.email_locations) ? u.email_locations : (u.email_locations ? [u.email_locations] : []);
        modalEmailLocs.value = locsArr.join(", ");
    }
    document.getElementById("profile-modal-time").value = u.email_time || "20:00";
    document.getElementById("profile-modal-daily-email").checked = u.daily_email !== 0 && u.daily_email !== false;

    // Telegram & Autofill Settings
    const tgAlerts = document.getElementById("profile-modal-telegram-alerts");
    if (tgAlerts) tgAlerts.checked = u.telegram_alerts === 1 || u.telegram_alerts === true;
    const tgToken = document.getElementById("profile-modal-telegram-token");
    if (tgToken) tgToken.value = u.telegram_bot_token || "";
    const tgChat = document.getElementById("profile-modal-telegram-chatid");
    if (tgChat) tgChat.value = u.telegram_chat_id || "";

    const phoneInp = document.getElementById("profile-modal-phone");
    if (phoneInp) phoneInp.value = u.phone || "";
    const noticeInp = document.getElementById("profile-modal-notice");
    if (noticeInp) noticeInp.value = u.notice_period || "Immediate";
    const ctcInp = document.getElementById("profile-modal-ctc");
    if (ctcInp) ctcInp.value = u.expected_ctc || "";
    const ghInp = document.getElementById("profile-modal-github");
    if (ghInp) ghInp.value = u.github_url || "";
    const liInp = document.getElementById("profile-modal-linkedin");
    if (liInp) liInp.value = u.linkedin_url || "";
    const pfInp = document.getElementById("profile-modal-portfolio");
    if (pfInp) pfInp.value = u.portfolio_url || "";
    const colInp = document.getElementById("profile-modal-college");
    if (colInp) colInp.value = u.college_name || "";

    state.profileModalSkills = [...(u.skills || [])];
    renderProfileModalSkills();

    document.getElementById("profile-modal").style.display = "flex";
}

function closeProfileModal() {
    document.getElementById("profile-modal").style.display = "none";
}

async function testTelegramAlert() {
    const token = (document.getElementById("profile-modal-telegram-token")?.value || "").trim();
    const chatId = (document.getElementById("profile-modal-telegram-chatid")?.value || "").trim();
    if (!token || !chatId) {
        showToast("⚠️ Please enter both Bot Token and Chat ID to test.");
        return;
    }
    const btn = document.getElementById("btn-test-telegram");
    const origText = btn.innerHTML;
    btn.innerHTML = "<span>⏳ Testing...</span>";
    btn.disabled = true;

    try {
        const res = await fetch("/api/telegram/test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bot_token: token, chat_id: chatId })
        });
        const data = await res.json();
        if (res.ok) {
            showToast("✅ " + data.message);
        } else {
            showToast("❌ " + (data.detail || "Telegram test failed."));
        }
    } catch (e) {
        showToast("❌ Telegram test error: " + e.message);
    } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

function renderProfileModalSkills() {
    const container = document.getElementById("profile-modal-skills-chips");
    if (!container) return;
    container.innerHTML = state.profileModalSkills.map(s => `
        <span class="skill-tag">
            ${escapeHtml(s)}
            <button onclick="removeProfileModalSkill('${escapeHtml(s)}')" style="background:none; border:none; color:inherit; opacity:0.75; cursor:pointer; font-size:12px; margin-left:4px;" title="Remove skill">&times;</button>
        </span>
    `).join("");
}

function addProfileModalSkill() {
    const inp = document.getElementById("profile-modal-new-skill");
    const skill = inp.value.trim();
    if (!skill) return;

    if (!state.profileModalSkills.includes(skill)) {
        state.profileModalSkills.push(skill);
        renderProfileModalSkills();
        inp.value = "";
    }
}

function removeProfileModalSkill(skill) {
    state.profileModalSkills = state.profileModalSkills.filter(s => s !== skill);
    renderProfileModalSkills();
}

async function saveProfileChanges() {
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in to save your profile changes.");
        return;
    }
    const name = document.getElementById("profile-modal-name").value.trim();
    const pw = document.getElementById("profile-modal-password").value.trim();
    const role = document.getElementById("profile-modal-role").value.trim();
    const exp = document.getElementById("profile-modal-exp").value;
    const time = document.getElementById("profile-modal-time").value || "20:00";
    const dailyEmail = document.getElementById("profile-modal-daily-email").checked;

    const tgAlerts = document.getElementById("profile-modal-telegram-alerts")?.checked || false;
    const tgToken = (document.getElementById("profile-modal-telegram-token")?.value || "").trim();
    const tgChat = (document.getElementById("profile-modal-telegram-chatid")?.value || "").trim();

    const phoneVal = (document.getElementById("profile-modal-phone")?.value || "").trim();
    const noticeVal = (document.getElementById("profile-modal-notice")?.value || "Immediate").trim();
    const ctcVal = (document.getElementById("profile-modal-ctc")?.value || "").trim();
    const ghVal = (document.getElementById("profile-modal-github")?.value || "").trim();
    const liVal = (document.getElementById("profile-modal-linkedin")?.value || "").trim();
    const pfVal = (document.getElementById("profile-modal-portfolio")?.value || "").trim();
    const colVal = (document.getElementById("profile-modal-college")?.value || "").trim();
    const emailExpVal = document.getElementById("profile-modal-email-exp")?.value || "1_year";
    const yrsExpVal = (document.getElementById("profile-modal-years-exp")?.value || "1").trim();
    const modalEmailRolesVal = document.getElementById("profile-modal-email-roles")?.value || "";
    const modalEmailLangsVal = document.getElementById("profile-modal-email-languages")?.value || "";
    const modalEmailLocsVal = document.getElementById("profile-modal-email-locations")?.value || "";
    const modalRolesArr = modalEmailRolesVal.split(",").map(s => s.trim()).filter(Boolean);
    const modalLangsArr = modalEmailLangsVal.split(",").map(s => s.trim()).filter(Boolean);
    const modalLocsArr = modalEmailLocsVal.split(",").map(s => s.trim()).filter(Boolean);

    showToast("Saving your profile preferences...");

    try {
        const payload = {
            email: state.currentUser.email,
            name: name || state.currentUser.name,
            target_role: role || state.currentUser.target_role,
            experience_level: exp,
            years_experience: yrsExpVal,
            email_experience_filter: emailExpVal,
            email_roles: modalRolesArr,
            email_languages: modalLangsArr,
            email_locations: modalLocsArr,
            email_time: time,
            daily_email: dailyEmail,
            telegram_alerts: tgAlerts,
            telegram_bot_token: tgToken,
            telegram_chat_id: tgChat,
            phone: phoneVal,
            notice_period: noticeVal,
            expected_ctc: ctcVal,
            github_url: ghVal,
            linkedin_url: liVal,
            portfolio_url: pfVal,
            college_name: colVal,
            skills: state.profileModalSkills
        };
        if (pw) payload.password = pw;

        const res = await fetch("/api/auth/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.user) {
            state.currentUser = data.user;
            if (time) {
                localStorage.setItem("jobradar_scheduled_time", time);
                state.currentUser.email_time = time;
            }
            localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
            renderUserHeader();
            closeProfileModal();
            loadPipelineStatus();
            fetchJobs(true);
            showToast("✨ Profile, Telegram & application details saved successfully!");
        }
    } catch (e) {
        showToast("Error saving profile: " + e.message);
    }
}

// ------------------------------------------------------------------------------
// Jobs Fetching & Filtering
// ------------------------------------------------------------------------------
async function fetchJobs(reset = false) {
    if (reset) {
        state.offset = 0;
        state.jobs = [];
    }

    const { search, experience, site, is_remote, min_score, status_filter, posted_within, skill_tag, location } = state.filters;
    const userEmail = state.currentUser?.email || "";
    const locInput = document.getElementById("filter-location")?.value.trim() || "";
    const activeLoc = (location && location !== "all") ? location : locInput;
    const params = new URLSearchParams({
        email: userEmail,
        search: search || "",
        location: activeLoc || "all",
        site: site || "all",
        experience: experience || "all",
        status_filter: status_filter || "",
        min_score: min_score || 0,
        posted_within: posted_within || "",
        skill_tag: skill_tag || "",
        limit: state.limit,
        offset: state.offset
    });
    if (is_remote !== null) params.append("is_remote", is_remote);

    const container = document.getElementById("jobs-container");
    if (reset) {
        container.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: var(--text-muted);">
                <div class="logo-icon" style="margin: 0 auto 12px; animation: spin 1.2s linear infinite;">&#10038;</div>
                <div style="font-weight: 600;">Finding matching software opportunities...</div>
            </div>
        `;
    }

    try {
        const res = await fetch(`/api/jobs?${params.toString()}`);
        const data = await res.json();

        state.jobs = reset ? data.jobs : [...state.jobs, ...data.jobs];
        state.totalJobs = data.total;

        document.getElementById("visible-job-count").textContent = `${state.jobs.length} of ${data.total} Available`;
        document.getElementById("sidebar-job-count").textContent = data.total;
        document.getElementById("stat-total-jobs").textContent = data.total;

        // Count 80%+ Super Matches
        const superCount = state.jobs.filter(j => j.match && j.match.score >= 80).length;
        document.getElementById("stat-super-matches").textContent = superCount || `${Math.min(data.total, 42)}+`;

        renderJobCards(state.jobs);

        const btnLoadMore = document.getElementById("btn-load-more");
        if (state.jobs.length >= data.total) {
            btnLoadMore.style.display = "none";
        } else {
            btnLoadMore.style.display = "inline-block";
        }
    } catch (e) {
        console.error("Error fetching jobs:", e);
        showToast("Error fetching jobs. Check connection.");
    }
}

function loadMoreJobs() {
    state.offset += state.limit;
    fetchJobs(false);
}

function debounceFetchJobs() {
    clearTimeout(state.debounceTimer);
    state.debounceTimer = setTimeout(() => {
        state.filters.search = document.getElementById("filter-search").value.trim();
        const locInp = document.getElementById("filter-location");
        if (locInp) {
            state.filters.location = locInp.value.trim() || "all";
        }
        fetchJobs(true);
    }, 350);
}

function setLocationFilter(el) {
    const val = el.getAttribute("data-value") || "all";
    const locInp = document.getElementById("filter-location");

    if (val === "all") {
        // Clear all specific locations, activate "All Cities"
        document.querySelectorAll('[data-filter="location"]').forEach(p => p.classList.remove("active"));
        document.querySelectorAll('.suggestion-chip').forEach(c => c.classList.remove("active"));
        el.classList.add("active");
        state.filters.location = "all";
        if (locInp) locInp.value = "";
    } else {
        // Deactivate "All Cities"
        const allLocPill = document.querySelector('[data-filter="location"][data-value="all"]');
        if (allLocPill) allLocPill.classList.remove("active");

        // Toggle this pill
        el.classList.toggle("active");

        // Gather all currently active locations
        const activePills = Array.from(document.querySelectorAll('[data-filter="location"].active'))
            .filter(p => p.getAttribute("data-value") !== "all");

        const activeVals = activePills.map(p => p.getAttribute("data-value"));

        // Sync suggestion chips
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            const chipText = chip.textContent.toLowerCase();
            const isActive = activeVals.some(v => chipText.includes(v.toLowerCase()));
            if (isActive) chip.classList.add("active");
            else chip.classList.remove("active");
        });

        if (activeVals.length === 0) {
            if (allLocPill) allLocPill.classList.add("active");
            state.filters.location = "all";
            if (locInp) locInp.value = "";
        } else {
            state.filters.location = activeVals.join(",");
            if (locInp) {
                locInp.value = activePills.map(p => p.textContent.replace(/^📍\s*|🌐\s*/, '').trim()).join(", ");
            }
        }
    }
    fetchJobs(true);
}

function applyLocationSuggestion(locName) {
    const lower = locName.toLowerCase();
    let targetPill = null;
    document.querySelectorAll('[data-filter="location"]').forEach(p => {
        const val = (p.getAttribute("data-value") || "").toLowerCase();
        if (val === lower || (lower === "bangalore" && val === "bangalore") || (lower === "delhi ncr" && val === "delhi") || (lower === "remote" && val === "remote")) {
            targetPill = p;
        }
    });
    if (targetPill) {
        setLocationFilter(targetPill);
    } else {
        const locInp = document.getElementById("filter-location");
        if (locInp) {
            const current = locInp.value.trim();
            locInp.value = current ? `${current}, ${locName}` : locName;
            state.filters.location = locInp.value;
            fetchJobs(true);
        }
    }
}

function setFilter(el) {
    const filterType = el.getAttribute("data-filter");
    const value = el.getAttribute("data-value");

    if (value === "all") {
        // Clear all specific selections, activate "All"
        document.querySelectorAll(`[data-filter="${filterType}"]`).forEach(p => p.classList.remove("active"));
        el.classList.add("active");
        state.filters[filterType] = "all";
    } else {
        // Deactivate the "All" pill
        const allPill = document.querySelector(`[data-filter="${filterType}"][data-value="all"]`);
        if (allPill) allPill.classList.remove("active");

        // Toggle this specific pill
        el.classList.toggle("active");

        // Gather all currently active values
        const activePills = Array.from(document.querySelectorAll(`[data-filter="${filterType}"].active`))
            .filter(p => p.getAttribute("data-value") !== "all");

        if (activePills.length === 0) {
            // Nothing selected: fallback to "All"
            if (allPill) allPill.classList.add("active");
            state.filters[filterType] = "all";
        } else {
            state.filters[filterType] = activePills.map(p => p.getAttribute("data-value")).join(",");
        }
    }
    fetchJobs(true);
}

function setDateFilter(el) {
    const val = el.getAttribute("data-value") || "";
    if (el.classList.contains("active") && val !== "") {
        document.querySelectorAll('[data-filter="posted_within"]').forEach(p => p.classList.remove("active"));
        const anytimePill = document.querySelector('[data-filter="posted_within"][data-value=""]');
        if (anytimePill) anytimePill.classList.add("active");
        state.filters.posted_within = "";
    } else {
        document.querySelectorAll('[data-filter="posted_within"]').forEach(p => p.classList.remove("active"));
        el.classList.add("active");
        state.filters.posted_within = val;
    }
    fetchJobs(true);
}

function setSkillTagFilter(el) {
    const val = el.getAttribute("data-value") || "";

    if (val === "") {
        // Clear all specific skills, activate "All Tech"
        document.querySelectorAll('[data-filter="skill_tag"]').forEach(p => p.classList.remove("active"));
        el.classList.add("active");
        state.filters.skill_tag = "";
    } else {
        // Deactivate "All Tech"
        const allTechPill = document.querySelector('[data-filter="skill_tag"][data-value=""]');
        if (allTechPill) allTechPill.classList.remove("active");

        // Toggle this skill
        el.classList.toggle("active");

        const activePills = Array.from(document.querySelectorAll('[data-filter="skill_tag"].active'))
            .filter(p => p.getAttribute("data-value") !== "");

        if (activePills.length === 0) {
            if (allTechPill) allTechPill.classList.add("active");
            state.filters.skill_tag = "";
        } else {
            state.filters.skill_tag = activePills.map(p => p.getAttribute("data-value")).join(",");
        }
    }
    fetchJobs(true);
}

function toggleRemotePill(el) {
    el.classList.toggle("active");
    state.filters.is_remote = el.classList.contains("active") ? true : null;
    fetchJobs(true);
}

function toggleScorePill(el) {
    el.classList.toggle("active");
    state.filters.min_score = el.classList.contains("active") ? 80 : 0;
    fetchJobs(true);
}

// ------------------------------------------------------------------------------
// Render Job Cards on Main Feed
// ------------------------------------------------------------------------------
function renderJobCards(jobs) {
    const container = document.getElementById("jobs-container");
    if (!jobs || jobs.length === 0) {
        container.innerHTML = `
            <div style="background:var(--bg-surface); border:1px dashed var(--border-default); border-radius:16px; padding:48px 24px; text-align:center; grid-column:1/-1;">
                <div style="font-size:36px; margin-bottom:12px;">&#128269;</div>
                <h3 style="font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">No Matching Roles Found</h3>
                <p style="font-size:14px; color:var(--text-secondary); max-width:400px; margin:0 auto 16px;">
                    Try clearing your search query or switching to "All Sources" in the filter pills above.
                </p>
                <button class="btn btn-secondary btn-sm" onclick="clearFilters()">Reset Filters</button>
            </div>
        `;
        return;
    }

    container.innerHTML = jobs.map(job => createJobCardHTML(job)).join("");
}

function createJobCardHTML(job) {
    const title = escapeHtml(job.title || "Software Engineer");
    const company = escapeHtml(job.company || "Tech Company");
    const location = escapeHtml(job.location || "India");
    const site = (job.site || "Web").toLowerCase();
    const siteName = escapeHtml(job.site || "Web");
    const isRemote = job.is_remote || location.toLowerCase().includes("remote");
    const salary = job.salary ? escapeHtml(job.salary) : "";
    const datePosted = escapeHtml(job.date_posted || "Recently");
    const applyUrl = job.job_url || "#";
    const snippet = escapeHtml(job.snippet || "");
    const initial = company.charAt(0).toUpperCase() || "C";

    // Match info
    const match = job.match || { score: 65, label: "Good Match", badge_class: "badge-sky", matched_skills: [], missing_skills: [] };
    const score = match.score;
    const badgeClass = match.badge_class || "badge-indigo";

    // Saved/Applied state
    const isSaved = job.user_status === "saved";
    const isApplied = job.user_status === "applied";

    // Matched skills HTML
    const matchedPills = (match.matched_skills || []).map(s => 
        `<span class="skill-matched">&#10003; ${escapeHtml(s)}</span>`
    ).join("");

    const missingPills = (match.missing_skills || []).map(s => 
        `<span class="skill-missing">+ ${escapeHtml(s)}</span>`
    ).join("");

    return `
    <div class="job-card" id="card-${job.id}" onclick="openJobDetailModal('${job.id}')" title="Click to view full job details">
        <div class="job-card-top">
            <div class="job-main-info">
                <div class="company-logo-avatar">${initial}</div>
                <div class="job-title-group">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px; flex-wrap:wrap;">
                        <span class="badge badge-${site}">${siteName}</span>
                        ${job.exp_badge ? (() => {
                            const cat = job.exp_badge.category;
                            const styleStr = cat === 'senior' ? 'background:rgba(168,85,247,0.14); color:#c084fc; border:1px solid rgba(168,85,247,0.35);' :
                                            (cat === 'mid' ? 'background:rgba(99,102,241,0.14); color:#818cf8; border:1px solid rgba(99,102,241,0.35);' :
                                            (cat === 'fresher' ? 'background:rgba(16,185,129,0.14); color:#34d399; border:1px solid rgba(16,185,129,0.35);' :
                                            'background:rgba(59,130,246,0.14); color:#60a5fa; border:1px solid rgba(59,130,246,0.35);'));
                            return `<span class="badge" style="${styleStr}">${escapeHtml(job.exp_badge.label || '🎯 1-2 Yrs Exp')}</span>`;
                        })() : ''}
                        ${isRemote ? `<span class="badge" style="background:#ecfdf5; color:#065f46;">🌐 Remote</span>` : ''}
                        ${salary ? `<span class="badge" style="background:#fef3c7; color:#92400e;">💰 ${salary}</span>` : ''}
                    </div>
                    <h3>${title}</h3>
                    <div class="company-meta-line">
                        <span class="company-name">${company}</span>
                        <span class="meta-dot">&bull;</span>
                        <span>&#128205; ${location}</span>
                        <span class="meta-dot">&bull;</span>
                        <span>&#128197; ${datePosted}</span>
                    </div>
                </div>
            </div>

            <!-- Match Score Badge -->
            <div class="match-score-pill ${badgeClass}">
                <span>&#9889;</span>
                <span>${score}% Match</span>
            </div>
        </div>

        <!-- Skills Breakdown Line -->
        <div class="match-skills-breakdown">
            <div class="skills-row">
                <span class="skills-label">Skill Fit:</span>
                ${matchedPills || `<span style="color:var(--text-muted); font-size:11px;">Matches general role requirements</span>`}
                ${missingPills}
            </div>
        </div>

        ${snippet ? `<div class="job-snippet-text">${snippet}</div>` : ''}

        <!-- Card Actions -->
        <div class="job-card-actions" onclick="event.stopPropagation()">
            <div class="card-action-group">
                <button class="btn btn-sm ${isSaved ? 'btn-primary' : 'btn-secondary'}" onclick="event.stopPropagation(); toggleSaveJob('${job.id}')">
                    <span>${isSaved ? '★ Saved' : '☆ Save'}</span>
                </button>
                <button class="btn btn-sm ${isApplied ? 'btn-emerald' : 'btn-secondary'}" onclick="event.stopPropagation(); toggleAppliedJob('${job.id}')">
                    <span>${isApplied ? '✓ Applied' : 'Mark Applied'}</span>
                </button>
                <select class="kanban-stage-select" style="max-width:110px;" onclick="event.stopPropagation()" onchange="event.stopPropagation(); setJobStageFromCard('${job.id}', this.value)">
                    <option value="" disabled selected>Stage...</option>
                    <option value="saved">📌 Wishlist</option>
                    <option value="applied">🚀 Applied</option>
                    <option value="interviewing">🎯 Interviewing</option>
                    <option value="offered">🏆 Offer</option>
                </select>
                <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); openPitchModal('${job.id}', 'cover')" title="Generate AI Cover Letter & LinkedIn Note">
                    <span>⚡ Pitch</span>
                </button>
                <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); openAutofillForJob('${job.id}', '${(job.company || '').replace(/'/g, "\\'")}', '${(job.title || '').replace(/'/g, "\\'")}')" title="1-Click Application Auto-Fill for Greenhouse, Lever & Workday">
                    <span>⚡ Auto-Fill</span>
                </button>
                <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); launchInterviewForJob('${job.id}')" title="Practice AI Mock Technical & HR Interview for this role">
                    <span>🎯 Interview</span>
                </button>
            </div>

            <div class="card-action-group" style="display:flex; gap:6px;">
                <button class="btn btn-sm" style="background:#0284c7; color:#fff; font-weight:700; border:none; box-shadow:0 2px 4px rgba(2,132,199,0.25);" onclick="event.stopPropagation(); openReferralModal('${job.id}')" title="Find Seniors & Alumni on LinkedIn and get an Employee Referral">
                    <span>🤝 Get Referral</span>
                </button>
                <a href="${applyUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm" onclick="event.stopPropagation()">
                    <span>Apply Now &rarr;</span>
                </a>
            </div>
        </div>
    </div>
    `;
}

// User Actions: Save & Applied from main feed
async function toggleSaveJob(jobId) {
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in or create an account to bookmark jobs.");
        return;
    }
    try {
        const res = await fetch("/api/jobs/toggle-save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_email: state.currentUser.email, job_id: jobId, status: "saved" })
        });
        const data = await res.json();
        const j = state.jobs.find(x => x.id === jobId);
        if (j) j.user_status = data.user_status;
        renderJobCards(state.jobs);
        fetchStats();
        showToast(data.user_status === "saved" ? "Job bookmarked in your Wishlist!" : "Job removed from bookmarks.");
    } catch (e) {
        console.error(e);
    }
}

async function toggleAppliedJob(jobId) {
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in or create an account to track applications.");
        return;
    }
    try {
        const j = state.jobs.find(x => x.id === jobId);
        const nextStatus = j && j.user_status === "applied" ? "" : "applied";
        const res = await fetch("/api/jobs/set-status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_email: state.currentUser.email, job_id: jobId, status: nextStatus })
        });
        const data = await res.json();
        if (j) j.user_status = data.user_status;
        renderJobCards(state.jobs);
        fetchStats();
        showToast(data.user_status === "applied" ? "Marked as Applied! Added to Application Pipeline." : "Removed from applied.");
    } catch (e) {
        console.error(e);
    }
}

async function setJobStageFromCard(jobId, stage) {
    if (!stage) return;
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in or create an account to update job stages.");
        return;
    }
    try {
        await fetch("/api/tracker/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_email: state.currentUser.email, job_id: jobId, status: stage })
        });
        const j = state.jobs.find(x => x.id === jobId);
        if (j) j.user_status = stage;
        renderJobCards(state.jobs);
        fetchStats();
        showToast(`Moved to ${stage.toUpperCase()} stage in your pipeline!`);
    } catch (e) {
        console.error(e);
    }
}

// ------------------------------------------------------------------------------
// Application Tracker (Kanban Pipeline & Notes)
// ------------------------------------------------------------------------------
async function loadTrackerJobs() {
    const colSaved = document.getElementById("kanban-saved-list");
    const colReferral = document.getElementById("kanban-referral-list");
    const colApplied = document.getElementById("kanban-applied-list");
    const colInterview = document.getElementById("kanban-interviewing-list");
    const colOffered = document.getElementById("kanban-offered-list");

    if (colSaved) colSaved.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Loading...</div>`;
    if (colReferral) colReferral.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Loading...</div>`;
    if (colApplied) colApplied.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Loading...</div>`;
    if (colInterview) colInterview.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Loading...</div>`;
    if (colOffered) colOffered.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Loading...</div>`;

    try {
        const userEmail = state.currentUser?.email || "";
        const res = await fetch(`/api/tracker?email=${encodeURIComponent(userEmail)}`);
        const data = await res.json();
        const items = data.items || [];
        const stats = data.stats || {};
        state.trackerItems = items;

        // Update stats strip
        if (document.getElementById("tracker-stat-saved")) document.getElementById("tracker-stat-saved").textContent = stats.saved || 0;
        if (document.getElementById("tracker-stat-referrals")) document.getElementById("tracker-stat-referrals").textContent = stats.referrals || 0;
        if (document.getElementById("tracker-stat-applied")) document.getElementById("tracker-stat-applied").textContent = stats.applied || 0;
        if (document.getElementById("tracker-stat-interviewing")) document.getElementById("tracker-stat-interviewing").textContent = stats.interviewing || 0;
        if (document.getElementById("tracker-stat-offered")) document.getElementById("tracker-stat-offered").textContent = stats.offered || 0;

        // Group into pipeline stages
        const savedList = items.filter(x => x.status === "saved");
        const referralList = items.filter(x => x.status === "referral_requested" || x.status === "referral");
        const appliedList = items.filter(x => x.status === "applied");
        const interviewList = items.filter(x => x.status === "interviewing");
        const offeredList = items.filter(x => x.status === "offered" || x.status === "offer");

        if (document.getElementById("tracker-saved-count")) document.getElementById("tracker-saved-count").textContent = savedList.length;
        if (document.getElementById("tracker-referral-count")) document.getElementById("tracker-referral-count").textContent = referralList.length;
        if (document.getElementById("tracker-applied-count")) document.getElementById("tracker-applied-count").textContent = appliedList.length;
        if (document.getElementById("tracker-interviewing-count")) document.getElementById("tracker-interviewing-count").textContent = interviewList.length;
        if (document.getElementById("tracker-offered-count")) document.getElementById("tracker-offered-count").textContent = offeredList.length;
        if (document.getElementById("sidebar-applied-count")) document.getElementById("sidebar-applied-count").textContent = appliedList.length;

        if (colSaved) {
            colSaved.innerHTML = savedList.length 
                ? savedList.map(item => createKanbanCard(item)).join("") 
                : `<div style="padding:24px; text-align:center; color:var(--text-muted); font-size:12px;">No saved roles yet. Bookmark jobs to review later!</div>`;
        }

        if (colReferral) {
            colReferral.innerHTML = referralList.length 
                ? referralList.map(item => createKanbanCard(item)).join("") 
                : `<div style="padding:24px; text-align:center; color:var(--text-muted); font-size:12px;">No referrals requested yet. Click "Get Referral" on any job!</div>`;
        }

        if (colApplied) {
            colApplied.innerHTML = appliedList.length 
                ? appliedList.map(item => createKanbanCard(item)).join("") 
                : `<div style="padding:24px; text-align:center; color:var(--text-muted); font-size:12px;">No applications sent yet. Apply to matching roles!</div>`;
        }

        if (colInterview) {
            colInterview.innerHTML = interviewList.length 
                ? interviewList.map(item => createKanbanCard(item)).join("") 
                : `<div style="padding:24px; text-align:center; color:var(--text-muted); font-size:12px;">Move cards here when recruiters reach out!</div>`;
        }

        if (colOffered) {
            colOffered.innerHTML = offeredList.length 
                ? offeredList.map(item => createKanbanCard(item)).join("") 
                : `<div style="padding:24px; text-align:center; color:var(--text-muted); font-size:12px;">Offers received will appear here! 🎉</div>`;
        }

    } catch (e) {
        console.error("Tracker load error:", e);
    }
}

function createKanbanCard(item) {
    const site = (item.site || "web").toLowerCase();
    const notesHtml = item.notes ? `
        <div class="kanban-card-notes-preview">
            <strong>Notes:</strong> ${escapeHtml(item.notes)}
        </div>
    ` : "";

    const dateMeta = item.applied_date ? `Applied: ${item.applied_date}` : `Updated: ${item.updated_at ? item.updated_at.split(' ')[0] : 'Recently'}`;

    return `
    <div class="kanban-card" id="kcard-${item.job_id}">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div class="kanban-card-title">${escapeHtml(item.title)}</div>
            <button onclick="removeTrackerJob('${item.job_id}')" title="Remove from Tracker" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:14px; padding:2px 4px;">&times;</button>
        </div>
        <div class="kanban-card-company">${escapeHtml(item.company)} &bull; ${escapeHtml(item.location)}</div>
        
        <div class="kanban-card-meta">
            <span class="badge badge-${site}">${escapeHtml(item.site)}</span>
            <span>📅 ${dateMeta}</span>
        </div>

        ${notesHtml}

        <div class="kanban-card-actions">
            <select class="kanban-stage-select" onchange="changeTrackerStage('${item.job_id}', this.value)">
                <option value="saved" ${item.status === 'saved' ? 'selected' : ''}>📌 Wishlist</option>
                <option value="referral_requested" ${item.status === 'referral_requested' || item.status === 'referral' ? 'selected' : ''}>🤝 Referral</option>
                <option value="applied" ${item.status === 'applied' ? 'selected' : ''}>🚀 Applied</option>
                <option value="interviewing" ${item.status === 'interviewing' ? 'selected' : ''}>🎯 Interview</option>
                <option value="offered" ${item.status === 'offered' || item.status === 'offer' ? 'selected' : ''}>🏆 Offer</option>
            </select>

            <button class="btn btn-secondary btn-sm" style="padding:4px 7px; font-size:11px; background:#eff6ff; color:#1d4ed8; border-color:#bfdbfe;" onclick="openReferralModal('${item.job_id}')" title="LinkedIn Senior Referral Hub">
                🤝 Referral
            </button>

            <button class="btn btn-secondary btn-sm" style="padding:4px 7px; font-size:11px;" onclick="openPitchModal('${item.job_id}', 'cover')" title="Generate AI Cover Letter">
                ⚡ Pitch
            </button>

            <button class="btn btn-secondary btn-sm" style="padding:4px 7px; font-size:11px;" onclick="openPitchModal('${item.job_id}', 'interview')" title="Interview Questions & Prep">
                🎯 Prep
            </button>

            <button class="btn btn-secondary btn-sm" style="padding:4px 7px; font-size:11px;" onclick="openNoteModal('${item.job_id}')" title="Edit Interview Notes">
                📝 Notes
            </button>

            <a href="${item.job_url || '#'}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm" style="padding:4px 8px; font-size:11px;">
                Apply ↗
            </a>
        </div>
    </div>
    `;
}

async function changeTrackerStage(jobId, newStage) {
    try {
        await fetch("/api/tracker/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_email: state.currentUser.email, job_id: jobId, status: newStage })
        });
        showToast(`Moved to ${newStage.toUpperCase()} stage!`);
        loadTrackerJobs();
        fetchStats();
    } catch (e) {
        showToast("Error moving stage: " + e.message);
    }
}

async function removeTrackerJob(jobId) {
    try {
        await fetch("/api/tracker/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_email: state.currentUser.email, job_id: jobId })
        });
        showToast("Removed from application tracker.");
        loadTrackerJobs();
        fetchStats();
    } catch (e) {
        showToast("Error deleting: " + e.message);
    }
}

// Notes Modal Logic
function openNoteModal(jobId, maybeTitle, maybeCompany, maybeNote) {
    const item = (state.trackerItems || []).find(x => x.job_id === jobId) || 
                 (state.jobs || []).find(x => x.id === jobId) || {};

    const title = maybeTitle || item.title || "Job Application";
    const company = maybeCompany || item.company || "Target Company";
    const currentNote = maybeNote !== undefined ? maybeNote : (item.notes || "");

    document.getElementById("note-modal-job-id").value = jobId;
    document.getElementById("note-modal-job-title").textContent = title;
    document.getElementById("note-modal-job-company").textContent = company;
    document.getElementById("note-modal-text").value = currentNote;
    document.getElementById("note-modal").style.display = "flex";
}

function closeNoteModal() {
    document.getElementById("note-modal").style.display = "none";
}

async function saveJobNote() {
    const jobId = document.getElementById("note-modal-job-id").value;
    const notes = document.getElementById("note-modal-text").value.trim();

    try {
        await fetch("/api/tracker/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                user_email: state.currentUser.email, 
                job_id: jobId, 
                status: "applied", // retains or keeps status in backend
                notes: notes 
            })
        });
        closeNoteModal();
        showToast("Application notes updated!");
        loadTrackerJobs();
    } catch (e) {
        showToast("Error saving note: " + e.message);
    }
}

function exportTrackerToCSV() {
    const items = state.trackerItems || [];
    if (!items.length) {
        return showToast("⚠️ No tracked applications to export. Bookmark or apply to jobs first!");
    }

    const headers = ["Job Title", "Company", "Location", "Platform", "Pipeline Stage", "Applied Date", "Notes", "Job URL"];
    const rows = items.map(item => {
        const title = (item.title || "").replace(/"/g, '""');
        const company = (item.company || "").replace(/"/g, '""');
        const location = (item.location || "").replace(/"/g, '""');
        const site = (item.site || "Web").replace(/"/g, '""');
        const status = (item.status || "saved").replace(/"/g, '""');
        const appliedDate = (item.applied_date || "").replace(/"/g, '""');
        const notes = (item.notes || "").replace(/"/g, '""');
        const url = (item.job_url || "").replace(/"/g, '""');
        return `"${title}","${company}","${location}","${site}","${status}","${appliedDate}","${notes}","${url}"`;
    });

    const csvContent = [headers.map(h => `"${h}"`).join(","), ...rows].join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const filename = `JobRadar_Applications_${new Date().toISOString().slice(0, 10)}.csv`;
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    showToast(`📥 Exported ${items.length} job applications to ${filename}!`);
}

// ------------------------------------------------------------------------------
// Resume ATS Analysis & Bullet Enhancer
// ------------------------------------------------------------------------------
async function analyzeResumeATS() {
    if (!state.currentUser || !state.currentUser.email) return;
    try {
        const res = await fetch("/api/resume/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: state.currentUser.email })
        });
        const data = await res.json();
        if (data.analysis) {
            const score = data.analysis.ats_score || 0;
            const scoreEl = document.getElementById("ats-score-display");
            if (scoreEl) scoreEl.textContent = score;

            const circle = document.getElementById("ats-circle-container");
            if (circle) {
                if (score >= 80) {
                    circle.style.borderColor = "#10b981";
                    circle.style.boxShadow = "0 0 26px rgba(16, 185, 129, 0.4)";
                } else if (score >= 60) {
                    circle.style.borderColor = "#6366f1";
                    circle.style.boxShadow = "0 0 26px rgba(99, 102, 241, 0.4)";
                } else {
                    circle.style.borderColor = "#f59e0b";
                    circle.style.boxShadow = "0 0 26px rgba(245, 158, 11, 0.4)";
                }
            }

            // Update Active Resume Badge & Filename
            const badgeEl = document.getElementById("active-resume-badge");
            const textEl = document.getElementById("active-resume-text");
            if (badgeEl && textEl) {
                if (data.filename) {
                    badgeEl.style.display = "inline-flex";
                    textEl.textContent = `Active Resume: ${data.filename} (${(data.skills || []).length} Skills Extracted)`;
                } else if (data.skills && data.skills.length > 0) {
                    badgeEl.style.display = "inline-flex";
                    textEl.textContent = `Active Profile: ${data.skills.length} Technical Skills Active`;
                } else {
                    badgeEl.style.display = "none";
                }
            }

            // Populate Dynamic AI Suggestions
            const sugGrid = document.getElementById("ai-suggestions-grid");
            if (sugGrid && data.analysis.suggestions) {
                if (data.analysis.suggestions.length === 0) {
                    sugGrid.innerHTML = `
                        <div style="background:var(--bg-surface); border:1px solid var(--border-default); border-radius:var(--radius-lg); padding:20px; text-align:center; grid-column:1/-1;">
                            <div style="font-size:24px; margin-bottom:6px;">🎉</div>
                            <div style="font-weight:700; color:var(--text-primary); font-size:15px;">High-Caliber ATS Alignment!</div>
                            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Your profile contains strong technical keywords, clear quantifiable metrics, and high-impact action verbs.</div>
                        </div>
                    `;
                } else {
                    sugGrid.innerHTML = data.analysis.suggestions.map(s => {
                        const icon = s.type === "skills" ? "⚡" : (s.type === "metrics" ? "📊" : (s.type === "verbs" ? "🚀" : (s.type === "projects" ? "💻" : "💡")));
                        const badgeClass = s.type === "skills" ? "badge-indigo" : (s.type === "metrics" ? "badge-emerald" : "badge-sky");
                        return `
                        <div style="background:var(--bg-surface); border:1px solid var(--border-default); border-radius:var(--radius-lg); padding:18px; display:flex; flex-direction:column; gap:10px; transition:transform 0.2s ease, box-shadow 0.2s ease;" onmouseenter="this.style.transform='translateY(-2px)'" onmouseleave="this.style.transform='translateY(0)'">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div style="display:flex; align-items:center; gap:8px; font-weight:700; color:var(--text-primary); font-size:14px;">
                                    <span>${icon}</span>
                                    <span>${escapeHtml(s.title)}</span>
                                </div>
                                <span class="badge ${badgeClass}">${escapeHtml(s.type || "AI Tip")}</span>
                            </div>
                            <div style="font-size:13px; color:var(--text-secondary); line-height:1.5;">
                                ${escapeHtml(s.desc)}
                            </div>
                        </div>
                        `;
                    }).join("");
                }
            }
        }
    } catch (e) {
        console.error("Error analyzing resume:", e);
    }
}

async function enhanceBulletAction() {
    const raw = document.getElementById("raw-bullet-input").value.trim();
    if (!raw) return showToast("Please type a bullet point to enhance");

    showToast("AI is optimizing your bullet point...");
    try {
        const res = await fetch("/api/resume/enhance-bullet", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bullet: raw })
        });
        const data = await res.json();
        if (data.result && data.result.enhanced) {
            document.getElementById("enhanced-bullet-text").textContent = data.result.enhanced;
            document.getElementById("enhanced-bullet-result").style.display = "block";
            showToast("✨ Bullet point enhanced into STAR format!");
        }
    } catch (e) {
        showToast("Error enhancing bullet: " + e.message);
    }
}

function copyEnhancedBullet() {
    const text = document.getElementById("enhanced-bullet-text").textContent;
    navigator.clipboard.writeText(text);
    showToast("Copied optimized bullet to clipboard!");
}

async function addUserSkill() {
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in or create an account to customize your skills.");
        return;
    }
    const inp = document.getElementById("add-skill-input");
    const skill = inp.value.trim();
    if (!skill) return;

    if (!state.currentUser.skills) state.currentUser.skills = [];
    if (!state.currentUser.skills.includes(skill)) {
        state.currentUser.skills.push(skill);
        await saveCurrentSkills();
        inp.value = "";
        renderUserHeader();
        await analyzeResumeATS();
        fetchJobs(true);
        showToast(`Added ${skill} to your skills profile!`);
    }
}

async function removeUserSkill(skill) {
    if (!state.currentUser || !state.currentUser.email) return;
    if (!state.currentUser.skills) state.currentUser.skills = [];
    state.currentUser.skills = state.currentUser.skills.filter(s => s !== skill);
    await saveCurrentSkills();
    renderUserHeader();
    await analyzeResumeATS();
    fetchJobs(true);
}

async function saveCurrentSkills() {
    await fetch("/api/auth/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            email: state.currentUser.email,
            skills: state.currentUser.skills
        })
    });
    localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
}

// Resume Upload & Presets
function setupDropZone() {
    const dz = document.getElementById("resume-drop-zone-main");
    if (!dz) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dz.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); }, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dz.addEventListener(eventName, () => dz.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dz.addEventListener(eventName, () => dz.classList.remove('dragover'), false);
    });

    dz.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) handleResumeUpload(files[0]);
    });
}

async function handleResumeUpload(file) {
    if (!file) return;
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in or create an account to upload your resume.");
        return;
    }
    const statusEl = document.getElementById("resume-upload-status");
    if (statusEl) {
        statusEl.style.display = "block";
        statusEl.textContent = `⏳ Uploading and analyzing ${file.name}...`;
    }
    showToast(`Parsing resume: ${file.name}...`);

    const formData = new FormData();
    formData.append("email", state.currentUser.email);
    formData.append("file", file);

    try {
        const res = await fetch("/api/user/resume/upload", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "ok") {
            state.currentUser = data.user;
            localStorage.setItem("jobradar_active_user", JSON.stringify(data.user));
            renderUserHeader();
            await analyzeResumeATS();
            if (statusEl) {
                statusEl.textContent = `✅ Successfully uploaded ${file.name} (${data.extracted_skills.length} skills detected)`;
            }
            showToast(`🎉 Detected ${data.extracted_skills.length} skills from your resume! Tailoring your jobs...`);
            fetchJobs(true);
        } else {
            if (statusEl) {
                statusEl.textContent = `❌ Upload failed: ${data.detail || "Error"}`;
            }
            showToast("Failed to parse resume: " + (data.detail || "Error"));
        }
    } catch (e) {
        if (statusEl) {
            statusEl.textContent = `❌ Upload error: ${e.message}`;
        }
        showToast("Error uploading resume: " + e.message);
    }
}

async function applyPreset(presetType) {
    if (!state.currentUser || !state.currentUser.email) {
        openAuthModal("login");
        showToast("Please sign in or create an account to customize resume presets.");
        return;
    }
    const presets = {
        fresher: {
            skills: ["Python", "JavaScript", "SQL", "HTML", "CSS", "Git", "Data Structures", "Algorithms"],
            exp: "fresher"
        },
        fullstack: {
            skills: ["React", "Node.js", "TypeScript", "FastAPI", "PostgreSQL", "Docker", "AWS", "Git"],
            exp: "mid"
        },
        python_ai: {
            skills: ["Python", "FastAPI", "Docker", "PostgreSQL", "Machine Learning", "NLP", "Pandas", "SQL"],
            exp: "mid"
        }
    };

    const chosen = presets[presetType];
    if (!chosen) return;

    const res = await fetch("/api/user/resume/paste", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
            email: state.currentUser.email,
            text: chosen.skills.join(" "),
            experience_level: chosen.exp
        })
    });

    const data = await res.json();
    if (data.user) {
        state.currentUser = data.user;
        localStorage.setItem("jobradar_active_user", JSON.stringify(data.user));
        renderUserHeader();
        analyzeResumeATS();
        showToast(`Applied ${presetType.toUpperCase()} preset with ${chosen.skills.length} skills!`);
        fetchJobs(true);
    }
}

// ------------------------------------------------------------------------------
// Automation & Daily Mail Agent
// ------------------------------------------------------------------------------
function handleScheduleTimeChange(timeVal) {
    saveCustomScheduleTime();
}

function handleAutoEmailInput(emailVal) {
    const clean = (emailVal || "").trim();
    if (clean) {
        localStorage.setItem("jobradar_user_email", clean);
    }
}

async function loadPipelineStatus() {
    try {
        const activeEmail = state.currentUser?.email || document.getElementById("auto-email-input")?.value.trim() || localStorage.getItem("jobradar_user_email") || "";
        const url = activeEmail ? `/api/automation/pipeline-status?email=${encodeURIComponent(activeEmail)}` : "/api/automation/pipeline-status";
        const res = await fetch(url);
        const data = await res.json();
        if (data.status === "ok") {
            const nextScrapeEl = document.getElementById("pipeline-next-scrape");
            const nextDigestEl = document.getElementById("pipeline-next-digest");
            const engineStatusEl = document.getElementById("pipeline-engine-status");
            const lastScrapedEl = document.getElementById("pipeline-last-scraped");
            const autoToggle = document.getElementById("pipeline-auto-scrape-toggle");
            const leadSelect = document.getElementById("pipeline-lead-time");
            const badgeEl = document.getElementById("pipeline-status-badge");
            const inputScheduleTime = document.getElementById("input-schedule-time");

            if (leadSelect) leadSelect.value = data.lead_minutes || 30;
            if (autoToggle) autoToggle.checked = data.auto_scrape_enabled;

            // Respect the user's scheduled time:
            // 1) state.currentUser?.email_time
            // 2) localStorage.getItem("jobradar_scheduled_time")
            // 3) data.next_scheduled_digest
            const effectiveTime = state.currentUser?.email_time || localStorage.getItem("jobradar_scheduled_time") || data.next_scheduled_digest || "20:00";
            
            localStorage.setItem("jobradar_scheduled_time", effectiveTime);
            if (state.currentUser && !state.currentUser.email_time) {
                state.currentUser.email_time = effectiveTime;
                localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
            }

            if (nextDigestEl) nextDigestEl.textContent = `${effectiveTime} (${formatTimeTo12h(effectiveTime)})`;
            if (inputScheduleTime) {
                inputScheduleTime.value = effectiveTime;
            }
            const profileTimeInput = document.getElementById("profile-modal-time");
            if (profileTimeInput) {
                profileTimeInput.value = effectiveTime;
            }

            // Sync preview scrape time with effectiveTime
            const leadMin = parseInt(leadSelect?.value || "30", 10);
            try {
                const parts = effectiveTime.split(":");
                const total = (parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10) - leadMin + 1440) % 1440;
                const h = String(Math.floor(total / 60)).padStart(2, "0");
                const m = String(total % 60).padStart(2, "0");
                const scrapeStr = `${h}:${m}`;
                if (nextScrapeEl) nextScrapeEl.textContent = `${scrapeStr} (${formatTimeTo12h(scrapeStr)})`;
            } catch (e) {}

            if (engineStatusEl) {
                if (data.is_running) {
                    engineStatusEl.innerHTML = `<span style="color:#f59e0b;">⚡ Crawling 6 Platforms...</span>`;
                } else {
                    engineStatusEl.innerHTML = `<span style="color:#10b981;">● Active &bull; Ready</span>`;
                }
            }

            if (lastScrapedEl) {
                lastScrapedEl.textContent = data.last_run ? `Last run: ${data.last_run}` : "Last run: Scheduled";
            }

            if (badgeEl) {
                badgeEl.style.display = data.auto_scrape_enabled ? "inline-flex" : "none";
            }

            // Sync sidebar schedule badge
            const sideSchedule = document.getElementById("sidebar-schedule-display");
            if (sideSchedule) {
                sideSchedule.textContent = `Daily Digest: ${formatTimeTo12h(effectiveTime)}`;
            }
        }
    } catch (e) {
        console.error("Failed to load pipeline status:", e);
    }
}

function syncPipelineTimesPreview() {
    const timeVal = document.getElementById("input-schedule-time")?.value || "20:00";
    const leadMin = parseInt(document.getElementById("pipeline-lead-time")?.value || "30", 10);
    
    // Calculate preview scrape time
    try {
        const parts = timeVal.split(":");
        const total = (parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10) - leadMin + 1440) % 1440;
        const h = String(Math.floor(total / 60)).padStart(2, "0");
        const m = String(total % 60).padStart(2, "0");
        const scrapeStr = `${h}:${m}`;

        const nextScrapeEl = document.getElementById("pipeline-next-scrape");
        const nextDigestEl = document.getElementById("pipeline-next-digest");
        if (nextScrapeEl) nextScrapeEl.textContent = `${scrapeStr} (${formatTimeTo12h(scrapeStr)})`;
        if (nextDigestEl) nextDigestEl.textContent = `${timeVal} (${formatTimeTo12h(timeVal)})`;
    } catch (e) {}
}

async function updatePipelineLeadTime() {
    const leadMin = parseInt(document.getElementById("pipeline-lead-time")?.value || "30", 10);
    const autoToggle = document.getElementById("pipeline-auto-scrape-toggle")?.checked ?? true;
    syncPipelineTimesPreview();

    try {
        const res = await fetch("/api/automation/auto-scrape-settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: autoToggle, lead_minutes: leadMin })
        });
        const data = await res.json();
        if (data.status === "ok") {
            showToast(`⚙️ Pre-scrape scheduled ${leadMin} mins before daily digest!`);
            loadPipelineStatus();
        }
    } catch (e) {
        showToast("Error updating lead time: " + e.message);
    }
}

async function toggleAutoScrapePipeline() {
    const autoToggle = document.getElementById("pipeline-auto-scrape-toggle")?.checked ?? true;
    const leadMin = parseInt(document.getElementById("pipeline-lead-time")?.value || "30", 10);

    try {
        const res = await fetch("/api/automation/auto-scrape-settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: autoToggle, lead_minutes: leadMin })
        });
        const data = await res.json();
        if (data.status === "ok") {
            showToast(autoToggle ? "✅ Pre-digest automated scraping ENABLED!" : "⏸️ Pre-digest automated scraping PAUSED.");
            loadPipelineStatus();
        }
    } catch (e) {
        showToast("Error toggling pipeline: " + e.message);
    }
}

async function saveCustomScheduleTime() {
    const timeVal = document.getElementById("input-schedule-time")?.value || "20:00";
    const emailVal = state.currentUser?.email || document.getElementById("auto-email-input")?.value.trim() || localStorage.getItem("jobradar_user_email") || "";

    if (!emailVal) {
        openAuthModal("signup");
        showToast("Please enter your email address to schedule daily job digests.");
        return;
    }

    localStorage.setItem("jobradar_scheduled_time", timeVal);
    localStorage.setItem("jobradar_user_email", emailVal);
    if (state.currentUser) {
        state.currentUser.email_time = timeVal;
        state.currentUser.email = emailVal;
        localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
    }

    const sideSchedule = document.getElementById("sidebar-schedule-display");
    if (sideSchedule) sideSchedule.textContent = `Daily Digest: ${formatTimeTo12h(timeVal)}`;
    const nextDigestEl = document.getElementById("pipeline-next-digest");
    if (nextDigestEl) nextDigestEl.textContent = `${timeVal} (${formatTimeTo12h(timeVal)})`;
    const profileTimeInput = document.getElementById("profile-modal-time");
    if (profileTimeInput) profileTimeInput.value = timeVal;

    showToast(`Setting daily email alert for ${emailVal} at ${formatTimeTo12h(timeVal)}...`);

    try {
        const res = await fetch("/api/automation/schedule", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: emailVal, email_time: timeVal, daily_email: true })
        });
        const data = await res.json();
        if (data.status === "ok") {
            if (data.user && state.currentUser) {
                state.currentUser = { ...state.currentUser, ...data.user };
                localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
            }
            if (data.triggered_now) {
                showToast(`🚀 Scheduled time reached! 100-Job Digest is being emailed right now to ${emailVal}!`, 5000);
            } else {
                showToast(`⏰ 100-Job digest scheduled for ${formatTimeTo12h(timeVal)} daily to ${emailVal}!`);
            }
            await loadPipelineStatus();
        } else {
            showToast(`⚠️ ${data.message || "Could not update schedule"}`);
        }
    } catch (e) {
        showToast("Error updating schedule: " + e.message);
    }
}

function addQuickRoleToEmail(roleName) {
    const inp = document.getElementById("auto-email-roles-input");
    if (!inp) return;
    const current = inp.value.split(",").map(s => s.trim()).filter(Boolean);
    if (!current.some(c => c.toLowerCase() === roleName.toLowerCase())) {
        current.push(roleName);
        inp.value = current.join(", ");
    }
}

function addQuickLangToEmail(langName) {
    const inp = document.getElementById("auto-email-languages-input");
    if (!inp) return;
    const current = inp.value.split(",").map(s => s.trim()).filter(Boolean);
    if (!current.some(c => c.toLowerCase() === langName.toLowerCase())) {
        current.push(langName);
        inp.value = current.join(", ");
    }
}

function addQuickLocationToEmail(locName) {
    const inp = document.getElementById("auto-email-locations-input");
    if (!inp) return;
    const current = inp.value.split(",").map(s => s.trim()).filter(Boolean);
    if (!current.some(c => c.toLowerCase() === locName.toLowerCase())) {
        current.push(locName);
        inp.value = current.join(", ");
    }
}

function addQuickLocationToProfile(locName) {
    const inp = document.getElementById("profile-modal-email-locations");
    if (!inp) return;
    const current = inp.value.split(",").map(s => s.trim()).filter(Boolean);
    if (!current.some(c => c.toLowerCase() === locName.toLowerCase())) {
        current.push(locName);
        inp.value = current.join(", ");
    }
}

async function saveEmailDigestFilters() {
    if (!state.currentUser || !state.currentUser.email) return;
    const expVal = document.getElementById("auto-email-exp-filter")?.value || "1_year";
    const rolesRaw = document.getElementById("auto-email-roles-input")?.value || "";
    const langsRaw = document.getElementById("auto-email-languages-input")?.value || "";
    const locsRaw = document.getElementById("auto-email-locations-input")?.value || "";

    const rolesArr = rolesRaw.split(",").map(s => s.trim()).filter(Boolean);
    const langsArr = langsRaw.split(",").map(s => s.trim()).filter(Boolean);
    const locsArr = locsRaw.split(",").map(s => s.trim()).filter(Boolean);

    state.currentUser.email_experience_filter = expVal;
    state.currentUser.email_roles = rolesArr;
    state.currentUser.email_languages = langsArr;
    state.currentUser.email_locations = locsArr;

    try {
        await fetch("/api/auth/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: state.currentUser.email,
                email_experience_filter: expVal,
                email_roles: rolesArr,
                email_languages: langsArr,
                email_locations: locsArr
            })
        });
        localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
        showToast("✅ Email digest filters saved! Only matching experience, roles, tech stack, and locations will be emailed.");
    } catch (e) {
        showToast("Error saving email filters: " + e.message);
    }
}

async function saveEmailExpFilter(filterVal) {
    if (!state.currentUser || !state.currentUser.email) return;
    state.currentUser.email_experience_filter = filterVal;
    try {
        await fetch("/api/auth/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: state.currentUser.email,
                email_experience_filter: filterVal
            })
        });
        localStorage.setItem("jobradar_active_user", JSON.stringify(state.currentUser));
        const labels = {
            "1_year": "1 Year Experience Roles Only (0-2 Yrs)",
            "fresher": "Freshers & Interns Only (0-1 Yrs)",
            "junior": "Junior Developer (1-2 Yrs)",
            "mid": "Mid-Level Roles (2-5 Yrs)",
            "senior": "Senior & Lead Roles (5+ Yrs)",
            "all": "All Experience Levels"
        };
        showToast(`✅ Email Filter Saved: ${labels[filterVal] || filterVal}! (App continues displaying all jobs)`);
    } catch (e) {
        showToast("Error updating email filter: " + e.message);
    }
}

async function sendEmailDigestNow() {
    const targetEmail = state.currentUser?.email || document.getElementById("auto-email-input")?.value.trim() || localStorage.getItem("jobradar_user_email") || "";
    if (!targetEmail) {
        openAuthModal("signup");
        showToast("Please enter your email address to receive job digests.");
        return;
    }

    const filter = state.currentUser?.email_experience_filter || document.getElementById("auto-email-exp-filter")?.value || "1_year";
    const rolesRaw = document.getElementById("auto-email-roles-input")?.value || "";
    const langsRaw = document.getElementById("auto-email-languages-input")?.value || "";
    const roles = rolesRaw ? rolesRaw.split(",").map(s => s.trim()).filter(Boolean) : (state.currentUser?.email_roles || ["Software Engineer", "Python Developer"]);
    const langs = langsRaw ? langsRaw.split(",").map(s => s.trim()).filter(Boolean) : (state.currentUser?.email_languages || ["Python", "JavaScript"]);

    const diag = document.getElementById("email-delivery-diag");
    if (diag) {
        diag.style.display = "block";
        diag.style.background = "rgba(79, 70, 229, 0.1)";
        diag.style.border = "1px solid rgba(79, 70, 229, 0.3)";
        diag.style.color = "var(--text-primary)";
        diag.innerHTML = `⏳ Building 100-job curated digest and delivering to <strong>${targetEmail}</strong>...`;
    }
    showToast(`Dispatching 100-job curated digest to ${targetEmail}...`);

    try {
        const res = await fetch("/api/automation/send-digest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                user_email: targetEmail,
                experience_filter: filter,
                roles: roles,
                languages: langs
            })
        });
        const data = await res.json();
        if (data.status === "ok") {
            showToast(`📬 ${data.message}`);
            if (diag) {
                diag.style.background = "rgba(16, 185, 129, 0.1)";
                diag.style.border = "1px solid rgba(16, 185, 129, 0.3)";
                diag.innerHTML = `✅ <strong>Delivery Success!</strong> ${data.message}`;
            }
        } else {
            showToast(`⚠️ ${data.message}`);
            if (diag) {
                diag.style.background = "rgba(239, 68, 68, 0.1)";
                diag.style.border = "1px solid rgba(239, 68, 68, 0.3)";
                diag.innerHTML = `❌ <strong>Delivery Blocked / Failed:</strong><br>${data.message}`;
            }
        }
    } catch (e) {
        showToast("Error sending email: " + e.message);
        if (diag) {
            diag.style.display = "block";
            diag.style.background = "rgba(239, 68, 68, 0.1)";
            diag.innerHTML = `❌ <strong>Network Error:</strong> ${e.message}`;
        }
    }
}

function toggleAdminEmailConfig() {
    const card = document.getElementById("card-cloud-email-settings");
    if (!card) return;
    const isHidden = card.style.display === "none" || !card.style.display;
    card.style.display = isHidden ? "block" : "none";
    if (isHidden) {
        loadEmailSettings();
        card.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

async function loadEmailSettings() {
    try {
        const res = await fetch("/api/automation/email-settings");
        const data = await res.json();
        if (data.status === "ok") {
            const badge = document.getElementById("delivery-method-badge");
            const resendInp = document.getElementById("input-resend-key");
            const brevoInp = document.getElementById("input-brevo-key");
            const senderInp = document.getElementById("input-sender-email");

            if (senderInp && data.sender_email) senderInp.value = data.sender_email;
            if (resendInp && data.has_resend && !resendInp.value) {
                resendInp.placeholder = data.resend_api_key;
            }
            if (brevoInp && data.has_brevo && !brevoInp.value) {
                brevoInp.placeholder = data.brevo_api_key;
            }

            if (badge) {
                if (data.active_method === "resend") {
                    badge.innerHTML = `<span class="status-dot" style="background:#10b981;"></span> Resend HTTPS Active (Port 443)`;
                    badge.style.color = "#10b981";
                } else if (data.active_method === "brevo") {
                    badge.innerHTML = `<span class="status-dot" style="background:#10b981;"></span> Brevo HTTPS Active (Port 443)`;
                    badge.style.color = "#10b981";
                } else if (data.active_method === "smtp") {
                    badge.innerHTML = `<span class="status-dot" style="background:#3b82f6;"></span> Gmail SMTP (Port 465)`;
                    badge.style.color = "#60a5fa";
                } else {
                    badge.innerHTML = `<span class="status-dot" style="background:#ef4444;"></span> Not Configured`;
                    badge.style.color = "#f87171";
                }
            }
        }
    } catch (e) {
        console.warn("Could not load email settings:", e);
    }
}

async function saveEmailDeliverySettings() {
    const resendKey = document.getElementById("input-resend-key")?.value.trim();
    const brevoKey = document.getElementById("input-brevo-key")?.value.trim();
    const senderEmail = document.getElementById("input-sender-email")?.value.trim();
    const senderPass = document.getElementById("input-sender-password")?.value.trim();

    const payload = {};
    if (resendKey) payload.resend_api_key = resendKey;
    if (brevoKey) payload.brevo_api_key = brevoKey;
    if (senderEmail) payload.sender_email = senderEmail;
    if (senderPass) payload.sender_app_password = senderPass;

    try {
        const res = await fetch("/api/automation/email-settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === "ok") {
            showToast("💾 Email delivery credentials saved!");
            await loadEmailSettings();
        } else {
            showToast("⚠️ " + (data.message || "Failed to save settings"));
        }
    } catch (e) {
        showToast("Error saving email settings: " + e.message);
    }
}

async function testEmailDelivery() {
    const targetEmail = state.currentUser?.email || document.getElementById("auto-email-input")?.value.trim() || localStorage.getItem("jobradar_user_email") || "";
    if (!targetEmail) {
        showToast("⚠️ Please enter a recipient email address in the box above first!");
        return;
    }
    const diag = document.getElementById("email-delivery-diag");
    if (diag) {
        diag.style.display = "block";
        diag.style.background = "rgba(79, 70, 229, 0.1)";
        diag.style.border = "1px solid rgba(79, 70, 229, 0.3)";
        diag.style.color = "var(--text-primary)";
        diag.innerHTML = `⏳ Testing email delivery to <strong>${targetEmail}</strong>...`;
    }
    showToast(`Dispatching test digest to ${targetEmail}...`);

    try {
        const res = await fetch("/api/automation/test-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ recipient: targetEmail })
        });
        const data = await res.json();
        if (data.status === "ok") {
            showToast(`📬 ${data.message}`);
            if (diag) {
                diag.style.background = "rgba(16, 185, 129, 0.1)";
                diag.style.border = "1px solid rgba(16, 185, 129, 0.3)";
                diag.innerHTML = `✅ <strong>Delivery Success!</strong> ${data.message}`;
            }
        } else {
            showToast(`❌ ${data.message}`);
            if (diag) {
                diag.style.background = "rgba(239, 68, 68, 0.1)";
                diag.style.border = "1px solid rgba(239, 68, 68, 0.3)";
                diag.innerHTML = `❌ <strong>Delivery Blocked / Failed:</strong><br>${data.message}`;
            }
        }
    } catch (e) {
        showToast("Error: " + e.message);
        if (diag) {
            diag.style.display = "block";
            diag.style.background = "rgba(239, 68, 68, 0.1)";
            diag.innerHTML = `❌ <strong>Network Error:</strong> ${e.message}`;
        }
    }
}

async function triggerLiveScrape() {
    const btnHeader = document.getElementById("btn-scan");
    const spinnerHeader = document.getElementById("scan-spinner");
    const scanTextHeader = document.getElementById("scan-text");

    const btnCard = document.getElementById("btn-pipeline-scan");
    const spinnerCard = document.getElementById("pipeline-scan-spinner");
    const scanTextCard = document.getElementById("pipeline-scan-text");

    if (btnHeader) btnHeader.disabled = true;
    if (spinnerHeader) spinnerHeader.style.animation = "spin 1s linear infinite";
    if (scanTextHeader) scanTextHeader.textContent = "Scanning India Roles...";

    if (btnCard) btnCard.disabled = true;
    if (spinnerCard) spinnerCard.style.animation = "spin 1s linear infinite";
    if (scanTextCard) scanTextCard.textContent = "Crawling LinkedIn, Indeed, Internshala, Naukri & Google...";

    showToast("🔎 Multi-source India scraper launched in background!");

    try {
        const res = await fetch("/api/automation/scan-now", { method: "POST" });
        const data = await res.json();
        
        let checks = 0;
        const interval = setInterval(async () => {
            checks++;
            const sRes = await fetch("/api/automation/scan-status");
            const sData = await sRes.json();
            if (!sData.is_running || checks > 15) {
                clearInterval(interval);
                if (btnHeader) {
                    btnHeader.disabled = false;
                    spinnerHeader.style.animation = "";
                    scanTextHeader.textContent = "Scan for Jobs";
                }
                if (btnCard) {
                    btnCard.disabled = false;
                    spinnerCard.style.animation = "";
                    scanTextCard.textContent = "Run Scraper Now (Collect Fresh India Roles)";
                }
                showToast("✨ Scraping complete! " + (sData.last_result || "Updated database."));
                fetchStats();
                fetchJobs(true);
                loadPipelineStatus();
            }
        }, 5000);
    } catch (e) {
        if (btnHeader) {
            btnHeader.disabled = false;
            spinnerHeader.style.animation = "";
            scanTextHeader.textContent = "Scan for Jobs";
        }
        if (btnCard) {
            btnCard.disabled = false;
            spinnerCard.style.animation = "";
            scanTextCard.textContent = "Run Scraper Now (Collect Fresh India Roles)";
        }
    }
}

async function fetchStats() {
    try {
        const userEmail = state.currentUser?.email || "";
        const res = await fetch(`/api/stats?email=${encodeURIComponent(userEmail)}`);
        const data = await res.json();
        if (data.stats) {
            document.getElementById("stat-total-jobs").textContent = data.stats.total;
            document.getElementById("stat-saved-jobs").textContent = data.stats.saved || 0;
            document.getElementById("stat-applied-jobs").textContent = data.stats.applied || 0;
            document.getElementById("sidebar-applied-count").textContent = data.stats.applied || 0;
        }
    } catch (e) {}
}

// ------------------------------------------------------------------------------
// AI Career Assistant Chatbot
// ------------------------------------------------------------------------------
function toggleChatbot() {
    const win = document.getElementById("chatbot-window");
    if (!win) return;
    win.classList.toggle("open");
    if (win.classList.contains("open")) {
        document.getElementById("chat-input-field")?.focus();
    }
}

function sendQuickPrompt(promptText) {
    const win = document.getElementById("chatbot-window");
    if (win && !win.classList.contains("open")) {
        win.classList.add("open");
    }
    document.getElementById("chat-input-field").value = promptText;
    sendChatMessage();
}

function formatChatbotMarkdown(md) {
    if (!md) return "";
    let html = escapeHtml(md);
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Italics
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
    // Headers
    html = html.replace(/^### (.*$)/gim, "<h4 style='margin:6px 0; font-size:14px; color:var(--primary-600);'>$1</h4>");
    html = html.replace(/^## (.*$)/gim, "<h3 style='margin:8px 0; font-size:15px; color:var(--primary-700);'>$1</h3>");
    // Code
    html = html.replace(/`(.*?)`/g, "<code style='background:#f1f5f9; padding:2px 4px; border-radius:4px; font-family:monospace;'>$1</code>");
    // Bullet lists
    html = html.replace(/^\s*-\s+(.*$)/gim, "<li style='margin-left:14px;'>$1</li>");
    html = html.replace(/^\s*\d+\.\s+(.*$)/gim, "<li style='margin-left:14px;'>$1</li>");
    // Line breaks
    html = html.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");
    return html;
}

async function sendChatMessage() {
    const input = document.getElementById("chat-input-field");
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    appendChatBubble(text, "user");

    const container = document.getElementById("chat-messages-container");
    const tempBubble = document.createElement("div");
    tempBubble.className = "chat-bubble bot";
    tempBubble.innerHTML = "<em>Career Assistant is thinking...</em>";
    container.appendChild(tempBubble);
    container.scrollTop = container.scrollHeight;

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, email: state.currentUser.email })
        });
        const data = await res.json();
        if (data.status === "ok" && data.data) {
            tempBubble.innerHTML = formatChatbotMarkdown(data.data.reply);
        } else {
            tempBubble.textContent = data.detail || "I am here to help!";
        }
    } catch (e) {
        tempBubble.textContent = "Sorry, I could not connect right now: " + e.message;
    }
    container.scrollTop = container.scrollHeight;
}

function appendChatBubble(text, sender) {
    const container = document.getElementById("chat-messages-container");
    const b = document.createElement("div");
    b.className = `chat-bubble ${sender}`;
    b.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
    container.appendChild(b);
    container.scrollTop = container.scrollHeight;
}

// ------------------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------------------
function showToast(message) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `<span>&#10038;</span> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

function clearFilters() {
    const searchInp = document.getElementById("filter-search");
    if (searchInp) searchInp.value = "";
    const locInp = document.getElementById("filter-location");
    if (locInp) locInp.value = "";
    state.filters = {
        search: "",
        location: "all",
        experience: "all",
        site: "all",
        is_remote: null,
        min_score: 0,
        status_filter: "",
        posted_within: "",
        skill_tag: ""
    };
    document.querySelectorAll(".pill").forEach(p => {
        if (p.getAttribute("data-value") === "all" || (!p.hasAttribute("data-value") && p.getAttribute("data-action") === "all")) {
            p.classList.add("active");
        } else {
            p.classList.remove("active");
        }
    });
    document.querySelectorAll(".suggestion-chip").forEach(chip => chip.classList.remove("active"));
    fetchJobs(true);
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ------------------------------------------------------------------------------
// 1-Click AI Outreach Pitch & Interview Prep Modal
// ------------------------------------------------------------------------------
async function openPitchModal(jobId, initialTab = 'cover') {
    const modal = document.getElementById("pitch-modal");
    if (modal) modal.style.display = "flex";
    switchPitchTab(initialTab);

    // Instant feedback with job info
    const cardJob = state.jobs.find(x => x.id === jobId);
    if (cardJob) {
        document.getElementById("pitch-modal-role").textContent = cardJob.title;
        document.getElementById("pitch-modal-company").textContent = cardJob.company;
    } else {
        document.getElementById("pitch-modal-role").textContent = "Role Opportunity";
        document.getElementById("pitch-modal-company").textContent = "Target Company";
    }

    document.getElementById("cover-letter-text").value = "✨ AI is crafting your tailored Cover Letter based on your resume skills...";
    document.getElementById("linkedin-msg-text").value = "💬 AI is crafting a high-impact LinkedIn connection note...";
    document.getElementById("cold-email-subject").value = "Generating subject line...";
    document.getElementById("cold-email-body").value = "✉️ AI is crafting your cold email pitch...";

    const techContainer = document.getElementById("interview-tech-qs");
    if (techContainer) techContainer.innerHTML = "<div style='color:var(--text-muted); padding:10px;'>Predicting role-specific technical questions...</div>";

    try {
        const res = await fetch("/api/ai/generate-pitch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ job_id: jobId, user_email: state.currentUser.email })
        });

        if (!res.ok) {
            return showToast("Failed to generate outreach pitch");
        }

        const data = await res.json();
        const p = data.pitch;
        const job = data.job;

        document.getElementById("pitch-modal-role").textContent = job.title;
        document.getElementById("pitch-modal-company").textContent = job.company;
        document.getElementById("cover-letter-text").value = p.cover_letter || "";
        document.getElementById("linkedin-msg-text").value = p.linkedin_message || "";
        document.getElementById("cold-email-subject").value = p.cold_email_subject || "";
        document.getElementById("cold-email-body").value = p.cold_email_body || "";

        // Render Interview Prep Questions
        const prep = p.interview_prep || {};
        const behavContainer = document.getElementById("interview-behavioral-qs");
        const patternsContainer = document.getElementById("interview-coding-patterns");

        if (techContainer) {
            techContainer.innerHTML = (prep.technical_questions || []).map((t, idx) => `
                <div style="background:#f8fafc; border:1px solid var(--border-default); border-radius:10px; padding:12px;">
                    <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">
                        ${idx + 1}. [${escapeHtml(t.topic)}] ${escapeHtml(t.q)}
                    </div>
                    <div style="font-size:12px; color:var(--text-secondary); line-height:1.4;">
                        💡 <strong>Key Hint / Answer Points:</strong> ${escapeHtml(t.tip)}
                    </div>
                </div>
            `).join("");
        }

        if (behavContainer) {
            behavContainer.innerHTML = (prep.behavioral_questions || []).map((b, idx) => `
                <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; padding:12px;">
                    <div style="font-weight:700; font-size:13px; color:#166534; margin-bottom:4px;">
                        ${idx + 1}. ${escapeHtml(b.q)}
                    </div>
                    <div style="font-size:12px; color:#14532d; line-height:1.4;">
                        🌟 <strong>STAR Approach:</strong> ${escapeHtml(b.tip)}
                    </div>
                </div>
            `).join("");
        }

        if (patternsContainer) {
            patternsContainer.innerHTML = (prep.coding_patterns || []).map(cp => `
                <span class="badge" style="background:#fef3c7; color:#92400e; font-size:12px; padding:4px 10px;">
                    ⚡ ${escapeHtml(cp)}
                </span>
            `).join("");
        }

    } catch (e) {
        showToast("Error generating pitch: " + e.message);
    }
}

// Click outside or press ESC to close any modal
document.addEventListener("click", (e) => {
    ['profile-modal', 'note-modal', 'pitch-modal', 'job-detail-modal', 'auth-onboarding-screen', 'resource-reader-modal', 'add-resource-modal', 'referral-modal'].forEach(mId => {
        const m = document.getElementById(mId);
        if (m && e.target === m) {
            m.style.display = "none";
        }
    });
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        ['profile-modal', 'note-modal', 'pitch-modal', 'job-detail-modal', 'auth-onboarding-screen', 'resource-reader-modal', 'add-resource-modal', 'referral-modal'].forEach(mId => {
            const m = document.getElementById(mId);
            if (m) m.style.display = "none";
        });
    }

    // Ctrl + K or Cmd + K to quick-focus Job Search
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        if (state.activeView !== "jobs") switchView("jobs");
        const s = document.getElementById("filter-search");
        if (s) {
            s.focus();
            s.select();
            showToast("🔍 Quick search activated (Ctrl+K)");
        }
    }
});

function closePitchModal() {
    document.getElementById("pitch-modal").style.display = "none";
}

// ------------------------------------------------------------------------------
// Job Details Modal Logic
// ------------------------------------------------------------------------------
function openJobDetailModal(jobId) {
    state.selectedDetailJobId = jobId;
    const j = (state.jobs || []).find(x => x.id === jobId) || 
              (state.trackerItems || []).find(x => x.job_id === jobId) || {};

    const modal = document.getElementById("job-detail-modal");
    if (!modal) return;

    const title = j.title || "Software Engineer";
    const company = j.company || "Tech Company";
    const location = j.location || "India";
    const site = (j.site || "Web").toLowerCase();
    const siteName = j.site || "Web";
    const isRemote = j.is_remote || (location.toLowerCase().includes("remote"));
    const salary = j.salary || "";
    const datePosted = j.date_posted || (j.applied_date ? `Applied: ${j.applied_date}` : "Recently");
    const applyUrl = j.job_url || "#";
    const description = j.description || j.snippet || "Full job description available on application portal.";

    const match = j.match || { score: 70, matched_skills: [], missing_skills: [] };
    const score = match.score || 70;

    document.getElementById("jd-title").textContent = title;
    document.getElementById("jd-company").textContent = company;
    document.getElementById("jd-location").textContent = location;
    document.getElementById("jd-date").textContent = datePosted;
    document.getElementById("jd-description").textContent = description;

    // Badges
    const siteBadge = document.getElementById("jd-site-badge");
    siteBadge.className = `badge badge-${site}`;
    siteBadge.textContent = siteName;

    const remoteBadge = document.getElementById("jd-remote-badge");
    remoteBadge.style.display = isRemote ? "inline-flex" : "none";

    const salaryBadge = document.getElementById("jd-salary-badge");
    if (salary) {
        salaryBadge.style.display = "inline-flex";
        salaryBadge.textContent = `💰 ${salary}`;
    } else {
        salaryBadge.style.display = "none";
    }

    const matchBadge = document.getElementById("jd-match-badge");
    matchBadge.innerHTML = `<span>⚡</span> <span>${score}% Match</span>`;

    // Skills breakdown
    const skillsContainer = document.getElementById("jd-skills-breakdown");
    const matchedPills = (match.matched_skills || []).map(s => 
        `<span class="skill-matched">&#10003; ${escapeHtml(s)}</span>`
    ).join("");
    const missingPills = (match.missing_skills || []).map(s => 
        `<span class="skill-missing">+ ${escapeHtml(s)}</span>`
    ).join("");
    skillsContainer.innerHTML = (matchedPills || `<span style="font-size:12px; color:var(--text-muted);">Matches core profile expectations</span>`) + missingPills;

    // Save button state
    const isSaved = j.user_status === "saved";
    document.getElementById("jd-btn-save").innerHTML = `<span>${isSaved ? '★ Saved' : '☆ Save'}</span>`;

    // Apply URL
    const applyBtn = document.getElementById("jd-btn-apply");
    applyBtn.href = applyUrl;

    // Load 1-Click Application Autofill snippets dynamically
    loadJobAutofillSnippets(jobId);

    modal.style.display = "flex";
}

async function loadJobAutofillSnippets(jobId) {
    const whyHire = document.getElementById("autofill-preview-why-hire");
    const whyComp = document.getElementById("autofill-preview-why-comp");
    if (whyHire) whyHire.textContent = "Loading tailored answer...";
    if (whyComp) whyComp.textContent = "Loading tailored answer...";

    try {
        const res = await fetch(`/api/autofill/${jobId}?email=${encodeURIComponent(state.currentUser.email)}`);
        const data = await res.json();
        if (data.status === "ok" && data.snippets) {
            state.currentAutofill = data.snippets;
            if (whyHire) whyHire.textContent = data.snippets.why_hire_me;
            if (whyComp) whyComp.textContent = data.snippets.why_this_company;
        }
    } catch (e) {
        console.error("Autofill fetch error:", e);
    }
}

function copyAutofillSnippet(field) {
    if (!state.currentAutofill) {
        showToast("Autofill snippets still loading...");
        return;
    }
    const val = state.currentAutofill[field];
    if (val) {
        navigator.clipboard.writeText(val);
        showToast("📋 Copied answer snippet to clipboard!");
    }
}

function copyFullAutofillProfile() {
    if (!state.currentAutofill) {
        showToast("Autofill snippets still loading...");
        return;
    }
    const a = state.currentAutofill;
    const fullText = `Full Name: ${a.name}
Email: ${a.email}
Phone: ${a.phone || 'N/A'}
Experience: ${a.years_experience}
Notice Period: ${a.notice_period}
Expected CTC: ${a.expected_ctc || 'Competitive'}
GitHub: ${a.github_url || 'N/A'}
LinkedIn: ${a.linkedin_url || 'N/A'}
Portfolio: ${a.portfolio_url || 'N/A'}

--- Summary of Background ---
${a.experience_summary}

--- Why Hire Me ---
${a.why_hire_me}

--- Why This Role & Company ---
${a.why_this_company}`;

    navigator.clipboard.writeText(fullText);
    showToast("📋 Copied complete application profile to clipboard!");
}

async function sendJobToTelegram() {
    if (!state.selectedDetailJobId) return;
    const btn = document.getElementById("jd-btn-telegram");
    const origText = btn.innerHTML;
    btn.innerHTML = "<span>⏳ Sending...</span>";
    btn.disabled = true;

    try {
        const res = await fetch("/api/telegram/send-job-alert", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: state.currentUser.email,
                job_id: state.selectedDetailJobId
            })
        });
        const data = await res.json();
        if (res.ok) {
            showToast("✈️ Alert sent directly to your phone via Telegram!");
        } else {
            showToast("❌ " + (data.detail || "Failed to send alert. Make sure Telegram is set up in Profile!"));
        }
    } catch (e) {
        showToast("❌ Error: " + e.message);
    } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}

function downloadPitchTxt(type = 'cover') {
    let text = "";
    const role = (document.getElementById("pitch-modal-role").textContent || "Job").replace(/\s+/g, '_');
    const comp = (document.getElementById("pitch-modal-company").textContent || "Company").replace(/\s+/g, '_');
    let filename = `JobRadar_${comp}_${role}.txt`;

    if (type === 'cover') {
        text = document.getElementById("cover-letter-text").value;
        filename = `Cover_Letter_${comp}_${role}.txt`;
    } else if (type === 'interview') {
        const tech = document.getElementById("interview-tech-qs")?.innerText || "";
        const hr = document.getElementById("interview-behavioral-qs")?.innerText || "";
        text = `=== JOBRADAR AI INTERVIEW PREPARATION GUIDE ===\nTarget Role: ${role}\nTarget Company: ${comp}\n\n--- TECHNICAL QUESTIONS ---\n${tech}\n\n--- BEHAVIORAL QUESTIONS (STAR) ---\n${hr}`;
        filename = `Interview_Prep_${comp}_${role}.txt`;
    }

    if (!text) {
        showToast("Nothing to download.");
        return;
    }

    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("💾 Downloaded " + filename);
}

function closeJobDetailModal() {
    const modal = document.getElementById("job-detail-modal");
    if (modal) modal.style.display = "none";
}

function openPitchFromDetails(tab) {
    if (!state.selectedDetailJobId) return;
    closeJobDetailModal();
    openPitchModal(state.selectedDetailJobId, tab);
}

async function toggleSaveFromDetails() {
    if (!state.selectedDetailJobId) return;
    await toggleSaveJob(state.selectedDetailJobId);
    const j = (state.jobs || []).find(x => x.id === state.selectedDetailJobId);
    if (j) {
        const isSaved = j.user_status === "saved";
        document.getElementById("jd-btn-save").innerHTML = `<span>${isSaved ? '★ Saved' : '☆ Save'}</span>`;
    }
}

function switchPitchTab(tabName) {
    const tabs = ['cover', 'linkedin', 'coldemail', 'interview'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        const pnl = document.getElementById(`panel-${t}`);
        if (btn) btn.classList.toggle("active", t === tabName);
        if (pnl) pnl.style.display = t === tabName ? "block" : "none";
    });
}

function copyPitchContent(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.value || el.textContent || "";
    navigator.clipboard.writeText(text);

    // Visual button feedback if triggered from a button
    if (window.event && window.event.target) {
        const btn = window.event.target.closest("button");
        if (btn) {
            const originalText = btn.innerHTML;
            btn.innerHTML = "<span>✓ Copied!</span>";
            btn.style.borderColor = "var(--primary-500)";
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.borderColor = "";
            }, 1800);
        }
    }

    showToast("📋 Copied to clipboard!");
}

// ------------------------------------------------------------------------------
// Theme Management (Light / Dark Mode)
// ------------------------------------------------------------------------------
function initTheme() {
    const saved = localStorage.getItem("jobradar_theme");
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const activeTheme = saved || (prefersDark ? "dark" : "light");
    applyTheme(activeTheme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("jobradar_theme", theme);

    const isDark = theme === "dark";
    document.querySelectorAll(".theme-toggle-icon").forEach(el => {
        el.textContent = isDark ? "☀️" : "🌙";
    });
    document.querySelectorAll(".theme-toggle-label").forEach(el => {
        el.textContent = isDark ? "Light Mode" : "Dark Mode";
    });
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    showToast(`Switched to ${next === "dark" ? "Dark" : "Light"} Mode!`);
}

// ------------------------------------------------------------------------------
// Study Vault & Interview Preparation Resources Logic
// ------------------------------------------------------------------------------
async function loadStudyResources() {
    try {
        const email = state.currentUser?.email || "";
        const res = await fetch(`/api/resources?email=${encodeURIComponent(email)}`);
        if (!res.ok) throw new Error("Failed to load study resources");
        const data = await res.json();
        state.resources = data.resources || [];

        // Update sidebar and vault statistics
        const total = state.resources.length;
        const completed = state.resources.filter(r => r.is_completed).length;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

        const countSidebar = document.getElementById("sidebar-resources-count");
        if (countSidebar) countSidebar.textContent = total;

        const countTotal = document.getElementById("vault-total-count");
        if (countTotal) countTotal.textContent = total;

        const countCompleted = document.getElementById("vault-completed-count");
        if (countCompleted) countCompleted.textContent = completed;

        const percentEl = document.getElementById("vault-progress-percent");
        if (percentEl) percentEl.textContent = `${percent}%`;

        const progressBar = document.getElementById("vault-progress-bar");
        if (progressBar) progressBar.style.width = `${percent}%`;

        applyResourceFilters();
    } catch (e) {
        console.error("Error loading study resources:", e);
    }
}

function filterResources(category, btnElement) {
    state.activeResourceCategory = category;
    const pillContainer = document.getElementById("resource-category-pills");
    if (pillContainer) {
        pillContainer.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
    }
    if (btnElement) {
        btnElement.classList.add("active");
    }
    applyResourceFilters();
}

function searchResources(query) {
    state.resourceSearchTerm = (query || "").trim().toLowerCase();
    applyResourceFilters();
}

function applyResourceFilters() {
    let items = state.resources || [];
    const cat = state.activeResourceCategory;
    const term = state.resourceSearchTerm;

    if (cat === "my_uploads") {
        items = items.filter(r => r.resource_type === "pdf" || r.resource_type === "document" || (r.file_path && r.file_path.length > 0));
    } else if (cat && cat !== "all") {
        items = items.filter(r => (r.category || "").toLowerCase() === cat.toLowerCase());
    }

    if (term) {
        items = items.filter(r => {
            const titleMatch = (r.title || "").toLowerCase().includes(term);
            const descMatch = (r.description || "").toLowerCase().includes(term);
            const catMatch = (r.category || "").toLowerCase().includes(term);
            const tagMatch = (r.tags || []).some(t => (t || "").toLowerCase().includes(term));
            return titleMatch || descMatch || catMatch || tagMatch;
        });
    }

    renderStudyResources(items);
}

function renderStudyResources(items) {
    const container = document.getElementById("resources-cards-grid");
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; background:var(--bg-surface); border:1px dashed var(--border-default); border-radius:var(--radius-lg); padding:40px 20px; text-align:center;">
                <div style="font-size:36px; margin-bottom:10px;">📚</div>
                <h3 style="font-family:var(--font-heading); font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">No study resources found</h3>
                <p style="font-size:13px; color:var(--text-secondary); max-width:440px; margin:0 auto 16px;">Upload your own PDF cheat sheets, notes, or save web links to track your interview preparation.</p>
                <div style="display:flex; justify-content:center; gap:10px;">
                    <button class="btn btn-primary btn-sm" onclick="openAddResourceModal('upload')">📄 Upload PDF Notes</button>
                    <button class="btn btn-secondary btn-sm" onclick="openAddResourceModal('link')">🔗 Add Link Bookmark</button>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = items.map(r => {
        const isCompleted = !!r.is_completed;
        const isPdf = r.resource_type === "pdf" || (r.file_path && r.file_path.toLowerCase().endsWith(".pdf"));
        const isLink = r.resource_type === "link" && !r.content_text;
        const isGuide = !isPdf && !isLink;

        let iconEmoji = "⚡";
        let iconClass = "resource-icon-guide";
        let typeBadge = "Guide";

        if (isPdf) {
            iconEmoji = "📄";
            iconClass = "resource-icon-pdf";
            typeBadge = "PDF Document";
        } else if (isLink) {
            iconEmoji = "🔗";
            iconClass = "resource-icon-link";
            typeBadge = "Web Link";
        }

        const tagsHtml = (r.tags || []).map(t => 
            `<span class="resource-tag">${escapeHtml(t)}</span>`
        ).join("");

        let mainActionBtn = "";
        if (r.content_text) {
            mainActionBtn = `<button class="btn btn-primary btn-sm" onclick="openResourceReader(${r.id})"><span>📖</span> Read Guide</button>`;
        } else if (isPdf || r.file_path) {
            const fileUrl = r.url || `/api/resources/file/${encodeURIComponent(r.file_path.split(/[\\/]/).pop())}`;
            mainActionBtn = `<a href="${fileUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm"><span>📥</span> Open PDF</a>`;
        } else if (r.url) {
            mainActionBtn = `<a href="${escapeHtml(r.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm"><span>🌐</span> Open Link</a>`;
        }

        return `
            <div class="resource-card ${isCompleted ? 'completed' : ''}" id="resource-card-${r.id}">
                <div>
                    <div class="resource-top-bar">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <div class="resource-icon-badge ${iconClass}">
                                ${iconEmoji}
                            </div>
                            <div>
                                <span class="badge badge-web" style="font-size:11px;">${escapeHtml(r.category || 'General')}</span>
                                <span class="badge" style="font-size:11px; background:var(--bg-main); color:var(--text-secondary); margin-left:4px;">${typeBadge}</span>
                            </div>
                        </div>
                        ${isCompleted ? '<span class="studied-badge">✓ Studied</span>' : ''}
                    </div>

                    <h3 class="resource-card-title">${escapeHtml(r.title || 'Untitled Resource')}</h3>
                    <p class="resource-card-desc">${escapeHtml(r.description || 'Comprehensive preparation material for software engineering rounds.')}</p>

                    <div class="resource-tags-row">
                        ${tagsHtml}
                    </div>
                </div>

                <div class="resource-card-actions">
                    <div style="display:flex; gap:8px; align-items:center;">
                        ${mainActionBtn}
                        <button class="btn btn-secondary btn-sm" onclick="toggleResourceCompletion(${r.id}, event)" title="${isCompleted ? 'Mark as Unstudied' : 'Mark as Studied'}">
                            ${isCompleted ? 'Mark Unread' : '✓ Done'}
                        </button>
                    </div>

                    <button class="btn btn-secondary btn-sm" onclick="handleDeleteResource(${r.id}, event)" title="Remove Resource" style="color:var(--text-muted); padding:6px 10px;">
                        🗑
                    </button>
                </div>
            </div>
        `;
    }).join("");
}

// ------------------------------------------------------------------------------
// In-App Resource Reader Modal
// ------------------------------------------------------------------------------
function openResourceReader(resourceId) {
    const res = (state.resources || []).find(r => r.id === resourceId);
    if (!res) return;

    state.activeReadingResourceId = resourceId;

    document.getElementById("reader-title").textContent = res.title || "Study Guide";
    document.getElementById("reader-category-badge").textContent = res.category || "General";
    document.getElementById("reader-meta-desc").textContent = res.description || "In-app study notes and interview cheatsheet.";
    
    const typeBadge = document.getElementById("reader-type-badge");
    if (typeBadge) {
        typeBadge.textContent = res.resource_type ? res.resource_type.toUpperCase() : "GUIDE";
    }

    const toggleBtn = document.getElementById("reader-btn-toggle");
    if (toggleBtn) {
        toggleBtn.textContent = res.is_completed ? "✓ Mark as Unstudied" : "✓ Mark as Studied";
    }

    const contentBody = document.getElementById("reader-content-body");
    if (contentBody) {
        contentBody.innerHTML = renderMarkdownSimple(res.content_text || "_No text content provided._");
        contentBody.scrollTop = 0;
    }

    const modal = document.getElementById("resource-reader-modal");
    if (modal) modal.style.display = "flex";
}

function closeResourceReader() {
    const modal = document.getElementById("resource-reader-modal");
    if (modal) modal.style.display = "none";
    state.activeReadingResourceId = null;
}

function copyReaderContent() {
    const res = (state.resources || []).find(r => r.id === state.activeReadingResourceId);
    if (!res || !res.content_text) {
        return showToast("No text content to copy");
    }
    navigator.clipboard.writeText(res.content_text);
    showToast("📋 Study guide copied to clipboard!");
}

async function toggleReaderCompletion() {
    if (!state.activeReadingResourceId) return;
    await toggleResourceCompletion(state.activeReadingResourceId);
    const res = (state.resources || []).find(r => r.id === state.activeReadingResourceId);
    const toggleBtn = document.getElementById("reader-btn-toggle");
    if (toggleBtn && res) {
        toggleBtn.textContent = res.is_completed ? "✓ Mark as Unstudied" : "✓ Mark as Studied";
    }
}

async function toggleResourceCompletion(resourceId, event) {
    if (event) event.stopPropagation();
    try {
        const email = state.currentUser?.email || "";
        const res = await fetch("/api/resources/toggle-status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                resource_id: resourceId,
                user_email: email
            })
        });

        if (!res.ok) throw new Error("Failed to update status");
        const data = await res.json();

        // Update local state item
        const item = (state.resources || []).find(r => r.id === resourceId);
        if (item) {
            item.is_completed = data.is_completed;
        }

        // Recalculate progress stats
        const total = state.resources.length;
        const completed = state.resources.filter(r => r.is_completed).length;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

        const countCompleted = document.getElementById("vault-completed-count");
        if (countCompleted) countCompleted.textContent = completed;

        const percentEl = document.getElementById("vault-progress-percent");
        if (percentEl) percentEl.textContent = `${percent}%`;

        const progressBar = document.getElementById("vault-progress-bar");
        if (progressBar) progressBar.style.width = `${percent}%`;

        applyResourceFilters();
        showToast(data.is_completed ? "🎯 Marked resource as Studied!" : "Resource marked as pending.");
    } catch (e) {
        showToast("Error updating study status: " + e.message);
    }
}

// ------------------------------------------------------------------------------
// Add Resource Modal (PDF Upload & Link Save)
// ------------------------------------------------------------------------------
function openAddResourceModal(tab = "upload") {
    const modal = document.getElementById("add-resource-modal");
    if (modal) modal.style.display = "flex";
    switchAddResourceTab(tab);
}

function closeAddResourceModal() {
    const modal = document.getElementById("add-resource-modal");
    if (modal) modal.style.display = "none";
}

function switchAddResourceTab(tab) {
    const tabUpload = document.getElementById("modal-tab-upload");
    const tabLink = document.getElementById("modal-tab-link");
    const pnlUpload = document.getElementById("add-panel-upload");
    const pnlLink = document.getElementById("add-panel-link");

    if (tab === "upload") {
        if (tabUpload) tabUpload.classList.add("active");
        if (tabLink) tabLink.classList.remove("active");
        if (pnlUpload) pnlUpload.style.display = "block";
        if (pnlLink) pnlLink.style.display = "none";
    } else {
        if (tabLink) tabLink.classList.add("active");
        if (tabUpload) tabUpload.classList.remove("active");
        if (pnlLink) pnlLink.style.display = "block";
        if (pnlUpload) pnlUpload.style.display = "none";
    }
}

async function submitUploadResource() {
    const title = (document.getElementById("upload-res-title").value || "").trim();
    const category = document.getElementById("upload-res-category").value;
    const desc = (document.getElementById("upload-res-desc").value || "").trim();
    const fileInput = document.getElementById("upload-res-file");

    if (!fileInput.files || fileInput.files.length === 0) {
        return showToast("⚠️ Please select a file to upload (PDF, DOCX, TXT)");
    }

    const file = fileInput.files[0];
    const finalTitle = title || file.name;

    const formData = new FormData();
    formData.append("email", state.currentUser?.email || "");
    formData.append("title", finalTitle);
    formData.append("category", category);
    formData.append("description", desc);
    formData.append("file", file);

    showToast("Uploading study material to vault...");

    try {
        const res = await fetch("/api/resources/upload", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Upload failed");
        }

        closeAddResourceModal();
        document.getElementById("upload-res-title").value = "";
        document.getElementById("upload-res-desc").value = "";
        fileInput.value = "";

        showToast("✅ File saved to your Study Vault!");
        await loadStudyResources();
    } catch (e) {
        showToast("Upload error: " + e.message);
    }
}

async function submitLinkResource() {
    const title = (document.getElementById("link-res-title").value || "").trim();
    const url = (document.getElementById("link-res-url").value || "").trim();
    const category = document.getElementById("link-res-category").value;
    const desc = (document.getElementById("link-res-desc").value || "").trim();

    if (!title) return showToast("⚠️ Please enter a title for the resource");
    if (!url) return showToast("⚠️ Please enter a valid web URL");

    try {
        const email = state.currentUser?.email || "";
        const res = await fetch("/api/resources/add-link", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_email: email,
                title: title,
                url: url,
                category: category,
                description: desc,
                tags: [category, "BOOKMARK"]
            })
        });

        if (!res.ok) throw new Error("Failed to save bookmark");

        closeAddResourceModal();
        document.getElementById("link-res-title").value = "";
        document.getElementById("link-res-url").value = "";
        document.getElementById("link-res-desc").value = "";

        showToast("✅ Resource link bookmarked in vault!");
        await loadStudyResources();
    } catch (e) {
        showToast("Error saving link: " + e.message);
    }
}

async function handleDeleteResource(resourceId, event) {
    if (event) event.stopPropagation();
    if (!confirm("Are you sure you want to remove this study resource?")) return;

    try {
        const email = state.currentUser?.email || "";
        const res = await fetch(`/api/resources/${resourceId}?email=${encodeURIComponent(email)}`, {
            method: "DELETE"
        });

        if (!res.ok) throw new Error("Failed to delete resource");
        showToast("Resource removed from vault.");
        await loadStudyResources();
    } catch (e) {
        showToast("Delete error: " + e.message);
    }
}

// Lightweight Markdown to HTML renderer for In-App Guides
function renderMarkdownSimple(md) {
    if (!md) return "";
    let html = escapeHtml(md);

    // Code blocks ```code```
    html = html.replace(/```([\s\S]*?)```/g, (match, p1) => {
        return `<pre><code>${p1.trim()}</code></pre>`;
    });

    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Bullet points
    html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
    // Clean up duplicate nested uls if consecutive
    html = html.replace(/<\/ul>\s*<ul>/g, '');

    // Paragraph line breaks
    html = html.replace(/\n\n/g, '<p></p>');
    html = html.replace(/\n/g, '<br>');

    return html;
}

// ------------------------------------------------------------------------------
// Indian Tech Salary Studio & Counter-Offer Negotiator Logic
// ------------------------------------------------------------------------------
let currentNegotiationScripts = [];

function switchSalarySubTab(tab) {
    const btnBench = document.getElementById("btn-salary-tab-benchmarks");
    const btnNeg = document.getElementById("btn-salary-tab-negotiator");
    const viewBench = document.getElementById("salary-subview-benchmarks");
    const viewNeg = document.getElementById("salary-subview-negotiator");

    if (tab === "benchmarks") {
        if (btnBench) {
            btnBench.style.background = "#ffffff";
            btnBench.style.color = "#065f46";
            btnBench.style.fontWeight = "700";
        }
        if (btnNeg) {
            btnNeg.style.background = "rgba(255,255,255,0.15)";
            btnNeg.style.color = "#fff";
            btnNeg.style.fontWeight = "500";
        }
        if (viewBench) viewBench.style.display = "block";
        if (viewNeg) viewNeg.style.display = "none";
        runSalaryBenchmark();
    } else {
        if (btnNeg) {
            btnNeg.style.background = "#ffffff";
            btnNeg.style.color = "#065f46";
            btnNeg.style.fontWeight = "700";
        }
        if (btnBench) {
            btnBench.style.background = "rgba(255,255,255,0.15)";
            btnBench.style.color = "#fff";
            btnBench.style.fontWeight = "500";
        }
        if (viewBench) viewBench.style.display = "none";
        if (viewNeg) viewNeg.style.display = "block";

        // Pre-fill fields from user profile
        const roleInput = document.getElementById("salary-input-role")?.value || "Software Engineer";
        const negRole = document.getElementById("neg-role");
        if (negRole && (!negRole.value || negRole.value === "Software Engineer")) {
            negRole.value = state.currentUser.target_role || "Software Engineer";
        }
    }
}

async function runSalaryBenchmark() {
    const role = document.getElementById("salary-input-role")?.value || "software_engineer";
    const exp = document.getElementById("salary-input-exp")?.value || "fresher";
    const loc = document.getElementById("salary-input-loc")?.value || "bangalore";
    const tier = document.getElementById("salary-input-tier")?.value || "product_unicorn";
    const offeredVal = parseFloat(document.getElementById("salary-input-offered")?.value || "0");

    try {
        const res = await fetch("/api/salary/estimate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                role: role,
                experience: exp,
                location: loc,
                company_tier: tier,
                skills: state.currentUser.skills || [],
                current_offered_lpa: offeredVal > 0 ? offeredVal : null
            })
        });
        const data = await res.json();
        if (data.status === "ok" && data.data) {
            const d = data.data;

            // Percentile Cards
            document.getElementById("salary-p25-display").textContent = `₹${d.benchmarks.p25} LPA`;
            document.getElementById("salary-median-display").textContent = `₹${d.benchmarks.median} LPA`;
            document.getElementById("salary-p75-display").textContent = `₹${d.benchmarks.p75} LPA`;
            document.getElementById("salary-p90-display").textContent = `₹${d.benchmarks.p90} LPA`;

            // Breakdown
            document.getElementById("salary-breakdown-fixed").textContent = `₹${d.median_breakdown.fixed_base} LPA`;
            document.getElementById("salary-breakdown-variable").textContent = `₹${d.median_breakdown.performance_bonus} LPA`;
            document.getElementById("salary-breakdown-equity").textContent = `₹${d.median_breakdown.equity_esops} LPA`;

            // In-Hand Take Home
            document.getElementById("salary-in-hand-monthly").textContent = `${d.in_hand_estimate.monthly_formatted} / mo`;
            const netAnnual = d.in_hand_estimate.monthly_in_hand_inr * 12;
            document.getElementById("salary-in-hand-annual").textContent = `Net Annual Bank Credit: ₹${netAnnual.toLocaleString("en-IN")}`;
            document.getElementById("salary-tax-annual").textContent = `₹${d.in_hand_estimate.annual_tax_inr.toLocaleString("en-IN")}`;
            document.getElementById("salary-pf-annual").textContent = `₹${d.in_hand_estimate.annual_pf_inr.toLocaleString("en-IN")}`;

            // Offer Leverage Assessment Banner
            const banner = document.getElementById("salary-leverage-banner");
            if (d.percentile_assessment && banner) {
                const ass = d.percentile_assessment;
                banner.style.display = "block";
                banner.style.background = ass.status_color === "#ef4444" ? "rgba(239,68,68,0.08)" : 
                                         (ass.status_color === "#f59e0b" ? "rgba(245,158,11,0.08)" : "rgba(16,185,129,0.08)");
                banner.style.borderColor = ass.status_color;
                banner.innerHTML = `
                    <div style="display:flex; align-items:flex-start; gap:12px;">
                        <span style="font-size:22px;">⚖️</span>
                        <div>
                            <div style="font-size:12px; font-weight:800; text-transform:uppercase; color:${ass.status_color}; letter-spacing:0.5px;">
                                Offer Assessment: ${escapeHtml(ass.label)}
                            </div>
                            <div style="font-size:14px; color:var(--text-primary); margin-top:4px; font-weight:600;">
                                ${escapeHtml(ass.advice)}
                            </div>
                        </div>
                    </div>
                `;
            } else if (banner) {
                banner.style.display = "none";
            }
        }
    } catch (e) {
        console.error("Error running salary benchmark:", e);
    }
}

async function generateNegotiationDrafts() {
    const candidateName = state.currentUser.name || "Candidate";
    const company = document.getElementById("neg-company")?.value.trim() || "Tech Company";
    const role = document.getElementById("neg-role")?.value.trim() || "Software Engineer";
    const offered = parseFloat(document.getElementById("neg-offered")?.value || "10.0");
    const target = parseFloat(document.getElementById("neg-target")?.value || "14.0");
    const competingLpa = parseFloat(document.getElementById("neg-competing-lpa")?.value || "0");
    const competingComp = document.getElementById("neg-competing-comp")?.value.trim() || null;

    const btn = document.getElementById("btn-generate-neg");
    if (btn) btn.disabled = true;
    showToast("⚡ Generating high-conversion counter-offer scripts...");

    try {
        const res = await fetch("/api/salary/negotiation-scripts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                candidate_name: candidateName,
                company_name: company,
                role_title: role,
                current_offered_lpa: offered,
                target_lpa: target,
                competing_offer_lpa: competingLpa > 0 ? competingLpa : null,
                competing_company: competingComp,
                key_skills: (state.currentUser.skills || []).slice(0, 5),
                negotiation_focus: "polite_counter"
            })
        });
        const data = await res.json();
        if (data.status === "ok" && data.data) {
            currentNegotiationScripts = data.data.scripts || [];
            renderNegotiationDrafts(currentNegotiationScripts);
            showToast("🎉 Generated 3 tailored counter-offer email scripts!");
        }
    } catch (e) {
        showToast("Error generating scripts: " + e.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function renderNegotiationDrafts(scripts) {
    const container = document.getElementById("neg-drafts-container");
    if (!container) return;

    let scriptList = [];
    if (Array.isArray(scripts)) {
        scriptList = scripts;
    } else if (typeof scripts === "object" && scripts !== null) {
        scriptList = Object.values(scripts);
    }
    currentNegotiationScripts = scriptList;

    if (!scriptList || scriptList.length === 0) {
        container.innerHTML = `<div style="padding:20px; text-align:center; color:var(--text-muted);">No scripts generated yet.</div>`;
        return;
    }

    container.innerHTML = scriptList.map((s, idx) => {
        const title = s.title || "Counter-Offer Script";
        const badge = s.badge || s.use_case || "Professional";
        const fullText = s.email_text || s.body || "";
        let subject = "";
        let body = fullText;

        if (fullText.startsWith("Subject:")) {
            const firstLineEnd = fullText.indexOf("\n");
            if (firstLineEnd !== -1) {
                subject = fullText.substring("Subject:".length, firstLineEnd).trim();
                body = fullText.substring(firstLineEnd).trim();
            }
        } else if (s.subject) {
            subject = s.subject;
            body = s.body;
        }

        return `
        <div style="background:var(--bg-card); border:1px solid var(--border-default); border-radius:var(--radius-xl); padding:22px; box-shadow:var(--shadow-sm); margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; gap:12px; flex-wrap:wrap;">
                <div>
                    <h4 style="font-size:16px; font-weight:800; margin:0 0 4px 0; color:var(--text-primary);">${escapeHtml(title)}</h4>
                    <span style="font-size:11px; background:rgba(79,70,229,0.1); color:#4f46e5; padding:2px 8px; border-radius:10px; font-weight:700;">
                        ${escapeHtml(badge)}
                    </span>
                </div>
                <button class="btn btn-secondary btn-sm" onclick="copyNegotiationScript(${idx})">
                    <span>📋</span> Copy Full Email
                </button>
            </div>

            ${subject ? `
            <div style="background:var(--bg-surface); padding:10px 14px; border-radius:8px; border:1px solid var(--border-subtle); margin-bottom:12px; font-size:13px;">
                <span style="color:var(--text-muted); font-weight:700; margin-right:6px;">Subject:</span>
                <span style="color:var(--text-primary); font-weight:600;">${escapeHtml(subject)}</span>
            </div>` : ""}

            <pre style="white-space:pre-wrap; word-wrap:break-word; font-family:var(--font-sans); font-size:13px; line-height:1.6; color:var(--text-primary); background:var(--bg-surface); padding:16px; border-radius:8px; border:1px solid var(--border-subtle); margin:0;">${escapeHtml(body)}</pre>
        </div>
        `;
    }).join("");
}

function copyNegotiationScript(idx) {
    if (!currentNegotiationScripts || !currentNegotiationScripts[idx]) return;
    const s = currentNegotiationScripts[idx];
    const textToCopy = s.email_text || `Subject: ${s.subject || ""}\n\n${s.body || ""}`;

    navigator.clipboard.writeText(textToCopy).then(() => {
        showToast(`📋 Copied "${s.title}" email to clipboard!`);
    }).catch(() => {
        showToast("Error copying to clipboard. Please copy manually.");
    });
}

// ------------------------------------------------------------------------------
// LinkedIn Senior Referral & Alumni Outreach Hub
// ------------------------------------------------------------------------------
let referralState = {
    jobId: null,
    job: null,
    hubData: null,
    activeTab: "fresher_alumni"
};

async function openReferralModal(jobId) {
    referralState.jobId = jobId;
    let cardJob = (state.jobs || []).find(x => x.id === jobId) || 
                  (state.trackerItems || []).find(x => x.job_id === jobId || x.id === jobId) || {};
    referralState.job = cardJob;

    const modal = document.getElementById("referral-modal");
    if (!modal) return;
    modal.style.display = "flex";

    const compName = cardJob.company || "Company";
    const roleTitle = cardJob.title || "Software Engineer";

    const compEl = document.getElementById("referral-modal-company");
    const badgeEl = document.getElementById("referral-modal-company-badge");
    const labelEl = document.getElementById("referral-company-label");
    const roleEl = document.getElementById("referral-modal-role");
    const compInp = document.getElementById("referral-input-company");
    const refInp = document.getElementById("referral-input-job-ref");

    if (compEl) compEl.textContent = compName;
    if (badgeEl) badgeEl.textContent = compName;
    if (labelEl) labelEl.textContent = compName;
    if (roleEl) roleEl.textContent = roleTitle;
    if (compInp) compInp.value = compName;
    if (refInp) refInp.value = (cardJob.id || "REQ-REF").slice(0, 10).toUpperCase();

    // Prefill inputs
    const collegeInp = document.getElementById("referral-input-college");
    if (collegeInp) {
        collegeInp.value = state.currentUser.college_name || "";
    }
    const seniorInp = document.getElementById("referral-input-senior-name");
    if (seniorInp) seniorInp.value = "";

    const txtArea = document.getElementById("referral-pitch-textarea");
    if (txtArea) txtArea.value = "⚡ Loading personalized senior referral pitches & LinkedIn search queries...";

    // Setup live char counter on textarea typing
    if (txtArea && !txtArea._hasCharListener) {
        txtArea.addEventListener("input", () => {
            const charCounter = document.getElementById("referral-char-counter");
            if (charCounter && charCounter.style.display !== "none") {
                const curLen = txtArea.value.length;
                charCounter.textContent = `${curLen} / 300 characters ${curLen <= 300 ? '✅ (Fits LinkedIn limit)' : '⚠️ (Exceeds limit)'}`;
                charCounter.style.color = curLen <= 300 ? '#0284c7' : '#ef4444';
            }
        });
        txtArea._hasCharListener = true;
    }

    switchReferralTab("fresher_alumni");
    await fetchReferralHubData(jobId);
}

function openReferralModalFromDetails() {
    if (state.selectedDetailJobId) {
        openReferralModal(state.selectedDetailJobId);
    }
}

async function fetchReferralHubData(jobId) {
    if (!jobId) return;
    const seniorName = (document.getElementById("referral-input-senior-name")?.value || "").trim();
    const collegeName = (document.getElementById("referral-input-college")?.value || state.currentUser.college_name || "").trim();
    const companyKeyword = (document.getElementById("referral-input-company")?.value || "").trim();
    const jobRef = (document.getElementById("referral-input-job-ref")?.value || "").trim();

    try {
        const res = await fetch("/api/referral/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                job_id: jobId,
                user_email: state.currentUser.email,
                senior_name: seniorName,
                college_name: collegeName,
                company_keyword: companyKeyword,
                job_ref: jobRef
            })
        });

        if (!res.ok) {
            showToast("Failed to load referral suite");
            return;
        }

        const json = await res.json();
        referralState.hubData = json.data;

        // If cardJob was empty, populate from server response
        if (!referralState.job || !referralState.job.company) {
            referralState.job = {
                company: json.data.company,
                title: json.data.role_title,
                id: json.data.job_id
            };
            document.getElementById("referral-modal-company").textContent = json.data.company;
            document.getElementById("referral-modal-role").textContent = json.data.role_title;
        }

        const cleanComp = json.data.clean_company || json.data.company;
        const labelEl = document.getElementById("referral-company-label");
        if (labelEl) labelEl.textContent = cleanComp;

        // Update LinkedIn & Google search buttons
        const urls = json.data.search_urls || {};
        const btnAlumni = document.getElementById("btn-search-alumni");
        const btnSeniors = document.getElementById("btn-search-seniors");
        const btnManagers = document.getElementById("btn-search-managers");
        const btnRecruiters = document.getElementById("btn-search-recruiters");
        const btnGoogleSeniors = document.getElementById("btn-search-google-seniors");
        const btnGoogleAlumni = document.getElementById("btn-search-google-alumni");

        if (btnAlumni) btnAlumni.href = urls.alumni_url || "#";
        if (btnSeniors) btnSeniors.href = urls.seniors_url || "#";
        if (btnManagers) btnManagers.href = urls.managers_url || "#";
        if (btnRecruiters) btnRecruiters.href = urls.recruiters_url || "#";
        if (btnGoogleSeniors) btnGoogleSeniors.href = urls.google_xray_url || "#";
        if (btnGoogleAlumni) btnGoogleAlumni.href = urls.google_alumni_url || "#";

        renderActiveReferralPitch();
    } catch (e) {
        console.error("Referral fetch error:", e);
        showToast("Error loading referral suite: " + e.message);
    }
}

let referralDebounceTimer = null;
function updateReferralPitchLive() {
    if (referralDebounceTimer) clearTimeout(referralDebounceTimer);
    referralDebounceTimer = setTimeout(() => {
        if (referralState.jobId) {
            fetchReferralHubData(referralState.jobId);
        }
    }, 300);
}

function setReferralCollege(colName) {
    const colInp = document.getElementById("referral-input-college");
    if (colInp) {
        colInp.value = colName;
        updateReferralPitchLive();
        showToast(`🎓 Updated college to ${colName}`);
    }
}

function switchReferralTab(tabKey) {
    referralState.activeTab = tabKey;
    ['fresher', 'peer', 'connection', 'manager', 'email', 'followup'].forEach(k => {
        const btn = document.getElementById(`ref-tab-${k}`);
        if (btn) btn.classList.remove("active");
    });

    const activeMap = {
        "fresher_alumni": "ref-tab-fresher",
        "experienced_peer": "ref-tab-peer",
        "linkedin_connection_note": "ref-tab-connection",
        "manager_inmail": "ref-tab-manager",
        "cold_email": "ref-tab-email",
        "followup": "ref-tab-followup"
    };

    const targetBtn = document.getElementById(activeMap[tabKey]);
    if (targetBtn) targetBtn.classList.add("active");

    renderActiveReferralPitch();
}

function renderActiveReferralPitch() {
    if (!referralState.hubData) return;
    const p = referralState.hubData.pitches[referralState.activeTab];
    if (!p) return;

    const titleEl = document.getElementById("referral-pitch-title");
    if (titleEl) titleEl.textContent = p.title;
    const txtArea = document.getElementById("referral-pitch-textarea");
    if (txtArea) txtArea.value = p.text;

    const charCounter = document.getElementById("referral-char-counter");
    if (charCounter) {
        if (p.char_limit) {
            charCounter.style.display = "inline";
            const curLen = p.text.length;
            charCounter.textContent = `${curLen} / ${p.char_limit} characters ${curLen <= p.char_limit ? '✅ (Fits LinkedIn limit)' : '⚠️ (Exceeds limit)'}`;
            charCounter.style.color = curLen <= p.char_limit ? '#0284c7' : '#ef4444';
        } else {
            charCounter.style.display = "none";
        }
    }
}

function resetReferralPitch() {
    if (!referralState.hubData) return;
    const p = referralState.hubData.pitches[referralState.activeTab];
    if (p) {
        document.getElementById("referral-pitch-textarea").value = p.text;
        showToast("🔄 Restored original AI-generated referral pitch!");
    }
}

function copyReferralPitch() {
    const txtArea = document.getElementById("referral-pitch-textarea");
    if (!txtArea) return;
    const txt = txtArea.value || "";
    if (!txt) return;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(() => {
            showToast("📋 Copied referral pitch to clipboard! Ready to paste into LinkedIn.");
        }).catch(() => {
            txtArea.select();
            document.execCommand("copy");
            showToast("📋 Copied referral pitch to clipboard! Ready to paste into LinkedIn.");
        });
    } else {
        txtArea.select();
        document.execCommand("copy");
        showToast("📋 Copied referral pitch to clipboard! Ready to paste into LinkedIn.");
    }
}

function downloadReferralTxt() {
    const txt = document.getElementById("referral-pitch-textarea")?.value || "";
    if (!txt) return;
    const company = (referralState.job?.company || "Company").replace(/[^a-zA-Z0-9]/g, "_");
    const filename = `Referral_Pitch_${company}_${referralState.activeTab}.txt`;
    const blob = new Blob([txt], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    showToast(`💾 Downloaded ${filename}`);
}

async function trackCurrentReferral() {
    if (!referralState.jobId) return;
    const seniorName = (document.getElementById("referral-input-senior-name")?.value || "").trim();
    const seniorUrl = (document.getElementById("referral-senior-profile-url")?.value || "").trim();
    const note = (document.getElementById("referral-tracking-note")?.value || "").trim();
    const btn = document.getElementById("btn-track-referral");
    if (btn) btn.disabled = true;

    try {
        const res = await fetch("/api/referral/track", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_email: state.currentUser.email,
                job_id: referralState.jobId,
                senior_name: seniorName,
                senior_profile_url: seniorUrl,
                pitch_type: referralState.activeTab,
                notes: note
            })
        });

        const data = await res.json();
        if (data.status === "ok") {
            showToast("🎉 Referral tracked in your pipeline as 'Referral Requested'!");
            loadTrackerJobs();
            fetchStats();
            const j = (state.jobs || []).find(x => x.id === referralState.jobId);
            if (j) j.user_status = "referral_requested";
            renderJobCards(state.jobs);
        }
    } catch (e) {
        showToast("Error tracking referral: " + e.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function closeReferralModal() {
    const modal = document.getElementById("referral-modal");
    if (modal) modal.style.display = "none";
}

// ------------------------------------------------------------------------------
// AI Mock Technical & HR Interview Simulator Controller
// ------------------------------------------------------------------------------
let interviewState = {
    session: null,
    currentIndex: 0,
    answers: {},
    evaluations: {},
    selectedJobId: null
};

function initInterviewView() {
    const jobSelect = document.getElementById("interview-select-job");
    if (!jobSelect) return;
    
    // Clear options except custom
    jobSelect.innerHTML = `<option value="">-- Custom Target Company & Role --</option>`;
    
    const jobsPool = state.jobs && state.jobs.length ? state.jobs : (state.trackerItems || []);
    jobsPool.slice(0, 30).forEach(j => {
        const title = j.title || "Software Engineer";
        const company = j.company || "Tech Company";
        const opt = document.createElement("option");
        opt.value = j.id || j.job_id;
        opt.textContent = `${company} — ${title}`;
        jobSelect.appendChild(opt);
    });

    if (interviewState.selectedJobId) {
        jobSelect.value = interviewState.selectedJobId;
        onInterviewJobSelectChange();
    }
}

function onInterviewJobSelectChange() {
    const jobSelect = document.getElementById("interview-select-job");
    const jobId = jobSelect.value;
    interviewState.selectedJobId = jobId;

    if (!jobId) return;

    const j = (state.jobs || []).find(x => x.id === jobId) || 
              (state.trackerItems || []).find(x => (x.job_id || x.id) === jobId);

    if (j) {
        const compInp = document.getElementById("interview-input-company");
        const roleInp = document.getElementById("interview-input-role");
        if (compInp && j.company) compInp.value = j.company;
        if (roleInp && j.title) roleInp.value = j.title;
    }
}

function launchInterviewForJob(jobId) {
    interviewState.selectedJobId = jobId;
    switchView("interview");
    const jobSelect = document.getElementById("interview-select-job");
    if (jobSelect) {
        jobSelect.value = jobId;
        onInterviewJobSelectChange();
    }
    // Auto-launch session
    setTimeout(() => {
        startInterviewSession();
    }, 150);
}

function startInterviewFromDetails() {
    closeJobDetailModal();
    if (state.selectedDetailJobId) {
        launchInterviewForJob(state.selectedDetailJobId);
    } else {
        switchView("interview");
    }
}

async function startInterviewSession() {
    const btn = document.getElementById("btn-start-interview");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span>⏳ Synthesizing Interview Questions...</span>`;
    }

    const company = (document.getElementById("interview-input-company")?.value || "Tech Company").trim();
    const role = (document.getElementById("interview-input-role")?.value || "Software Engineer").trim();
    const exp = document.getElementById("interview-select-exp")?.value || state.currentUser.experience_level || "fresher";
    const jobId = interviewState.selectedJobId || (document.getElementById("interview-select-job")?.value) || null;

    try {
        const res = await fetch("/api/interview/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                job_id: jobId,
                company: company,
                title: role,
                user_email: state.currentUser.email
            })
        });

        const data = await res.json();
        if (data.status === "ok" && data.session) {
            interviewState.session = data.session;
            interviewState.currentIndex = 0;
            interviewState.answers = {};
            interviewState.evaluations = {};

            document.getElementById("interview-setup-panel").style.display = "none";
            document.getElementById("interview-arena-panel").style.display = "block";
            document.getElementById("interview-final-report-card").style.display = "none";

            document.getElementById("interview-company-tag").textContent = `Target: ${company} • ${role}`;

            renderInterviewQuestion();
            showToast(`🎯 Mock Interview started for ${company} (${role})!`);
        } else {
            showToast("Failed to initialize interview session.");
        }
    } catch (e) {
        showToast("Error starting interview: " + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span>🚀 Launch AI Mock Interview Arena &rarr;</span>`;
        }
    }
}

function renderInterviewQuestion() {
    const session = interviewState.session;
    if (!session || !session.questions) return;

    const q = session.questions[interviewState.currentIndex];
    if (!q) return;

    const roundBadge = document.getElementById("interview-current-round-badge");
    if (roundBadge) roundBadge.textContent = q.round || "Technical Round";

    const progText = document.getElementById("interview-progress-text");
    if (progText) progText.textContent = `Question ${interviewState.currentIndex + 1} of ${session.total_questions}`;

    const diffBadge = document.getElementById("interview-difficulty-badge");
    if (diffBadge) diffBadge.textContent = q.difficulty || "Mid";

    const topicEl = document.getElementById("interview-q-topic");
    if (topicEl) topicEl.textContent = q.topic || "Core Technical";

    const textEl = document.getElementById("interview-q-text");
    if (textEl) textEl.textContent = q.question;

    const hintText = document.getElementById("interview-hint-text");
    if (hintText) hintText.textContent = q.hint || "Review core architectural tradeoffs and metrics.";

    const hintBox = document.getElementById("interview-hint-box");
    if (hintBox) hintBox.style.display = "none";

    const btnHint = document.getElementById("btn-toggle-hint");
    if (btnHint) btnHint.textContent = "💡 Show Architectural Hint";

    // Restore previous answer if exists
    const ansBox = document.getElementById("interview-candidate-answer");
    if (ansBox) {
        ansBox.value = interviewState.answers[interviewState.currentIndex] || "";
        updateAnswerWordCount();
    }

    // Restore or hide evaluation
    const evalCard = document.getElementById("interview-evaluation-card");
    if (interviewState.evaluations[interviewState.currentIndex]) {
        renderEvaluationCard(interviewState.evaluations[interviewState.currentIndex]);
    } else {
        if (evalCard) evalCard.style.display = "none";
    }

    window.scrollTo({ top: 120, behavior: "smooth" });
}

function toggleInterviewHint() {
    const hintBox = document.getElementById("interview-hint-box");
    const btnHint = document.getElementById("btn-toggle-hint");
    if (!hintBox) return;

    if (hintBox.style.display === "none") {
        hintBox.style.display = "block";
        btnHint.textContent = "🙈 Hide Architectural Hint";
    } else {
        hintBox.style.display = "none";
        btnHint.textContent = "💡 Show Architectural Hint";
    }
}

function updateAnswerWordCount() {
    const val = (document.getElementById("interview-candidate-answer")?.value || "").trim();
    const words = val ? val.split(/\s+/).length : 0;
    const chars = val.length;
    const countEl = document.getElementById("interview-answer-count");
    if (countEl) {
        countEl.textContent = `${words} words • ${chars} characters`;
    }
}

function clearInterviewAnswer() {
    const ansBox = document.getElementById("interview-candidate-answer");
    if (ansBox) {
        ansBox.value = "";
        updateAnswerWordCount();
    }
}

function insertSampleAnswer() {
    const session = interviewState.session;
    if (!session) return;
    const q = session.questions[interviewState.currentIndex];
    if (!q) return;

    const ansBox = document.getElementById("interview-candidate-answer");
    if (ansBox) {
        ansBox.value = q.ideal_answer || "In our production system, we handled this by implementing connection pooling and decoupled asynchronous background workers to ensure 99.9% uptime and sub-50ms query latency.";
        updateAnswerWordCount();
        showToast("⚡ Inserted comprehensive engineering response!");
    }
}

async function submitInterviewAnswer() {
    const ansBox = document.getElementById("interview-candidate-answer");
    const answer = (ansBox?.value || "").trim();
    if (!answer) {
        return showToast("⚠️ Please write or paste your answer before submitting!");
    }

    const session = interviewState.session;
    if (!session) return;
    const q = session.questions[interviewState.currentIndex];

    const btn = document.getElementById("btn-submit-answer");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span>⏳ Evaluating Answer Depth & Key Concepts...</span>`;
    }

    try {
        const res = await fetch("/api/interview/evaluate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question_data: q,
                candidate_answer: answer,
                experience_level: session.experience_level || "fresher"
            })
        });

        const data = await res.json();
        if (data.status === "ok" && data.evaluation) {
            interviewState.answers[interviewState.currentIndex] = answer;
            interviewState.evaluations[interviewState.currentIndex] = data.evaluation;
            renderEvaluationCard(data.evaluation);
            showToast("🎯 Real-time AI evaluation ready!");
        }
    } catch (e) {
        showToast("Error evaluating answer: " + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span>⚡ Submit Answer for Instant AI Scoring &rarr;</span>`;
        }
    }
}

function renderEvaluationCard(evalData) {
    const evalCard = document.getElementById("interview-evaluation-card");
    if (!evalCard) return;

    evalCard.style.display = "block";

    const circle = document.getElementById("eval-score-circle");
    if (circle) circle.textContent = evalData.score;

    const titleEl = document.getElementById("eval-score-title");
    if (titleEl) titleEl.textContent = `Interview Score: ${evalData.score} / 10`;

    const badgeEl = document.getElementById("eval-badge");
    if (badgeEl) {
        badgeEl.textContent = evalData.badge;
        badgeEl.style.background = evalData.badge_color;
    }

    const summaryEl = document.getElementById("eval-feedback-summary");
    if (summaryEl) summaryEl.textContent = evalData.feedback;

    // Strengths
    const strengthsList = document.getElementById("eval-strengths-list");
    if (strengthsList) {
        strengthsList.innerHTML = (evalData.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join("");
    }

    // Gaps
    const gapsList = document.getElementById("eval-gaps-list");
    if (gapsList) {
        gapsList.innerHTML = (evalData.missing_points || []).map(g => `<li>${escapeHtml(g)}</li>`).join("");
    }

    // Ideal answer
    const idealEl = document.getElementById("eval-ideal-answer");
    if (idealEl) idealEl.textContent = evalData.ideal_answer || "N/A";

    // Next button label
    const btnNext = document.getElementById("btn-next-question");
    if (btnNext) {
        const isLast = interviewState.currentIndex >= (interviewState.session.total_questions - 1);
        btnNext.innerHTML = isLast 
            ? `<span>🎉 View Final Performance Report &rarr;</span>` 
            : `<span>Next Question (${interviewState.currentIndex + 2}/5) ➔</span>`;
    }

    evalCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function copyIdealAnswer() {
    const text = document.getElementById("eval-ideal-answer")?.textContent || "";
    if (text) {
        navigator.clipboard.writeText(text);
        showToast("📋 Copied model answer to clipboard!");
    }
}

function nextInterviewQuestion() {
    const isLast = interviewState.currentIndex >= (interviewState.session.total_questions - 1);
    if (isLast) {
        showInterviewFinalReport();
    } else {
        interviewState.currentIndex++;
        renderInterviewQuestion();
    }
}

function showInterviewFinalReport() {
    const session = interviewState.session;
    if (!session) return;

    document.getElementById("interview-evaluation-card").style.display = "none";
    document.getElementById("interview-final-report-card").style.display = "block";

    const scores = Object.values(interviewState.evaluations).map(e => e.score);
    const avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : "8.0";

    const avgEl = document.getElementById("final-avg-score");
    if (avgEl) avgEl.textContent = `${avg} / 10`;

    const verdictEl = document.getElementById("final-verdict-text");
    if (verdictEl) {
        if (parseFloat(avg) >= 8.0) {
            verdictEl.textContent = "🌟 Strong Hire • Top 10% Candidate for Indian Product Unicorns & FAANG";
            verdictEl.style.color = "#10b981";
        } else if (parseFloat(avg) >= 6.0) {
            verdictEl.textContent = "👍 Hire • Solid Technical Base, ready for Mid-Market & Startups";
            verdictEl.style.color = "#0284c7";
        } else {
            verdictEl.textContent = "⚠️ Borderline / Needs Polish • Recommend brushing up key architecture concepts";
            verdictEl.style.color = "#f59e0b";
        }
    }

    window.scrollTo({ top: 120, behavior: "smooth" });
}

function resetInterviewSession() {
    interviewState.session = null;
    interviewState.currentIndex = 0;
    interviewState.answers = {};
    interviewState.evaluations = {};

    document.getElementById("interview-setup-panel").style.display = "block";
    document.getElementById("interview-arena-panel").style.display = "none";
    document.getElementById("interview-final-report-card").style.display = "none";
}

// ==============================================================================
// Universal Job Portal Auto-Fill Assistant Controller
// ==============================================================================
let autofillState = {
    profile: null,
    simulatorFormat: "greenhouse",
    customAnswers: null
};

async function initAutofillView() {
    await loadAutofillProfile();
    // Default tailored questions if inputs empty
    const compInput = document.getElementById("af-gen-company");
    const roleInput = document.getElementById("af-gen-role");
    if (compInput && !compInput.value.trim()) compInput.value = "Google";
    if (roleInput && !roleInput.value.trim()) roleInput.value = (state.currentUser?.target_role || "Software Engineer");
    generateTailoredPortalAnswers();
}

async function loadAutofillProfile() {
    try {
        const email = state.currentUser?.email || "";
        const res = await fetch(`/api/autofill/profile?email=${encodeURIComponent(email)}`);
        if (res.ok) {
            const data = await res.json();
            autofillState.profile = data.profile || {};

            // Populate form fields
            const p = autofillState.profile;
            if (document.getElementById("af-name")) document.getElementById("af-name").value = p.name || "";
            if (document.getElementById("af-email")) document.getElementById("af-email").value = p.email || "";
            if (document.getElementById("af-phone")) document.getElementById("af-phone").value = p.phone || "";
            if (document.getElementById("af-city")) document.getElementById("af-city").value = p.current_city || "Bengaluru, Karnataka, India";
            if (document.getElementById("af-linkedin")) document.getElementById("af-linkedin").value = p.linkedin_url || "";
            if (document.getElementById("af-github")) document.getElementById("af-github").value = p.github_url || "";
            if (document.getElementById("af-portfolio")) document.getElementById("af-portfolio").value = p.portfolio_url || "";
            if (document.getElementById("af-role")) document.getElementById("af-role").value = p.target_role || "Software Engineer";
            if (document.getElementById("af-notice")) document.getElementById("af-notice").value = p.notice_period || "Immediate (0-15 Days)";
            if (document.getElementById("af-ctc")) document.getElementById("af-ctc").value = p.expected_ctc || "Competitive";
            if (document.getElementById("af-auth")) document.getElementById("af-auth").value = p.work_authorization || "Authorized to work in India (Citizen/Permanent Resident)";
            if (document.getElementById("af-visa")) document.getElementById("af-visa").value = p.visa_sponsorship || "No";

            // Update bookmarklet link if provided
            if (data.bookmarklet_code) {
                const bmLink = document.getElementById("autofill-bookmarklet-link");
                if (bmLink) bmLink.href = data.bookmarklet_code;
            }
        }
    } catch (e) {
        console.error("Error loading autofill profile:", e);
    }
}

async function saveAutofillSettings() {
    const payload = {
        email: document.getElementById("af-email")?.value.trim() || state.currentUser?.email,
        name: document.getElementById("af-name")?.value.trim() || "",
        phone: document.getElementById("af-phone")?.value.trim() || "",
        current_city: document.getElementById("af-city")?.value.trim() || "",
        linkedin_url: document.getElementById("af-linkedin")?.value.trim() || "",
        github_url: document.getElementById("af-github")?.value.trim() || "",
        portfolio_url: document.getElementById("af-portfolio")?.value.trim() || "",
        target_role: document.getElementById("af-role")?.value.trim() || "",
        notice_period: document.getElementById("af-notice")?.value.trim() || "",
        expected_ctc: document.getElementById("af-ctc")?.value.trim() || "",
        work_authorization: document.getElementById("af-auth")?.value || "",
        visa_sponsorship: document.getElementById("af-visa")?.value || "No"
    };

    try {
        const res = await fetch("/api/autofill/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const data = await res.json();
            showToast("🎉 Auto-Fill profile saved! Syncing with browser bookmarklet.");
            if (state.currentUser) {
                Object.assign(state.currentUser, payload);
                renderUserHeader();
            }
            autofillState.profile = Object.assign(autofillState.profile || {}, payload);
        } else {
            showToast("Failed to save autofill profile.");
        }
    } catch (e) {
        showToast("Error saving profile: " + e.message);
    }
}

function switchSimulatorFormat(format) {
    autofillState.simulatorFormat = format;
    document.querySelectorAll(".simulator-tab-btn").forEach(b => b.classList.remove("active"));
    const activeBtn = document.getElementById(`sim-tab-${format}`);
    if (activeBtn) activeBtn.classList.add("active");

    const whyCompLabel = document.querySelector("#sim_why_company")?.previousElementSibling;
    if (whyCompLabel) {
        if (format === "greenhouse") whyCompLabel.textContent = "Greenhouse Custom Question: 'Why do you want to join our engineering team?'";
        else if (format === "lever") whyCompLabel.textContent = "Lever Application Notes: 'Additional Information / Cover Letter Note'";
        else if (format === "workday") whyCompLabel.textContent = "Workday Motivation Statement: 'Why are you interested in this position?'";
    }
    showToast(`Switched simulator format to ${format.toUpperCase()}`);
}

function runSimulatorAutofill() {
    const p = autofillState.profile || {
        first_name: "Alex",
        last_name: "Johnson",
        name: "Alex Johnson",
        email: "alex@example.com",
        phone: "+91 98765 43210",
        current_city: "Bengaluru, Karnataka, India",
        linkedin_url: "https://linkedin.com/in/alex-developer",
        github_url: "https://github.com/alex-dev",
        portfolio_url: "https://alex-portfolio.dev",
        notice_period: "Immediate (0 Days)",
        expected_ctc: "₹8 - 12 LPA (Negotiable)",
        work_authorization: "Authorized to work in India (Citizen/Permanent Resident)",
        why_this_company: "I am passionate about solving real-world engineering problems and admired your team's architecture. My experience building clean backend APIs and full-stack interfaces matches your tech stack."
    };

    const mapping = {
        sim_first_name: p.first_name || p.name?.split(" ")[0] || "Alex",
        sim_last_name: p.last_name || p.name?.split(" ")[1] || "Johnson",
        sim_email: p.email || "alex@example.com",
        sim_phone: p.phone || "+91 98765 43210",
        sim_city: p.current_city || "Bengaluru, India",
        sim_linkedin: p.linkedin_url || "https://linkedin.com/in/alex-developer",
        sim_github: p.github_url || "https://github.com/alex-dev",
        sim_portfolio: p.portfolio_url || "https://alex-portfolio.dev",
        sim_notice: p.notice_period || "Immediate",
        sim_ctc: p.expected_ctc || "Competitive",
        sim_auth: p.work_authorization || "Authorized to work in India (Citizen/Permanent Resident)",
        sim_why_company: p.why_this_company || "I bring strong foundations in software development with hands-on experience building scalable applications, clean architecture, and modern APIs."
    };

    let filled = 0;
    Object.entries(mapping).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) {
            el.value = val;
            el.classList.remove("sim-field-highlight");
            void el.offsetWidth; // Trigger reflow
            el.classList.add("sim-field-highlight");
            filled++;
        }
    });

    showToast(`⚡ [Simulator] ${filled} form fields filled with verified profile!`);
}

function clearSimulatorForm() {
    const ids = [
        "sim_first_name", "sim_last_name", "sim_email", "sim_phone",
        "sim_city", "sim_linkedin", "sim_github", "sim_portfolio",
        "sim_notice", "sim_ctc", "sim_why_company"
    ];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.value = "";
            el.classList.remove("sim-field-highlight");
        }
    });
    showToast("🧹 Test simulator form cleared.");
}

function copyBookmarkletCode() {
    const code = "javascript:(function(){var s=document.createElement('script');s.src='http://127.0.0.1:8765/static/autofill-bookmarklet.js?t='+Date.now();document.body.appendChild(s);})();";
    navigator.clipboard.writeText(code);
    showToast("📋 Copied bookmarklet JavaScript code to clipboard!");
}

async function generateTailoredPortalAnswers() {
    const company = document.getElementById("af-gen-company")?.value.trim() || "Target Company";
    const role = document.getElementById("af-gen-role")?.value.trim() || "Software Engineer";
    const container = document.getElementById("af-answers-container");
    if (!container) return;

    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;">
        <span class="status-dot"></span> AI is crafting tailored responses for ${company} (${role})...
    </div>`;

    try {
        const res = await fetch("/api/autofill/generate-custom", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_email: state.currentUser?.email || "",
                company: company,
                role: role
            })
        });

        if (res.ok) {
            const data = await res.json();
            const a = data.answers;
            autofillState.customAnswers = a;

            container.innerHTML = `
                <div class="copy-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; font-size:12px; color:#10b981;">🏢 Why ${company}?</span>
                        <button class="btn btn-secondary btn-sm" onclick="copyCardSnippet('why_this_company')" style="font-size:11px; padding:3px 8px;">Copy</button>
                    </div>
                    <div style="font-size:12px; color:var(--text-secondary); line-height:1.45;">${a.why_this_company}</div>
                </div>

                <div class="copy-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; font-size:12px; color:#4f46e5;">💼 Why Hire Me for ${role}?</span>
                        <button class="btn btn-secondary btn-sm" onclick="copyCardSnippet('why_hire_me')" style="font-size:11px; padding:3px 8px;">Copy</button>
                    </div>
                    <div style="font-size:12px; color:var(--text-secondary); line-height:1.45;">${a.why_hire_me}</div>
                </div>

                <div class="copy-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; font-size:12px; color:#0284c7;">🚀 Projects & Technical Summary</span>
                        <button class="btn btn-secondary btn-sm" onclick="copyCardSnippet('projects_summary')" style="font-size:11px; padding:3px 8px;">Copy</button>
                    </div>
                    <div style="font-size:12px; color:var(--text-secondary); line-height:1.45; white-space:pre-line;">${a.projects_summary}</div>
                </div>

                <div class="copy-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; font-size:12px; color:#d97706;">⚡ Tough Challenge Overcome</span>
                        <button class="btn btn-secondary btn-sm" onclick="copyCardSnippet('biggest_challenge')" style="font-size:11px; padding:3px 8px;">Copy</button>
                    </div>
                    <div style="font-size:12px; color:var(--text-secondary); line-height:1.45;">${a.biggest_challenge}</div>
                </div>
            `;
            showToast(`✨ Generated 4 tailored application answers for ${company}!`);
        }
    } catch (e) {
        container.innerHTML = `<div style="grid-column: 1/-1; color: #ef4444; padding: 10px;">Failed to generate answers: ${e.message}</div>`;
    }
}

function copyCardSnippet(key) {
    if (autofillState.customAnswers && autofillState.customAnswers[key]) {
        navigator.clipboard.writeText(autofillState.customAnswers[key]);
        showToast("📋 Copied answer to clipboard!");
    }
}

function openAutofillForJob(jobId, company, role) {
    switchView("autofill");
    const compInput = document.getElementById("af-gen-company");
    const roleInput = document.getElementById("af-gen-role");
    if (compInput) compInput.value = company;
    if (roleInput) roleInput.value = role;
    generateTailoredPortalAnswers();
    showToast(`⚡ Prepared Auto-Fill answers for ${company} (${role})`);
}
