document.addEventListener('DOMContentLoaded', function() {
    // Function to initialize form handlers
    function initializeFormHandlers() {
        const registrationForm = document.getElementById('customer-registration-form') || document.getElementById('customerRegistrationForm');
        if (!registrationForm) return;

        // Handle form submission
        registrationForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(registrationForm);
            const currentStep = parseInt(registrationForm.querySelector('input[name="step"]').value);
            const url = registrationForm.action;
            const submitButton = registrationForm.querySelector('button[type="submit"]');
            const originalButtonText = submitButton ? submitButton.innerHTML : '';
            const loadingOverlay = document.getElementById('loading-overlay');

            // Show loading state
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Processing...';
            }
            
            // Show loading overlay with fade-in effect
            if (loadingOverlay) {
                loadingOverlay.style.display = 'flex';
                setTimeout(() => loadingOverlay.style.opacity = '1', 10);
            }

            try {
                // Submit form via AJAX
                const response = await fetch(url, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'same-origin'
                });

    // Delegated interactions for dynamically injected steps
    document.addEventListener('click', function(e){
        // Step 2: Intent card selection (service/sales/inquiry)
        var intentCard = e.target.closest('.intent-card');
        if (intentCard) {
            var radio = intentCard.querySelector('input[name="intent"]');
            if (radio) {
                radio.checked = true;
                // Update hidden intent holder if present
                var hidden = document.getElementById('registrationIntent');
                if (hidden) hidden.value = radio.value;
                // Visual highlight
                document.querySelectorAll('.intent-card').forEach(function(c){ c.classList.remove('border-primary'); });
                intentCard.classList.add('border-primary');
                // Auto-save intent selection to session without navigation
                var form = document.getElementById('customer-registration-form') || document.getElementById('customerRegistrationForm');
                if (form) {
                    var fd = new FormData(form);
                    fetch(form.action || window.location.href, {
                        method: 'POST',
                        body: fd,
                        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') },
                        credentials: 'same-origin'
                    }).catch(function(){ /* ignore */ });
                }
            }
        }

        // Step 3: Toggle service offers (checkboxes are hidden)
        var svcLabel = e.target.closest('.service-offer');
        if (svcLabel) {
            var cb = svcLabel.querySelector('input[type="checkbox"][name="service_selection"]');
            if (cb) {
                cb.checked = !cb.checked;
                svcLabel.classList.toggle('border-primary', cb.checked);
                svcLabel.classList.toggle('bg-light', cb.checked);
            }
        }

        // Step 3: Service type radio card selection handler (if cards are used)
        var svcTypeCard = e.target.closest('.service-card');
        if (svcTypeCard) {
            var radio2 = svcTypeCard.querySelector('input[name="service_type"]');
            if (radio2) {
                radio2.checked = true;
                document.querySelectorAll('.service-card').forEach(function(c){ c.classList.remove('border-primary','bg-light'); });
                svcTypeCard.classList.add('border-primary','bg-light');
                // Auto-save service_type selection
                var form2 = document.getElementById('customer-registration-form') || document.getElementById('customerRegistrationForm');
                if (form2) {
                    var fd2 = new FormData(form2);
                    fetch(form2.action || window.location.href, {
                        method: 'POST',
                        body: fd2,
                        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') },
                        credentials: 'same-origin'
                    }).catch(function(){ /* ignore */ });
                }
            }
        }

        // Generic: Next buttons inside steps may be type="button"; submit form to advance
        var nextBtnIds = ['nextStepBtn','nextStep2','nextServiceBtn'];
        var clickedId = (e.target && e.target.id) || (e.target.closest('button') && e.target.closest('button').id) || '';
        if (nextBtnIds.indexOf(clickedId) !== -1) {
            var form = document.getElementById('customerRegistrationForm') || document.getElementById('customer-registration-form');
            if (form) {
                e.preventDefault();
                // Clear save-only flag if any
                var saveOnly = form.querySelector('#saveOnly');
                if (saveOnly) saveOnly.value = '0';
                form.requestSubmit ? form.requestSubmit() : form.submit();
            }
        }
    });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || 'An error occurred while processing your request.');
                }

                if (data.success) {
                    if (data.redirect_url) {
                        // Show server-provided message type if available
                        const t = data.message_type || 'success';
                        showMessage(data.message || 'Processing...', t);
                        setTimeout(() => { window.location.href = data.redirect_url; }, 1500);
                        return;
                    } else if (data.form_html) {
                        // Update the form with the response
                        const formContainer = document.getElementById('form-container');
                        if (formContainer) {
                            // Add fade-out effect
                            formContainer.style.opacity = '0';
                            formContainer.style.transition = 'opacity 0.3s ease-in-out';
                            
                            setTimeout(() => {
                                formContainer.innerHTML = data.form_html;
                                // Fade in the new content
                                setTimeout(() => formContainer.style.opacity = '1', 10);
                                
                                // Update URL with current step
                                const url = new URL(window.location);
                                const newStep = (typeof data.next_step !== 'undefined' && data.next_step !== null) ? parseInt(data.next_step) : (currentStep + 1);
                                url.searchParams.set('step', newStep);

                                // Update browser history without page reload
                                window.history.pushState({ step: newStep }, '', url);
                                
                                // Reinitialize form handlers for the new content
                                initializeFormHandlers();
                                
                                // Scroll to top of form
                                window.scrollTo({ top: 0, behavior: 'smooth' });
                                
                                // Show success message if present
                                if (data.message) {
                                    showMessage(data.message, 'success');
                                }
                            }, 300);
                        }
                    } else {
                        // Handle other success cases
                        if (data.message) {
                            showMessage(data.message, 'success');
                        }
                    }
                } else {
                    // Handle form validation errors
                    if (data.errors) {
                        // Clear previous error states
                        registrationForm.querySelectorAll('.is-invalid').forEach(el => {
                            el.classList.remove('is-invalid');
                        });
                        
                        // Show field-specific errors
                        Object.entries(data.errors).forEach(([field, messages]) => {
                            const input = registrationForm.querySelector(`[name="${field}"]`);
                            if (input) {
                                // Add invalid class to the input
                                input.classList.add('is-invalid');
                                
                                // Find or create error message element
                                let errorElement = input.nextElementSibling;
                                if (!errorElement || !errorElement.classList.contains('invalid-feedback')) {
                                    errorElement = document.createElement('div');
                                    errorElement.className = 'invalid-feedback d-block';
                                    input.parentNode.insertBefore(errorElement, input.nextSibling);
                                }
                                
                                // Update error message
                                const errorMessage = Array.isArray(messages) ? messages.join(' ') : messages;
                                errorElement.textContent = errorMessage;
                                
                                // Scroll to the first error field
                                if (Object.keys(data.errors)[0] === field) {
                                    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                }
                            }
                        });
                        
                        // Show general error message if no field-specific errors
                        if (Object.keys(data.errors).length === 0 && data.message) {
                            showMessage(data.message, 'error');
                        }
                    } else if (data.message) {
                        // If backend asked us to redirect on a non-success (e.g., duplicate detected), honor it
                        if (data.redirect_url) {
                            const t = data.message_type || 'info';
                            showMessage(data.message, t);
                            setTimeout(() => { window.location.href = data.redirect_url; }, 1500);
                        } else {
                            showMessage(data.message, 'error');
                        }
                    } else {
                        showMessage('An unknown error occurred. Please try again.', 'error');
                    }
                }
            } catch (error) {
                console.error('Error:', error);
                showMessage('An unexpected error occurred. Please try again or contact support if the problem persists.', 'error');
                
                // Log the error to your error tracking service if available
                if (window.console && console.error) {
                    console.error('Registration Error:', error);
                }
            } finally {
                // Hide loading overlay with fade-out effect
                if (loadingOverlay) {
                    loadingOverlay.style.opacity = '0';
                    setTimeout(() => {
                        loadingOverlay.style.display = 'none';
                    }, 300);
                }
                
                // Reset button state
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalButtonText;
                }
                
                // Re-enable any disabled form elements
                registrationForm.querySelectorAll(':disabled').forEach(el => {
                    if (el.getAttribute('data-was-disabled') === 'true') {
                        el.disabled = false;
                    }
                });
            }
        });

        // Handle back button
        const backButton = document.querySelector('.btn-back');
        if (backButton) {
            backButton.addEventListener('click', function(e) {
                e.preventDefault();
                const currentStep = parseInt(registrationForm.querySelector('input[name="step"]').value);
                if (currentStep > 1) {
                    const prevStep = currentStep - 1;
                    // Update URL without page reload
                    const newUrl = new URL(window.location);
                    newUrl.searchParams.set('step', prevStep);
                    window.history.pushState({}, '', newUrl);
                    // Load the previous step
                    loadStep(prevStep);
                } else {
                    // If on first step, go to customer list
                    window.location.href = backButton.getAttribute('href') || "{% url 'tracker:customers_list' %}";
                }
            });
        }

        // Bind auto-select brand when item changes (works for dynamically injected Step 3)
        try {
            const itemEl = document.getElementById('id_item_name');
            const brandEl = document.getElementById('id_brand');
            if (itemEl && brandEl && !itemEl.dataset.brandListenerBound) {
                let mapping = {};
                try {
                    const attr = itemEl.getAttribute('data-brands');
                    mapping = JSON.parse(attr && attr.trim() ? attr : '{}');
                } catch (e) { mapping = {}; }

                const onItemChange = function(){
                    const bn = mapping[this.value];
                    if (!bn) return;
                    for (let i = 0; i < brandEl.options.length; i++) {
                        if (brandEl.options[i].text === bn || brandEl.options[i].value === bn) {
                            brandEl.selectedIndex = i;
                            break;
                        }
                    }
                };

                itemEl.addEventListener('change', onItemChange);
                // Mark as bound to avoid duplicate listeners on re-init
                itemEl.dataset.brandListenerBound = '1';
                // If item already selected (e.g., after validation), set brand immediately
                if (itemEl.value) { onItemChange.call(itemEl); }
            }
        } catch (e) { /* noop */ }
    }

    // Initialize form handlers on page load
    initializeFormHandlers();

    // Handle browser back/forward buttons
    window.addEventListener('popstate', function(event) {
        const urlParams = new URLSearchParams(window.location.search);
        const step = parseInt(urlParams.get('step') || '1');
        
        // Only load step if it's different from current step
        const currentStepInput = document.querySelector('input[name="step"]');
        const currentStep = currentStepInput ? parseInt(currentStepInput.value) : 1;
        
        if (step !== currentStep) {
            loadStep(step);
        }
    });
    
    // Handle back button clicks in the form
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-back') || e.target.closest('.btn-back')) {
            e.preventDefault();
            const currentStepInput = document.querySelector('input[name="step"]');
            const currentStep = currentStepInput ? parseInt(currentStepInput.value) : 1;
            
            if (currentStep > 1) {
                loadStep(currentStep - 1);
            } else {
                // If on first step, go to customer list
                const backButton = document.querySelector('.btn-back');
                if (backButton && backButton.href) {
                    window.location.href = backButton.href;
                } else {
                    // Fallback URL if button href is not available
                    window.location.href = '/customers/';
                }
            }
        }
    });

    // Function to load a specific step
    async function loadStep(step) {
        const url = new URL(window.location);
        url.searchParams.set('step', step);
        
        const loadingOverlay = document.getElementById('loading-overlay');
        const formContainer = document.getElementById('form-container');
        
        if (!formContainer) return;
        
        try {
            // Show loading state with fade effect
            if (loadingOverlay) {
                loadingOverlay.style.display = 'flex';
                setTimeout(() => loadingOverlay.style.opacity = '1', 10);
            }
            
            // Add fade-out effect to form container
            formContainer.style.opacity = '0';
            formContainer.style.transition = 'opacity 0.3s ease-in-out';
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-Partial-Content': 'true'  // Custom header to identify partial content requests
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.form_html) {
                // Update the form content
                formContainer.innerHTML = data.form_html;
                
                // Update the step in the form
                const stepInput = formContainer.querySelector('input[name="step"]');
                if (stepInput) stepInput.value = step;
                
                // Update browser history
                window.history.pushState({ step: step }, '', url);
                
                // Fade in the new content
                setTimeout(() => formContainer.style.opacity = '1', 10);
                
                // Reinitialize form handlers
                initializeFormHandlers();
                
                // Scroll to top smoothly
                window.scrollTo({ top: 0, behavior: 'smooth' });
                
                // Show success message if present
                if (data.message) {
                    showMessage(data.message, 'success');
                }
            } else if (data.redirect_url) {
                // If the response includes a redirect URL, navigate to it
                window.location.href = data.redirect_url;
                return;
            } else {
                throw new Error(data.message || 'Failed to load form step');
            }
        } catch (error) {
            console.error('Error loading step:', error);
            showMessage('Error loading form step. Please try again.', 'error');
            
            // If there was an error, revert to the previous URL
            window.history.back();
        } finally {
            // Hide loading overlay with fade-out effect
            if (loadingOverlay) {
                loadingOverlay.style.opacity = '0';
                setTimeout(() => {
                    loadingOverlay.style.display = 'none';
                }, 300);
            }
            
            // Ensure form container is visible even if there was an error
            formContainer.style.opacity = '1';
        }
    }

    // Show toast message
    function showMessage(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1100'; // Above modals
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast show align-items-center text-white bg-${type} border-0 mb-2`;
        toast.role = 'alert';
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Set up the toast content
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${getIconForType(type)} ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add the toast to the container
        toastContainer.appendChild(toast);
        
        // Initialize Bootstrap toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: type === 'error' ? 10000 : 5000
        });
        
        // Show the toast
        bsToast.show();
        
        // Remove toast from DOM after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
            
            // Remove container if no more toasts
            if (toastContainer && toastContainer.children.length === 0) {
                toastContainer.remove();
            }
        });
        
        // Helper function to get appropriate icon for message type
        function getIconForType(type) {
            const icons = {
                'success': '<i class="fas fa-check-circle me-2"></i>',
                'error': '<i class="fas fa-times-circle me-2"></i>',
                'warning': '<i class="fas fa-exclamation-triangle me-2"></i>',
                'info': '<i class="fas fa-info-circle me-2"></i>'
            };
            return icons[type] || '';
        }
    }

    // Helper function to get CSRF token
    function getCookie(name) {
        // Try to get from meta tag first (recommended for AJAX requests)
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        if (csrfToken) return csrfToken;
        
        // Fall back to cookie
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        
        if (!cookieValue) {
            console.warn('CSRF token not found in cookies or meta tag');
        }
        
        return cookieValue;
    }
    
    // Initialize form handlers when the DOM is fully loaded
    document.addEventListener('DOMContentLoaded', initializeFormHandlers);
    
    // Handle page refresh with unsaved changes
    window.addEventListener('beforeunload', function(e) {
        const form = document.getElementById('customer-registration-form');
        if (form) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton && submitButton.disabled) {
                // If form is submitting, don't show the warning
                return undefined;
            }
            
            // Check if the form has been modified
            const formData = new FormData(form);
            let isFormModified = false;
            
            for (let [key, value] of formData.entries()) {
                // Skip hidden fields and CSRF token
                if (key === 'csrfmiddlewaretoken' || key.startsWith('step')) continue;
                
                // If any field has a value, consider the form modified
                if (value && value.toString().trim() !== '') {
                    isFormModified = true;
                    break;
                }
            }
            
            if (isFormModified) {
                // Custom message for modern browsers
                const confirmationMessage = 'You have unsaved changes. Are you sure you want to leave?';
                e.returnValue = confirmationMessage; // Standard for most browsers
                return confirmationMessage; // For some older browsers
            }
        }
    });
});
