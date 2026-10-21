/**
 * Common helpers for web UI.
 */

function showStatus(message, type = 'success') {
    const statusDiv = document.getElementById('status');
    if (!statusDiv) {
        console.log(`Status [${type}]: ${message}`);
        return;
    }

    statusDiv.textContent = message;
    statusDiv.className = 'status ' + type;
    statusDiv.style.display = 'block';

    if (type === 'success') {
        setTimeout(() => {
            hideStatus();
        }, 5000);
    }
}

function hideStatus() {
    const statusDiv = document.getElementById('status');
    if (statusDiv) {
        statusDiv.style.display = 'none';
    }
}

function showLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

function validateYear(year, minYear = 2000, maxYear = 2100) {
    return !!year && year >= minYear && year <= maxYear;
}

function formatMoney(amount) {
    return parseFloat(amount || 0).toLocaleString('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Стандарт времени: моменты приходят из API в UTC (с «Z» или «+00:00»),
// человеку показываем МСК независимо от часового пояса браузера.
const MOSCOW_TIME_ZONE = 'Europe/Moscow';

function formatMoscowDateTime(isoString) {
    const moment = new Date(isoString);
    if (Number.isNaN(moment.getTime())) return '';
    return moment.toLocaleString('ru-RU', {
        timeZone: MOSCOW_TIME_ZONE,
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    }) + ' МСК';
}

function moscowYearMonth() {
    const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: MOSCOW_TIME_ZONE, year: 'numeric', month: 'numeric'
    }).formatToParts(new Date());
    const part = type => Number(parts.find(item => item.type === type).value);
    return { year: part('year'), month: part('month') };
}

function formatCurrency(amount) {
    return `${formatMoney(amount)} ₽`;
}

async function makeRequest(url, options = {}) {
    try {
        showLoading();

        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const result = await response.json();

        hideLoading();

        if (!response.ok) {
            throw new Error(result.message || `Ошибка ${response.status}`);
        }

        return result;
    } catch (error) {
        hideLoading();
        showStatus(`Ошибка: ${error.message}`, 'error');
        throw error;
    }
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

function setupModalCloseOnClickOutside(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeModal(modalId);
            }
        });
    }
}

function setupModalCloseOnEsc(modalId) {
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal(modalId);
        }
    });
}

function initModals() {
    const modals = document.querySelectorAll('.modal');

    modals.forEach(modal => {
        const modalId = modal.id;
        if (modalId) {
            setupModalCloseOnClickOutside(modalId);
            setupModalCloseOnEsc(modalId);

            const closeButtons = modal.querySelectorAll('.close-modal');
            closeButtons.forEach(button => {
                button.addEventListener('click', () => closeModal(modalId));
            });
        }
    });
}

function attachDateMask(input) {
    if (!input) return;
    input.addEventListener('input', function() {
        const raw = input.value;
        const digits = raw.replace(/\D/g, '').slice(0, 8);
        if (digits.length === 0) {
            input.value = '';
            return;
        }
        if (raw.includes('/') || raw.includes('-')) {
            if (digits.length >= 5) {
                input.value = `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
            } else if (digits.length >= 3) {
                input.value = `${digits.slice(0, 2)}/${digits.slice(2)}`;
            } else {
                input.value = digits;
            }
            return;
        }

        if (digits.length >= 5) {
            input.value = `${digits.slice(0, 2)}.${digits.slice(2, 4)}.${digits.slice(4)}`;
        } else if (digits.length >= 3) {
            input.value = `${digits.slice(0, 2)}.${digits.slice(2)}`;
        } else {
            input.value = digits;
        }
    });
}

function isValidDateString(value) {
    if (!value) return true;
    if (/^\d{8}$/.test(value)) return true;
    return /^\d{2}[.\/-]\d{2}[.\/-]\d{4}$/.test(value);
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showStatus,
        hideStatus,
        showLoading,
        hideLoading,
        validateYear,
        formatMoney,
        formatCurrency,
        makeRequest,
        openModal,
        closeModal,
        attachDateMask,
        isValidDateString,
        initModals
    };
}