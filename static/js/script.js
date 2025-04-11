$(document).ready(function() {
    $('#analyze-btn').click(function() {
        const period = $('#period-select').val();
        const $btn = $(this);
        
        // Show loading state
        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span> Memproses...');
        $('#loading-indicator').removeClass('d-none');
        $('#recommendations').html('<div class="text-center py-3"><i class="fas fa-spinner fa-spin"></i></div>');
        
        $.ajax({
            url: '/get_recommendations',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ period: period }),
            success: function(response) {
                if (response.status === 'success') {
                    // Update price info
                    $('#current-price').text('$' + response.current_price.toLocaleString());
                    $('#sma20-value').text(response.sma_20.toLocaleString());
                    $('#sma50-value').text(response.sma_50.toLocaleString());
                    $('#rsi-value').text(response.rsi.toLocaleString());
                    
                    // Render recommendations
                    let recHtml = '';
                    response.recommendations.forEach(rec => {
                        recHtml += `
                            <div class="alert ${getAlertClass(rec.type)} mb-3">
                                <div class="d-flex align-items-center">
                                    <div class="flex-shrink-0">
                                        <i class="${getIconClass(rec.type)} fa-lg me-2"></i>
                                    </div>
                                    <div class="flex-grow-1 ms-2">
                                        <h6 class="alert-heading mb-1">${rec.type}</h6>
                                        <div class="d-flex flex-wrap">
                                            <span class="me-3"><strong>Tanggal:</strong> ${rec.date}</span>
                                            <span class="me-3"><strong>Harga:</strong> $${rec.price.toLocaleString()}</span>
                                            ${rec.rsi ? `<span class="me-3"><strong>RSI:</strong> ${rec.rsi}</span>` : ''}
                                        </div>
                                        <p class="mb-0 mt-1"><strong>Aksi:</strong> ${rec.strength}</p>
                                        ${rec.description ? `<p class="mt-1 mb-0 small">${rec.description}</p>` : ''}
                                        ${rec.allocation ? `<div class="mt-2">
                                            <div class="progress">
                                                <div class="progress-bar bg-warning" role="progressbar" 
                                                    style="width: ${rec.allocation}%" 
                                                    aria-valuenow="${rec.allocation}" 
                                                    aria-valuemin="0" 
                                                    aria-valuemax="100">
                                                    Alokasi ${rec.allocation}%
                                                </div>
                                            </div>
                                        </div>` : ''}
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    $('#recommendations').html(recHtml);
                    
                    // Render chart
                    const chartData = JSON.parse(response.chart);
                    Plotly.newPlot('price-chart', chartData.data, chartData.layout);
                } else {
                    showError(response.message || 'Terjadi kesalahan');
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON?.message || 'Gagal memuat data';
                showError(errorMsg);
            },
            complete: function() {
                $btn.prop('disabled', false).html('<i class="fas fa-chart-line me-2"></i>Analisis Sekarang');
                $('#loading-indicator').addClass('d-none');
            }
        });
    });
    
    // Trigger initial analysis
    $('#analyze-btn').click();
});

function getAlertClass(type) {
    const classes = {
        'Golden Cross': 'alert-success',
        'RSI Extreme Oversold': 'alert-danger',
        'RSI Oversold': 'alert-warning',
        'RSI Normal': 'alert-info'
    };
    return classes[type] || 'alert-secondary';
}

function getIconClass(type) {
    const icons = {
        'Golden Cross': 'fas fa-crosshairs',
        'RSI Extreme Oversold': 'fas fa-arrow-down',
        'RSI Oversold': 'fas fa-arrow-circle-down',
        'RSI Normal': 'fas fa-info-circle'
    };
    return icons[type] || 'fas fa-chart-line';
}

function showError(message) {
    $('#recommendations').html(`
        <div class="alert alert-danger">
            <h6><i class="fas fa-exclamation-triangle me-2"></i>Error</h6>
            <p class="mb-0">${message}</p>
        </div>
    `);
}
