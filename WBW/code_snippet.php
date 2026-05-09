<?php
add_action( 'wp_footer', function() { ?>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
<style>
    /* Ensure cursor indicates clickability */
    .wpfFilterTitle { cursor: pointer; }
</style>
<script type="text/javascript">
(function() {
    /* -------------------------------------------------------
     * ARCHITECT FIX V9: (Capture Phase & Auto-Collapse)
     * Intercepts clicks and automatically collapses accordions
     * after AJAX reloads and hard page loads.
     * ------------------------------------------------------- */

    // Helper: Closes all accordions safely
    function closeAllFilters() {
        var allWrappers = document.querySelectorAll('.wpfMainWrapper');
        allWrappers.forEach(function(el) {
            el.classList.remove('architect-open');
            
            var content = el.querySelector('.wpfFilterContent');
            var icon = el.querySelector('.wpfFilterTitle i');
            
            if (content) {
                content.classList.add('wpfHide');
                content.style.display = 'none';
            }
            if (icon) {
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
            }
        });
    }

    // Main Click Handler (Capture Phase)
    function handleArchitectClick(e) {
        var title = e.target.closest('.wpfFilterTitle');
        if (!title) return;

        // Prevent the plugin from interfering
        e.preventDefault();
        e.stopPropagation(); 

        var wrapper = title.closest('.wpfMainWrapper');
        var targetContent = wrapper.querySelector('.wpfFilterContent');
        var isOpen = wrapper.classList.contains('architect-open');

        // A: Close ALL filters first (Accordion logic)
        closeAllFilters();

        // B: If it was closed, open it now and reveal content
        if (!isOpen) {
            wrapper.classList.add('architect-open');
            
            if (targetContent) {
                targetContent.classList.remove('wpfHide');
                targetContent.style.display = 'block';
            }
            
            var activeIcon = title.querySelector('i');
            if (activeIcon) {
                activeIcon.classList.remove('fa-chevron-down');
                activeIcon.classList.add('fa-chevron-up');
            }
        }
    }

    // Attach Event Listener using CAPTURE PHASE
    document.addEventListener('click', handleArchitectClick, true);

    /* --- HELPER: RESTORE ICONS --- */
    function maintainFilters() {
        var titles = document.querySelectorAll('.wpfFilterTitle');
        titles.forEach(function(title) {
            if (!title.querySelector('.fa-chevron-down') && !title.querySelector('.fa-chevron-up')) {
                var junk = title.querySelectorAll('i, span.wpfIcon');
                junk.forEach(n => n.remove());
                
                var icon = document.createElement('i');
                var isOpen = title.closest('.wpfMainWrapper').classList.contains('architect-open');
                
                icon.className = isOpen ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
                icon.style.float = 'right';
                icon.style.marginTop = '5px';
                title.appendChild(icon);
            }
        });
    }

    // Run on Load
    maintainFilters();

    // 1. Force collapse after AJAX requests (Plugin auto-reload)
    if (typeof jQuery !== 'undefined') {
        jQuery(document).ajaxComplete(function() {
            setTimeout(function() {
                maintainFilters();
                closeAllFilters(); // <--- Auto-Collapse after AJAX completes
            }, 150); // Slight delay allows DOM to finish rendering
        });
    }

    // 2. Force collapse on hard page loads with active URL parameters
    window.addEventListener('load', function() {
        setTimeout(closeAllFilters, 250); 
    });

})();
</script>
<?php } );