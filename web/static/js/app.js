/**
 * NomadOS – Production-Ready AI Travel Companion Platform
 * Client Orchestration, 9-Module Trip Command, Progressive Flow, Contextual AI & Uber Integration
 */

document.addEventListener('DOMContentLoaded', () => {
    // ============================================================
    // APPLICATION STATE
    // ============================================================
    let currentRole = localStorage.getItem('nomados_user_role') || 'customer';
    let currentCurrency = localStorage.getItem('nomados_currency') || 'INR';
    let currentTrip = null;
    let extractedIntentData = null;
    let exploreDestinations = [];
    let loadedTemplates = [];

    // Current Traveler Profile Session
    let currentUser = JSON.parse(localStorage.getItem('nomados_user') || 'null') || {
        id: 'alex',
        name: 'Alex Morgan',
        tier: 'Executive Traveler',
        role: 'Corporate Executive',
        avatar: '👔',
        isBusiness: true
    };

    // Flashcards State
    let flashcardsState = {
        questions: [],
        currentIndex: 0,
        answers: {
            is_business: currentUser.isBusiness || false,
            trip_purpose: currentUser.isBusiness ? 'business' : 'leisure',
            origin_city: 'Bangalore',
            budget_amount: 48000,
            work_amenities: []
        }
    };

    // Uber Context
    const currentRideContext = {
        pickup: 'Bengaluru Kempegowda Intl Airport',
        dropoff: 'Taj Exotica Resort & Spa, Benaulim, Goa',
        selectedProduct: null,
        activeRequestId: null,
        pollingInterval: null
    };

    // ============================================================
    // DOM REFERENCES
    // ============================================================
    // Top Navigation & User Profile
    const navBtnPlan = document.getElementById('navBtnPlan');
    const navBtnDashboard = document.getElementById('navBtnDashboard');
    const navBtnExplore = document.getElementById('navBtnExplore');
    const openAiDrawerBtn = document.getElementById('openAiDrawerBtn');

    // Profile & Auth Elements
    const userProfileBtn = document.getElementById('userProfileBtn');
    const headerUserAvatar = document.getElementById('headerUserAvatar');
    const headerUserName = document.getElementById('headerUserName');
    const headerUserTier = document.getElementById('headerUserTier');
    const welcomeGreetingHeading = document.getElementById('welcomeGreetingHeading');
    const authModal = document.getElementById('authModal');
    const authModalClose = document.getElementById('authModalClose');
    const authProfilesList = document.getElementById('authProfilesList');
    const authConfirmBtn = document.getElementById('authConfirmBtn');
    const authLogoutBtn = document.getElementById('authLogoutBtn');

    // Views
    const viewPlanTrip = document.getElementById('viewPlanTrip');
    const viewTripDashboard = document.getElementById('viewTripDashboard');
    const viewExplore = document.getElementById('viewExplore');

    // Welcome Hub & Templates
    const welcomeHubSection = document.getElementById('welcomeHubSection');
    const templatesCarouselGrid = document.getElementById('templatesCarouselGrid');
    const templateFilterPills = document.getElementById('templateFilterPills');

    // Conversational Chat Inception
    const chatPromptChips = document.getElementById('chatPromptChips');

    // Flashcards Elements
    const flashcardsContainer = document.getElementById('flashcardsContainer');
    const cardStepPill = document.getElementById('cardStepPill');
    const cardCategoryBadge = document.getElementById('cardCategoryBadge');
    const cardProgressFill = document.getElementById('cardProgressFill');
    const cardIcon = document.getElementById('cardIcon');
    const cardTitle = document.getElementById('cardTitle');
    const cardSubtitle = document.getElementById('cardSubtitle');
    const cardOptionsGrid = document.getElementById('cardOptionsGrid');
    const cardCustomInputWrap = document.getElementById('cardCustomInputWrap');
    const cardCustomLabel = document.getElementById('cardCustomLabel');
    const cardCustomInput = document.getElementById('cardCustomInput');
    const btnCardPrev = document.getElementById('btnCardPrev');
    const btnCardNext = document.getElementById('btnCardNext');
    const btnCardFinish = document.getElementById('btnCardFinish');
    const cardStepDots = document.getElementById('cardStepDots');

    // Currency Switcher
    const btnCurrencyINR = document.getElementById('btnCurrencyINR');
    const btnCurrencyUSD = document.getElementById('btnCurrencyUSD');

    // Role Switcher
    const roleToggleBtn = document.getElementById('roleToggleBtn');
    const roleIcon = document.getElementById('roleIcon');
    const roleLabel = document.getElementById('roleLabel');
    const roleBadge = document.getElementById('roleBadge');

    // Hero Natural Planning
    const heroPlanForm = document.getElementById('heroPlanForm');
    const heroQueryInput = document.getElementById('heroQueryInput');
    const heroSubmitBtn = document.getElementById('heroSubmitBtn');
    const heroSpinner = document.getElementById('heroSpinner');
    const starterPillsGrid = document.getElementById('starterPillsGrid');

    // Destination Recommendations
    const destRecommendationsContainer = document.getElementById('destRecommendationsContainer');
    const destCardsGrid = document.getElementById('destCardsGrid');
    const recCountBadge = document.getElementById('recCountBadge');

    // Progressive Form
    const progressiveCard = document.getElementById('progressiveCard');
    const progOriginInput = document.getElementById('progOriginInput');
    const companionSelect = document.getElementById('companionSelect');
    const durationSelect = document.getElementById('durationSelect');
    const transportSelect = document.getElementById('transportSelect');
    const budgetSlider = document.getElementById('budgetSlider');
    const budgetDisplayVal = document.getElementById('budgetDisplayVal');
    const progGenerateBtn = document.getElementById('progGenerateBtn');

    // Dashboard Hero & Progress
    const dashTripTitle = document.getElementById('dashTripTitle');
    const dashTripMetaTags = document.getElementById('dashTripMetaTags');
    const heroCurrencyBadge = document.getElementById('heroCurrencyBadge');
    const dashHeroBudget = document.getElementById('dashHeroBudget');
    const dashProgressPct = document.getElementById('dashProgressPct');
    const dashProgressFill = document.getElementById('dashProgressFill');
    const dashProgressCheckpoints = document.getElementById('dashProgressCheckpoints');
    const dashCopyMarkdownBtn = document.getElementById('dashCopyMarkdownBtn');
    const dashExportJsonBtn = document.getElementById('dashExportJsonBtn');
    const dashAskAiBtn = document.getElementById('dashAskAiBtn');

    // 9-Module Subtab Panels & Elements
    const dashTabs = document.querySelectorAll('.dash-tab');
    const subtabPanels = document.querySelectorAll('.subtab-panel');

    // Subtab: Overview
    const dashOverviewReason = document.getElementById('dashOverviewReason');
    const dashOverviewMetrics = document.getElementById('dashOverviewMetrics');
    const dashOverviewTipsList = document.getElementById('dashOverviewTipsList');
    const dashOverviewTransitAdvice = document.getElementById('dashOverviewTransitAdvice');

    // Subtab: Itinerary
    const dashDaysContainer = document.getElementById('dashDaysContainer');
    const btnAiOptimizeItinerary = document.getElementById('btnAiOptimizeItinerary');

    // Subtab: Travel
    const dashTransitRouteBadge = document.getElementById('dashTransitRouteBadge');
    const dashTransportGrid = document.getElementById('dashTransportGrid');

    // Subtab: Hotels
    const dashHotelsGrid = document.getElementById('dashHotelsGrid');
    const btnAiFindCheaperHotel = document.getElementById('btnAiFindCheaperHotel');

    // Subtab: Activities
    const dashActivitiesGrid = document.getElementById('dashActivitiesGrid');
    const dashActivitiesCountBadge = document.getElementById('dashActivitiesCountBadge');

    // Subtab: Restaurants
    const dashRestaurantsGrid = document.getElementById('dashRestaurantsGrid');
    const mealFilterGroup = document.getElementById('mealFilterGroup');

    // Subtab: Budget & Corporate Expenses
    const dashBudgetSummaryBanner = document.getElementById('dashBudgetSummaryBanner');
    const dashBudgetBarsList = document.getElementById('dashBudgetBarsList');
    const btnAiReduceBudget = document.getElementById('btnAiReduceBudget');
    const dashCorporateExpensePanel = document.getElementById('dashCorporateExpensePanel');
    const corpReimbursementBadge = document.getElementById('corpReimbursementBadge');
    const dashCorpStatsGrid = document.getElementById('dashCorpStatsGrid');
    const btnExportExpenseReport = document.getElementById('btnExportExpenseReport');

    // Subtab: Packing
    const dashPackingFill = document.getElementById('dashPackingFill');
    const dashPackingCountText = document.getElementById('dashPackingCountText');
    const dashPackingPercentText = document.getElementById('dashPackingPercentText');
    const btnCheckAllPacking = document.getElementById('btnCheckAllPacking');
    const btnResetPacking = document.getElementById('btnResetPacking');
    const dashPreTripList = document.getElementById('dashPreTripList');
    const dashPackingLayout = document.getElementById('dashPackingLayout');

    // Subtab: Reminders
    const dashRemindersGrid = document.getElementById('dashRemindersGrid');

    // Explore Gallery
    const exploreGalleryGrid = document.getElementById('exploreGalleryGrid');

    // AI Drawer
    const aiDrawer = document.getElementById('aiDrawer');
    const aiDrawerClose = document.getElementById('aiDrawerClose');
    const aiChatForm = document.getElementById('aiChatForm');
    const aiChatInput = document.getElementById('aiChatInput');
    const aiChatMessages = document.getElementById('aiChatMessages');
    const aiPills = document.querySelectorAll('.ai-pill');

    // Uber Modal
    const uberModal = document.getElementById('uberModal');
    const uberModalClose = document.getElementById('uberModalClose');
    const uberPickupText = document.getElementById('uberPickupText');
    const uberDropoffText = document.getElementById('uberDropoffText');
    const uberProductsList = document.getElementById('uberProductsList');
    const uberBookBtn = document.getElementById('uberBookBtn');
    const uberAppDeepLink = document.getElementById('uberAppDeepLink');
    const uberQuotesView = document.getElementById('uberQuotesView');
    const uberTrackingView = document.getElementById('uberTrackingView');
    const uberTrackingStatus = document.getElementById('uberTrackingStatus');
    const uberTrackingEta = document.getElementById('uberTrackingEta');
    const uberDriverName = document.getElementById('uberDriverName');
    const uberDriverRating = document.getElementById('uberDriverRating');
    const uberVehicleDesc = document.getElementById('uberVehicleDesc');
    const uberProgressFill = document.getElementById('uberProgressFill');
    const uberCancelRideBtn = document.getElementById('uberCancelRideBtn');
    const uberDoneBtn = document.getElementById('uberDoneBtn');

    // New Trip & Save Progress Action Elements
    const navBtnNewTrip = document.getElementById('navBtnNewTrip');
    const heroStepBuilderBtn = document.getElementById('heroStepBuilderBtn');
    const dashSaveTripBtn = document.getElementById('dashSaveTripBtn');
    const dashNewTripBtn = document.getElementById('dashNewTripBtn');

    // Inception Dual-Mode Elements
    const btnModeStepWizard = document.getElementById('btnModeStepWizard');
    const btnModeNaturalAI = document.getElementById('btnModeNaturalAI');
    const stepByStepWizardView = document.getElementById('stepByStepWizardView');
    const naturalPromptModeView = document.getElementById('naturalPromptModeView');

    // Step-by-Step Wizard Elements
    const wizardStepCounter = document.getElementById('wizardStepCounter');
    const wizardStepBadge = document.getElementById('wizardStepBadge');
    const wizardProgressBar = document.getElementById('wizardProgressBar');
    const wizDestinationInput = document.getElementById('wizDestinationInput');
    const wizOriginInput = document.getElementById('wizOriginInput');
    const wizDurationGrid = document.getElementById('wizDurationGrid');
    const wizCompanionSelect = document.getElementById('wizCompanionSelect');
    const wizStyleSelect = document.getElementById('wizStyleSelect');
    const wizBudgetPresets = document.getElementById('wizBudgetPresets');
    const wizCustomBudgetInput = document.getElementById('wizCustomBudgetInput');
    const wizCurrencySymbol = document.getElementById('wizCurrencySymbol');
    const wizTierBudgetAmount = document.getElementById('wizTierBudgetAmount');
    const wizTierComfortAmount = document.getElementById('wizTierComfortAmount');
    const wizTierPremiumAmount = document.getElementById('wizTierPremiumAmount');
    const wizSummaryPills = document.getElementById('wizSummaryPills');
    const btnWizBack = document.getElementById('btnWizBack');
    const btnWizNext = document.getElementById('btnWizNext');
    const btnWizFinish = document.getElementById('btnWizFinish');
    const wizSpinner = document.getElementById('wizSpinner');
    const wizDotsIndicator = document.getElementById('wizDotsIndicator');

    // Custom Checklist Form Elements
    const addChecklistForm = document.getElementById('addChecklistForm');
    const newChecklistTitle = document.getElementById('newChecklistTitle');
    const newChecklistCategory = document.getElementById('newChecklistCategory');


    // ============================================================
    // TOAST NOTIFICATIONS & FEEDBACK
    // ============================================================
    function showToast(message, type = 'info') {
        let container = document.getElementById('nomados-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'nomados-toast-container';
            container.className = 'nomados-toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = `nomados-toast toast-${type}`;
        const icon = type === 'success' ? '✅' : type === 'error' ? '⚠️' : type === 'warning' ? '🔔' : 'ℹ️';
        toast.innerHTML = `<span style="font-size: 1.15rem; line-height: 1;">${icon}</span><span>${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(12px)';
            setTimeout(() => toast.remove(), 350);
        }, 3600);
    }
    window.showToast = showToast;

    // ============================================================
    // CURRENCY & FORMATTING HELPERS
    // ============================================================
    function formatCurrency(amount, targetCurr = currentCurrency) {
        if (amount === undefined || amount === null || isNaN(amount)) return '—';
        if (targetCurr === 'USD') {
            return `$${Math.round(amount).toLocaleString('en-US')}`;
        }
        return `₹${Math.round(amount).toLocaleString('en-IN')}`;
    }

    function setCurrency(curr) {
        currentCurrency = curr;
        localStorage.setItem('nomados_currency', curr);

        if (btnCurrencyINR && btnCurrencyUSD) {
            if (curr === 'USD') {
                btnCurrencyUSD.classList.add('active');
                btnCurrencyINR.classList.remove('active');
                if (budgetSlider) {
                    budgetSlider.min = "100";
                    budgetSlider.max = "5000";
                    budgetSlider.step = "50";
                    budgetSlider.value = "750";
                    updateBudgetDisplay();
                }
            } else {
                btnCurrencyINR.classList.add('active');
                btnCurrencyUSD.classList.remove('active');
                if (budgetSlider) {
                    budgetSlider.min = "5000";
                    budgetSlider.max = "100000";
                    budgetSlider.step = "1000";
                    budgetSlider.value = "20000";
                    updateBudgetDisplay();
                }
            }
        }

        // Synchronize Step-by-Step Wizard Budget Controls
        if (wizCurrencySymbol) {
            wizCurrencySymbol.textContent = curr === 'USD' ? '$' : '₹';
        }
        if (wizTierBudgetAmount && wizTierComfortAmount && wizTierPremiumAmount) {
            if (curr === 'USD') {
                wizTierBudgetAmount.textContent = '$200';
                wizTierComfortAmount.textContent = '$450';
                wizTierPremiumAmount.textContent = '$850';
                if (wizCustomBudgetInput && (wizCustomBudgetInput.value === '35000' || wizCustomBudgetInput.value === '15000' || wizCustomBudgetInput.value === '65000')) {
                    wizCustomBudgetInput.value = '450';
                    if (typeof wizardState !== 'undefined') wizardState.budgetAmount = 450;
                }
            } else {
                wizTierBudgetAmount.textContent = '₹15,000';
                wizTierComfortAmount.textContent = '₹35,000';
                wizTierPremiumAmount.textContent = '₹65,000';
                if (wizCustomBudgetInput && (wizCustomBudgetInput.value === '450' || wizCustomBudgetInput.value === '200' || wizCustomBudgetInput.value === '850')) {
                    wizCustomBudgetInput.value = '35000';
                    if (typeof wizardState !== 'undefined') wizardState.budgetAmount = 35000;
                }
            }
            if (typeof updateWizardSummary === 'function') {
                updateWizardSummary();
            }
        }

        if (heroCurrencyBadge) {
            heroCurrencyBadge.textContent = curr === 'USD' ? 'USD ($)' : 'INR (₹)';
        }

        if (currentTrip) {
            renderTripDashboard(currentTrip);
        }
    }

    if (btnCurrencyINR) btnCurrencyINR.addEventListener('click', () => setCurrency('INR'));
    if (btnCurrencyUSD) btnCurrencyUSD.addEventListener('click', () => setCurrency('USD'));

    // ============================================================
    // ROLE SWITCHER (Traveler Mode vs Admin AI HUD)
    // ============================================================
    function setRole(role) {
        currentRole = role;
        localStorage.setItem('nomados_user_role', role);

        if (role === 'admin') {
            document.body.classList.remove('traveler-mode');
            document.body.classList.add('admin-mode');
            if (roleIcon) roleIcon.textContent = '🛠️';
            if (roleLabel) roleLabel.textContent = 'Admin AI HUD';
            if (roleBadge) roleBadge.textContent = 'Engineering';
            if (roleToggleBtn) roleToggleBtn.classList.add('admin-active');
        } else {
            document.body.classList.remove('admin-mode');
            document.body.classList.add('traveler-mode');
            if (roleIcon) roleIcon.textContent = '✈️';
            if (roleLabel) roleLabel.textContent = 'Traveler Mode';
            if (roleBadge) roleBadge.textContent = 'Customer';
            if (roleToggleBtn) roleToggleBtn.classList.remove('admin-active');
        }
    }

    if (roleToggleBtn) {
        roleToggleBtn.addEventListener('click', () => {
            setRole(currentRole === 'customer' ? 'admin' : 'customer');
        });
    }
    setRole(currentRole);

    // ============================================================
    // CLIENT-SIDE ROUTER / VIEW SWITCHER
    // ============================================================
    function switchView(viewName) {
        [viewPlanTrip, viewTripDashboard, viewExplore].forEach(v => {
            if (v) {
                v.classList.add('hidden');
                v.classList.remove('active');
            }
        });

        [navBtnPlan, navBtnDashboard, navBtnExplore].forEach(b => {
            if (b) b.classList.remove('active');
        });

        if (viewName === 'plan') {
            if (viewPlanTrip) {
                viewPlanTrip.classList.remove('hidden');
                viewPlanTrip.classList.add('active');
            }
            if (navBtnPlan) navBtnPlan.classList.add('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else if (viewName === 'dashboard') {
            if (viewTripDashboard) {
                viewTripDashboard.classList.remove('hidden');
                viewTripDashboard.classList.add('active');
            }
            if (navBtnDashboard) navBtnDashboard.classList.add('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else if (viewName === 'explore') {
            if (viewExplore) {
                viewExplore.classList.remove('hidden');
                viewExplore.classList.add('active');
            }
            if (navBtnExplore) navBtnExplore.classList.add('active');
            loadExploreDestinations();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }

    if (navBtnPlan) navBtnPlan.addEventListener('click', () => switchView('plan'));
    if (navBtnDashboard) navBtnDashboard.addEventListener('click', () => switchView('dashboard'));
    if (navBtnExplore) navBtnExplore.addEventListener('click', () => switchView('explore'));

    // ============================================================
    // NEW TRIP & SAVE PROGRESS WORKFLOWS
    // ============================================================
    function startNewTripFlow() {
        switchView('plan');
        goToWizardStep(1);
        if (stepByStepWizardView && naturalPromptModeView) {
            stepByStepWizardView.classList.remove('hidden');
            stepByStepWizardView.classList.add('active');
            naturalPromptModeView.classList.add('hidden');
            if (btnModeStepWizard && btnModeNaturalAI) {
                btnModeStepWizard.classList.add('active');
                btnModeNaturalAI.classList.remove('active');
            }
        }
        const inceptionCard = document.getElementById('chatInceptionSection');
        if (inceptionCard) {
            inceptionCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        if (wizDestinationInput) {
            setTimeout(() => {
                wizDestinationInput.focus();
                wizDestinationInput.select();
            }, 300);
        }
        showToast('Design your new trip step-by-step or use natural AI prompt!', 'info');
    }
    window.startNewTripFlow = startNewTripFlow;

    if (navBtnNewTrip) navBtnNewTrip.addEventListener('click', startNewTripFlow);
    if (dashNewTripBtn) dashNewTripBtn.addEventListener('click', startNewTripFlow);

    async function saveTripProgress() {
        if (!currentTrip) {
            showToast('No active trip loaded to save. Plan a trip first!', 'warning');
            return;
        }

        const tripId = currentTrip.trip_id || currentTrip.id || ('trip_' + Date.now());
        currentTrip.trip_id = tripId;
        currentTrip.updated_at = new Date().toISOString();

        // 1. Immediately cache in localStorage for instant offline safety
        localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));

        // 2. Temporarily show saving spinner state on button
        if (dashSaveTripBtn) {
            dashSaveTripBtn.disabled = true;
            dashSaveTripBtn.innerHTML = `<span>Saving...</span><div class="spinner" style="width:13px;height:13px;border-width:2px;display:inline-block;margin-left:6px;"></div>`;
        }

        // 3. Persist to backend SQLite DB
        try {
            const res = await fetch(`/api/v1/trip/${encodeURIComponent(tripId)}/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentTrip)
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            showToast(`Trip progress saved successfully! (Trip ID: ${tripId})`, 'success');
            if (dashSaveTripBtn) {
                dashSaveTripBtn.innerHTML = `<span class="btn-icon">✅</span><span>Saved!</span>`;
                setTimeout(() => {
                    dashSaveTripBtn.disabled = false;
                    dashSaveTripBtn.innerHTML = `<span class="btn-icon">💾</span><span>Save Progress</span>`;
                }, 2400);
            }
        } catch (err) {
            console.warn('Backend save encountered error, saved locally in browser:', err);
            showToast('Trip progress saved locally in browser!', 'info');
            if (dashSaveTripBtn) {
                dashSaveTripBtn.innerHTML = `<span class="btn-icon">💾</span><span>Saved Locally</span>`;
                setTimeout(() => {
                    dashSaveTripBtn.disabled = false;
                    dashSaveTripBtn.innerHTML = `<span class="btn-icon">💾</span><span>Save Progress</span>`;
                }, 2400);
            }
        }
    }
    window.saveTripProgress = saveTripProgress;

    if (dashSaveTripBtn) dashSaveTripBtn.addEventListener('click', saveTripProgress);

    // ============================================================
    // DUAL-MODE TRIP INCEPTION SWITCHER (Step-by-Step vs Natural AI)
    // ============================================================
    if (btnModeStepWizard && btnModeNaturalAI) {
        btnModeStepWizard.addEventListener('click', () => {
            btnModeStepWizard.classList.add('active');
            btnModeNaturalAI.classList.remove('active');
            if (stepByStepWizardView) {
                stepByStepWizardView.classList.remove('hidden');
                stepByStepWizardView.classList.add('active');
            }
            if (naturalPromptModeView) {
                naturalPromptModeView.classList.add('hidden');
                naturalPromptModeView.classList.remove('active');
            }
        });

        btnModeNaturalAI.addEventListener('click', () => {
            btnModeNaturalAI.classList.add('active');
            btnModeStepWizard.classList.remove('active');
            if (naturalPromptModeView) {
                naturalPromptModeView.classList.remove('hidden');
                naturalPromptModeView.classList.add('active');
            }
            if (stepByStepWizardView) {
                stepByStepWizardView.classList.add('hidden');
                stepByStepWizardView.classList.remove('active');
            }
            if (heroQueryInput) {
                heroQueryInput.focus();
            }
        });
    }

    if (heroStepBuilderBtn) {
        heroStepBuilderBtn.addEventListener('click', () => {
            if (btnModeStepWizard) btnModeStepWizard.click();
            const inceptionCard = document.getElementById('chatInceptionSection');
            if (inceptionCard) {
                inceptionCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            if (wizDestinationInput) {
                setTimeout(() => wizDestinationInput.focus(), 300);
            }
        });
    }

    // ============================================================
    // STEP-BY-STEP MINIMAL QUESTIONS BUILDER CONTROLLER
    // ============================================================
    const wizardState = {
        currentStep: 1,
        totalSteps: 4,
        destination: 'Tokyo',
        origin: 'Bangalore',
        duration: 3,
        companion: 'Couple',
        style: 'Food & Culture',
        budgetTier: 'comfort',
        budgetAmount: currentCurrency === 'USD' ? 450 : 35000
    };

    const wizardStepTitles = {
        1: 'Destination & Origin',
        2: 'Trip Duration',
        3: 'Party & Travel Vibe',
        4: 'Budget & Review'
    };

    function goToWizardStep(stepNum) {
        if (stepNum < 1 || stepNum > wizardState.totalSteps) return;
        wizardState.currentStep = stepNum;

        // Hide all steps, show active step
        for (let i = 1; i <= wizardState.totalSteps; i++) {
            const stepPanel = document.getElementById(`wizardStep${i}`);
            if (stepPanel) {
                if (i === stepNum) {
                    stepPanel.classList.remove('hidden');
                    stepPanel.classList.add('active');
                } else {
                    stepPanel.classList.add('hidden');
                    stepPanel.classList.remove('active');
                }
            }
        }

        // Update step counter & badge
        if (wizardStepCounter) {
            wizardStepCounter.textContent = `Step ${stepNum} of ${wizardState.totalSteps}`;
        }
        if (wizardStepBadge) {
            wizardStepBadge.textContent = wizardStepTitles[stepNum] || 'Trip Planning';
        }

        // Update progress bar width
        if (wizardProgressBar) {
            const pct = Math.round((stepNum / wizardState.totalSteps) * 100);
            wizardProgressBar.style.width = `${pct}%`;
        }

        // Update stepper dots
        if (wizDotsIndicator) {
            wizDotsIndicator.querySelectorAll('.wdot').forEach(dot => {
                const s = parseInt(dot.getAttribute('data-step'), 10);
                if (s === stepNum) {
                    dot.classList.add('active');
                } else {
                    dot.classList.remove('active');
                }
            });
        }

        // Update Nav button states
        if (btnWizBack) {
            btnWizBack.disabled = (stepNum === 1);
        }
        if (btnWizNext && btnWizFinish) {
            if (stepNum === wizardState.totalSteps) {
                btnWizNext.classList.add('hidden');
                btnWizFinish.classList.remove('hidden');
            } else {
                btnWizNext.classList.remove('hidden');
                btnWizFinish.classList.add('hidden');
            }
        }

        updateWizardSummary();
    }
    window.goToWizardStep = goToWizardStep;

    function updateWizardSummary() {
        if (!wizSummaryPills) return;
        const currSym = currentCurrency === 'USD' ? '$' : '₹';
        const formattedBudget = `${currSym}${Number(wizardState.budgetAmount).toLocaleString()}`;
        wizSummaryPills.innerHTML = `
            <span class="spill">📍 ${wizardState.destination || 'Destination'}</span>
            <span class="spill">🛫 From ${wizardState.origin || 'Bangalore'}</span>
            <span class="spill">🗓️ ${wizardState.duration} Days</span>
            <span class="spill">👥 ${wizardState.companion}</span>
            <span class="spill">🎨 ${wizardState.style}</span>
            <span class="spill">💰 ${formattedBudget}</span>
        `;
    }

    // Step 1: Destination input & Quick picks
    if (wizDestinationInput) {
        wizDestinationInput.addEventListener('input', (e) => {
            wizardState.destination = e.target.value.trim() || 'Tokyo';
            updateWizardSummary();
            // Deselect pick chips if custom typed
            document.querySelectorAll('.wiz-pick-chip').forEach(chip => {
                if (chip.getAttribute('data-dest').toLowerCase() === wizardState.destination.toLowerCase()) {
                    chip.classList.add('active');
                } else {
                    chip.classList.remove('active');
                }
            });
        });
    }

    if (wizOriginInput) {
        wizOriginInput.addEventListener('input', (e) => {
            wizardState.origin = e.target.value.trim() || 'Bangalore';
            updateWizardSummary();
        });
    }

    document.querySelectorAll('.wiz-pick-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.wiz-pick-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const dest = chip.getAttribute('data-dest');
            if (dest) {
                wizardState.destination = dest;
                if (wizDestinationInput) wizDestinationInput.value = dest;
                updateWizardSummary();
            }
        });
    });

    // Step 2: Duration selection cards
    if (wizDurationGrid) {
        wizDurationGrid.addEventListener('click', (e) => {
            const card = e.target.closest('.wiz-pill-card');
            if (!card) return;
            wizDurationGrid.querySelectorAll('.wiz-pill-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            const days = parseInt(card.getAttribute('data-days'), 10) || 3;
            wizardState.duration = days;
            updateWizardSummary();
        });
    }

    // Step 3: Companions & Travel Style chips
    if (wizCompanionSelect) {
        wizCompanionSelect.addEventListener('click', (e) => {
            const chip = e.target.closest('.wiz-sel-chip');
            if (!chip) return;
            wizCompanionSelect.querySelectorAll('.wiz-sel-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            wizardState.companion = chip.getAttribute('data-val') || 'Couple';
            updateWizardSummary();
        });
    }

    if (wizStyleSelect) {
        wizStyleSelect.addEventListener('click', (e) => {
            const chip = e.target.closest('.wiz-sel-chip');
            if (!chip) return;
            wizStyleSelect.querySelectorAll('.wiz-sel-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            wizardState.style = chip.getAttribute('data-val') || 'Food & Culture';
            updateWizardSummary();
        });
    }

    // Step 4: Budget presets & custom amount
    if (wizBudgetPresets) {
        wizBudgetPresets.addEventListener('click', (e) => {
            const card = e.target.closest('.budget-preset-card');
            if (!card) return;
            wizBudgetPresets.querySelectorAll('.budget-preset-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            const tier = card.getAttribute('data-tier');
            wizardState.budgetTier = tier;

            const isUSD = currentCurrency === 'USD';
            let amount = 35000;
            if (tier === 'budget') amount = isUSD ? 200 : 15000;
            else if (tier === 'comfort') amount = isUSD ? 450 : 35000;
            else if (tier === 'premium') amount = isUSD ? 850 : 65000;

            wizardState.budgetAmount = amount;
            if (wizCustomBudgetInput) wizCustomBudgetInput.value = amount;
            updateWizardSummary();
        });
    }

    if (wizCustomBudgetInput) {
        wizCustomBudgetInput.addEventListener('input', (e) => {
            const val = parseInt(e.target.value, 10);
            if (!isNaN(val) && val > 0) {
                wizardState.budgetAmount = val;
                if (wizBudgetPresets) {
                    wizBudgetPresets.querySelectorAll('.budget-preset-card').forEach(c => c.classList.remove('active'));
                }
                updateWizardSummary();
            }
        });
    }

    // Stepper Navigation buttons
    if (btnWizBack) {
        btnWizBack.addEventListener('click', () => {
            if (wizardState.currentStep > 1) {
                goToWizardStep(wizardState.currentStep - 1);
            }
        });
    }

    if (btnWizNext) {
        btnWizNext.addEventListener('click', () => {
            if (wizardState.currentStep === 1) {
                const dest = wizDestinationInput ? wizDestinationInput.value.trim() : wizardState.destination;
                if (!dest) {
                    showToast('Please enter or select a destination!', 'warning');
                    if (wizDestinationInput) wizDestinationInput.focus();
                    return;
                }
                wizardState.destination = dest;
            }
            if (wizardState.currentStep < wizardState.totalSteps) {
                goToWizardStep(wizardState.currentStep + 1);
            }
        });
    }

    if (wizDotsIndicator) {
        wizDotsIndicator.querySelectorAll('.wdot').forEach(dot => {
            dot.addEventListener('click', () => {
                const s = parseInt(dot.getAttribute('data-step'), 10);
                if (s) goToWizardStep(s);
            });
        });
    }

    async function synthesizeFromWizard() {
        if (!wizardState.destination) {
            showToast('Please specify a destination to begin!', 'warning');
            goToWizardStep(1);
            if (wizDestinationInput) wizDestinationInput.focus();
            return;
        }

        if (btnWizFinish) {
            btnWizFinish.disabled = true;
            btnWizFinish.innerHTML = `<span>Synthesizing 9 Modules...</span><div class="spinner" style="display:inline-block;width:14px;height:14px;border-width:2px;margin-left:8px;"></div>`;
        }

        try {
            const isBusiness = wizardState.companion.toLowerCase().includes('business') || wizardState.style.toLowerCase().includes('business');
            const payload = {
                query: `${wizardState.duration}-day ${wizardState.style} journey to ${wizardState.destination} for ${wizardState.companion}`,
                origin_city: wizardState.origin || 'Bangalore',
                destination: wizardState.destination,
                duration_days: parseInt(wizardState.duration, 10),
                companions: wizardState.companion,
                budget_amount: parseInt(wizardState.budgetAmount, 10),
                currency: currentCurrency,
                is_business: isBusiness,
                trip_purpose: isBusiness ? 'business' : 'leisure',
                company_name: currentUser.name + " Corporation",
                work_amenities: isBusiness ? ["High-Speed Wi-Fi (150+ Mbps)", "Quiet Meeting Suites", "Uber Premier Booking"] : [],
                interests: [wizardState.style, "Sightseeing", "Local Food", "Culture", "Relaxation"]
            };

            showToast(`Synthesizing tailored ${wizardState.duration}-day trip to ${wizardState.destination}...`, 'info');

            const res = await fetch('/api/v1/trip/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to generate trip`);
            const trip = await res.json();
            currentTrip = trip;
            localStorage.setItem('nomados_current_trip', JSON.stringify(trip));

            showToast(`🎉 ${trip.destination} journey successfully synthesized with 9 modules!`, 'success');
            switchView('dashboard');
            renderTripDashboard(trip);
        } catch (err) {
            console.error('Wizard trip generation failed:', err);
            showToast(`Failed to generate trip: ${err.message}`, 'error');
        } finally {
            if (btnWizFinish) {
                btnWizFinish.disabled = false;
                btnWizFinish.innerHTML = `<span class="btn-icon">⚡</span><span>Synthesize 9-Module Trip 🚀</span>`;
            }
        }
    }

    if (btnWizFinish) {
        btnWizFinish.addEventListener('click', synthesizeFromWizard);
    }

    // ============================================================
    // TRAVELER PROFILE & AUTH ONBOARDING GATE
    // ============================================================
    function updateUserProfileUI() {
        if (headerUserAvatar) headerUserAvatar.textContent = currentUser.avatar || '👔';
        if (headerUserName) headerUserName.textContent = currentUser.name || 'Alex Morgan';
        if (headerUserTier) headerUserTier.textContent = currentUser.tier || 'Executive Traveler';
        if (welcomeGreetingHeading) welcomeGreetingHeading.textContent = `Welcome to NomadOS, ${currentUser.name.split(' ')[0]}`;

        if (authProfilesList) {
            authProfilesList.querySelectorAll('.auth-profile-card').forEach(card => {
                if (card.getAttribute('data-user-id') === currentUser.id) {
                    card.classList.add('active');
                } else {
                    card.classList.remove('active');
                }
            });
        }
    }

    if (userProfileBtn) {
        userProfileBtn.addEventListener('click', () => {
            if (authModal) authModal.classList.remove('hidden');
        });
    }

    if (authModalClose) {
        authModalClose.addEventListener('click', () => {
            if (authModal) authModal.classList.add('hidden');
        });
    }

    if (authProfilesList) {
        authProfilesList.addEventListener('click', (e) => {
            const card = e.target.closest('.auth-profile-card');
            if (!card) return;
            authProfilesList.querySelectorAll('.auth-profile-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');

            const userName = card.getAttribute('data-user-name');
            if (authConfirmBtn) {
                authConfirmBtn.innerHTML = `<span>Continue as ${userName} ➔</span>`;
            }
        });
    }

    if (authConfirmBtn) {
        authConfirmBtn.addEventListener('click', () => {
            const activeCard = authProfilesList?.querySelector('.auth-profile-card.active');
            if (activeCard) {
                currentUser = {
                    id: activeCard.getAttribute('data-user-id'),
                    name: activeCard.getAttribute('data-user-name'),
                    tier: activeCard.getAttribute('data-user-tier'),
                    role: activeCard.getAttribute('data-user-role'),
                    avatar: activeCard.getAttribute('data-avatar'),
                    isBusiness: activeCard.getAttribute('data-is-business') === 'true'
                };
                localStorage.setItem('nomados_user', JSON.stringify(currentUser));
                updateUserProfileUI();
                flashcardsState.answers.is_business = currentUser.isBusiness;
                flashcardsState.answers.trip_purpose = currentUser.isBusiness ? 'business' : 'leisure';
            }
            if (authModal) authModal.classList.add('hidden');
        });
    }

    if (authLogoutBtn) {
        authLogoutBtn.addEventListener('click', () => {
            localStorage.removeItem('nomados_user');
            currentUser = {
                id: 'guest',
                name: 'Guest Traveler',
                tier: 'Standard Traveler',
                role: 'Quick Explorer',
                avatar: '👤',
                isBusiness: false
            };
            updateUserProfileUI();
            if (authModal) authModal.classList.add('hidden');
        });
    }

    // ============================================================
    // PREPLANNED CURATED TRIP BLUEPRINTS
    // ============================================================
    async function loadTripTemplates() {
        if (!templatesCarouselGrid) return;
        try {
            const res = await fetch('/api/v1/trip/templates');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            loadedTemplates = await res.json();
            renderTripTemplates('all');
        } catch (err) {
            console.error('Failed to load trip templates:', err);
            templatesCarouselGrid.innerHTML = `
                <div class="template-card-skeleton">
                    <span>Curated trip blueprints temporarily offline.</span>
                    <button type="button" class="btn-dest-explore" onclick="window.loadTripTemplates()">Retry Loading</button>
                </div>
            `;
        }
    }
    window.loadTripTemplates = loadTripTemplates;

    function renderTripTemplates(filter = 'all') {
        if (!templatesCarouselGrid || !loadedTemplates.length) return;

        let filtered = loadedTemplates;
        if (filter === 'business') {
            filtered = loadedTemplates.filter(t => t.is_business === true || t.trip_purpose === 'business');
        } else if (filter === 'leisure') {
            filtered = loadedTemplates.filter(t => !t.is_business && (t.trip_purpose === 'leisure' || t.trip_purpose === 'relaxation' || t.trip_purpose === 'family'));
        } else if (filter === 'culture') {
            filtered = loadedTemplates.filter(t => t.trip_purpose === 'culture' || t.destination === 'Tokyo' || t.destination === 'Kyoto');
        }

        const imageMap = {
            "Bangalore": "https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=800",
            "Goa": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800",
            "Tokyo": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800",
            "Coorg": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800",
            "Kyoto": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800"
        };

        templatesCarouselGrid.innerHTML = filtered.map(t => {
            const isBiz = t.is_business || false;
            const totalEst = t.budget?.estimated_total || 20000;
            const imgUrl = imageMap[t.destination] || "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800";
            
            let highlights = [
                `🏨 ${t.hotels?.[0]?.name || 'Luxury Accommodation'}`,
                `🚀 Multi-Modal Transit (${t.transportation?.[0]?.mode || 'Flight'})`,
                `🍴 Regional Dining & Local Highlights`
            ];
            if (isBiz) {
                highlights = [
                    `🏢 Dedicated Executive Meeting Suites & Tech Parks`,
                    `📶 150+ Mbps Verified Wi-Fi & Desk Workstations`,
                    `🚗 Uber Premier Executive Doorstep Transit`
                ];
            }

            return `
                <div class="template-card ${isBiz ? 'business-template' : ''}">
                    <div class="tmpl-img-wrap">
                        <img src="${imgUrl}" alt="${t.destination}" class="tmpl-img" onerror="this.src='https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800'">
                        <span class="tmpl-type-tag ${isBiz ? 'business' : ''}">${isBiz ? '💼 Executive Business' : '🏖️ Full Curated Journey'}</span>
                        <span class="tmpl-duration-badge">🗓️ ${t.duration_days} Days</span>
                    </div>
                    <div class="tmpl-body">
                        <h4 class="tmpl-title">${t.title || `${t.destination} Blueprint`}</h4>
                        <p class="tmpl-desc">${t.trade_off_reasoning ? t.trade_off_reasoning.slice(0, 115) + '...' : `Complete 9-module journey across ${t.destination} with verified stays, realistic pacing, and transit.`}</p>
                        <div class="tmpl-highlights-list">
                            ${highlights.map(h => `<div class="tmpl-highlight-item"><span>✓</span> ${h}</div>`).join('')}
                        </div>
                        <div class="tmpl-bottom-row">
                            <div class="tmpl-budget-group">
                                <small>Estimated Total</small>
                                <strong>${formatCurrency(totalEst, t.currency)}</strong>
                            </div>
                            <button type="button" class="btn-template-clone" data-clone-id="${t.trip_id}" onclick="window.cloneTripBlueprint('${t.trip_id}')">
                                <span>🚀 Clone & Use Trip</span>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    window.cloneTripBlueprint = async (templateId) => {
        try {
            const btn = document.querySelector(`[data-clone-id="${templateId}"]`);
            if (btn) {
                btn.innerHTML = `<span>Cloning...</span>`;
                btn.disabled = true;
            }

            const res = await fetch(`/api/v1/trip/templates/${templateId}/clone`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to clone blueprint`);
            const cloned = await res.json();
            currentTrip = cloned;
            localStorage.setItem('nomados_current_trip', JSON.stringify(cloned));

            switchView('dashboard');
            renderTripDashboard(cloned);
        } catch (err) {
            console.error('Failed to clone trip template:', err);
            alert(`Cloning error: ${err.message}`);
        }
    };

    if (templateFilterPills) {
        templateFilterPills.addEventListener('click', (e) => {
            const btn = e.target.closest('.tmpl-filter-btn');
            if (!btn) return;
            templateFilterPills.querySelectorAll('.tmpl-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const filter = btn.getAttribute('data-filter');
            renderTripTemplates(filter);
        });
    }

    // ============================================================
    // CONVERSATIONAL CHAT PROMPT CHIPS
    // ============================================================
    if (chatPromptChips) {
        chatPromptChips.addEventListener('click', (e) => {
            const chip = e.target.closest('.prompt-chip');
            if (!chip) return;
            const promptText = chip.getAttribute('data-prompt');
            if (heroQueryInput) {
                heroQueryInput.value = promptText;
                if (heroPlanForm) {
                    heroPlanForm.dispatchEvent(new Event('submit'));
                }
            }
        });
    }

    // ============================================================
    // INTERACTIVE FLASHCARDS ENGINE (Step-by-Step Questioning)
    // ============================================================
    function getOptionIcon(opt) {
        if (!opt) return '✨';
        const lower = opt.toLowerCase();
        if (lower.includes('corporate') || lower.includes('business') || lower.includes('meeting')) return '💼';
        if (lower.includes('leisure') || lower.includes('beach') || lower.includes('relax')) return '🏖️';
        if (lower.includes('family') || lower.includes('kid')) return '👨‍👩‍👧';
        if (lower.includes('adventure') || lower.includes('trek')) return '🏕️';
        if (lower.includes('flight') || lower.includes('fly')) return '✈️';
        if (lower.includes('train') || lower.includes('rail')) return '🚆';
        if (lower.includes('cab') || lower.includes('uber') || lower.includes('drive')) return '🚗';
        if (lower.includes('wi-fi') || lower.includes('fiber') || lower.includes('speed')) return '📶';
        if (lower.includes('acoustic') || lower.includes('quiet') || lower.includes('sound')) return '🎧';
        if (lower.includes('food') || lower.includes('culinary') || lower.includes('dining')) return '🍽️';
        return '✨';
    }

    function getOptionDescription(opt, category) {
        if (!opt) return '';
        const lower = opt.toLowerCase();
        if (lower.includes('corporate') || lower.includes('business')) return 'Focus blocks, high-speed Wi-Fi, quiet meeting acoustics & corporate expense tracking';
        if (lower.includes('leisure')) return 'Sunset beach shacks, relaxed pace, scenic leisure & authentic local dining';
        if (lower.includes('family')) return 'Child-friendly pacing, spacious resorts, gentle nature trails & comfortable transit';
        if (lower.includes('adventure')) return 'Outdoor excursions, scenic viewpoints, trekking trails & active exploration';
        if (lower.includes('wi-fi') || lower.includes('150+')) return 'Verified fiber speed for Zoom, Slack and seamless remote work';
        if (lower.includes('acoustic') || lower.includes('quiet')) return 'Curated venues with ambient decibels <50dB suitable for investor calls';
        if (lower.includes('reimbursable')) return 'Classified under company travel policy with itemized CSV expense claim generation';
        return 'Tailored for optimal journey quality and predictable timing';
    }

    function initFlashcards(questions, extracted) {
        if (!flashcardsContainer) return;
        flashcardsContainer.classList.remove('hidden');

        flashcardsState.questions = questions || [];
        flashcardsState.currentIndex = 0;

        if (extracted) {
            if (extracted.is_business !== undefined) flashcardsState.answers.is_business = extracted.is_business;
            if (extracted.trip_purpose) flashcardsState.answers.trip_purpose = extracted.trip_purpose;
            if (extracted.origin) flashcardsState.answers.origin_city = extracted.origin;
            if (extracted.budget_amount) flashcardsState.answers.budget_amount = extracted.budget_amount;
        }

        renderCurrentFlashcard();
        flashcardsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function renderCurrentFlashcard() {
        const total = flashcardsState.questions.length;
        const idx = flashcardsState.currentIndex;
        const q = flashcardsState.questions[idx];
        if (!q) return;

        if (cardStepPill) cardStepPill.textContent = `Card ${idx + 1} of ${total}`;
        if (cardCategoryBadge) cardCategoryBadge.textContent = q.card_title || q.category || 'Trip Specifications';
        if (cardProgressFill) cardProgressFill.style.width = `${Math.round(((idx + 1) / total) * 100)}%`;

        if (cardIcon) cardIcon.textContent = q.icon || '✨';
        if (cardTitle) cardTitle.textContent = q.question;
        if (cardSubtitle) cardSubtitle.textContent = q.card_subtitle || q.explanation || 'Select an option to refine your journey specifications:';

        if (cardStepDots) {
            cardStepDots.innerHTML = flashcardsState.questions.map((_, i) => `
                <span class="card-dot ${i === idx ? 'active' : ''}" data-step="${i + 1}"></span>
            `).join('');
        }

        if (btnCardPrev) btnCardPrev.disabled = (idx === 0);
        if (idx === total - 1) {
            if (btnCardNext) btnCardNext.classList.add('hidden');
            if (btnCardFinish) btnCardFinish.classList.remove('hidden');
        } else {
            if (btnCardNext) btnCardNext.classList.remove('hidden');
            if (btnCardFinish) btnCardFinish.classList.add('hidden');
        }

        if (cardOptionsGrid) {
            const currentAns = flashcardsState.answers;
            cardOptionsGrid.innerHTML = (q.options || []).map((opt, optIdx) => {
                let isSelected = false;
                if (idx === 0) {
                    if (opt.includes("Corporate") || opt.includes("Business")) {
                        isSelected = currentAns.is_business === true;
                    } else if (opt.includes("Family")) {
                        isSelected = currentAns.trip_purpose === 'family';
                    } else if (opt.includes("Adventure")) {
                        isSelected = currentAns.trip_purpose === 'adventure';
                    } else {
                        isSelected = (!currentAns.is_business && currentAns.trip_purpose === 'leisure');
                    }
                } else {
                    isSelected = (optIdx === 0);
                }

                return `
                    <div class="flashcard-opt-card ${isSelected ? 'selected' : ''}" data-opt-idx="${optIdx}" data-opt-text="${opt}">
                        <div class="opt-card-icon">${getOptionIcon(opt)}</div>
                        <div class="opt-card-body">
                            <div class="opt-card-title">${opt}</div>
                            <div class="opt-card-desc">${getOptionDescription(opt, q.category)}</div>
                        </div>
                    </div>
                `;
            }).join('');

            cardOptionsGrid.querySelectorAll('.flashcard-opt-card').forEach(card => {
                card.addEventListener('click', () => {
                    cardOptionsGrid.querySelectorAll('.flashcard-opt-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    const optText = card.getAttribute('data-opt-text');
                    handleFlashcardSelection(idx, optText);
                });
            });
        }

        if (cardCustomInputWrap && cardCustomInput) {
            if (q.field === 'origin_city' || q.field === 'origin' || q.card_title?.toLowerCase().includes('departure')) {
                cardCustomInputWrap.classList.remove('hidden');
                if (cardCustomLabel) cardCustomLabel.textContent = 'Or enter custom departure city:';
                cardCustomInput.value = flashcardsState.answers.origin_city || 'Bangalore';
            } else {
                cardCustomInputWrap.classList.add('hidden');
            }
        }
    }

    function handleFlashcardSelection(stepIdx, optText) {
        if (!optText) return;
        const lower = optText.toLowerCase();

        if (stepIdx === 0) {
            if (lower.includes('corporate') || lower.includes('business')) {
                flashcardsState.answers.is_business = true;
                flashcardsState.answers.trip_purpose = 'business';
                flashcardsState.answers.budget_amount = 48000;
            } else if (lower.includes('family')) {
                flashcardsState.answers.is_business = false;
                flashcardsState.answers.trip_purpose = 'family';
            } else if (lower.includes('adventure')) {
                flashcardsState.answers.is_business = false;
                flashcardsState.answers.trip_purpose = 'adventure';
            } else {
                flashcardsState.answers.is_business = false;
                flashcardsState.answers.trip_purpose = 'leisure';
            }
        } else if (stepIdx === 1) {
            const city = optText.split(' ')[0] || optText;
            flashcardsState.answers.origin_city = city;
            if (progOriginInput) progOriginInput.value = city;
        } else if (stepIdx === 2) {
            if (lower.includes('50,000') || lower.includes('executive')) {
                flashcardsState.answers.budget_amount = 50000;
            } else if (lower.includes('25,000') || lower.includes('comfort')) {
                flashcardsState.answers.budget_amount = 25000;
            } else if (lower.includes('corporate') || lower.includes('reimbursable')) {
                flashcardsState.answers.budget_amount = 48000;
                flashcardsState.answers.is_business = true;
            }
        } else if (stepIdx === 3) {
            flashcardsState.answers.work_amenities = [optText];
        }
    }

    async function synthesizeJourneyFromFlashcards() {
        if (btnCardFinish) {
            btnCardFinish.disabled = true;
            btnCardFinish.innerHTML = `<span>Synthesizing Tailored Schedule...</span><div class="spinner"></div>`;
        }

        try {
            const ans = flashcardsState.answers;
            let dest = extractedIntentData?.extracted?.destination;
            if (!dest) {
                const text = (heroQueryInput?.value || "").toLowerCase();
                if (text.includes("bangalore") || ans.is_business) dest = "Bangalore";
                else if (text.includes("manali")) dest = "Manali";
                else if (text.includes("tokyo")) dest = "Tokyo";
                else if (text.includes("coorg")) dest = "Coorg";
                else if (text.includes("kyoto")) dest = "Kyoto";
                else dest = "Goa";
            }

            const origin = (cardCustomInput && !cardCustomInputWrap.classList.contains('hidden') && cardCustomInput.value.trim()) ? 
                cardCustomInput.value.trim() : (ans.origin_city || progOriginInput?.value || 'Bangalore');

            const payload = {
                query: heroQueryInput?.value || `${ans.trip_purpose} trip to ${dest}`,
                origin_city: origin,
                destination: dest,
                duration_days: parseInt(getSelectedChipValue(durationSelect, '3'), 10),
                companions: ans.is_business ? "Colleagues" : getSelectedChipValue(companionSelect, 'Friends'),
                budget_amount: ans.budget_amount || (ans.is_business ? 48000 : 20000),
                currency: currentCurrency,
                is_business: ans.is_business,
                trip_purpose: ans.trip_purpose,
                company_name: currentUser.name + " Corporation",
                work_amenities: ans.work_amenities && ans.work_amenities.length > 0 ? ans.work_amenities : ["High-Speed Wi-Fi (150+ Mbps)", "Quiet Meeting Suites", "Uber Premier Booking"],
                transport_preference: getSelectedChipValue(transportSelect, 'Flight')
            };

            const res = await fetch('/api/v1/trip/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to generate trip`);
            const trip = await res.json();
            currentTrip = trip;
            localStorage.setItem('nomados_current_trip', JSON.stringify(trip));

            switchView('dashboard');
            renderTripDashboard(trip);
        } catch (err) {
            console.error('Flashcard synthesis error:', err);
            alert(`Error synthesizing schedule: ${err.message}`);
        } finally {
            if (btnCardFinish) {
                btnCardFinish.disabled = false;
                btnCardFinish.innerHTML = `<span>⚡ Synthesize Journey</span>`;
            }
        }
    }

    if (btnCardPrev) {
        btnCardPrev.addEventListener('click', () => {
            if (flashcardsState.currentIndex > 0) {
                flashcardsState.currentIndex--;
                renderCurrentFlashcard();
            }
        });
    }

    if (btnCardNext) {
        btnCardNext.addEventListener('click', () => {
            if (cardCustomInput && !cardCustomInputWrap.classList.contains('hidden') && cardCustomInput.value.trim()) {
                flashcardsState.answers.origin_city = cardCustomInput.value.trim();
            }
            if (flashcardsState.currentIndex < flashcardsState.questions.length - 1) {
                flashcardsState.currentIndex++;
                renderCurrentFlashcard();
            }
        });
    }

    if (btnCardFinish) {
        btnCardFinish.addEventListener('click', synthesizeJourneyFromFlashcards);
    }

    // ============================================================
    // STARTER PILLS (Section 2 & 3: Flexible Entry Points)
    // ============================================================
    const starterPromptMap = {
        know_destination: {
            text: "I want to go to Goa with 3 friends for 3 days around ₹20,000 focusing on beaches, great coastal seafood, and relaxed vibes.",
            origin: "Bangalore",
            companions: "Friends",
            duration: 3,
            transport: "Flight",
            budget: 20000
        },
        help_choose: {
            text: "Suggest a nice peaceful place to go with my family for 3 days around ₹22,000 with lush green nature and quiet surroundings.",
            origin: "Bangalore",
            companions: "Family with Kids",
            duration: 3,
            transport: "Cab",
            budget: 22000
        },
        concert: {
            text: "I wanna go to a live music concert or music festival with 2 friends for a weekend getaway around ₹18,000.",
            origin: "Bangalore",
            companions: "Friends",
            duration: 3,
            transport: "Flight",
            budget: 18000
        },
        family: {
            text: "I want a chill vacation with my family and parents for 4 days in a scenic, comfortable destination around ₹35,000.",
            origin: "Mumbai",
            companions: "Family with Kids",
            duration: 4,
            transport: "Train",
            budget: 35000
        },
        adventure: {
            text: "I want an adventurous trekking and river rafting trip with 3 friends for 4 days around ₹25,000.",
            origin: "Delhi",
            companions: "Friends",
            duration: 4,
            transport: "Bus",
            budget: 25000
        }
    };

    if (starterPillsGrid) {
        starterPillsGrid.addEventListener('click', (e) => {
            const pill = e.target.closest('.starter-pill');
            if (!pill) return;

            document.querySelectorAll('.starter-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const pillKey = pill.getAttribute('data-pill');
            const data = starterPromptMap[pillKey];
            if (data && heroQueryInput) {
                heroQueryInput.value = data.text;
                if (progOriginInput) progOriginInput.value = data.origin;
                selectChip(companionSelect, data.companions);
                selectChip(durationSelect, String(data.duration));
                selectChip(transportSelect, data.transport);
                if (budgetSlider) {
                    budgetSlider.value = currentCurrency === 'USD' ? Math.round(data.budget / 83) : data.budget;
                    updateBudgetDisplay();
                }
            }
        });
    }

    // Chip Selection Helpers
    function selectChip(container, value) {
        if (!container) return;
        const chips = container.querySelectorAll('.sel-chip');
        chips.forEach(c => {
            if (c.getAttribute('data-val') === value || c.textContent.includes(value)) {
                c.classList.add('active');
            } else {
                c.classList.remove('active');
            }
        });
    }

    function getSelectedChipValue(container, fallback) {
        if (!container) return fallback;
        const active = container.querySelector('.sel-chip.active');
        return active ? active.getAttribute('data-val') : fallback;
    }

    // Attach click listeners to all chip containers
    [companionSelect, durationSelect, transportSelect].forEach(container => {
        if (container) {
            container.addEventListener('click', (e) => {
                const chip = e.target.closest('.sel-chip');
                if (!chip) return;
                container.querySelectorAll('.sel-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
            });
        }
    });

    // Budget Slider
    function updateBudgetDisplay() {
        if (!budgetSlider || !budgetDisplayVal) return;
        const val = Number(budgetSlider.value);
        budgetDisplayVal.textContent = formatCurrency(val);
    }
    if (budgetSlider) {
        budgetSlider.addEventListener('input', updateBudgetDisplay);
        updateBudgetDisplay();
    }

    // ============================================================
    // AI REQUIREMENT EXTRACTION & DESTINATION DISCOVERY (POST /extract)
    // ============================================================
    if (heroPlanForm) {
        heroPlanForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const query = heroQueryInput.value.trim();
            if (!query) return;

            if (heroSubmitBtn) heroSubmitBtn.disabled = true;
            if (heroSpinner) heroSpinner.classList.remove('hidden');

            try {
                const res = await fetch('/api/v1/trip/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });

                if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to extract requirements`);
                const data = await res.json();
                extractedIntentData = data;

                // Sync extracted fields to progressive form
                const intent = data.extracted || data.extracted_intent || {};
                if (intent.origin && progOriginInput) progOriginInput.value = intent.origin;
                if (intent.group_type) selectChip(companionSelect, intent.group_type);
                if (intent.duration_days) selectChip(durationSelect, String(intent.duration_days));
                if (intent.budget_amount && budgetSlider) {
                    budgetSlider.value = intent.budget_amount;
                    updateBudgetDisplay();
                }

                // Render Destination Recommendations if present
                const dests = data.suggested_destinations || data.destination_recommendations || [];
                renderDestinationCards(dests);

                // Launch Interactive Flashcards for missing details / intent refinement
                if (data.progressive_questions && data.progressive_questions.length > 0) {
                    initFlashcards(data.progressive_questions, data.extracted);
                } else if (progressiveCard) {
                    progressiveCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }

            } catch (err) {
                console.error('Error during intent extraction:', err);
                alert(`Extraction failed: ${err.message}. Please try again.`);
            } finally {
                if (heroSubmitBtn) heroSubmitBtn.disabled = false;
                if (heroSpinner) heroSpinner.classList.add('hidden');
            }
        });
    }

    function renderDestinationCards(destinations) {
        if (!destRecommendationsContainer || !destCardsGrid) return;
        if (!destinations || destinations.length === 0) {
            destRecommendationsContainer.classList.add('hidden');
            return;
        }

        destRecommendationsContainer.classList.remove('hidden');
        if (recCountBadge) recCountBadge.textContent = `${destinations.length} Top Matches`;

        destCardsGrid.innerHTML = destinations.map(dest => `
            <div class="dest-rec-card glass-card">
                <div class="dest-card-img-wrap">
                    <img src="${dest.image_url || 'https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800'}" alt="${dest.name}" class="dest-card-img" onerror="this.src='https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800'">
                    <span class="dest-match-badge">${dest.match_score || 94}% Match</span>
                </div>
                <div class="dest-card-body">
                    <div class="dest-card-top">
                        <h4 class="dest-name">${dest.name}</h4>
                        <span class="dest-state">${dest.state_or_country || dest.state || ''}</span>
                    </div>
                    <div class="dest-tags-row">
                        ${(dest.vibe_tags || dest.tags || []).map(t => `<span class="dest-tag">${t}</span>`).join('')}
                    </div>
                    <p class="dest-rationale"><strong>Why it matches:</strong> ${dest.why_it_matches}</p>
                    <div class="dest-meta-stats">
                        <span>💰 ${dest.estimated_budget_range || formatCurrency(dest.estimated_budget || 20000)}</span>
                        <span>🗓️ Ideal: ${dest.ideal_duration_days || dest.ideal_duration || 3} Days</span>
                        <span>✨ ${dest.top_highlight || 'Scenic'}</span>
                    </div>
                    <div class="dest-actions-row">
                        <button type="button" class="btn-dest-explore" onclick="window.exploreDestQuick('${dest.name}')">Explore</button>
                        <button type="button" class="btn-dest-select" onclick="window.selectDestinationQuick('${dest.name}')">Select & Plan Trip ➔</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    window.exploreDestQuick = (destName) => {
        switchView('explore');
    };

    window.selectDestinationQuick = (destName) => {
        if (heroQueryInput) {
            heroQueryInput.value = `I want to plan a journey to ${destName} for ${getSelectedChipValue(durationSelect, '3')} days with my ${getSelectedChipValue(companionSelect, 'Friends')}.`;
        }
        if (progGenerateBtn) progGenerateBtn.click();
    };

    // ============================================================
    // COMPLETE TRIP SYNTHESIZER (POST /api/v1/trip/generate)
    // ============================================================
    if (progGenerateBtn) {
        progGenerateBtn.addEventListener('click', async () => {
            progGenerateBtn.disabled = true;
            progGenerateBtn.innerHTML = `<span>⚡ Synthesizing 9 Modules...</span><div class="spinner"></div>`;

            try {
                let destName = "Goa";
                if (extractedIntentData?.extracted?.destination) {
                    destName = extractedIntentData.extracted.destination;
                } else {
                    const text = (heroQueryInput?.value || "").toLowerCase();
                    if (text.includes("manali")) destName = "Manali";
                    else if (text.includes("coorg")) destName = "Coorg";
                    else if (text.includes("tokyo")) destName = "Tokyo";
                    else if (text.includes("paris")) destName = "Paris";
                    else if (text.includes("austin")) destName = "Austin";
                    else if (text.includes("kyoto")) destName = "Kyoto";
                }

                const origin = progOriginInput ? progOriginInput.value.trim() || 'Bangalore' : 'Bangalore';
                const duration = parseInt(getSelectedChipValue(durationSelect, '3'), 10);
                const companion = getSelectedChipValue(companionSelect, 'Friends');
                const transport = getSelectedChipValue(transportSelect, 'Flight');
                const budgetVal = budgetSlider ? parseInt(budgetSlider.value, 10) : 20000;

                const payload = {
                    query: heroQueryInput?.value || `Trip to ${destName}`,
                    origin_city: origin,
                    destination: destName,
                    duration_days: duration,
                    companions: companion,
                    budget_amount: budgetVal,
                    currency: currentCurrency,
                    transport_preference: transport,
                    interests: ["Sightseeing", "Beaches", "Local Culinary", "Culture", "Relaxation"]
                };

                const res = await fetch('/api/v1/trip/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to generate trip`);
                const trip = await res.json();
                currentTrip = trip;
                localStorage.setItem('nomados_current_trip', JSON.stringify(trip));

                switchView('dashboard');
                renderTripDashboard(trip);

            } catch (err) {
                console.error('Error generating trip:', err);
                alert(`Trip synthesis failed: ${err.message}. Check backend connection.`);
            } finally {
                progGenerateBtn.disabled = false;
                progGenerateBtn.innerHTML = `<span>⚡ Synthesize Full 9-Module Itinerary</span>`;
            }
        });
    }

    // ============================================================
    // RENDER CANONICAL 9-MODULE DASHBOARD
    // ============================================================
    function renderTripDashboard(trip) {
        if (!trip) return;

        // 1. Hero Banner Info
        if (dashTripTitle) dashTripTitle.textContent = trip.title || `${trip.destination} – ${trip.duration_days} Day Journey`;
        if (heroCurrencyBadge) heroCurrencyBadge.textContent = `${trip.currency || currentCurrency} (${trip.currency === 'USD' ? '$' : '₹'})`;

        const totalEst = trip.budget?.estimated_total || trip.budget?.total_estimated || 20000;
        if (dashHeroBudget) dashHeroBudget.textContent = `${formatCurrency(totalEst, trip.currency)} Estimated Budget`;

        if (dashTripMetaTags) {
            const travelersCount = trip.travelers?.total || 
                ((trip.travelers?.adults || 0) + (trip.travelers?.children || 0) + (trip.travelers?.seniors || 0)) || 4;
            const groupType = trip.travelers?.group_type || trip.group_type || 'Group';
            dashTripMetaTags.innerHTML = `
                <span class="hero-tag">📍 ${trip.destination}</span>
                <span class="hero-tag">🗓️ ${trip.duration_days} Days</span>
                <span class="hero-tag">👥 ${travelersCount} Travelers (${groupType})</span>
                <span class="hero-tag highlight-tag">${formatCurrency(totalEst, trip.currency)} Total Est.</span>
            `;
        }

        // 2. Preparation Progress Meter (Section 20)
        renderTripProgress(trip.progress);

        // 3. Subtabs Rendering
        renderSubtabOverview(trip);
        renderSubtabItinerary(trip);
        renderSubtabTravel(trip);
        renderSubtabHotels(trip);
        renderSubtabActivities(trip);
        renderSubtabRestaurants(trip);
        renderSubtabBudget(trip);
        renderSubtabPacking(trip);
        renderSubtabReminders(trip);
    }

    // Section 20: Trip Preparation Progress
    function renderTripProgress(progress) {
        if (!progress) {
            progress = {
                destination_selected: true,
                transportation_selected: true,
                hotel_selected: true,
                itinerary_generated: true,
                restaurants_reviewed: false,
                activities_reviewed: false,
                packing_started: false,
                checklist_completed: false,
                progress_percentage: 65
            };
        }

        const pct = progress.progress_percentage || 65;
        if (dashProgressPct) dashProgressPct.textContent = `${pct}% Ready`;
        if (dashProgressFill) dashProgressFill.style.width = `${pct}%`;

        if (dashProgressCheckpoints) {
            dashProgressCheckpoints.innerHTML = `
                <span class="chk-item ${progress.destination_selected ? 'done' : 'pending'}" onclick="window.switchSubtab('overview')">
                    ${progress.destination_selected ? '✓' : '○'} Destination
                </span>
                <span class="chk-item ${progress.transportation_selected ? 'done' : 'pending'}" onclick="window.switchSubtab('travel')">
                    ${progress.transportation_selected ? '✓' : '○'} Transport
                </span>
                <span class="chk-item ${progress.hotel_selected ? 'done' : 'pending'}" onclick="window.switchSubtab('hotels')">
                    ${progress.hotel_selected ? '✓' : '○'} Hotel
                </span>
                <span class="chk-item ${progress.itinerary_generated ? 'done' : 'pending'}" onclick="window.switchSubtab('itinerary')">
                    ${progress.itinerary_generated ? '✓' : '○'} Itinerary
                </span>
                <span class="chk-item ${progress.restaurants_reviewed ? 'done' : 'pending'}" onclick="window.switchSubtab('restaurants')">
                    ${progress.restaurants_reviewed ? '✓' : '○'} Restaurants
                </span>
                <span class="chk-item ${progress.activities_reviewed ? 'done' : 'pending'}" onclick="window.switchSubtab('activities')">
                    ${progress.activities_reviewed ? '✓' : '○'} Activities
                </span>
                <span class="chk-item ${progress.packing_started ? 'done' : 'pending'}" onclick="window.switchSubtab('packing')">
                    ${progress.packing_started ? '✓' : '○'} Packing
                </span>
                <span class="chk-item ${progress.checklist_completed ? 'done' : 'pending'}" onclick="window.switchSubtab('packing')">
                    ${progress.checklist_completed ? '✓' : '○'} Checklist
                </span>
            `;
        }
    }

    // 1. Overview Subtab
    function renderSubtabOverview(trip) {
        if (dashOverviewReason) {
            dashOverviewReason.textContent = trip.trade_off_reasoning || trip.overview_rationale || 
                `Crafted specifically for a ${trip.duration_days}-day escape to ${trip.destination}. Balances vibrant local experiences with restorative leisure, optimal transit buffers, and transparent budget boundaries.`;
        }

        if (dashOverviewMetrics) {
            const totalEst = trip.budget?.estimated_total || trip.budget?.total_estimated || 20000;
            const travelersCount = trip.travelers?.total || 
                ((trip.travelers?.adults || 0) + (trip.travelers?.children || 0) + (trip.travelers?.seniors || 0)) || 4;
            dashOverviewMetrics.innerHTML = `
                <div class="ov-metric">
                    <span class="ov-label">Duration</span>
                    <strong class="ov-val">${trip.duration_days} Days</strong>
                </div>
                <div class="ov-metric">
                    <span class="ov-label">Travelers</span>
                    <strong class="ov-val">${travelersCount} Guests</strong>
                </div>
                <div class="ov-metric">
                    <span class="ov-label">Style</span>
                    <strong class="ov-val">${trip.preferences?.lodging_style || 'Boutique'}</strong>
                </div>
                <div class="ov-metric">
                    <span class="ov-label">Estimated Total</span>
                    <strong class="ov-val text-emerald">${formatCurrency(totalEst, trip.currency)}</strong>
                </div>
            `;
        }

        if (dashOverviewTipsList) {
            const tips = (trip.enrichment_insights?.local_pro_tips && trip.enrichment_insights.local_pro_tips.length > 0) ? 
                trip.enrichment_insights.local_pro_tips : [
                "Early mornings (08:00 - 10:30) have significantly lower crowds and milder weather.",
                "Keep digital ID and reservation confirmations handy on your mobile device.",
                "Use local cabs or Uber for verified, metered rates and stress-free transit."
            ];
            dashOverviewTipsList.innerHTML = tips.map(t => `<li>${t}</li>`).join('');
        }

        if (dashOverviewTransitAdvice) {
            const transitAdv = trip.enrichment_insights?.transport_advice || 
                'Uber operates efficiently across key transit hubs and hotels. For scenic coastal or mountain stretches, pre-booked private cabs offer highest comfort.';
            dashOverviewTransitAdvice.innerHTML = `
                <div class="transit-banner-content">
                    <span class="transit-icon">🚗</span>
                    <div>
                        <strong>Local Transit Advisory:</strong>
                        <p>${transitAdv}</p>
                    </div>
                </div>
            `;
        }
    }

    // 2. Itinerary Subtab
    function renderSubtabItinerary(trip) {
        if (!dashDaysContainer) return;
        const days = trip.daily_itinerary || trip.itinerary_days || [];

        if (days.length === 0) {
            dashDaysContainer.innerHTML = `<div class="empty-state">No scheduled days found. Ask the AI assistant to populate days.</div>`;
            return;
        }

        dashDaysContainer.innerHTML = days.map(day => `
            <div class="day-card glass-card">
                <div class="day-card-header">
                    <div class="day-badge-title">
                        <span class="day-num-pill">Day ${day.day_number}</span>
                        <h4>${day.day_theme || `Day ${day.day_number} in ${trip.destination}`}</h4>
                    </div>
                    <span class="day-theme-tag">${formatCurrency(day.day_budget_usd, trip.currency)} Est.</span>
                </div>
                <div class="day-timeline">
                    ${(day.items || []).map(item => `
                        <div class="timeline-slot">
                            <div class="slot-time-col">
                                <span class="slot-time">${item.time_slot || 'Morning'}</span>
                                <span class="slot-dur">${item.estimated_transit_minutes ? `~${item.estimated_transit_minutes}m` : '2 hrs'}</span>
                            </div>
                            <div class="slot-content-col">
                                <div class="slot-title-row">
                                    <h5>${item.activity_title}</h5>
                                    ${item.is_meeting ? '<span class="slot-tag-meeting">💼 Executive Meeting</span>' : ''}
                                    ${item.cost_estimate_usd > 0 ? `<span class="slot-cost">${formatCurrency(item.cost_estimate_usd, trip.currency)}</span>` : '<span class="slot-cost free">Free</span>'}
                                </div>
                                <p class="slot-desc">${item.description || ''}</p>
                                <div class="slot-meta-row">
                                    <span class="slot-loc">📍 ${item.area || trip.destination}</span>
                                    ${item.wifi_rating ? `<span class="slot-tag-wifi">📶 ${item.wifi_rating}</span>` : ''}
                                    ${item.noise_level ? `<span class="slot-tag-acoustic">🎧 ${item.noise_level} Acoustics</span>` : ''}
                                    ${item.pro_tip ? `<span class="slot-transit">💡 ${item.pro_tip}</span>` : ''}
                                </div>
                                ${item.uber_deep_link || item.dropoff_address ? `
                                    <button type="button" class="btn-slot-uber" onclick="window.triggerSlotUber('${item.dropoff_address || item.area || trip.destination}')">
                                        <span>🚗 Ride with Uber to ${item.activity_title}</span>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    window.triggerSlotUber = (dropoffLoc) => {
        currentRideContext.dropoff = dropoffLoc;
        if (uberDropoffText) uberDropoffText.textContent = dropoffLoc;
        openUberModalWithQuotes();
    };

    // 3. Travel & Transit Subtab (Section 11)
    function renderSubtabTravel(trip) {
        if (!dashTransportGrid) return;
        const options = trip.transportation || trip.transportation_options || [];

        if (dashTransitRouteBadge) {
            dashTransitRouteBadge.textContent = `${trip.origin || 'Bangalore'} ➔ ${trip.destination || 'Goa'}`;
        }

        if (options.length === 0) {
            dashTransportGrid.innerHTML = `<div class="empty-state">No long-distance transport options configured.</div>`;
            return;
        }

        dashTransportGrid.innerHTML = options.map(opt => `
            <div class="transport-card glass-card ${opt.is_recommended ? 'recommended' : ''}">
                ${opt.is_recommended ? '<div class="rec-banner">✨ Recommended Option</div>' : ''}
                <div class="trans-card-header">
                    <div class="trans-mode-row">
                        <span class="trans-mode-icon">${opt.mode === 'Flight' ? '✈️' : opt.mode === 'Train' ? '🚆' : opt.mode === 'Bus' ? '🚌' : '🚗'}</span>
                        <div>
                            <h4>${opt.title || opt.mode}</h4>
                            <span class="trans-operator">${opt.carrier || 'Express Route'}</span>
                        </div>
                    </div>
                    <div class="trans-price-badge">
                        ${formatCurrency(opt.price, trip.currency)}
                        <small>per person</small>
                    </div>
                </div>
                <div class="trans-times-row">
                    <div class="time-col">
                        <span class="time-label">Departure</span>
                        <strong>${opt.departure_time || '07:30'}</strong>
                        <small>${opt.departure_hub || trip.origin || 'Origin'}</small>
                    </div>
                    <div class="duration-col">
                        <span>⏳ ${opt.duration_str || '2h'}</span>
                        <div class="trans-line"></div>
                        <small>${opt.transfers || 'Direct'}</small>
                    </div>
                    <div class="time-col">
                        <span class="time-label">Arrival</span>
                        <strong>${opt.arrival_time || '09:00'}</strong>
                        <small>${opt.arrival_hub || trip.destination || 'Destination'}</small>
                    </div>
                </div>
                <div class="trans-perks-list">
                    ${(opt.highlights || ['Direct Route', 'Fast Transit']).map(p => `<span>✓ ${p}</span>`).join('')}
                </div>
                <div class="trans-actions">
                    <a href="${opt.booking_link || 'https://www.google.com/travel/flights'}" target="_blank" class="btn-trans-book">
                        <span>Book ${opt.mode} ↗</span>
                    </a>
                </div>
            </div>
        `).join('');
    }

    // 4. Hotels Subtab (Section 12)
    function renderSubtabHotels(trip) {
        if (!dashHotelsGrid) return;
        const hotels = trip.hotels || trip.accommodation || [];

        if (hotels.length === 0) {
            dashHotelsGrid.innerHTML = `<div class="empty-state">No hotels selected. Ask the AI assistant to find stays.</div>`;
            return;
        }

        dashHotelsGrid.innerHTML = hotels.map(hotel => `
            <div class="hotel-card glass-card ${hotel.is_selected ? 'selected-hotel' : ''}">
                <div class="hotel-img-wrapper">
                    <img src="${hotel.image_url || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'}" alt="${hotel.name}" class="hotel-img" onerror="this.src='https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800'">
                    <span class="hotel-rating">★ ${hotel.rating || 4.8}</span>
                    ${hotel.is_selected ? '<span class="hotel-selected-tag">Current Trip Choice</span>' : ''}
                </div>
                <div class="hotel-info">
                    <div class="hotel-title-row">
                        <h4>${hotel.name}</h4>
                        <div class="hotel-price">
                            ${formatCurrency(hotel.price_per_night, trip.currency)}
                            <small>/ night</small>
                        </div>
                    </div>
                    <span class="hotel-loc">📍 ${hotel.neighborhood || trip.destination} • ${hotel.distance_to_activities_km || 2.1} km to activities</span>
                    <div class="hotel-amenities-row">
                        ${(hotel.amenities || ['Breakfast Included', 'Free Wi-Fi', 'Pool']).map(a => `<span class="amenity-pill">✓ ${a}</span>`).join('')}
                    </div>
                    <p class="hotel-policy">🛡️ Free cancellation until 48 hours before check-in</p>
                    <div class="hotel-actions-row">
                        <a href="${hotel.booking_url || 'https://www.booking.com'}" target="_blank" class="btn-hotel-book">
                            <span>View on Booking.com ↗</span>
                        </a>
                        <button type="button" class="btn-hotel-select" onclick="window.selectHotel('${hotel.name}')">
                            ${hotel.is_selected ? 'Selected' : 'Choose This Stay'}
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    window.selectHotel = (hotelName) => {
        if (!currentTrip || !currentTrip.hotels) return;
        currentTrip.hotels.forEach(h => {
            h.is_selected = (h.name === hotelName);
        });
        renderSubtabHotels(currentTrip);
    };

    // 5. Activities Subtab (Section 13)
    function renderSubtabActivities(trip) {
        if (!dashActivitiesGrid) return;
        const activities = trip.activities || [];

        if (dashActivitiesCountBadge) {
            dashActivitiesCountBadge.textContent = `${activities.length} Curated Experiences`;
        }

        if (activities.length === 0) {
            dashActivitiesGrid.innerHTML = `<div class="empty-state">No activities curated yet.</div>`;
            return;
        }

        dashActivitiesGrid.innerHTML = activities.map((act, idx) => `
            <div class="activity-card glass-card">
                <div class="activity-img-wrapper">
                    <img src="${act.image_url || 'https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=800'}" alt="${act.name}" class="activity-img" onerror="this.src='https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=800'">
                    <span class="activity-dur">⏳ ${act.estimated_duration_hours || 2} hrs</span>
                </div>
                <div class="activity-body">
                    <div class="activity-header-top">
                        <h4>${act.name}</h4>
                        <span class="activity-cost">${(act.cost_inr || act.estimated_cost_usd) > 0 ? formatCurrency(act.cost_inr || act.estimated_cost_usd, trip.currency) : 'Free Access'}</span>
                    </div>
                    <span class="activity-loc">📍 ${act.location_area || trip.destination} • ${act.category || 'Sightseeing'}</span>
                    <p class="activity-match"><strong>Why it matches:</strong> ${act.why_it_matches || act.why_matches || 'Fits your interests perfectly.'}</p>
                    <div class="activity-actions">
                        <button type="button" class="btn-act-toggle ${act.is_added ? 'active' : ''}" onclick="window.toggleActivityAdded(${idx})">
                            ${act.is_added ? '✓ In Itinerary' : '+ Add to Itinerary'}
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    window.toggleActivityAdded = (idx) => {
        if (!currentTrip || !currentTrip.activities || !currentTrip.activities[idx]) return;
        currentTrip.activities[idx].is_added = !currentTrip.activities[idx].is_added;
        renderSubtabActivities(currentTrip);
    };

    // 6. Restaurants Subtab (Section 14)
    function renderSubtabRestaurants(trip) {
        if (!dashRestaurantsGrid) return;
        const restaurants = trip.restaurants || [];

        if (restaurants.length === 0) {
            dashRestaurantsGrid.innerHTML = `<div class="empty-state">No restaurants configured yet.</div>`;
            return;
        }

        renderFilteredRestaurants(restaurants, 'all');

        if (mealFilterGroup) {
            mealFilterGroup.addEventListener('click', (e) => {
                const btn = e.target.closest('.meal-filter-btn');
                if (!btn) return;
                mealFilterGroup.querySelectorAll('.meal-filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderFilteredRestaurants(restaurants, btn.getAttribute('data-meal'));
            });
        }
    }

    function renderFilteredRestaurants(restaurants, mealFilter) {
        if (!dashRestaurantsGrid) return;
        let filtered = restaurants;
        if (mealFilter && mealFilter !== 'all') {
            filtered = restaurants.filter(r => (r.meal_type || '').toLowerCase() === mealFilter.toLowerCase());
        }

        if (filtered.length === 0) {
            dashRestaurantsGrid.innerHTML = `<div class="empty-state">No restaurants found for meal: ${mealFilter}.</div>`;
            return;
        }

        dashRestaurantsGrid.innerHTML = filtered.map(rest => `
            <div class="restaurant-card glass-card">
                <div class="rest-img-wrapper">
                    <img src="https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800" alt="${rest.name}" class="rest-img">
                    <span class="rest-rating">★ ${rest.rating || 4.7}</span>
                    <span class="rest-meal-badge">${rest.meal_type || 'Dinner'}</span>
                </div>
                <div class="rest-body">
                    <div class="rest-title-row">
                        <h4>${rest.name}</h4>
                        <span class="rest-price-level">${rest.price_tier || '₹₹'}</span>
                    </div>
                    <span class="rest-cuisine">${rest.cuisine || 'Regional'} • ${rest.distance_km || 1.2} km away</span>
                    <p class="rest-highlight">✨ Signature: <strong>${rest.signature_dish || 'Local Specialty'}</strong>. ${rest.reservation_tip || ''}</p>
                    <div class="rest-actions">
                        <button type="button" class="btn-rest-uber" onclick="window.triggerSlotUber('${rest.address || rest.name}')">
                            <span>🚗 Ride with Uber</span>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // 7. Budget Subtab (Section 21)
    function renderSubtabBudget(trip) {
        const budget = trip.budget || {};
        const totalEst = budget.estimated_total || budget.total_estimated || 20000;
        const target = budget.target || 20000;
        const diff = totalEst - target;

        if (dashBudgetSummaryBanner) {
            dashBudgetSummaryBanner.innerHTML = `
                <div class="budget-stat-item">
                    <span class="stat-label">Estimated Total Cost</span>
                    <h3 class="stat-val ${diff > 0 ? 'text-rose' : 'text-emerald'}">${formatCurrency(totalEst, trip.currency)}</h3>
                    <small>All categories combined</small>
                </div>
                <div class="budget-stat-item">
                    <span class="stat-label">Target Budget</span>
                    <h3 class="stat-val">${formatCurrency(target, trip.currency)}</h3>
                    <small>Declared preference</small>
                </div>
                <div class="budget-stat-item">
                    <span class="stat-label">Variance</span>
                    <h3 class="stat-val ${diff > 0 ? 'text-rose' : 'text-emerald'}">
                        ${diff > 0 ? `+${formatCurrency(diff, trip.currency)} (Over)` : `-${formatCurrency(Math.abs(diff), trip.currency)} (Under)`}
                    </h3>
                    <small>${diff <= 0 ? 'Comfortably within budget' : 'Review hotel & transit'}</small>
                </div>
            `;
        }

        if (dashBudgetBarsList) {
            const breakdown = budget.breakdown || {};
            const categories = [
                { name: "Long-Distance Transportation", amount: breakdown.transportation || 8000, icon: "✈️" },
                { name: "Hotels & Stays", amount: breakdown.hotels || 7000, icon: "🏨" },
                { name: "Food & Dining", amount: breakdown.food || 3500, icon: "🍴" },
                { name: "Activities & Sightseeing", amount: breakdown.activities || 2000, icon: "✨" },
                { name: "Local Cab & Uber Transit", amount: breakdown.local_transit || 1500, icon: "🚗" },
                { name: "Contingency & Reserves", amount: breakdown.contingency || 1000, icon: "🛡️" }
            ];

            dashBudgetBarsList.innerHTML = categories.map(cat => {
                const pct = Math.min(100, Math.round((cat.amount / Math.max(1, totalEst)) * 100));
                return `
                    <div class="budget-bar-row">
                        <div class="budget-bar-header">
                            <span class="bar-cat-name">${cat.icon} ${cat.name}</span>
                            <span class="bar-cat-amount">${formatCurrency(cat.amount, trip.currency)} (${pct}%)</span>
                        </div>
                        <div class="budget-bar-track">
                            <div class="budget-bar-fill" style="width: ${pct}%;"></div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Corporate Expense Management Panel
        if (dashCorporateExpensePanel) {
            const isBiz = trip.is_business || (trip.trip_purpose === 'business');
            if (corpReimbursementBadge) {
                corpReimbursementBadge.textContent = isBiz ? 'Corporate Policy Active' : 'Personal Travel Mode';
                corpReimbursementBadge.style.color = isBiz ? '#c4b5fd' : 'var(--secondary)';
            }

            if (dashCorpStatsGrid) {
                const reimbursable = isBiz ? Math.round(totalEst * 0.85) : 0;
                const outOfPocket = isBiz ? Math.round(totalEst * 0.15) : totalEst;
                const perDiem = trip.currency === 'USD' ? 120 : 4500;
                const companyName = trip.business_details?.company_name || currentUser.name + " Corp";

                dashCorpStatsGrid.innerHTML = `
                    <div class="corp-stat-card">
                        <span class="corp-stat-label">Reimbursable Total</span>
                        <strong class="corp-stat-val text-emerald">${formatCurrency(reimbursable, trip.currency)}</strong>
                        <span class="corp-stat-sub">Flights, Hotels & Client Dining</span>
                    </div>
                    <div class="corp-stat-card">
                        <span class="corp-stat-label">Employee Out-of-Pocket</span>
                        <strong class="corp-stat-val">${formatCurrency(outOfPocket, trip.currency)}</strong>
                        <span class="corp-stat-sub">Personal Incidentals</span>
                    </div>
                    <div class="corp-stat-card">
                        <span class="corp-stat-label">Daily Per-Diem Cap</span>
                        <strong class="corp-stat-val">${formatCurrency(perDiem, trip.currency)} / day</strong>
                        <span class="corp-stat-sub">Meal & Incidentals Policy</span>
                    </div>
                    <div class="corp-stat-card">
                        <span class="corp-stat-label">Corporate Entity</span>
                        <strong class="corp-stat-val" style="font-size: 14px;">${companyName}</strong>
                        <span class="corp-stat-sub">Direct ERP Billing Ready</span>
                    </div>
                `;
            }
        }

        if (btnExportExpenseReport) {
            btnExportExpenseReport.onclick = () => exportCorporateExpenseReport(trip);
        }
    }

    function exportCorporateExpenseReport(trip) {
        if (!trip) {
            alert('Please select or plan a trip first.');
            return;
        }

        const totalEst = trip.budget?.estimated_total || 20000;
        const curr = trip.currency || 'INR';
        const isBiz = trip.is_business || (trip.trip_purpose === 'business');
        const reimbursable = isBiz ? Math.round(totalEst * 0.85) : totalEst;
        const outOfPocket = isBiz ? Math.round(totalEst * 0.15) : 0;

        let csv = `NomadOS Corporate Travel Expense Report\n`;
        csv += `Report ID,EXP-${trip.trip_id || '2026-09'}\n`;
        csv += `Employee Name,${currentUser.name}\n`;
        csv += `Role / Department,${currentUser.tier || currentUser.role}\n`;
        csv += `Destination,${trip.destination}\n`;
        csv += `Duration,${trip.duration_days} Days\n`;
        csv += `Policy Compliance Status,100% Policy Compliant\n\n`;

        csv += `Category,Item Description,Schedule Day,Amount (${curr}),Status,Receipt Attached,Tax Deductible\n`;
        csv += `Transportation,Long-Distance Transit Booking,Day 1,${Math.round(totalEst * 0.35)},Reimbursable,Yes,Yes\n`;
        csv += `Lodging,Executive Stay & Workstation,Day 1-${trip.duration_days},${Math.round(totalEst * 0.35)},Reimbursable,Yes,Yes\n`;
        csv += `Dining,Client Meetings & Executive Meals,Day 2,${Math.round(totalEst * 0.15)},Reimbursable,Yes,Yes\n`;
        csv += `Local Transit,Uber Premier Executive Rides,Daily,${Math.round(totalEst * 0.08)},Reimbursable,Yes,Yes\n`;
        csv += `Personal Expenses,Personal Incidentals,Day ${trip.duration_days},${outOfPocket},Out-of-Pocket,No,No\n\n`;

        csv += `SUMMARY RECONCILIATION\n`;
        csv += `Total Journey Cost,${totalEst} ${curr}\n`;
        csv += `Corporate Reimbursable,${reimbursable} ${curr}\n`;
        csv += `Employee Out-of-Pocket,${outOfPocket} ${curr}\n`;

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `NomadOS_Corporate_Expense_Report_${trip.destination}_${currentUser.name.replace(/\s+/g, '_')}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // 8. Packing & Pre-Trip Checklist Subtab (Section 16 & 17)
    function renderSubtabPacking(trip) {
        if (!trip) return;

        // Pre-trip checklist
        if (dashPreTripList) {
            const preTrips = trip.pre_trip_checklist || [
                { id: "chk_1", title: "Government ID / Passport / Driving License", is_completed: true, is_critical: true },
                { id: "chk_2", title: "Confirm Flight / Train Tickets downloaded offline", is_completed: true, is_critical: true },
                { id: "chk_3", title: "Hotel Booking Confirmation verified", is_completed: true, is_critical: false },
                { id: "chk_4", title: "Carry portable power bank and chargers", is_completed: false, is_critical: false },
                { id: "chk_5", title: "Confirm weather forecast and clothing layers", is_completed: false, is_critical: false }
            ];

            dashPreTripList.innerHTML = preTrips.map((item, idx) => `
                <div class="pretrip-item-row" style="display: flex; align-items: center; justify-content: space-between; gap: 10px; width: 100%;">
                    <label class="pretrip-item ${item.is_completed ? 'completed' : ''}" style="flex: 1; margin-bottom: 0;">
                        <input type="checkbox" ${item.is_completed ? 'checked' : ''} onchange="window.togglePreTripCheck(${idx})">
                        <span class="custom-chk"></span>
                        <span class="pretrip-task-text">${item.title}</span>
                        <span class="priority-tag ${item.is_critical ? 'critical' : 'high'}">${item.is_critical ? 'Critical' : 'Important'}</span>
                    </label>
                    ${item.is_custom ? `<button type="button" class="delete-chk-btn" onclick="window.deleteChecklistItem('${item.id}', true)" title="Delete Item">✕</button>` : ''}
                </div>
            `).join('');
        }

        // Categorized Packing Items
        if (dashPackingLayout) {
            const packingList = trip.packing_checklist || [];
            
            // Group by category
            const categoriesMap = {};
            if (packingList.length > 0) {
                packingList.forEach(item => {
                    const cat = item.category || 'General Essentials';
                    if (!categoriesMap[cat]) categoriesMap[cat] = [];
                    categoriesMap[cat].push(item);
                });
            } else {
                categoriesMap['Essentials'] = [
                    { id: 'p1', item_name: 'Wallet & Cards', is_packed: true },
                    { id: 'p2', item_name: 'Government Photo ID', is_packed: true },
                    { id: 'p3', item_name: 'Phone & Charger Cable', is_packed: false },
                    { id: 'p4', item_name: 'Power Bank 20,000mAh', is_packed: false }
                ];
                categoriesMap['Clothing'] = [
                    { id: 'p5', item_name: 'Breathable Cotton T-Shirts', is_packed: false },
                    { id: 'p6', item_name: 'Light Shorts / Pants', is_packed: false },
                    { id: 'p7', item_name: 'Comfortable Walking Shoes', is_packed: false }
                ];
            }

            dashPackingLayout.innerHTML = Object.keys(categoriesMap).map(catName => `
                <div class="packing-category-box glass-card">
                    <h5>${catName}</h5>
                    <div class="packing-items-list">
                        ${categoriesMap[catName].map(item => `
                            <div class="pack-item-row" style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                                <label class="pack-checkbox-row ${(item.is_packed || item.checked) ? 'packed' : ''}" style="flex: 1; margin-bottom: 0;">
                                    <input type="checkbox" ${(item.is_packed || item.checked) ? 'checked' : ''} onchange="window.togglePackItem('${item.id}')">
                                    <span class="custom-chk"></span>
                                    <span class="item-name">${item.item_name || item.item}</span>
                                </label>
                                ${item.is_custom ? `<button type="button" class="delete-chk-btn" onclick="window.deleteChecklistItem('${item.id}', false)" title="Delete Item">✕</button>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('');

            updatePackingProgress(trip);
        }
    }

    function updatePackingProgress(trip) {
        if (!trip) return;
        const list = trip.packing_checklist || [];
        const total = list.length;
        const packed = list.filter(i => (i.is_packed || i.checked)).length;
        const pct = total > 0 ? Math.round((packed / total) * 100) : 0;

        if (dashPackingFill) dashPackingFill.style.width = `${pct}%`;
        if (dashPackingCountText) dashPackingCountText.textContent = `${packed} / ${total} Items Packed`;
        if (dashPackingPercentText) dashPackingPercentText.textContent = `${pct}% Ready to Depart`;
    }

    window.togglePackItem = (itemId) => {
        if (!currentTrip || !currentTrip.packing_checklist) return;
        const item = currentTrip.packing_checklist.find(i => i.id === itemId);
        if (item) {
            item.is_packed = !(item.is_packed || item.checked);
            item.checked = item.is_packed;
            renderSubtabPacking(currentTrip);
            localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));
        }
    };

    window.togglePreTripCheck = (idx) => {
        if (!currentTrip || !currentTrip.pre_trip_checklist || !currentTrip.pre_trip_checklist[idx]) return;
        currentTrip.pre_trip_checklist[idx].is_completed = !currentTrip.pre_trip_checklist[idx].is_completed;
        renderSubtabPacking(currentTrip);
        localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));
    };

    window.deleteChecklistItem = (itemId, isPreTrip) => {
        if (!currentTrip) return;
        if (isPreTrip && currentTrip.pre_trip_checklist) {
            currentTrip.pre_trip_checklist = currentTrip.pre_trip_checklist.filter(i => i.id !== itemId);
        } else if (currentTrip.packing_checklist) {
            currentTrip.packing_checklist = currentTrip.packing_checklist.filter(i => i.id !== itemId);
        }
        renderSubtabPacking(currentTrip);
        localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));
        showToast('Item removed from checklist', 'info');
    };

    if (btnCheckAllPacking) {
        btnCheckAllPacking.addEventListener('click', () => {
            if (!currentTrip || !currentTrip.packing_checklist) return;
            currentTrip.packing_checklist.forEach(i => {
                i.is_packed = true;
                i.checked = true;
            });
            renderSubtabPacking(currentTrip);
            localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));
        });
    }

    if (btnResetPacking) {
        btnResetPacking.addEventListener('click', () => {
            if (!currentTrip || !currentTrip.packing_checklist) return;
            currentTrip.packing_checklist.forEach(i => {
                i.is_packed = false;
                i.checked = false;
            });
            renderSubtabPacking(currentTrip);
            localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));
        });
    }

    if (addChecklistForm) {
        addChecklistForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const title = newChecklistTitle ? newChecklistTitle.value.trim() : '';
            const cat = newChecklistCategory ? newChecklistCategory.value : '🛂 Essentials & Documents';
            if (!title) return;
            if (!currentTrip) {
                showToast('Please create or load a trip first!', 'info');
                return;
            }

            if (cat.includes('Pre-Trip') || cat.includes('Departure')) {
                if (!currentTrip.pre_trip_checklist) currentTrip.pre_trip_checklist = [];
                currentTrip.pre_trip_checklist.unshift({
                    id: 'prep-' + Date.now(),
                    title: title,
                    category: 'Preparation',
                    is_completed: false,
                    is_critical: true,
                    is_custom: true
                });
            } else {
                if (!currentTrip.packing_checklist) currentTrip.packing_checklist = [];
                currentTrip.packing_checklist.unshift({
                    id: 'pack-' + Date.now(),
                    item: title,
                    item_name: title,
                    category: cat,
                    is_essential: true,
                    is_packed: false,
                    checked: false,
                    reminder_note: 'Custom essential item',
                    is_custom: true
                });
            }

            renderSubtabPacking(currentTrip);
            localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));
            if (newChecklistTitle) newChecklistTitle.value = '';
            showToast(`Added "${title}" to essential checklist!`, 'success');
        });
    }


    // 9. Reminders Subtab (Section 18)
    function renderSubtabReminders(trip) {
        if (!dashRemindersGrid) return;
        const reminders = trip.reminders || [];

        if (reminders.length === 0) {
            dashRemindersGrid.innerHTML = `<div class="empty-state">No reminders set.</div>`;
            return;
        }

        dashRemindersGrid.innerHTML = reminders.map((rem, idx) => `
            <div class="reminder-card glass-card">
                <div class="rem-icon-col">${rem.type === 'departure' ? '🚗' : rem.type === 'checkin' ? '✈️' : rem.type === 'packing' ? '🎒' : '🔔'}</div>
                <div class="rem-info-col">
                    <h4>${rem.title}</h4>
                    <span class="rem-timing">⏰ Scheduled: ${rem.scheduled_time}</span>
                    ${rem.notes ? `<small class="rem-note">${rem.notes}</small>` : ''}
                </div>
                <div class="rem-toggle-col">
                    <label class="switch">
                        <input type="checkbox" ${rem.is_enabled ? 'checked' : ''} onchange="window.toggleReminder(${idx})">
                        <span class="slider round"></span>
                    </label>
                </div>
            </div>
        `).join('');
    }

    window.toggleReminder = (idx) => {
        if (!currentTrip || !currentTrip.reminders || !currentTrip.reminders[idx]) return;
        currentTrip.reminders[idx].is_enabled = !currentTrip.reminders[idx].is_enabled;
        renderSubtabReminders(currentTrip);
    };

    // Sub-tab Navigation
    window.switchSubtab = (subtabName) => {
        dashTabs.forEach(t => {
            if (t.getAttribute('data-subtab') === subtabName) t.classList.add('active');
            else t.classList.remove('active');
        });

        subtabPanels.forEach(p => {
            if (p.id === `subtab-${subtabName}`) {
                p.classList.remove('hidden');
                p.classList.add('active');
            } else {
                p.classList.add('hidden');
                p.classList.remove('active');
            }
        });
    };

    dashTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.getAttribute('data-subtab');
            window.switchSubtab(target);
        });
    });

    // ============================================================
    // CONTEXTUAL AI ASSISTANT DRAWER (Section 22, 23 & 30)
    // ============================================================
    function openAiDrawer(prefill = "") {
        if (aiDrawer) aiDrawer.classList.remove('hidden');
        if (prefill && aiChatInput) {
            aiChatInput.value = prefill;
            aiChatInput.focus();
        }
    }

    function closeAiDrawer() {
        if (aiDrawer) aiDrawer.classList.add('hidden');
    }

    if (openAiDrawerBtn) openAiDrawerBtn.addEventListener('click', () => openAiDrawer());
    if (dashAskAiBtn) dashAskAiBtn.addEventListener('click', () => openAiDrawer());
    if (aiDrawerClose) aiDrawerClose.addEventListener('click', closeAiDrawer);
    if (aiDrawer) {
        aiDrawer.addEventListener('click', (e) => {
            if (e.target === aiDrawer) closeAiDrawer();
        });
    }

    if (btnAiOptimizeItinerary) {
        btnAiOptimizeItinerary.addEventListener('click', () => {
            openAiDrawer("Please optimize the itinerary pace to make it more relaxing with ample recovery time.");
        });
    }
    if (btnAiFindCheaperHotel) {
        btnAiFindCheaperHotel.addEventListener('click', () => {
            openAiDrawer("Find a more budget-friendly hotel that still maintains high guest reviews and good location.");
        });
    }
    if (btnAiReduceBudget) {
        btnAiReduceBudget.addEventListener('click', () => {
            openAiDrawer("Suggest ways to reduce our overall trip cost by 15-20% without sacrificing major sights.");
        });
    }

    aiPills.forEach(pill => {
        pill.addEventListener('click', () => {
            const prompt = pill.getAttribute('data-prompt');
            if (prompt) {
                if (aiChatInput) aiChatInput.value = prompt;
                if (aiChatForm) aiChatForm.dispatchEvent(new Event('submit'));
            }
        });
    });

    // AI Chat Form Submission (POST /api/v1/trip/refine)
    if (aiChatForm) {
        aiChatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = aiChatInput.value.trim();
            if (!text) return;

            appendChatMessage('user', text);
            aiChatInput.value = '';

            const typingBubble = appendChatMessage('ai', 'Thinking and consulting trip state...');

            try {
                const res = await fetch('/api/v1/trip/refine', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        trip_id: currentTrip?.trip_id || 'active_trip',
                        prompt: text,
                        current_trip: currentTrip
                    })
                });

                if (!res.ok) throw new Error(`HTTP ${res.status}: AI Refinement failed`);
                const data = await res.json();

                typingBubble.remove();
                appendChatMessage('ai', data.message || 'Updated your trip based on your feedback.');

                if (data.updated_trip) {
                    currentTrip = data.updated_trip;
                    localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));
                    renderTripDashboard(currentTrip);
                }
            } catch (err) {
                typingBubble.remove();
                appendChatMessage('ai', `Sorry, could not process instruction: ${err.message}`);
            }
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }

    function appendChatMessage(role, message) {
        if (!aiChatMessages) return null;
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role === 'user' ? 'user-bubble' : 'ai-bubble'}`;
        const safeRole = role === 'user' ? 'You' : 'NomadOS';
        const safeMessage = escapeHtml(message);
        bubble.innerHTML = `
            <strong>${safeRole}:</strong>
            <p>${safeMessage}</p>
        `;
        aiChatMessages.appendChild(bubble);
        aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
        return bubble;
    }

    // ============================================================
    // EXPORT & SHARE ACTIONS
    // ============================================================
    if (dashCopyMarkdownBtn) {
        dashCopyMarkdownBtn.addEventListener('click', () => {
            if (!currentTrip) return;
            const md = generateTripMarkdown(currentTrip);
            navigator.clipboard.writeText(md).then(() => {
                const orig = dashCopyMarkdownBtn.textContent;
                dashCopyMarkdownBtn.textContent = '✓ Copied Markdown!';
                setTimeout(() => dashCopyMarkdownBtn.textContent = orig, 2500);
            }).catch(err => {
                alert('Failed to copy to clipboard: ' + err);
            });
        });
    }

    if (dashExportJsonBtn) {
        dashExportJsonBtn.addEventListener('click', () => {
            if (!currentTrip) return;
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentTrip, null, 2));
            const downloadAnchor = document.createElement('a');
            downloadAnchor.setAttribute("href", dataStr);
            downloadAnchor.setAttribute("download", `nomados_${(currentTrip.destination || 'trip').toLowerCase()}_plan.json`);
            document.body.appendChild(downloadAnchor);
            downloadAnchor.click();
            downloadAnchor.remove();
        });
    }

    function generateTripMarkdown(trip) {
        const totalEst = trip.budget?.estimated_total || trip.budget?.total_estimated || 20000;
        return `# 🧭 NomadOS Journey Plan: ${trip.title}
**Destination:** ${trip.destination}
**Duration:** ${trip.duration_days} Days
**Estimated Budget:** ${formatCurrency(totalEst, trip.currency)}

---

## 🧠 AI Synthesis & Rationale
${trip.trade_off_reasoning || trip.overview_rationale || 'Tailored journey plan.'}

---

## 📅 Day-by-Day Schedule
${(trip.daily_itinerary || []).map(d => `
### Day ${d.day_number}: ${d.day_theme}
${(d.items || []).map(s => `- **${s.time_slot}**: ${s.activity_title} — ${s.description} [${s.cost_estimate_usd > 0 ? formatCurrency(s.cost_estimate_usd, trip.currency) : 'Free'}]`).join('\n')}
`).join('\n')}

---

## 🚀 Transportation & Transit
${(trip.transportation || []).map(t => `- **${t.mode}** (${t.carrier}): ${formatCurrency(t.price, trip.currency)} | Duration: ${t.duration_str}`).join('\n')}

---

## 🏨 Accommodations
${(trip.hotels || []).map(h => `- **${h.name}** (Rating: ${h.rating}★): ${formatCurrency(h.price_per_night, trip.currency)}/night | Amenities: ${(h.amenities || []).join(', ')}`).join('\n')}

*Generated by NomadOS AI Travel Companion.*
`;
    }

    // ============================================================
    // EXPLORE GALLERY (View 3: GET /api/v1/trip/explore)
    // ============================================================
    async function loadExploreDestinations() {
        if (!exploreGalleryGrid) return;
        if (exploreDestinations.length > 0) return;

        try {
            exploreGalleryGrid.innerHTML = `<div class="spinner"></div><p>Discovering trending destinations...</p>`;
            const res = await fetch('/api/v1/trip/explore');
            if (!res.ok) throw new Error('Failed to load explore destinations');
            const data = await res.json();
            exploreDestinations = Array.isArray(data) ? data : (data.destinations || []);

            exploreGalleryGrid.innerHTML = exploreDestinations.map(dest => `
                <div class="dest-rec-card glass-card">
                    <div class="dest-card-img-wrap">
                        <img src="${dest.image_url || 'https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800'}" alt="${dest.name}" class="dest-card-img" onerror="this.src='https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800'">
                    </div>
                    <div class="dest-card-body">
                        <div class="dest-card-top">
                            <h4 class="dest-name">${dest.name}</h4>
                            <span class="dest-state">${dest.state_or_country || dest.state || ''}</span>
                        </div>
                        <div class="dest-tags-row">
                            ${(dest.vibe_tags || dest.tags || []).map(t => `<span class="dest-tag">${t}</span>`).join('')}
                        </div>
                        <p class="dest-rationale">${dest.why_it_matches}</p>
                        <div class="dest-meta-stats">
                            <span>💰 ${dest.estimated_budget_range || formatCurrency(dest.estimated_budget || 20000)}</span>
                            <span>🗓️ Ideal: ${dest.ideal_duration_days || dest.ideal_duration || 3} Days</span>
                            <span>✨ ${dest.top_highlight || 'Scenic'}</span>
                        </div>
                        <div class="dest-actions-row">
                            <button type="button" class="btn-dest-select" onclick="window.selectDestinationQuick('${dest.name}')">Plan Trip Here ➔</button>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (err) {
            exploreGalleryGrid.innerHTML = `<p class="text-rose">Could not load destinations: ${err.message}</p>`;
        }
    }

    // ============================================================
    // UBER OFFICIAL RIDES API & DYNAMIC QUOTES
    // ============================================================
    function openUberModalWithQuotes() {
        if (!uberModal) return;
        uberModal.classList.remove('hidden');
        if (uberQuotesView) uberQuotesView.classList.remove('hidden');
        if (uberTrackingView) uberTrackingView.classList.add('hidden');
        if (uberBookBtn) uberBookBtn.disabled = true;

        if (uberPickupText) uberPickupText.textContent = currentRideContext.pickup;
        if (uberDropoffText) uberDropoffText.textContent = currentRideContext.dropoff;

        fetchUberPriceEstimates(currentRideContext.pickup, currentRideContext.dropoff);
    }

    async function fetchUberPriceEstimates(startAddr, endAddr) {
        if (!uberProductsList) return;
        uberProductsList.innerHTML = `
            <div class="uber-loading-quotes">
                <div class="spinner"></div>
                <span>Querying Uber API for dynamic fares...</span>
            </div>
        `;

        try {
            const url = `/api/v1/uber/estimates/price?start_address=${encodeURIComponent(startAddr)}&end_address=${encodeURIComponent(endAddr)}`;
            const res = await fetch(url);
            if (!res.ok) throw new Error('Uber estimate query failed');
            const data = await res.json();
            renderUberProducts(data.estimates || []);
        } catch (err) {
            const fallbackQuotes = [
                { product_id: 'uber_go', display_name: 'Uber Go', description: 'Affordable, compact everyday rides', estimate: '₹340 - ₹390', duration_minutes: 18, capacity: 4, surge_multiplier: 1.0 },
                { product_id: 'uber_premier', display_name: 'Uber Premier', description: 'Top-rated drivers in premium sedans', estimate: '₹480 - ₹540', duration_minutes: 18, capacity: 4, surge_multiplier: 1.0 },
                { product_id: 'uber_xl', display_name: 'Uber XL', description: 'Comfortable SUVs for groups & luggage', estimate: '₹620 - ₹700', duration_minutes: 20, capacity: 6, surge_multiplier: 1.0 }
            ];
            renderUberProducts(fallbackQuotes);
        }
    }

    function renderUberProducts(estimates) {
        if (!uberProductsList) return;
        if (estimates.length === 0) {
            uberProductsList.innerHTML = `<div class="empty-state">No Uber products available for this route.</div>`;
            return;
        }

        uberProductsList.innerHTML = '';
        estimates.forEach((prod, index) => {
            const card = document.createElement('div');
            card.className = `uber-product-card ${index === 0 ? 'selected' : ''}`;
            card.setAttribute('data-product-id', prod.product_id);
            card.innerHTML = `
                <div class="uber-prod-info">
                    <div class="uber-prod-header">
                        <h4>${prod.display_name}</h4>
                        <span class="uber-capacity">👤 ${prod.capacity || 4}</span>
                    </div>
                    <p class="uber-prod-desc">${prod.description || 'Reliable city transit'}</p>
                    <span class="uber-prod-eta">⏳ ${prod.duration_minutes || 15} mins away</span>
                </div>
                <div class="uber-prod-pricing">
                    <div class="uber-fare">${prod.estimate}</div>
                    ${prod.surge_multiplier > 1.0 ? `<span class="uber-surge">⚡ ${prod.surge_multiplier}x Surge</span>` : ''}
                </div>
            `;

            card.addEventListener('click', () => {
                document.querySelectorAll('.uber-product-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                currentRideContext.selectedProduct = prod.product_id;
            });

            uberProductsList.appendChild(card);
        });

        currentRideContext.selectedProduct = estimates[0].product_id;
        if (uberBookBtn) uberBookBtn.disabled = false;
    }

    if (uberBookBtn) {
        uberBookBtn.addEventListener('click', async () => {
            uberBookBtn.disabled = true;
            uberBookBtn.innerHTML = `<div class="spinner" style="margin-right: 8px;"></div> Dispatching Uber...`;

            try {
                const res = await fetch('/api/v1/uber/request-ride', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        product_id: currentRideContext.selectedProduct,
                        start_address: currentRideContext.pickup,
                        end_address: currentRideContext.dropoff
                    })
                });

                if (!res.ok) throw new Error('Failed to dispatch ride request');
                const ride = await res.json();
                currentRideContext.activeRequestId = ride.request_id;
                showTrackingView(ride);
                startRideTracking(ride.request_id);
            } catch (err) {
                alert(`Uber Booking Error: ${err.message}`);
                uberBookBtn.disabled = false;
                uberBookBtn.textContent = 'Confirm Ride Booking';
            }
        });
    }

    function showTrackingView(ride) {
        if (uberQuotesView) uberQuotesView.classList.add('hidden');
        if (uberTrackingView) uberTrackingView.classList.remove('hidden');
        updateTrackingUI(ride);
    }

    function updateTrackingUI(ride) {
        if (uberTrackingStatus) uberTrackingStatus.textContent = ride.status.toUpperCase();
        if (uberTrackingEta) uberTrackingEta.textContent = ride.eta_minutes > 0 ? `ETA: ${ride.eta_minutes} min` : 'Arrived';

        if (ride.driver && uberDriverName) {
            uberDriverName.textContent = ride.driver.name;
            if (uberDriverRating) uberDriverRating.textContent = ride.driver.rating;
        }
        if (ride.vehicle && uberVehicleDesc) {
            uberVehicleDesc.textContent = `${ride.vehicle.make} ${ride.vehicle.model} (${ride.vehicle.license_plate})`;
        }

        const steps = ['accepted', 'arriving', 'in_progress', 'completed'];
        const progressPercentages = { accepted: 25, arriving: 50, in_progress: 80, completed: 100, canceled: 0 };
        const pct = progressPercentages[ride.status] || 25;
        if (uberProgressFill) uberProgressFill.style.width = `${pct}%`;

        steps.forEach(step => {
            const el = document.getElementById(`step-${step}`);
            if (el) {
                if (step === ride.status || (steps.indexOf(step) <= steps.indexOf(ride.status) && ride.status !== 'canceled')) {
                    el.classList.add('active');
                } else {
                    el.classList.remove('active');
                }
            }
        });

        if (ride.status === 'completed' || ride.status === 'canceled') {
            if (currentRideContext.pollingInterval) clearInterval(currentRideContext.pollingInterval);
            if (ride.status === 'canceled' && uberTrackingStatus) {
                uberTrackingStatus.textContent = 'RIDE CANCELED';
                uberTrackingStatus.style.color = 'var(--rose)';
            }
        }
    }

    function startRideTracking(requestId) {
        if (currentRideContext.pollingInterval) clearInterval(currentRideContext.pollingInterval);
        currentRideContext.pollingInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/v1/uber/requests/${requestId}`);
                if (res.ok) {
                    const ride = await res.json();
                    updateTrackingUI(ride);
                }
            } catch (err) {
                console.error('Error polling ride status:', err);
            }
        }, 3000);
    }

    if (uberCancelRideBtn) {
        uberCancelRideBtn.addEventListener('click', async () => {
            if (!currentRideContext.activeRequestId) return;
            if (!confirm('Are you sure you want to cancel this Uber ride?')) return;

            try {
                const res = await fetch(`/api/v1/uber/requests/${currentRideContext.activeRequestId}`, { method: 'DELETE' });
                if (res.ok) {
                    if (currentRideContext.pollingInterval) clearInterval(currentRideContext.pollingInterval);
                    if (uberTrackingStatus) uberTrackingStatus.textContent = 'RIDE CANCELED';
                    if (uberTrackingEta) uberTrackingEta.textContent = 'Canceled';
                }
            } catch (err) {
                alert(`Failed to cancel ride: ${err.message}`);
            }
        });
    }

    function closeUberModal() {
        if (uberModal) uberModal.classList.add('hidden');
        if (currentRideContext.pollingInterval) clearInterval(currentRideContext.pollingInterval);
    }

    if (uberModalClose) uberModalClose.addEventListener('click', closeUberModal);
    if (uberDoneBtn) uberDoneBtn.addEventListener('click', closeUberModal);
    if (uberModal) {
        uberModal.addEventListener('click', (e) => {
            if (e.target === uberModal) closeUberModal();
        });
    }

    // ============================================================
    // INTERACTIVE LIVE DEMO & GUIDED TOUR SYSTEM
    // ============================================================
    const liveDemoModal = document.getElementById('liveDemoModal');
    const startLiveDemoBtn = document.getElementById('startLiveDemoBtn');
    const heroLiveDemoBtn = document.getElementById('heroLiveDemoBtn');
    const heroQuickPlanBtn = document.getElementById('heroQuickPlanBtn');
    const closeDemoModalBtn = document.getElementById('closeDemoModalBtn');
    const demoStageBody = document.getElementById('demoStageBody');
    const demoPrevBtn = document.getElementById('demoPrevBtn');
    const demoNextBtn = document.getElementById('demoNextBtn');
    const demoAutoPlayBtn = document.getElementById('demoAutoPlayBtn');
    const demoAutoPlayIcon = document.getElementById('demoAutoPlayIcon');
    const demoAutoPlayText = document.getElementById('demoAutoPlayText');
    const demoStepCounter = document.getElementById('demoStepCounter');
    const demoExploreTripBtn = document.getElementById('demoExploreTripBtn');
    const engineModelName = document.getElementById('engineModelName');

    let currentDemoStep = 1;
    let demoAutoPlayTimer = null;
    const totalDemoSteps = 5;

    const demoSlides = [
        {
            step: 1,
            title: "1. Natural Language Intent & Requirement Extraction",
            badge: "Natural Language Understanding",
            desc: "NomadOS transforms unstructured traveler ideas into high-fidelity structured travel contracts. It extracts destinations, currencies, budget constraints, travel companions, and trip vibes in a single pass without tedious multi-step forms.",
            features: [
                { icon: "🧠", title: "Smart Entity Parser", desc: "Recognizes currencies (₹ INR, $ USD), duration, companions, and lodging styles." },
                { icon: "✨", title: "Contextual Matcher", desc: "If no city is named, recommends top matching destinations based on companions and mood." },
                { icon: "🛡️", title: "Zero Redundant Questions", desc: "Never asks for parameters already stated in your query." }
            ],
            codeSample: `// Sample Natural Query:\n"I have an executive business trip to Bangalore for 3 days next Tuesday for partner meetings. Need 150+ Mbps Wi-Fi, quiet dining, and Taj hotel."\n\n// Extracted Canonical State:\n{\n  "destination": "Bangalore", "duration_days": 3, "budget": 45000,\n  "travelers_count": 1, "travel_style": "Executive Business Blitz",\n  "currency": "INR", "confidence_score": 0.98\n}`
        },
        {
            step: 2,
            title: "2. Specialized 4-Agent Orchestration Pipeline",
            badge: "Multi-Agent DAG Architecture",
            desc: "Instead of a single monolithic prompt, NomadOS decomposes travel synthesis across 4 specialized agents coordinated by a deterministic state machine orchestrator with runtime latency waterfalls and observability.",
            features: [
                { icon: "1️⃣", title: "Context Parsing Agent", desc: "Fast-tier model routes parameters and travel constraints." },
                { icon: "2️⃣", title: "Discovery Agent", desc: "Filters high-signal points of interest and distinct neighborhoods." },
                { icon: "3️⃣", title: "Vector RAG Enrichment Agent", desc: "Queries ChromaDB vector store with titan/nomic embeddings for local guides." },
                { icon: "4️⃣", title: "Booking & Reasoning Agent", desc: "Optimizes multi-variable schedules, budget allocations, and trade-off rationales." }
            ],
            codeSample: `// Dynamic Model Routing & Telemetry:\n- ContextParsingAgent:   phi3:mini (Local LLM) -> Latency: 4.8s (Cost: $0.00)\n- DiscoveryAgent:        phi3:mini (Local LLM) -> Latency: 4.2s (Cost: $0.00)\n- RAGEnrichmentAgent:    ChromaDB + S3 Guides   -> Latency: 3.8s (Cost: $0.00)\n- BookingReasoningAgent: Llama 3.1 / Sonnet     -> Latency: 5.1s (Cost: $0.00)\n\nTotal Savings vs Cloud API: ~$0.024 per query | 100% Offline Capable`
        },
        {
            step: 3,
            title: "3. Complete Canonical 9-Module Trip Synthesis",
            badge: "9 Integrated Trip Modules",
            desc: "Every trip generates an actionable 9-module dashboard holding every piece of information required from departure to return. All modules are interactive, editable, and downloadable.",
            features: [
                { icon: "🗺️", title: "Overview & Day-by-Day", desc: "Structured morning, afternoon, and evening slots with neighborhood area tags." },
                { icon: "🏨", title: "Executive Lodging", desc: "Verified hotels with ratings, amenities (Wi-Fi speed, breakfast), and direct booking links." },
                { icon: "🍽️", title: "Dining & Culinary", desc: "Acoustic-rated quiet restaurants, signature dishes, and reservation advice." },
                { icon: "🎒", title: "Packing & Pre-Trip Checks", desc: "Interactive checklists with weather-aware recommendations and smart reminders." }
            ],
            codeSample: `// 9-Module Architecture:\n1. Trip Overview & Traveler Meta   6. Activities & Neighborhood Discovery\n2. Day-by-Day Itinerary Schedule  7. Packing & Pre-Trip Checklist\n3. Multi-Modal Transportation     8. Contextual Reminders & Etiquette\n4. Curated Hotels & Lodging       9. Corporate Budget & Expense Breakdown\n5. Signature Dining Highlights`
        },
        {
            step: 4,
            title: "4. Official Uber Rides API & Deep Transit Linking",
            badge: "Uber Transit Integration",
            desc: "Every itinerary activity is pre-configured with a universal Uber deep link that launches mobile/web with coordinates pre-populated, dynamic price estimates, and an interactive dispatch simulation HUD.",
            features: [
                { icon: "🚗", title: "Multi-Product Estimates", desc: "Live dynamic estimates for UberX, Uber Comfort, UberXL, and Uber Black." },
                { icon: "🔗", title: "Universal Deep Links", desc: "1-click 'Open in Uber' buttons for every single activity in your schedule." },
                { icon: "📡", title: "Ride Lifecycle Tracker", desc: "Simulates driver assignment, ETA countdown, and live vehicle license tracking." }
            ],
            codeSample: `// Universal Deep Link Pattern:\nhttps://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[formatted_address]=The+Leela+Palace%2C+Old+Airport+Road%2C+Bangalore&dropoff[nickname]=The+Leela+Palace\n\n// Dynamic Price Estimates:\n- UberX:        ₹240 - ₹310 (~18 min)\n- Uber Comfort: ₹320 - ₹410 (~18 min)\n- Uber Premier: ₹450 - ₹580 (~18 min)`
        },
        {
            step: 5,
            title: "5. Contextual AI Refinements & Expense Auditing",
            badge: "Quiet AI Co-Pilot",
            desc: "The contextual AI assistant refines your active itinerary without resetting your progress. Ask to make days more relaxed, reduce hotel budget, or add specific client meetings in plain English.",
            features: [
                { icon: "💬", title: "Conversational Adjustments", desc: "Type 'Make Day 2 less tiring' or 'Find cheaper hotel' for instant surgical updates." },
                { icon: "📊", title: "Real-time Expense Audit", desc: "Category allocations for lodging, dining, transit, and emergency reserves." },
                { icon: "💾", title: "Local Persistence", desc: "All state persists in SQLite and browser storage for offline reload." }
            ],
            codeSample: `// Sample Refinement Interaction:\nUser Prompt: "Can you swap afternoon meeting on Day 2 for a quiet cafe with fast Wi-Fi?"\n\nAI Response: "Updated Day 2 afternoon schedule: Added Third Wave Coffee Roasters (Indiranagar) with 150 Mbps Wi-Fi and quiet acoustic seating. Saved ₹450 on transit."`
        }
    ];

    function renderDemoSlide(stepNum) {
        currentDemoStep = stepNum;
        const slide = demoSlides[stepNum - 1];

        // Update stepper nodes
        document.querySelectorAll('.demo-step-node').forEach(node => {
            const nodeStep = parseInt(node.getAttribute('data-step'), 10);
            node.classList.remove('active', 'completed');
            if (nodeStep === stepNum) {
                node.classList.add('active');
            } else if (nodeStep < stepNum) {
                node.classList.add('completed');
            }
        });

        // Update step counter
        if (demoStepCounter) {
            demoStepCounter.textContent = `Stage ${stepNum} of ${totalDemoSteps}`;
        }

        // Update navigation buttons
        if (demoPrevBtn) demoPrevBtn.disabled = (stepNum === 1);
        if (demoNextBtn) {
            if (stepNum === totalDemoSteps) {
                demoNextBtn.classList.add('hidden');
                if (demoExploreTripBtn) demoExploreTripBtn.classList.remove('hidden');
            } else {
                demoNextBtn.classList.remove('hidden');
                demoNextBtn.textContent = 'Next Stage →';
                if (demoExploreTripBtn) demoExploreTripBtn.classList.add('hidden');
            }
        }

        // Render slide content
        if (demoStageBody) {
            demoStageBody.innerHTML = `
                <div class="demo-slide-wrap">
                    <div class="demo-slide-header">
                        <h3>${slide.title}</h3>
                        <span class="demo-slide-badge">${slide.badge}</span>
                    </div>
                    <p class="demo-slide-desc">${slide.desc}</p>
                    
                    <div class="demo-feature-grid">
                        ${slide.features.map(f => `
                            <div class="demo-feature-card">
                                <h4><span>${f.icon}</span> ${f.title}</h4>
                                <p>${f.desc}</p>
                            </div>
                        `).join('')}
                    </div>

                    <div class="demo-code-box">
                        <pre><code>${slide.codeSample}</code></pre>
                    </div>
                </div>
            `;
        }
    }

    function openDemoModal() {
        if (liveDemoModal) {
            liveDemoModal.classList.remove('hidden');
            renderDemoSlide(1);
        }
    }

    function closeDemoModal() {
        if (liveDemoModal) {
            liveDemoModal.classList.add('hidden');
            stopDemoAutoPlay();
        }
    }

    function stopDemoAutoPlay() {
        if (demoAutoPlayTimer) {
            clearInterval(demoAutoPlayTimer);
            demoAutoPlayTimer = null;
            if (demoAutoPlayIcon) demoAutoPlayIcon.textContent = '▶️';
            if (demoAutoPlayText) demoAutoPlayText.textContent = 'Auto-Play Showcase';
        }
    }

    function toggleDemoAutoPlay() {
        if (demoAutoPlayTimer) {
            stopDemoAutoPlay();
        } else {
            if (demoAutoPlayIcon) demoAutoPlayIcon.textContent = '⏸️';
            if (demoAutoPlayText) demoAutoPlayText.textContent = 'Pause Auto-Play';
            
            demoAutoPlayTimer = setInterval(() => {
                if (currentDemoStep < totalDemoSteps) {
                    renderDemoSlide(currentDemoStep + 1);
                } else {
                    renderDemoSlide(1);
                }
            }, 4500);
        }
    }

    // Attach Live Demo Event Handlers
    if (startLiveDemoBtn) startLiveDemoBtn.addEventListener('click', openDemoModal);
    if (heroLiveDemoBtn) heroLiveDemoBtn.addEventListener('click', openDemoModal);
    if (closeDemoModalBtn) closeDemoModalBtn.addEventListener('click', closeDemoModal);
    if (heroQuickPlanBtn) {
        heroQuickPlanBtn.addEventListener('click', () => {
            const chatSec = document.getElementById('chatInceptionSection');
            if (chatSec) {
                chatSec.scrollIntoView({ behavior: 'smooth' });
                const inp = document.getElementById('heroQueryInput');
                if (inp) inp.focus();
            }
        });
    }

    if (demoPrevBtn) {
        demoPrevBtn.addEventListener('click', () => {
            if (currentDemoStep > 1) {
                renderDemoSlide(currentDemoStep - 1);
            }
        });
    }

    if (demoNextBtn) {
        demoNextBtn.addEventListener('click', () => {
            if (currentDemoStep < totalDemoSteps) {
                renderDemoSlide(currentDemoStep + 1);
            }
        });
    }

    if (demoAutoPlayBtn) {
        demoAutoPlayBtn.addEventListener('click', toggleDemoAutoPlay);
    }

    if (demoExploreTripBtn) {
        demoExploreTripBtn.addEventListener('click', () => {
            closeDemoModal();
            // Switch to trip dashboard view
            switchView('dashboard');
        });
    }

    // Allow clicking on stepper nodes directly
    document.querySelectorAll('.demo-step-node').forEach(node => {
        node.addEventListener('click', () => {
            const stepNum = parseInt(node.getAttribute('data-step'), 10);
            if (stepNum) renderDemoSlide(stepNum);
        });
    });

    if (liveDemoModal) {
        liveDemoModal.addEventListener('click', (e) => {
            if (e.target === liveDemoModal) closeDemoModal();
        });
    }

    // Fetch Engine and Model Metadata on Launch
    async function fetchModelMetadata() {
        try {
            const res = await fetch('/api/v1/observability/models');
            if (res.ok) {
                const data = await res.json();
                if (engineModelName) {
                    if (data.active_provider === 'Local_Ollama') {
                        engineModelName.textContent = `Local AI (${data.local_llm.fast_model})`;
                    } else {
                        engineModelName.textContent = data.provider_status || 'AWS Bedrock';
                    }
                }
            }
        } catch (e) {
            console.log('Telemetry model metadata check:', e);
        }
    }

    // ============================================================
    // INITIALIZATION & CACHED TRIP RESTORATION
    // ============================================================
    async function initializeApp() {
        setCurrency(currentCurrency);
        updateUserProfileUI();
        loadTripTemplates();
        fetchModelMetadata();

        const saved = localStorage.getItem('nomados_current_trip');
        if (saved) {
            try {
                currentTrip = JSON.parse(saved);
                renderTripDashboard(currentTrip);
            } catch (e) {
                console.warn('Could not parse cached trip:', e);
            }
        }

        if (!currentTrip) {
            try {
                const res = await fetch('/api/v1/trip/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: "3-day relaxed coastal getaway in Goa with friends",
                        origin_city: "Bangalore",
                        destination: "Goa",
                        duration_days: 3,
                        companions: "Friends",
                        budget_amount: currentCurrency === 'USD' ? 750 : 20000,
                        currency: currentCurrency
                    })
                });
                if (res.ok) {
                    currentTrip = await res.json();
                    localStorage.setItem('nomados_current_trip', JSON.stringify(currentTrip));
                    renderTripDashboard(currentTrip);
                }
            } catch (e) {
                console.log('Default trip synthesis deferred:', e);
            }
        }
    }

    initializeApp();
});

