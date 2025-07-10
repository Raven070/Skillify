// This function runs once the entire HTML document has been loaded and parsed.
document.addEventListener('DOMContentLoaded', function() {

    // --- Mobile Navigation Menu Toggle ---
    // This section handles the functionality of the hamburger menu on smaller screens.
    const mobileNavToggle = document.querySelector('.mobile-nav-toggle');
    const primaryNav = document.querySelector('.navigation-group');

    // Check if both the button and the navigation menu exist before adding the event listener.
    if (mobileNavToggle && primaryNav) {
        mobileNavToggle.addEventListener('click', () => {
            // Check the current visibility state from the 'data-visible' attribute.
            const isVisible = primaryNav.getAttribute('data-visible');

            if (isVisible === "false" || isVisible === null) {
                // If the menu is hidden, show it.
                primaryNav.setAttribute('data-visible', "true");
                mobileNavToggle.setAttribute('aria-expanded', "true");
                mobileNavToggle.innerHTML = '✕'; // Change the icon to a close 'X'.
            } else {
                // If the menu is visible, hide it.
                primaryNav.setAttribute('data-visible', "false");
                mobileNavToggle.setAttribute('aria-expanded', "false");
                mobileNavToggle.innerHTML = '☰'; // Change the icon back to a hamburger.
            }
        });
    }


    // --- GSAP Scroll-Based Animations ---
    // Check if the GSAP library and its ScrollTrigger plugin are available on the page.
    if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {

        // Register the ScrollTrigger plugin with GSAP to enable scroll animations.
        gsap.registerPlugin(ScrollTrigger);

        // --- Animation for "Explore the Possibilities" (Capabilities) Section ---
        const capabilityPanels = gsap.utils.toArray(".capability-panel");

        capabilityPanels.forEach(panel => {
            // Create a GSAP timeline for each panel to sequence its animations.
            const timeline = gsap.timeline({
                scrollTrigger: {
                    trigger: panel,
                    start: "top 80%", // Animation starts when the top of the panel is 80% from the top of the viewport.
                    toggleActions: "play none none none" // Play the animation once on enter and do nothing on leave/re-enter.
                }
            });

            // The animation sequence: image fades/scales in, then title slides in, then description slides in.
            timeline.to(panel.querySelector(".capability-image"), {
                opacity: 1,
                scale: 1,
                duration: 0.8,
                ease: "power2.out"
            })
            .to(panel.querySelector(".capability-text h2"), {
                opacity: 1,
                x: 0,
                duration: 0.6,
                ease: "power2.out"
            }, "-=0.6") // The "-=0.6" overlaps the start of this animation with the previous one for a smoother effect.
            .to(panel.querySelector(".capability-text p"), {
                opacity: 1,
                x: 0,
                duration: 0.6,
                ease: "power2.out"
            }, "-=0.5"); // Overlap again.
        });


        // --- Animation for "Why Choose Us" (Features) Section ---
        // This targets all items in the new grid and animates them as they enter the viewport.
        gsap.from(".why-us-item", {
            opacity: 0,
            y: 30, // Animate from 30px below to its original position
            duration: 0.6,
            stagger: 0.2, // Animate each item 0.2s after the previous one
            ease: "power2.out",
            scrollTrigger: {
                trigger: ".why-us-grid", // Trigger the animation when the whole grid comes into view
                start: "top 80%",
                toggleActions: "play none none none"
            }
        });
    }
});
