/**
 * Main JavaScript for Product Adder
 * Handles UI interactions and API calls
 */

// Global state
let isLoading = false;

// Utility functions
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('loading');
    }
    isLoading = true;
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.remove('loading');
    }
    isLoading = false;
}

function showAlert(type, message, duration = 5000) {
    const alertContainer = document.querySelector('.container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
    
    // Auto-dismiss after specified duration
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    }
}

function updateStatusBadge(elementId, isConnected) {
    const badge = document.getElementById(elementId);
    if (!badge) return;
    
    if (isConnected) {
        badge.className = 'badge bg-success me-2';
        badge.textContent = 'Connected';
    } else {
        badge.className = 'badge bg-danger me-2';
        badge.textContent = 'Disconnected';
    }
    
    // Add animation
    badge.classList.add('status-update');
    setTimeout(() => {
        badge.classList.remove('status-update');
    }, 500);
}

function updateConnectionStatus(isHealthy) {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) return;
    
    if (isHealthy) {
        statusElement.className = 'badge bg-success';
        statusElement.textContent = 'Online';
    } else {
        statusElement.className = 'badge bg-danger';
        statusElement.textContent = 'Offline';
    }
}

// API functions
async function checkSystemStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        updateStatusBadge('jds-status', data.jds_connected);
        updateStatusBadge('shopify-status', data.shopify_connected);
        updateStatusBadge('database-status', data.database_connected);
        updateStatusBadge('overall-status', data.status === 'healthy');
        updateConnectionStatus(data.status === 'healthy');
        
        return data;
    } catch (error) {
        console.error('Error checking status:', error);
        updateStatusBadge('overall-status', false);
        updateConnectionStatus(false);
        return null;
    }
}

async function syncJDS() {
    if (isLoading) return;
    
    const spinner = document.getElementById('jds-spinner');
    const button = document.getElementById('sync-jds-btn-card');
    
    if (spinner) spinner.classList.remove('d-none');
    if (button) button.disabled = true;
    
    showLoading('jds-count');
    
    try {
        const response = await fetch('/api/sync/jds');
        const data = await response.json();
        
        if (data.success) {
            const countElement = document.getElementById('jds-count');
            if (countElement) {
                countElement.textContent = data.data.count;
                countElement.classList.add('status-update');
                setTimeout(() => countElement.classList.remove('status-update'), 500);
            }
            showAlert('success', data.message);
        } else {
            showAlert('danger', data.message);
        }
    } catch (error) {
        console.error('Error syncing JDS:', error);
        showAlert('danger', 'Error syncing JDS products');
    } finally {
        if (spinner) spinner.classList.add('d-none');
        if (button) button.disabled = false;
        hideLoading('jds-count');
    }
}

async function syncShopify() {
    if (isLoading) return;
    
    const spinner = document.getElementById('shopify-spinner');
    const button = document.getElementById('sync-shopify-btn-card');
    
    if (spinner) spinner.classList.remove('d-none');
    if (button) button.disabled = true;
    
    showLoading('shopify-count');
    
    try {
        const response = await fetch('/api/sync/shopify');
        const data = await response.json();
        
        if (data.success) {
            const countElement = document.getElementById('shopify-count');
            if (countElement) {
                countElement.textContent = data.data.count;
                countElement.classList.add('status-update');
                setTimeout(() => countElement.classList.remove('status-update'), 500);
            }
            showAlert('success', data.message);
        } else {
            showAlert('danger', data.message);
        }
    } catch (error) {
        console.error('Error syncing Shopify:', error);
        showAlert('danger', 'Error syncing Shopify products');
    } finally {
        if (spinner) spinner.classList.add('d-none');
        if (button) button.disabled = false;
        hideLoading('shopify-count');
    }
}

async function syncAll() {
    if (isLoading) return;
    
    const spinner = document.getElementById('sync-all-spinner');
    const button = document.getElementById('sync-all-btn');
    
    if (spinner) spinner.classList.remove('d-none');
    if (button) button.disabled = true;
    
    showLoading('jds-count');
    showLoading('shopify-count');
    
    try {
        const [jdsResponse, shopifyResponse] = await Promise.all([
            fetch('/api/sync/jds'),
            fetch('/api/sync/shopify')
        ]);
        
        const jdsResult = await jdsResponse.json();
        const shopifyResult = await shopifyResponse.json();
        
        if (jdsResult.success) {
            const countElement = document.getElementById('jds-count');
            if (countElement) {
                countElement.textContent = jdsResult.data.count;
                countElement.classList.add('status-update');
                setTimeout(() => countElement.classList.remove('status-update'), 500);
            }
        }
        
        if (shopifyResult.success) {
            const countElement = document.getElementById('shopify-count');
            if (countElement) {
                countElement.textContent = shopifyResult.data.count;
                countElement.classList.add('status-update');
                setTimeout(() => countElement.classList.remove('status-update'), 500);
            }
        }
        
        const allSuccess = jdsResult.success && shopifyResult.success;
        showAlert(
            allSuccess ? 'success' : 'warning',
            allSuccess ? 'All data synced successfully' : 'Some sync operations failed'
        );
    } catch (error) {
        console.error('Error syncing all data:', error);
        showAlert('danger', 'Error syncing data');
    } finally {
        if (spinner) spinner.classList.add('d-none');
        if (button) button.disabled = false;
        hideLoading('jds-count');
        hideLoading('shopify-count');
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Check system status on page load
    checkSystemStatus();
    
    // Set up event listeners for sync buttons
    const syncJDSBtn = document.getElementById('sync-jds-btn');
    const syncShopifyBtn = document.getElementById('sync-shopify-btn');
    const syncJDSBtnCard = document.getElementById('sync-jds-btn-card');
    const syncShopifyBtnCard = document.getElementById('sync-shopify-btn-card');
    const syncAllBtn = document.getElementById('sync-all-btn');
    const checkStatusBtn = document.getElementById('check-status-btn');
    
    if (syncJDSBtn) syncJDSBtn.addEventListener('click', syncJDS);
    if (syncShopifyBtn) syncShopifyBtn.addEventListener('click', syncShopify);
    if (syncJDSBtnCard) syncJDSBtnCard.addEventListener('click', syncJDS);
    if (syncShopifyBtnCard) syncShopifyBtnCard.addEventListener('click', syncShopify);
    if (syncAllBtn) syncAllBtn.addEventListener('click', syncAll);
    if (checkStatusBtn) checkStatusBtn.addEventListener('click', checkSystemStatus);
    
    // Auto-refresh status every 30 seconds
    setInterval(checkSystemStatus, 30000);
    
    // Add hover effects to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.add('card-hover');
    });
});

// Bulk operations for product management
async function addSelectedProducts(skus) {
    if (!skus || skus.length === 0) {
        showAlert('warning', 'Please select products to add');
        return;
    }
    
    try {
        const response = await fetch('/api/products/bulk-add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ skus: skus })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showDetailedResults('success', 'Product Creation Results', data);
            return data;
        } else {
            showDetailedResults('danger', 'Product Creation Failed', data);
            return null;
        }
    } catch (error) {
        console.error('Error adding products:', error);
        showAlert('danger', 'Error adding products: ' + error.message);
        return null;
    }
}

async function updateSelectedPricing(skus) {
    if (!skus || skus.length === 0) {
        showAlert('warning', 'Please select products to update');
        return;
    }
    
    try {
        const response = await fetch('/api/products/bulk-update-pricing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ skus: skus })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showDetailedResults('success', 'Price Update Results', data);
            return data;
        } else {
            showDetailedResults('danger', 'Price Update Failed', data);
            return null;
        }
    } catch (error) {
        console.error('Error updating pricing:', error);
        showAlert('danger', 'Error updating pricing: ' + error.message);
        return null;
    }
}

function showDetailedResults(type, title, data) {
    const alertContainer = document.querySelector('.container');
    if (!alertContainer) {
        console.error('Alert container not found');
        return;
    }
    const alertDiv = document.createElement('div');
    const allowedTypes = new Set(['success','danger','warning','info','primary','secondary','light','dark']);
    const safeType = allowedTypes.has(type) ? type : 'info';
    alertDiv.className = `alert alert-${safeType} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.setAttribute('aria-live', safeType === 'success' ? 'polite' : 'assertive');
    
    const esc = (v) => escapeHtml(String(v ?? ''));
    const num = (v) => (Number.isFinite(v) ? v : Number(v)) || 0;
    let content = `
        <h5 class="alert-heading">${esc(title)}</h5>
        <p><strong>Summary:</strong> ${esc(data.message)}</p>
    `;
    
    if (data.created_count !== undefined) {
        content += `<p><strong>Created:</strong> ${num(data.created_count)} products</p>`;
    }
    if (data.updated_count !== undefined) {
        content += `<p><strong>Updated:</strong> ${num(data.updated_count)} products</p>`;
    }
    if (data.failed_count !== undefined && Number(data.failed_count) > 0) {
        content += `<p><strong>Failed:</strong> ${num(data.failed_count)} products</p>`;
    }
    
    if (Array.isArray(data.validation_errors) && data.validation_errors.length > 0) {
        content += `
            <div class="mt-3">
                <strong>Validation Errors:</strong>
                <ul class="mb-0">
                    ${data.validation_errors.map(error => 
                        `<li><strong>${esc(error.sku)}</strong> (${esc(error.name)}): ${
                            (Array.isArray(error.errors) ? error.errors : []).map(e => esc(e)).join(', ')
                        }</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }
    
    if (Array.isArray(data.results) && data.results.length > 0) {
        const failedResults = data.results.filter(r => !r.success);
        if (failedResults.length > 0) {
            content += `
                <div class="mt-3">
                    <strong>Failed Products:</strong>
                    <ul class="mb-0">
                        ${failedResults.map(result => 
                            `<li><strong>${esc(result.sku)}</strong> (${esc(result.name)}): ${esc(result.error)}</li>`
                        ).join('')}
                    </ul>
                </div>
            `;
        }
    }
    
    content += `
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertDiv.innerHTML = content;
    alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
    
    // Auto-dismiss after 10 seconds for success, 15 seconds for errors
    const duration = safeType === 'success' ? 10000 : 15000;
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, duration);
}

// Utility function for escaping HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Utility function for debouncing
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for use in other scripts
window.ProductAdder = {
    checkSystemStatus,
    syncJDS,
    syncShopify,
    syncAll,
    showAlert,
    showDetailedResults,
    updateStatusBadge,
    updateConnectionStatus,
    addSelectedProducts,
    updateSelectedPricing,
    escapeHtml,
    debounce
};
