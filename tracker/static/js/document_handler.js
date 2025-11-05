/**
 * Document Handler Utility
 * Handles document extraction, data matching, and dynamic table updates
 */

class DocumentHandler {
    constructor() {
        this.extractedData = {};
        this.matchedRecords = {
            customer: null,
            vehicle: null,
            order: null
        };
        this.csrfToken = this.getCSRFToken();
    }

    /**
     * Get CSRF token from meta tag or form
     */
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) return input.value;
        return '';
    }

    /**
     * Upload document and extract data
     * @param {File} file - Document file
     * @param {string} vehiclePlate - Vehicle plate number
     * @param {string} customerPhone - Customer phone number
     * @param {string} documentType - Type of document
     * @returns {Promise} Extraction result
     */
    async uploadAndExtract(file, vehiclePlate, customerPhone = '', documentType = 'quotation', orderId = null) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('vehicle_plate', vehiclePlate);
            formData.append('customer_phone', customerPhone);
            formData.append('document_type', documentType);
            if (orderId) formData.append('order_id', String(orderId));

            const response = await fetch('/api/documents/upload/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken
                },
                body: formData
            });

            const data = await response.json();
            
            if (data.success) {
                this.extractedData = data.extracted_data;
                this.matchedRecords = data.matches || {};
                return {
                    success: true,
                    documentId: data.document_id,
                    extractedData: data.extracted_data,
                    matches: data.matches
                };
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Search for existing records by vehicle plate or job card
     * @param {string} jobCard - Job card number
     * @param {string} vehiclePlate - Vehicle plate number
     * @returns {Promise} Search results
     */
    async searchByJobCard(jobCard = '', vehiclePlate = '') {
        try {
            const response = await fetch('/api/documents/search-job-card/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    job_card_number: jobCard,
                    vehicle_plate: vehiclePlate
                })
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Search error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Create order from extracted document data
     * @param {Object} options - Order creation options
     * @returns {Promise} Order creation result
     */
    async createOrderFromDocument(options = {}) {
        try {
            const payload = {
                extraction_id: options.extractionId,
                use_extracted: options.useExtracted !== false,
                ...options
            };

            const response = await fetch('/api/documents/create-order/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            
            if (data.success) {
                return {
                    success: true,
                    orderId: data.order_id,
                    orderNumber: data.order_number,
                    customerId: data.customer_id,
                    vehicleId: data.vehicle_id
                };
            } else {
                throw new Error(data.error || 'Order creation failed');
            }
        } catch (error) {
            console.error('Order creation error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Check for data mismatches between extracted and existing data
     * @param {Object} extractedData - Extracted data from document
     * @param {Object} existingData - Existing database data
     * @returns {Object} Mismatches found
     */
    detectMismatches(extractedData, existingData) {
        const mismatches = {};
        
        Object.keys(extractedData).forEach(key => {
            const extractedValue = extractedData[key];
            const existingValue = existingData[key];

            if (extractedValue && existingValue && extractedValue !== existingValue) {
                mismatches[key] = {
                    existing: existingValue,
                    extracted: extractedValue
                };
            }
        });

        return mismatches;
    }

    /**
     * Handle data mismatch resolution
     * @param {Object} mismatches - Detected mismatches
     * @param {string} strategy - Resolution strategy (keep_existing, override, merge)
     * @param {Object} mergedData - Manually merged data (for merge strategy)
     * @returns {Object} Resolved data
     */
    resolveMismatches(mismatches, strategy = 'keep_existing', mergedData = {}) {
        let resolvedData = {};

        if (strategy === 'keep_existing') {
            Object.keys(mismatches).forEach(key => {
                resolvedData[key] = mismatches[key].existing;
            });
        } else if (strategy === 'override') {
            Object.keys(mismatches).forEach(key => {
                resolvedData[key] = mismatches[key].extracted;
            });
        } else if (strategy === 'merge') {
            resolvedData = mergedData;
        }

        return resolvedData;
    }

    /**
     * Update table with new extracted data
     * @param {string} tableSelector - CSS selector for table
     * @param {Object} data - Data to add or update
     * @param {string} rowIdentifier - Field to use for row identification
     */
    updateTableWithData(tableSelector, data, rowIdentifier = 'id') {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        const dataTable = table.DataTable ? table.DataTable() : null;
        const rowId = data[rowIdentifier];

        // If table uses DataTables
        if (dataTable) {
            const existingRow = dataTable.rows().nodes().to$().filter(`[data-id="${rowId}"]`);
            
            if (existingRow.length > 0) {
                // Update existing row
                dataTable.row(existingRow[0]).data(this.prepareRowData(data)).draw();
            } else {
                // Add new row
                dataTable.row.add(this.prepareRowData(data)).draw();
            }
        } else {
            // Fallback to manual table update
            this.updatePlainTable(table, data, rowId);
        }
    }

    /**
     * Prepare data for table row
     * @param {Object} data - Raw data
     * @returns {Array} Data formatted for table
     */
    prepareRowData(data) {
        return [
            data.id || '',
            data.name || data.full_name || data.order_number || '',
            data.phone || data.status || data.plate_number || '',
            data.email || data.vehicle_type || data.customer_name || '',
            data.address || data.created_at || this.formatDate(new Date()),
            this.getActionButtons(data)
        ];
    }

    /**
     * Update plain HTML table (without DataTables)
     * @param {HTMLElement} table - Table element
     * @param {Object} data - Data to update
     * @param {string} rowId - Row identifier
     */
    updatePlainTable(table, data, rowId) {
        const tbody = table.querySelector('tbody');
        let row = tbody.querySelector(`tr[data-id="${rowId}"]`);

        if (!row) {
            row = tbody.insertRow();
            row.dataset.id = rowId;
        }

        // Update row cells
        const cells = row.querySelectorAll('td');
        if (cells.length > 0) {
            cells[0].textContent = data.id || '';
            cells[1].textContent = data.name || data.full_name || data.order_number || '';
            cells[2].textContent = data.phone || data.status || '';
            cells[3].textContent = data.email || data.created_at || '';
            if (cells[4]) cells[4].innerHTML = this.getActionButtons(data);
        }
    }

    /**
     * Format date for display
     * @param {Date} date - Date to format
     * @returns {string} Formatted date
     */
    formatDate(date) {
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: '2-digit'
        });
    }

    /**
     * Get action buttons HTML for table row
     * @param {Object} data - Row data
     * @returns {string} HTML for action buttons
     */
    getActionButtons(data) {
        const id = data.id || '';
        const type = data.type || 'unknown';
        const baseUrl = type === 'customer' ? '/customers' : '/orders';

        return `
            <div class="btn-group btn-group-sm" role="group">
                <a href="${baseUrl}/${id}/" class="btn btn-outline-primary btn-sm" title="View">
                    <i class="fa fa-eye"></i>
                </a>
                <a href="${baseUrl}/${id}/edit/" class="btn btn-outline-secondary btn-sm" title="Edit">
                    <i class="fa fa-edit"></i>
                </a>
            </div>
        `;
    }

    /**
     * Enable automatic record linking based on vehicle plate or phone
     * @param {Object} extractedData - Extracted data from document
     * @returns {Promise} Link result
     */
    async autoLinkRecords(extractedData) {
        try {
            const response = await fetch('/api/documents/search-job-card/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    vehicle_plate: extractedData.vehicle_plate || '',
                    job_card_number: extractedData.job_card || ''
                })
            });

            const data = await response.json();
            
            if (data.found) {
                return {
                    autoLinked: true,
                    records: data.results
                };
            }

            return { autoLinked: false };
        } catch (error) {
            console.error('Auto-link error:', error);
            return { autoLinked: false, error: error.message };
        }
    }

    /**
    * Show notification to user (simple top-right toast)
    * @param {string} message - Notification message
    * @param {string} type - Notification type (success, error, warning, info)
    * @param {number} duration - Duration in ms (0 = persistent)
    */
    showNotification(message, type = 'info', duration = 3000) {
        const containerClass = 'fusion-toast-container';
        let container = document.querySelector(`.${containerClass}`);
        if (!container) {
            container = document.createElement('div');
            container.className = containerClass;
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        const toastType = type === 'error' ? 'error' : type;
        toast.className = `fusion-toast fusion-toast--${toastType}`;
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');

        toast.innerHTML = `
            <div class="fusion-toast__message">${message}</div>
            <button type="button" class="fusion-toast__close" aria-label="Close">&times;</button>
        `;

        container.appendChild(toast);

        const closeBtn = toast.querySelector('.fusion-toast__close');
        const removeToast = () => {
            toast.classList.add('fusion-toast--hide');
            toast.addEventListener('transitionend', () => toast.remove(), { once: true });
        };

        closeBtn.addEventListener('click', removeToast);

        if (duration > 0) {
            setTimeout(removeToast, duration);
        }

        return toast;
    }

    /**
     * Export table data to CSV
     * @param {string} tableSelector - CSS selector for table
     * @param {string} filename - Output filename
     */
    exportTableToCSV(tableSelector, filename = 'export.csv') {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        let csv = [];
        const rows = table.querySelectorAll('tr');

        rows.forEach((row, index) => {
            const cols = row.querySelectorAll('td, th');
            let csvRow = [];

            cols.forEach(col => {
                csvRow.push('"' + col.textContent.trim().replace(/"/g, '""') + '"');
            });

            csv.push(csvRow.join(','));
        });

        this.downloadCSV(csv.join('\n'), filename);
    }

    /**
     * Download CSV file
     * @param {string} csv - CSV content
     * @param {string} filename - Output filename
     */
    downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Initialize handler
const documentHandler = new DocumentHandler();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DocumentHandler;
}
