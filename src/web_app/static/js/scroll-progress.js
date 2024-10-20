function updateScrollProgress() {
    // Get the document height minus the viewport height
    let documentHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;

    // Current scroll position
    let scrollTop = window.scrollY;

    // Calculate the scroll percentage
    let scrollPercent = (scrollTop / documentHeight) * 100;

    // Set the width of the progress bar according to scroll percentage
    let progressBar = document.getElementById('progress-bar');
    progressBar.style.width = scrollPercent + "%";
}

// Trigger the scroll event on page load
document.addEventListener('DOMContentLoaded', function() {
    updateScrollProgress();  // Update the progress bar on page load
});

// Also update on scroll
document.addEventListener('scroll', updateScrollProgress);

// Handle window resize to adjust progress bar to container width
window.addEventListener('resize', function () {
    let progressBar = document.getElementById('progress-bar');
    let container = document.querySelector('.container');
    progressBar.style.maxWidth = container.offsetWidth + "px";
});
