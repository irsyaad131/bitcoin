// Update the success handler in your AJAX call
success: function(response) {
    if (response.status === 'success') {
        // Update price and indicators
        $('#current-price').text('$' + response.current_price.toLocaleString());
        $('#sma20-value').text(response.sma_20.toLocaleString());
        $('#sma50-value').text(response.sma_50.toLocaleString());
        $('#rsi-value').text(response.rsi.toLocaleString());
        
        // Create allocation recommendation
        const allocationRecommendation = {
            'type': 'Capital Allocation',
            'date': response.last_updated,
            'price': response.current_price,
            'strength': 'Recommended Allocation: ' + response.default_allocation + '%',
            'description': 'Based on current RSI of ' + response.rsi,
            'allocation': response.default_allocation,
            'rsi': response.rsi
        };
        
        // Add allocation recommendation to the list
        if (response.recommendations.length > 0) {
            response.recommendations.unshift(allocationRecommendation);
        } else {
            response.recommendations = [allocationRecommendation];
        }
        
        // Render recommendations (existing code)
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
                                <span class="me-3"><strong>Date:</strong> ${rec.date}</span>
                                <span class="me-3"><strong>Price:</strong> $${rec.price.toLocaleString()}</span>
                                ${rec.rsi ? `<span class="me-3"><strong>RSI:</strong> ${rec.rsi}</span>` : ''}
                            </div>
                            <p class="mb-0 mt-1"><strong>Action:</strong> ${rec.strength}</p>
                            ${rec.description ? `<p class="mt-1 mb-0 small">${rec.description}</p>` : ''}
                            ${rec.allocation ? `<div class="mt-2">
                                <div class="progress">
                                    <div class="progress-bar bg-warning" role="progressbar" 
                                        style="width: ${rec.allocation}%" 
                                        aria-valuenow="${rec.allocation}" 
                                        aria-valuemin="0" 
                                        aria-valuemax="100">
                                        ${rec.allocation}% Allocation
                                    </div>
                                </div>
                            </div>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        $('#recommendations').html(recHtml);
        
        // Render chart (existing code)
        const chartData = JSON.parse(response.chart);
        Plotly.newPlot('price-chart', chartData.data, chartData.layout);
    }
}
