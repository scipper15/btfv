document.addEventListener('DOMContentLoaded', function () {
    const burgerButton = document.getElementById('burger-menu-btn');
    const closeButton = document.getElementById('close-menu-btn');
    const menuContent = document.getElementById('burger-menu-content');

    // Open the burger menu
    burgerButton.addEventListener('click', () => {
        menuContent.classList.remove('hidden');
        // menuContent.classList.add('flex');
    });

    // Close the burger menu
    closeButton.addEventListener('click', () => {
        menuContent.classList.add('hidden');
        // menuContent.classList.remove('flex');
    });

    // Close menu when clicking outside the menu content
    menuContent.addEventListener('click', (e) => {
        if (e.target === menuContent) {
            menuContent.classList.add('hidden');
            // menuContent.classList.remove('flex');
        }
    });
});
