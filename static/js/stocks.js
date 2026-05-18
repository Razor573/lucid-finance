document.addEventListener('DOMContentLoaded', function() {
    const canvases = document.querySelectorAll('.sparkline-canvas');
    
    canvases.forEach(canvas => {
        const ticker = canvas.getAttribute('data-ticker');
        if (!ticker) return;
        
        fetch(`/stocks/api/history/${ticker}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network error');
                }
                return response.json();
            })
            .then(data => {
                if (!data.prices || data.prices.length === 0) {
                    drawErrorSparkline(canvas);
                    return;
                }
                
                renderSparkline(canvas, data.labels, data.prices);
            })
            .catch(err => {
                console.error(`Failed to fetch sparkline for ${ticker}:`, err);
                drawErrorSparkline(canvas);
            });
    });
});

function renderSparkline(canvas, labels, prices) {
    const ctx = canvas.getContext('2d');
    
    const firstPrice = prices[0];
    const lastPrice = prices[prices.length - 1];
    const isGain = lastPrice >= firstPrice;
    
    // green vs red glow colors matching index.css/vars
    const lineColor = isGain ? '#10b981' : '#f43f5e';
    const glowColor = isGain ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)';
    
    // gradient for sparkline area fill
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, glowColor);
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: prices,
                borderColor: lineColor,
                borderWidth: 1.8,
                pointRadius: 0,
                pointHoverRadius: 3,
                pointHitRadius: 10,
                fill: true,
                backgroundColor: gradient,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    displayColors: false,
                    backgroundColor: 'rgba(9, 11, 17, 0.85)',
                    titleColor: '#9ca3af',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(255, 255, 255, 0.08)',
                    borderWidth: 1,
                    padding: 6,
                    bodyFont: {
                        family: "'Plus Jakarta Sans', sans-serif",
                        size: 10,
                        weight: 'bold'
                    },
                    titleFont: {
                        family: "'Plus Jakarta Sans', sans-serif",
                        size: 8
                    },
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: { display: false },
                y: { display: false }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

function drawErrorSparkline(canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
}
