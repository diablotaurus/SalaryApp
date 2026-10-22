let salaryChart = null;
const MONTHS_FULL = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];
const MONTHS_SHORT = [
    'Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
    'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'
];

const COLORS = {
    advance: '#FF6384',
    salary: '#36A2EB',
    total: '#4BC0C0',
    yearly: '#4A90E2',
    growth: '#FF8C42',
    extras: '#9966FF'
};

const FILL = {
    advance: 'rgba(255, 99, 132, 0.2)',
    salary: 'rgba(54, 162, 235, 0.2)',
    total: 'rgba(75, 192, 192, 0.2)'
};
const LINE_ALPHA = 0.35;

function hexToRgba(hex, alpha) {
    const value = hex.replace('#', '');
    if (value.length !== 6) {
        return hex;
    }
    const r = parseInt(value.slice(0, 2), 16);
    const g = parseInt(value.slice(2, 4), 16);
    const b = parseInt(value.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function lineDataset(label, data, color) {
    return {
        label,
        data,
        borderColor: hexToRgba(color, LINE_ALPHA),
        backgroundColor: color,
        pointBackgroundColor: color,
        pointBorderColor: color,
        pointRadius: 4,
        pointHoverRadius: 5,
        borderWidth: 2,
        fill: false,
        tension: 0.2
    };
}

document.addEventListener('DOMContentLoaded', function() {
    initModals();
    loadYearsForCharts();
    loadChartData();
    loadBestPeriods();

    document.getElementById('chartYearSelect').addEventListener('change', loadChartData);
    document.getElementById('chartTypeSelect').addEventListener('change', loadChartData);
});

async function loadYearsForCharts() {
    try {
        const result = await makeRequest('/api/years');
        if (result.success) {
            const select = document.getElementById('chartYearSelect');
            const years = result.data;

            years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Ошибка загрузки лет для графиков:', error);
    }
}

async function loadChartData() {
    const year = document.getElementById('chartYearSelect').value;
    const chartType = document.getElementById('chartTypeSelect').value;

    try {
        let url = `/api/chart/${chartType}`;
        if (year !== 'all') {
            url += `?year=${year}`;
        }

        const result = await makeRequest(url);
        if (result.success) {
            updateChart(result.data, chartType);
        }
    } catch (error) {
        showStatus('Ошибка загрузки данных для графика: ' + error.message, 'error');
    }
}

async function loadBestPeriods() {
    const bestMonthEl = document.getElementById('bestMonth');
    const bestYearEl = document.getElementById('bestYear');

    try {
        const result = await makeRequest('/api/best_periods');
        if (!result.success) {
            bestMonthEl.innerHTML = '<div class="text-muted">Нет данных</div>';
            bestYearEl.innerHTML = '<div class="text-muted">Нет данных</div>';
            return;
        }

        const bestMonth = result.data.best_month;
        const bestYear = result.data.best_year;

        if (bestMonth) {
            const monthLabel = `${bestMonth.month_name} ${bestMonth.year}`;
            const total = formatCurrency(bestMonth.total);
            bestMonthEl.innerHTML = `<strong>${monthLabel}</strong><div class="text-muted">${total}</div>`;
        } else {
            bestMonthEl.innerHTML = '<div class="text-muted">Нет данных</div>';
        }

        if (bestYear) {
            const total = formatCurrency(bestYear.total);
            bestYearEl.innerHTML = `<strong>${bestYear.year}</strong><div class="text-muted">${total}</div>`;
        } else {
            bestYearEl.innerHTML = '<div class="text-muted">Нет данных</div>';
        }
    } catch (error) {
        bestMonthEl.innerHTML = '<div class="text-muted">Нет данных</div>';
        bestYearEl.innerHTML = '<div class="text-muted">Нет данных</div>';
    }
}

function buildMonthlyChartData(dto) {
    if (!dto || !dto.items || dto.items.length === 0) {
        return { labels: [], datasets: [] };
    }
    if (dto.period === 'all') {
        const labels = dto.items.map(i => `${MONTHS_SHORT[i.month - 1]} ${i.year}`);
        const totals = dto.items.map(i => i.total || 0);
        return {
            labels,
            datasets: [lineDataset('Итого', totals, COLORS.total)]
        };
    }
    const labels = dto.items.map(i => MONTHS_FULL[i.month - 1]);
    const advances = dto.items.map(i => i.advance || 0);
    const salaries = dto.items.map(i => i.salary || 0);
    const totals = dto.items.map(i => i.total || 0);
    const extras = dto.items.map(i => i.extras || 0);
    const datasets = [
        lineDataset('Аванс', advances, COLORS.advance),
        lineDataset('Зарплата', salaries, COLORS.salary),
        lineDataset('Итого', totals, COLORS.total)
    ];
    if (extras.some(value => value > 0)) {
        // Доп. выплаты — только если были в году (иначе график прежний)
        datasets.splice(2, 0, lineDataset('Доп. выплаты', extras, COLORS.extras));
    }
    return { labels, datasets };
}

function buildYearlyChartData(dto) {
    const items = (dto && dto.items) ? dto.items : [];
    const labels = items.map(i => String(i.year));
    const totals = items.map(i => i.total || 0);
    return {
        labels,
        datasets: [{
            label: 'Сумма дохода по годам',
            data: totals,
            backgroundColor: COLORS.yearly
        }]
    };
}

function buildGrowthChartData(dto) {
    const items = (dto && dto.items) ? dto.items : [];
    if (items.length < 2) {
        return { labels: [], datasets: [] };
    }
    const labels = [];
    const growthRates = [];
    for (let i = 1; i < items.length; i++) {
        const prev = items[i - 1];
        const curr = items[i];
        const prevTotal = prev.total || 0;
        const currTotal = curr.total || 0;
        const growth = prevTotal > 0 ? ((currTotal - prevTotal) / prevTotal) * 100 : 0;
        const prevLabel = `${prev.year}${prev.projected ? '*' : ''}`;
        const currLabel = `${curr.year}${curr.projected ? '*' : ''}`;
        labels.push(`${prevLabel}-${currLabel}`);
        growthRates.push(Number(growth.toFixed(2)));
    }
    return {
        labels,
        datasets: [lineDataset('Темпы роста, %', growthRates, COLORS.growth)]
    };
}

function buildAverageChartData(dto) {
    const items = (dto && dto.items) ? dto.items : [];
    const avgAdvance = new Array(12).fill(0);
    const avgSalary = new Array(12).fill(0);
    const avgTotal = new Array(12).fill(0);
    items.forEach(i => {
        const idx = (i.month || 1) - 1;
        if (idx >= 0 && idx < 12) {
            avgAdvance[idx] = i.avg_advance || 0;
            avgSalary[idx] = i.avg_salary || 0;
            avgTotal[idx] = i.avg_total || 0;
        }
    });
    return {
        labels: MONTHS_FULL,
        datasets: [
            lineDataset('Средний аванс', avgAdvance, COLORS.advance),
            lineDataset('Средняя зарплата', avgSalary, COLORS.salary),
            lineDataset('Средний итог', avgTotal, COLORS.total)
        ]
    };
}

function updateChart(data, chartType) {
    const ctx = document.getElementById('salaryChart').getContext('2d');

    if (salaryChart) {
        salaryChart.destroy();
    }

    let chartConfig = {};

    if (chartType === 'monthly') {
        const chartData = buildMonthlyChartData(data);
        chartConfig = {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Помесячные данные'
                    }
                }
            }
        };
    } else if (chartType === 'yearly_comparison') {
        const chartData = buildYearlyChartData(data);
        chartConfig = {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Сравнение по годам'
                    }
                }
            }
        };
    } else if (chartType === 'growth_rate') {
        const chartData = buildGrowthChartData(data);
        chartConfig = {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Темпы роста'
                    }
                }
            }
        };
    } else if (chartType === 'average_by_month') {
        const chartData = buildAverageChartData(data);
        chartConfig = {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Средние по месяцам'
                    }
                }
            }
        };
    }

    salaryChart = new Chart(ctx, chartConfig);
}

function updateStats(_data) {}
