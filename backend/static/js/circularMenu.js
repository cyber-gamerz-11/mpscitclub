// Circular Menu Logic for MPSC IT CLUB

document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menu-toggle');
    const menuOverlay = document.getElementById('menu-overlay');
    const circularMenu = document.getElementById('circular-menu');
    if (!menuToggle || !menuOverlay || !circularMenu) return;

    const menuItems = circularMenu.querySelectorAll('li');
    let isMenuOpen = false;
    let rotation = 0;
    let radius = 0;

    // 1. Position items in a circle
    function positionMenuItems() {
        // Force a layout recalculation for the container
        const container = document.querySelector('.circular-container');
        const containerWidth = container.offsetWidth || 320;
        
        // Dynamic radius: smaller percentage for mobile to prevent overflow
        const radiusFactor = window.innerWidth < 500 ? 2.5 : 2.2;
        radius = containerWidth / radiusFactor; 

        menuItems.forEach((li, index) => {
            const angle = (index / menuItems.length) * (Math.PI * 2);
            const x = Math.cos(angle) * radius;
            const y = Math.sin(angle) * radius;
            
            // Set position immediately
            li.style.transform = `translate(${x}px, ${y}px)`;
            
            // Keep links upright
            const link = li.querySelector('a');
            link.style.transform = `rotate(${-rotation}deg)`;
        });
    }

    // Initialize positions on load and resize
    positionMenuItems();
    window.addEventListener('resize', positionMenuItems);

    // 2. Toggle Menu
    menuToggle.addEventListener('click', () => {
        isMenuOpen = !isMenuOpen;
        menuToggle.classList.toggle('active');
        menuOverlay.classList.toggle('active');
        
        if (isMenuOpen) {
            document.body.style.overflow = 'hidden';
            
            // Re-calculate positions just in case container size changed while hidden
            setTimeout(() => {
                positionMenuItems();
                animateMenuItemsIn();
            }, 50); // Small delay to let overlay animate in
        } else {
            document.body.style.overflow = 'auto';
        }
    });

    function animateMenuItemsIn() {
        if (typeof synth !== 'undefined') synth.playClick();
        gsap.fromTo(menuItems, 
            { scale: 0, opacity: 0 },
            { 
                scale: 1, 
                opacity: 1, 
                duration: 0.8, 
                stagger: 0.08, 
                ease: "back.out(1.5)" 
            }
        );
    }

    // Add HUD interaction on hover
    const circularContainer = document.querySelector('.circular-container');
    menuItems.forEach(item => {
        item.addEventListener('mouseenter', () => {
            if (circularContainer) circularContainer.classList.add('fast-spin');
            if (typeof synth !== 'undefined') synth.playBackspace(); // Small blip sound
        });
        item.addEventListener('mouseleave', () => {
            if (circularContainer) circularContainer.classList.remove('fast-spin');
        });
    });

    // 3. Update Rotation & Keep Text Upright
    function updateMenuRotation() {
        gsap.to(circularMenu, {
            rotate: rotation,
            duration: 0.5,
            ease: "power2.out",
            overwrite: "auto"
        });

        // Keep links upright
        menuItems.forEach((li) => {
            const link = li.querySelector('a');
            gsap.to(link, {
                rotate: -rotation,
                duration: 0.5,
                ease: "power2.out",
                overwrite: "auto"
            });
        });
    }

    // 4. Interaction (Mouse & Touch)
    window.addEventListener('wheel', (e) => {
        if (isMenuOpen) {
            rotation += e.deltaY * 0.15;
            updateMenuRotation();
        }
    });

    let touchStartY = 0;
    let velocity = 0;
    let lastTouchY = 0;

    window.addEventListener('touchstart', (e) => {
        if (isMenuOpen) {
            touchStartY = e.touches[0].clientY;
            lastTouchY = touchStartY;
            velocity = 0;
        }
    });

    window.addEventListener('touchmove', (e) => {
        if (isMenuOpen) {
            const currentY = e.touches[0].clientY;
            const diff = lastTouchY - currentY;
            rotation += diff * 0.4;
            velocity = diff;
            lastTouchY = currentY;
            updateMenuRotation();
        }
    });

    window.addEventListener('touchend', () => {
        if (isMenuOpen) {
            const applyInertia = () => {
                if (Math.abs(velocity) > 0.1) {
                    rotation += velocity;
                    velocity *= 0.95; 
                    updateMenuRotation();
                    requestAnimationFrame(applyInertia);
                }
            };
            applyInertia();
        }
    });

    // 5. Close Menu on link click
    menuItems.forEach(item => {
        item.addEventListener('click', () => {
            isMenuOpen = false;
            menuToggle.classList.remove('active');
            menuOverlay.classList.remove('active');
            document.body.style.overflow = 'auto';
        });
    });
});
