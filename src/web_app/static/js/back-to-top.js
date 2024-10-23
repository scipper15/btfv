document.addEventListener('DOMContentLoaded', function () {
    const backToTopButton = document.getElementById('back-to-top');

    // Show the button after scrolling down 300px
    window.addEventListener('scroll', function () {
        if (window.scrollY > 300) {
            backToTopButton.classList.remove('hidden');
            backToTopButton.classList.add('opacity-100');
        } else {
            backToTopButton.classList.add('hidden');
            backToTopButton.classList.remove('opacity-100');
        }
    });

    // Scroll back to top when the button is clicked
    backToTopButton.addEventListener('click', function () {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'  // Smooth scrolling
        });
    });
});
