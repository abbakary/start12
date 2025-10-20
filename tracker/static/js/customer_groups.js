document.addEventListener('DOMContentLoaded', function() {
    // Handle AJAX form submissions and navigation
    const contentContainer = document.getElementById('main-content');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Function to load content via AJAX
    function loadContent(url, pushState = true) {
        if (loadingIndicator) loadingIndicator.style.display = 'block';
        
        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-AJAX': 'true'
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.text();
        })
        .then(html => {
            // Only update the content area, not the entire page
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newContent = doc.getElementById('main-content') || doc.body;
            
            if (contentContainer) {
                contentContainer.innerHTML = newContent.innerHTML;
            } else {
                document.body.innerHTML = newContent.innerHTML;
            }
            
            // Update the URL without reloading the page
            if (pushState) {
                window.history.pushState({}, '', url);
            }
            
            // Re-initialize any necessary scripts
            initializeComponents();
        })
        .catch(error => {
            console.error('Error loading content:', error);
            if (contentContainer) {
                contentContainer.innerHTML = '<div class="alert alert-danger">Error loading content. Please try again.</div>';
            }
        })
        .finally(() => {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
        });
    }
    
    // Handle AJAX form submissions
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (form.method.toLowerCase() === 'get' || form.classList.contains('no-ajax')) {
            return; // Let normal form submission happen
        }
        
        e.preventDefault();
        
        const formData = new FormData(form);
        const url = new URL(form.action || window.location.href);
        
        fetch(url, {
            method: form.method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-AJAX': 'true'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.redirect) {
                loadContent(data.redirect);
            } else if (data.html) {
                if (contentContainer) {
                    contentContainer.innerHTML = data.html;
                    initializeComponents();
                }
            }
        })
        .catch(console.error);
    });
    
    // Handle AJAX navigation
    document.addEventListener('click', function(e) {
        // Handle dropdown toggles
        const dropdownToggle = e.target.closest('[data-bs-toggle="dropdown"]');
        if (dropdownToggle) {
            e.preventDefault();
            const dropdown = new bootstrap.Dropdown(dropdownToggle);
            dropdown.toggle();
            return;
        }
        
        // Handle AJAX links
        const link = e.target.closest('a[href^="/"], a[href^="."]');
        if (!link || link.target === '_blank' || link.hasAttribute('download') || 
            link.classList.contains('no-ajax') || link.closest('.no-ajax')) {
            return;
        }
        
        e.preventDefault();
        const url = link.getAttribute('href');
        loadContent(url);
    });
    
    // Handle browser back/forward buttons
    window.addEventListener('popstate', function() {
        loadContent(window.location.href, false);
    });
    
    // Initialize components after AJAX load
    function initializeComponents() {
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
        
        // Initialize any other components as needed
    }
    
    // Initial component initialization
    initializeComponents();
});
