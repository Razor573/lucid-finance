document.addEventListener('DOMContentLoaded', function() {
    let spendingChartInstance = null;
    let trendChartInstance = null;

    const neonColors = {
        'Groceries': 'rgba(6, 182, 212, 0.85)',
        'Transport': 'rgba(245, 158, 11, 0.85)',
        'Entertainment': 'rgba(139, 92, 246, 0.85)',
        'Bills': 'rgba(244, 63, 94, 0.85)',
        'Salary': 'rgba(16, 185, 129, 0.85)',
        'Other': 'rgba(156, 163, 175, 0.7)'
    };

    const neonBorders = {
        'Groceries': '#06b6d4',
        'Transport': '#f59e0b',
        'Entertainment': '#8b5cf6',
        'Bills': '#f43f5e',
        'Salary': '#10b981',
        'Other': '#9ca3af'
    };

    // get spending data & render doughnut chart
    function renderSpendingChart(month = '') {
        const url = `/api/spending-by-category${month ? '?month=' + month : ''}`;
        
        fetch(url)
            .then(response => response.json())
            .then(res => {
                const ctx = document.getElementById('spendingChart').getContext('2d');
                
                const bgColors = res.labels.map(label => neonColors[label] || 'rgba(156, 163, 175, 0.6)');
                const borderColors = res.labels.map(label => neonBorders[label] || '#9ca3af');
                
                if (spendingChartInstance) {
                    spendingChartInstance.destroy();
                }
                
                spendingChartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: res.labels,
                        datasets: [{
                            data: res.data,
                            backgroundColor: bgColors,
                            borderColor: borderColors,
                            borderWidth: 1.5,
                            hoverOffset: 12
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right',
                                labels: {
                                    color: '#9ca3af',
                                    font: {
                                        family: "'Plus Jakarta Sans', sans-serif",
                                        weight: '600',
                                        size: 11
                                    },
                                    padding: 15,
                                    usePointStyle: true,
                                    pointStyle: 'circle'
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(9, 11, 17, 0.95)',
                                titleFont: { family: "'Plus Jakarta Sans', sans-serif", weight: '700' },
                                bodyFont: { family: "'Plus Jakarta Sans', sans-serif" },
                                borderColor: 'rgba(255,255,255,0.08)',
                                borderWidth: 1,
                                callbacks: {
                                    label: function(context) {
                                        let label = context.label || '';
                                        if (label) {
                                            label += ': ';
                                        }
                                        if (context.parsed !== null) {
                                            const currencySymbol = res.currency === 'GBP' ? '£' : (res.currency === 'USD' ? '$' : '€');
                                            label += currencySymbol + context.parsed.toFixed(2);
                                        }
                                        return label;
                                    }
                                }
                            }
                        },
                        cutout: '72%',
                        layout: {
                            padding: 10
                        }
                    }
                });
            })
            .catch(err => console.error('Error fetching spending data:', err));
    }

    // get historical cashflow trend for line chart
    function renderTrendChart() {
        fetch('/api/monthly-trend?months=6')
            .then(response => response.json())
            .then(res => {
                const ctx = document.getElementById('trendChart').getContext('2d');
                
                // gradients under lines
                const incomeGradient = ctx.createLinearGradient(0, 0, 0, 250);
                incomeGradient.addColorStop(0, 'rgba(16, 185, 129, 0.35)');
                incomeGradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
                
                const expenseGradient = ctx.createLinearGradient(0, 0, 0, 250);
                expenseGradient.addColorStop(0, 'rgba(244, 63, 94, 0.35)');
                expenseGradient.addColorStop(1, 'rgba(244, 63, 94, 0.0)');
                
                if (trendChartInstance) {
                    trendChartInstance.destroy();
                }
                
                trendChartInstance = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: res.labels,
                        datasets: [
                            {
                                label: 'Monthly Income',
                                data: res.income,
                                borderColor: '#10b981',
                                borderPercent: 3,
                                borderWidth: 3,
                                backgroundColor: incomeGradient,
                                fill: true,
                                tension: 0.4,
                                pointBackgroundColor: '#10b981',
                                pointBorderColor: 'rgba(255,255,255,0.8)',
                                pointHoverRadius: 7,
                                pointRadius: 4
                            },
                            {
                                label: 'Monthly Expenses',
                                data: res.expenses,
                                borderColor: '#f43f5e',
                                borderPercent: 3,
                                borderWidth: 3,
                                backgroundColor: expenseGradient,
                                fill: true,
                                tension: 0.4,
                                pointBackgroundColor: '#f43f5e',
                                pointBorderColor: 'rgba(255,255,255,0.8)',
                                pointHoverRadius: 7,
                                pointRadius: 4
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'top',
                                labels: {
                                    color: '#9ca3af',
                                    font: {
                                        family: "'Plus Jakarta Sans', sans-serif",
                                        weight: '600'
                                    },
                                    usePointStyle: true,
                                    pointStyle: 'circle'
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(9, 11, 17, 0.95)',
                                titleFont: { family: "'Plus Jakarta Sans', sans-serif", weight: '700' },
                                bodyFont: { family: "'Plus Jakarta Sans', sans-serif" },
                                borderColor: 'rgba(255,255,255,0.08)',
                                borderWidth: 1,
                                callbacks: {
                                    label: function(context) {
                                        let label = context.dataset.label || '';
                                        if (label) {
                                            label += ': ';
                                        }
                                        if (context.parsed.y !== null) {
                                            const currencySymbol = res.currency === 'GBP' ? '£' : (res.currency === 'USD' ? '$' : '€');
                                            label += currencySymbol + context.parsed.y.toFixed(2);
                                        }
                                        return label;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.05)',
                                    drawBorder: false
                                },
                                ticks: {
                                    color: '#6b7280',
                                    font: { family: "'Plus Jakarta Sans', sans-serif", weight: '500' }
                                }
                            },
                            x: {
                                grid: {
                                    display: false
                                },
                                ticks: {
                                    color: '#6b7280',
                                    font: { family: "'Plus Jakarta Sans', sans-serif", weight: '500' }
                                }
                            }
                        }
                    }
                });
            })
            .catch(err => console.error('Error fetching trend data:', err));
    }

    // handle category monthly filter selection
    const filterInput = document.getElementById('categoryMonthFilter');
    if (filterInput) {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        filterInput.value = `${year}-${month}`;
        
        filterInput.addEventListener('change', function(e) {
            renderSpendingChart(e.target.value);
        });
    }

    renderSpendingChart();
    renderTrendChart();
});
