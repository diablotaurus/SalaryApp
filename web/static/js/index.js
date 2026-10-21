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
                </div>
            `;
            document.getElementById('statistics').innerHTML = html;
        } else {
            showStatus('Ошибка загрузки статистики: ' + result.message, 'error');
        }
    } catch (error) {
        showStatus('Ошибка загрузки статистики: ' + error.message, 'error');
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
                    <tr>
                        <td>${salary.year}</td>
                        <td>
                            <span class="badge bg-primary month-badge">${monthName}</span>
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
        salary_date: document.getElementById('salary_date').value || ''
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

async function loadSalaryForPeriod() {
    const year = parseInt(document.getElementById('year').value);
    const month = parseInt(document.getElementById('month').value);

    if (!year || !month) {
        return;
    }

    try {
        const result = await makeRequest(`/api/salary/${year}/${month}`);
        if (result.success && result.data) {
            document.getElementById('advance').value = result.data.advance ?? 0;
            document.getElementById('salary').value = result.data.salary ?? 0;
            document.getElementById('advance_date').value = result.data.advance_date ?? '';
            document.getElementById('salary_date').value = result.data.salary_date ?? '';
        } else {
            document.getElementById('advance').value = '';
            document.getElementById('salary').value = '';
            document.getElementById('advance_date').value = '';
            document.getElementById('salary_date').value = '';
        }
    } catch (error) {
        document.getElementById('advance').value = '';
        document.getElementById('salary').value = '';
        document.getElementById('advance_date').value = '';
        document.getElementById('salary_date').value = '';
    }
}

function refreshData() {
    loadSalaries();
    loadStatistics();
    loadYearFilter();
    showStatus('Данные обновлены', 'success');
}
