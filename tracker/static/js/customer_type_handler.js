document.addEventListener('DOMContentLoaded', function() {
    // Get the customer type select element
    const customerTypeSelect = document.getElementById('customer-type');
    
    // If the customer type select exists, add an event listener
    if (customerTypeSelect) {
        // Initial setup
        toggleCustomerTypeFields(customerTypeSelect.value);
        
        // Add event listener for changes
        customerTypeSelect.addEventListener('change', function() {
            toggleCustomerTypeFields(this.value);
        });
    }
    
    // Function to toggle customer type fields based on selection
    function toggleCustomerTypeFields(customerType) {
        // Hide all sections first
        document.querySelectorAll('.customer-type-section').forEach(section => {
            section.style.display = 'none';
            // Clear required fields when hiding
            section.querySelectorAll('[required]').forEach(field => {
                field.required = false;
            });
        });
        
        // Show the appropriate section based on customer type
        if (customerType === 'personal') {
            const personalFields = document.getElementById('personal-fields');
            if (personalFields) {
                personalFields.style.display = 'block';
                // Make personal type radio required
                personalFields.querySelectorAll('[name="personal_type"]').forEach(radio => {
                    radio.required = true;
                });
            }
        } 
        else if (['government', 'ngo', 'company'].includes(customerType)) {
            const orgFields = document.getElementById('organization-fields');
            if (orgFields) {
                orgFields.style.display = 'block';
                // Make organization fields required
                orgFields.querySelectorAll('input').forEach(input => {
                    input.required = true;
                });
            }
        } 
        else if (customerType === 'bodaboda') {
            const bodabodaFields = document.getElementById('bodaboda-fields');
            if (bodabodaFields) {
                bodabodaFields.style.display = 'block';
                // Make bodaboda fields required
                bodabodaFields.querySelectorAll('input').forEach(input => {
                    input.required = true;
                });
            }
        }
    }
});
