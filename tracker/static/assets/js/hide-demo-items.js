// document.addEventListener('DOMContentLoaded', function() {
//     // Function to completely remove demo items and their containers
//     function removeDemoItems() {
//         // First, target the main navigation containers
//         const navContainers = [
//             '.page-header',
//             '.sidebar-wrapper',
//             '.page-sidebar',
//             '.page-header .nav-right',
//             '.page-header .nav-left',
//             '.page-header .header-wrapper',
//             '.main-nav',
//             '.main-menu',
//             '.main-navbar',
//             '.main-menu-wrapper'
//         ];

//         // Process each container
//         navContainers.forEach(selector => {
//             const containers = document.querySelectorAll(selector);
//             containers.forEach(container => {
//                 if (!container) return;
                
//                 // Look for specific demo items by exact text match
//                 const demoTexts = [
//                     'Quick option', 'Quick Option', 'QUICK OPTION',
//                     'Document', 'DOCUMENT',
//                     'Buy Now', 'BUY NOW', 'Buy now',
//                     'Check features', 'Check Features', 'CHECK FEATURES',
//                     'Support', 'SUPPORT'
//                 ];

//                 // Check all elements in the container
//                 const allElements = container.getElementsByTagName('*');
//                 for (let i = 0; i < allElements.length; i++) {
//                     const el = allElements[i];
//                     const text = (el.textContent || '').trim();
                    
//                     if (demoTexts.includes(text)) {
//                         // Remove the element and its parent if it's a list item
//                         if (el.parentElement && el.parentElement.tagName === 'LI') {
//                             el.parentElement.remove();
//                         } else if (el.parentElement) {
//                             // For other elements, try to find a parent with common navigation classes
//                             let parent = el.closest('li, .nav-item, .dropdown-item, .menu-item, .nav-link');
//                             if (parent) {
//                                 parent.remove();
//                             } else {
//                                 el.remove();
//                             }
//                         } else {
//                             el.remove();
//                         }
//                     }
//                 }
//             });
//         });

//         // Also check for any remaining demo items in the entire document
//         demoTexts.forEach(text => {
//             const xpath = `//*[text()='${text}']`;
//             const result = document.evaluate(xpath, document, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
            
//             for (let i = 0; i < result.snapshotLength; i++) {
//                 const el = result.snapshotItem(i);
//                 if (el.parentElement) {
//                     el.parentElement.remove();
//                 }
//             }
//         });
//     }
    
//     // Run immediately
//     removeDemoItems();
    
//     // Run again after a short delay to catch dynamically loaded content
//     setTimeout(removeDemoItems, 1000);
    
//     // Set up a MutationObserver to catch dynamically added content
//     const observer = new MutationObserver(function() {
//         removeDemoItems();
//     });
//     observer.observe(document.body, { 
//         childList: true, 
//         subtree: true 
//     });
// });
