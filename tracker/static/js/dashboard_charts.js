// Dashboard Charts
document.addEventListener('DOMContentLoaded', function() {
    // Order Status Doughnut Chart
    const ctx = document.getElementById('orderStatusChart');
    if (ctx) {
        const statusData = {
            completed: parseInt(document.querySelector('.col-3:nth-child(1) .fw-bold').textContent) || 0,
            in_progress: parseInt(document.querySelector('.col-3:nth-child(2) .fw-bold').textContent) || 0,
            overdue: parseInt(document.querySelector('.col-3:nth-child(3) .fw-bold').textContent) || 0,
            cancelled: parseInt(document.querySelector('.col-3:nth-child(4) .fw-bold').textContent) || 0
        };

        const total = statusData.completed + statusData.in_progress + statusData.overdue + statusData.cancelled;

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'In Progress', 'Overdue', 'Cancelled'],
                datasets: [{
                    data: [statusData.completed, statusData.in_progress, statusData.overdue, statusData.cancelled],
                    backgroundColor: ['#28a745', '#007bff', '#dc3545', '#6c757d'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} orders (${percentage}%)`;
                            }
                        },
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#fff',
                        borderWidth: 1
                    }
                },
                cutout: '60%',
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });
    }
});