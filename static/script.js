// ============================================================================
// CUSTOMER MANAGEMENT APP - JAVASCRIPT FUNCTIONS
// ============================================================================

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // ===== FORM VALIDATION =====
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Basic form validation
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#e74c3c';
                    
                    // Create error message if not exists
                    if (!field.nextElementSibling?.classList.contains('error-message')) {
                        const errorMsg = document.createElement('div');
                        errorMsg.className = 'error-message';
                        errorMsg.textContent = 'This field is required';
                        errorMsg.style.color = '#e74c3c';
                        errorMsg.style.fontSize = '13px';
                        errorMsg.style.marginTop = '5px';
                        field.parentNode.insertBefore(errorMsg, field.nextSibling);
                    }
                } else {
                    field.style.borderColor = '#e0e0e0';
                    const errorMsg = field.nextElementSibling;
                    if (errorMsg?.classList.contains('error-message')) {
                        errorMsg.remove();
                    }
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showToast('Please fill all required fields', 'error');
            }
        });
    });
    
    // ===== AMOUNT FORMATTING =====
    const amountInputs = document.querySelectorAll('input[name="amount"]');
    amountInputs.forEach(input => {
        // Format on blur
        input.addEventListener('blur', function() {
            const value = parseFloat(this.value);
            if (!isNaN(value)) {
                // Store the numeric value
                this.dataset.original = value;
                // Display formatted (without comma for input)
                this.value = value.toFixed(2);
            }
        });
        
        // Store numeric value on focus
        input.addEventListener('focus', function() {
            if (this.dataset.original) {
                this.value = this.dataset.original;
            }
        });
    });
    
    // ===== DATE INPUT DEFAULTS =====
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            const today = new Date().toISOString().split('T')[0];
            input.value = today;
        }
    });
    
    // ===== CUSTOMER ID GENERATION =====
    const serialInputs = document.querySelectorAll('input[name="serial_no"], #serial_no');
    const customerIdInputs = document.querySelectorAll('input[name="customer_id"]');
    
    if (serialInputs.length > 0 && customerIdInputs.length > 0) {
        serialInputs.forEach((serialInput, index) => {
            serialInput.addEventListener('change', function() {
                if (customerIdInputs[index] && !customerIdInputs[index].value) {
                    const serial = this.value;
                    const paddedSerial = String(serial).padStart(5, '0');
                    customerIdInputs[index].value = 'kn' + paddedSerial;
                }
            });
        });
    }
    
    // ===== SEARCH FUNCTIONALITY =====
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        // Debounce search to prevent too many requests
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (this.value.length >= 2 || this.value.length === 0) {
                    this.form.submit();
                }
            }, 500);
        });
    }
    
    // ===== TABLE SORTING =====
    const tableHeaders = document.querySelectorAll('.customer-table th');
    tableHeaders.forEach((header, index) => {
        if (!header.classList.contains('actions')) {
            header.style.cursor = 'pointer';
            header.title = 'Click to sort';
            
            header.addEventListener('click', () => {
                sortTable(index);
            });
        }
    });
    
    // ===== CONFIRMATION DIALOGS =====
    const deleteLinks = document.querySelectorAll('a.btn-delete');
    deleteLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const customerId = this.closest('tr').querySelector('.customer-id').textContent;
            if (!confirm(`Are you sure you want to delete customer ${customerId}? This action cannot be undone.`)) {
                e.preventDefault();
            }
        });
    });
    
    // ===== TOAST NOTIFICATIONS =====
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fas fa-${getToastIcon(type)}"></i>
            <span>${message}</span>
            <button class="toast-close">&times;</button>
        `;
        
        // Style the toast
        toast.style.position = 'fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.padding = '15px 20px';
        toast.style.borderRadius = '8px';
        toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        toast.style.zIndex = '9999';
        toast.style.display = 'flex';
        toast.style.alignItems = 'center';
        toast.style.gap = '10px';
        toast.style.animation = 'slideInRight 0.3s ease';
        
        // Type-specific styling
        const colors = {
            success: '#27ae60',
            error: '#e74c3c',
            warning: '#f39c12',
            info: '#3498db'
        };
        
        toast.style.backgroundColor = colors[type] || colors.info;
        toast.style.color = 'white';
        toast.style.fontWeight = '500';
        
        // Add to document
        document.body.appendChild(toast);
        
        // Close button functionality
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    }
    
    function getToastIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .toast-close {
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            margin-left: 10px;
            opacity: 0.8;
        }
        
        .toast-close:hover {
            opacity: 1;
        }
    `;
    document.head.appendChild(style);
    
    // ===== TABLE SORTING FUNCTION =====
    function sortTable(columnIndex) {
        const table = document.querySelector('.customer-table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Get current sort direction
        const header = table.querySelectorAll('th')[columnIndex];
        const isAscending = !header.classList.contains('asc');
        
        // Clear previous sort indicators
        table.querySelectorAll('th').forEach(th => {
            th.classList.remove('asc', 'desc');
        });
        
        // Set new sort indicator
        header.classList.add(isAscending ? 'asc' : 'desc');
        
        // Sort rows
        rows.sort((a, b) => {
            const aCell = a.querySelectorAll('td')[columnIndex];
            const bCell = b.querySelectorAll('td')[columnIndex];
            
            let aValue = aCell.textContent.trim();
            let bValue = bCell.textContent.trim();
            
            // Special handling for different data types
            if (columnIndex === 0 || columnIndex === 7) { // Serial or Amount
                aValue = parseFloat(aValue.replace(/[^\d.-]/g, '') || 0);
                bValue = parseFloat(bValue.replace(/[^\d.-]/g, '') || 0);
            } else if (columnIndex === 4) { // Date
                aValue = new Date(aValue);
                bValue = new Date(bValue);
            }
            
            // Compare values
            if (aValue < bValue) return isAscending ? -1 : 1;
            if (aValue > bValue) return isAscending ? 1 : -1;
            return 0;
        });
        
        // Reorder rows in DOM
        rows.forEach(row => tbody.appendChild(row));
        
        showToast(`Sorted by ${header.textContent} (${isAscending ? 'ascending' : 'descending'})`, 'info');
    }
    
    // ===== REAL-TIME CLOCK =====
    function updateClock() {
        const clockElement = document.getElementById('currentTime');
        if (clockElement) {
            const now = new Date();
            const options = {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            };
            clockElement.textContent = now.toLocaleDateString('en-US', options);
        }
    }
    
    if (document.getElementById('currentTime')) {
        updateClock();
        setInterval(updateClock, 1000);
    }
    
    // ===== AUTO-SAVE DRAFT (if needed) =====
    const form = document.querySelector('.customer-form');
    if (form) {
        const formData = {};
        
        // Save form data on change
        form.addEventListener('change', function() {
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                if (input.name) {
                    formData[input.name] = input.value;
                }
            });
            localStorage.setItem('customerFormDraft', JSON.stringify(formData));
        });
        
        // Load draft on page load
        const draft = localStorage.getItem('customerFormDraft');
        if (draft) {
            const formData = JSON.parse(draft);
            Object.keys(formData).forEach(key => {
                const input = form.querySelector(`[name="${key}"]`);
                if (input && !input.value) {
                    input.value = formData[key];
                }
            });
        }
        
        // Clear draft on successful submit
        form.addEventListener('submit', function() {
            localStorage.removeItem('customerFormDraft');
        });
    }
    
    // ===== PRINT FUNCTIONALITY =====
    window.printTable = function() {
        const printContent = document.querySelector('.table-container').innerHTML;
        const originalContent = document.body.innerHTML;
        
        document.body.innerHTML = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Customer Records - Print</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    table { width: 100%; border-collapse: collapse; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    .print-header { text-align: center; margin-bottom: 20px; }
                    .print-footer { margin-top: 20px; text-align: center; font-size: 12px; color: #666; }
                    @media print {
                        .no-print { display: none; }
                    }
                </style>
            </head>
            <body>
                <div class="print-header">
                    <h1>Customer Records</h1>
                    <p>Printed on: ${new Date().toLocaleString()}</p>
                </div>
                ${printContent}
                <div class="print-footer">
                    <p>Customer Management System | Local Storage Application</p>
                </div>
                <script>
                    window.onload = function() {
                        window.print();
                        setTimeout(() => {
                            document.body.innerHTML = originalContent;
                            location.reload();
                        }, 500);
                    };
                </\script>
            </body>
            </html>
        `;
    };
    
    // ===== EXPORT STATUS CHECK =====
    const exportBtn = document.querySelector('a[href*="export"]');
    if (exportBtn) {
        exportBtn.addEventListener('click', function(e) {
            const tableRows = document.querySelectorAll('.customer-table tbody tr');
            if (tableRows.length === 0) {
                e.preventDefault();
                showToast('No data available to export', 'warning');
            } else {
                showToast('Generating Excel file...', 'info');
            }
        });
    }
});