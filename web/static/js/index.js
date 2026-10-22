// Главная страница
let currentYearFilter = 'all';

// Форма открывается на текущем месяце по МСК
function setCurrentPeriod() {
    const { year, month } = moscowYearMonth();
    document.getElementById('year').value = year;
    document.getElementById('month').value = month;
}

document.addEventListener('DOMContentLoaded', function() {
    initModals();

    loadStatistics();
    loadSalaries();
    loadYearFilter();

    document.getElementById('addSalaryForm').addEventListener('submit', function(e) {
        e.preventDefault();
        addSalary();
    });

    document.getElementById('refreshBtn').addEventListener('click', function() {
        refreshData();
    });

    document.getElementById('yearFilter').addEventListener('change', function() {
        currentYearFilter = this.value;
        loadSalaries();
        loadStatistics();
    });

    setCurrentPeriod();
    loadSalaryForPeriod();

    document.getElementById('year').addEventListener('change', loadSalaryForPeriod);
    document.getElementById('month').addEventListener('change', loadSalaryForPeriod);

    // Клик по строке таблицы открывает этот месяц в форме для правки
    document.getElementById('salariesTable').addEventListener('click', function(e) {
        const row = e.target.closest('tr[data-year]');
        if (row) {
            openPeriodInForm(Number(row.dataset.year), Number(row.dataset.month));
        }
    });

    attachDateMask(document.getElementById('advance_date'));
    attachDateMask(document.getElementById('salary_date'));
});

async function loadStatistics() {
    try {
        let url = '/api/statistics';
        if (currentYearFilter !== 'all') {
            url += `?year=${currentYearFilter}`;
        }
        const result = await makeRequest(url);
        if (result.success) {
            const stats = result.data;
            const isAllYears = currentYearFilter === 'all';
            const yearsLabel = isAllYears ? 'Количество лет' : 'Выбранный год';
            const yearsValue = isAllYears
                ? `${stats.years_count} (${stats.first_year}–${stats.last_year})`
                : currentYearFilter;

            const html = `
                <div class="row text-center">
                    <div class="col-6 mb-3">
                        <h6 class="text-muted">Общая сумма</h6>
                        <h4 class="text-primary">${formatCurrency(stats.total_all)}</h4>
                    </div>
                    <div class="col-6 mb-3">
                        <h6 class="text-muted">Среднемесячно</h6>
                        <h4 class="text-success">${formatCurrency(stats.average_monthly)}</h4>
                    </div>
                    <div class="col-6">
                        <h6 class="text-muted">Всего записей</h6>
                        <h5>${stats.total_records}</h5>
                    </div>
                    <div class="col-6">
                        <h6 class="text-muted">${yearsLabel}</h6>
                        <h5>${yearsValue}</h5>
                    </div>
                    <div class="col-12 mt-2 d-none" id="forecastLine"></div>
                </div>
            `;
            document.getElementById('statistics').innerHTML = html;
            loadForecast(isAllYears);
        } else {
            showStatus('Ошибка загрузки статистики: ' + result.message, 'error');
        }
    } catch (error) {
        showStatus('Ошибка загрузки статистики: ' + error.message, 'error');
    }
}

// Прогноз итога текущего года (по МСК) — для «всех годов» и текущего года
async function loadForecast(isAllYears) {
    const { year } = moscowYearMonth();
    if (!isAllYears && Number(currentYearFilter) !== year) return;
    try {
        const result = await makeRequest('/api/forecast');
        const line = document.getElementById('forecastLine');
        if (result.success && result.data && line) {
            const rounded = Math.round(result.data.forecast / 1000) * 1000;
            line.innerHTML = `<small class="text-muted">Прогноз на ${result.data.year}: ≈ ${rounded.toLocaleString('ru-RU')} ₽</small>`;
            line.classList.remove('d-none');
        }
    } catch (error) {
        // прогноз необязателен — без него статистика остаётся как есть
    }
}

async function loadSalaries() {
    const tbody = document.getElementById('salariesTable');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Загрузка...</span>
                </div>
            </td>
        </tr>
    `;

    try {
        const result = await makeRequest('/api/salaries');
        if (result.success) {
            let salaries = result.data;

            if (currentYearFilter !== 'all') {
                salaries = salaries.filter(s => s.year == currentYearFilter);
            }

            salaries.sort((a, b) => {
                if (a.year !== b.year) return b.year - a.year;
                return b.month - a.month;
            });

            if (salaries.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="text-center text-muted">
                            <i class="bi bi-info-circle me-2"></i>
                            Нет данных для отображения
                        </td>
                    </tr>
                `;
                return;
            }

            let html = '';
            salaries.forEach(salary => {
                const monthName = salary.month_name || salary.month;
                const total = (salary.advance || 0) + (salary.salary || 0);
                const advanceDate = salary.advance_date || '-';
                const salaryDate = salary.salary_date || '-';

                html += `
                    <tr data-year="${salary.year}" data-month="${salary.month}" class="salary-row"
                        title="Изменить ${monthName} ${salary.year}">
                        <td>${salary.year}</td>
                        <td>
                            <span class="badge bg-primary month-badge">${monthName}</span>
                            ${salary.note ? `<i class="bi bi-sticky ms-1 text-muted" title="${escapeHtml(salary.note)}"></i>` : ''}
                        </td>
                        <td>${formatCurrency(salary.advance)}</td>
                        <td>${advanceDate}</td>
                        <td>${formatCurrency(salary.salary)}</td>
                        <td>${salaryDate}</td>
                        <td><strong>${formatCurrency(total)}</strong></td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
            markSelectedRow();
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        ${result.message}
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Ошибка сети: ${error.message}
                </td>
            </tr>
        `;
    }
}

async function loadYearFilter() {
    try {
        const result = await makeRequest('/api/years');
        if (result.success) {
            const years = result.data;
            const select = document.getElementById('yearFilter');

            const currentValue = select.value;

            select.innerHTML = '<option value="all">Все годы</option>';
            years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                select.appendChild(option);
            });

            if (currentValue && [...select.options].some(opt => opt.value === currentValue)) {
                select.value = currentValue;
                currentYearFilter = currentValue;
            }
        }
    } catch (error) {
        console.warn('Эндпоинт /api/years недоступен, используем старый метод');
        loadYearFilterFallback();
    }
}

async function loadYearFilterFallback() {
    try {
        const result = await makeRequest('/api/salaries');
        if (result.success) {
            const years = [...new Set(result.data.map(s => s.year))].sort((a, b) => b - a);
            const select = document.getElementById('yearFilter');

            const currentValue = select.value;
            select.innerHTML = '<option value="all">Все годы</option>';

            years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                select.appendChild(option);
            });

            if (currentValue && [...select.options].some(opt => opt.value === currentValue)) {
                select.value = currentValue;
                currentYearFilter = currentValue;
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки лет:', error);
    }
}

async function addSalary() {
    const form = document.getElementById('addSalaryForm');
    const formData = {
        year: parseInt(document.getElementById('year').value),
        month: parseInt(document.getElementById('month').value),
        advance: parseFloat(document.getElementById('advance').value) || 0,
        salary: parseFloat(document.getElementById('salary').value) || 0,
        advance_date: document.getElementById('advance_date').value || '',
        salary_date: document.getElementById('salary_date').value || '',
        // Поле подставлено из базы: пустое — заметку стёрли
        note: document.getElementById('note').value.trim()
    };

    if (formData.advance < 0 || formData.salary < 0) {
        showStatus('Аванс и зарплата не могут быть отрицательными', 'error');
        return;
    }
    if (!isValidDateString(formData.advance_date)) {
        showStatus('Неверный формат даты аванса. Ожидается ДД.ММ.ГГГГ', 'error');
        return;
    }
    if (!isValidDateString(formData.salary_date)) {
        showStatus('Неверный формат даты зарплаты. Ожидается ДД.ММ.ГГГГ', 'error');
        return;
    }

    try {
        const result = await makeRequest('/api/salary', {
            method: 'POST',
            body: JSON.stringify(formData)
        });

        if (result.success) {
            showStatus('Данные успешно сохранены!', 'success');
            form.reset();

            setCurrentPeriod();
            loadSalaryForPeriod();

            refreshData();
        } else {
            showStatus('Ошибка: ' + result.message, 'error');
        }
    } catch (error) {
        showStatus('Ошибка сети: ' + error.message, 'error');
    }
}

function openPeriodInForm(year, month) {
    document.getElementById('year').value = year;
    document.getElementById('month').value = month;
    loadSalaryForPeriod();
    // На узком экране форма выше таблицы — прокрутить к ней
    document.getElementById('addSalaryForm').scrollIntoView({ behavior: 'smooth', block: 'start' });
    document.getElementById('advance').focus({ preventScroll: true });
}

// Подсветить в таблице месяц, открытый в форме
function markSelectedRow() {
    const year = document.getElementById('year').value;
    const month = document.getElementById('month').value;
    document.querySelectorAll('#salariesTable tr[data-year]').forEach(row => {
        row.classList.toggle('table-active', row.dataset.year === year && row.dataset.month === month);
    });
}

// Кнопка и подсказка формы: новый месяц добавляется, заполненный — заменяется
function setFormMode(existing, year, month) {
    const button = document.getElementById('submitBtn');
    const hint = document.getElementById('periodHint');
    if (existing) {
        const monthName = document.querySelector(`#month option[value="${month}"]`).textContent.toLowerCase();
        button.innerHTML = '<i class="bi bi-pencil-square me-2"></i>Сохранить изменения';
        hint.textContent = `За ${monthName} ${year} уже есть данные — сохранение заменит их.`;
        hint.classList.remove('d-none');
    } else {
        button.innerHTML = '<i class="bi bi-plus-circle me-2"></i>Добавить';
        hint.textContent = '';
        hint.classList.add('d-none');
    }
}

function fillForm(data) {
    document.getElementById('advance').value = data ? (data.advance ?? 0) : '';
    document.getElementById('salary').value = data ? (data.salary ?? 0) : '';
    document.getElementById('advance_date').value = data ? (data.advance_date ?? '') : '';
    document.getElementById('salary_date').value = data ? (data.salary_date ?? '') : '';
    document.getElementById('note').value = data ? (data.note ?? '') : '';
}

async function loadSalaryForPeriod() {
    const year = parseInt(document.getElementById('year').value);
    const month = parseInt(document.getElementById('month').value);

    if (!year || !month) {
        return;
    }

    let data = null;
    try {
        // 404 — за месяц ещё нет данных: форма для нового месяца
        const result = await makeRequest(`/api/salary/${year}/${month}`);
        data = result.success && result.data ? result.data : null;
    } catch (error) {
        data = null;
    }
    fillForm(data);
    setFormMode(Boolean(data), year, month);
    markSelectedRow();
}

function refreshData() {
    loadSalaries();
    loadStatistics();
    loadYearFilter();
    showStatus('Данные обновлены', 'success');
}
