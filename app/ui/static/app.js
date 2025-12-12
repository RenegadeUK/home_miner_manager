// v0 Miner Controller - Main JavaScript

// Utility function for API calls
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call error:', error);
        throw error;
    }
}

// Format hashrate
function formatHashrate(ghs) {
    if (ghs >= 1000) {
        return (ghs / 1000).toFixed(2) + ' TH/s';
    }
    return ghs.toFixed(2) + ' GH/s';
}

// Format timestamp
function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Show notification (basic implementation)
function showNotification(message, type = 'info') {
    // TODO: Implement proper notification system
    console.log(`[${type}] ${message}`);
}

console.log('v0 Miner Controller initialized');
