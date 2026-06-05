// Main JS for MPSC IT CLUB - Premium High-Tech UI & Real-time Sound Synthesis

// 1. Audio Synthesizer via Web Audio API (No files required, ultra-low latency)
class AudioSynthesizer {
    constructor() {
        this.ctx = null;
        this.setupUserActivation();
    }
    
    init() {
        if (!this.ctx) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
    }
    
    setupUserActivation() {
        const activate = () => {
            this.init();
            if (this.ctx && this.ctx.state === 'suspended') {
                this.ctx.resume().catch(() => {});
            }
            // Remove listeners once active
            ['click', 'touchstart', 'mousemove', 'scroll', 'keydown'].forEach(evt => {
                document.removeEventListener(evt, activate);
            });
        };
        ['click', 'touchstart', 'mousemove', 'scroll', 'keydown'].forEach(evt => {
            document.addEventListener(evt, activate, { passive: true });
        });
    }
    
    playClick() {
        this.init();
        if (!this.ctx || this.ctx.state === 'suspended') return;
        try {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            
            const now = this.ctx.currentTime;
            osc.type = 'sine';
            // Digital high-frequency quick sweep
            osc.frequency.setValueAtTime(1500, now);
            osc.frequency.exponentialRampToValueAtTime(350, now + 0.02);
            
            gain.gain.setValueAtTime(0.006, now); // Soft click
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.025);
            
            osc.start(now);
            osc.stop(now + 0.03);
        } catch (e) {
            // Silently swallow audio exceptions
        }
    }
    
    playBackspace() {
        this.init();
        if (!this.ctx || this.ctx.state === 'suspended') return;
        try {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            
            const now = this.ctx.currentTime;
            osc.type = 'triangle';
            // Digital sweep up
            osc.frequency.setValueAtTime(280, now);
            osc.frequency.exponentialRampToValueAtTime(700, now + 0.04);
            
            gain.gain.setValueAtTime(0.01, now); // Soft data sweep
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.045);
            
            osc.start(now);
            osc.stop(now + 0.05);
        } catch (e) {}
    }
}

// Instantiate Synth globally
const synth = new AudioSynthesizer();

document.addEventListener('DOMContentLoaded', () => {
    // 2. High-Tech Loader Engine
    const loader = document.getElementById('loader');
    const percentEl = document.getElementById('loader-percent');
    const consoleEl = document.getElementById('loader-console');
    
    if (loader) {
        const consoleLogs = [
            { time: 0, text: "[ INFO ] Booting MPSC IT CORE v2.5.0...", success: false },
            { time: 250, text: "[ OK ] Neural link synapses established.", success: true },
            { time: 500, text: "[ INFO ] Authenticating secure club protocols...", success: false },
            { time: 800, text: "[ OK ] Connection verified [PORT: 5000]", success: true },
            { time: 1000, text: "[ INFO ] Synchronizing dynamic databases...", success: false },
            { time: 1300, text: "[ OK ] Executive records loaded successfully.", success: true },
            { time: 1600, text: "[ INFO ] Finalizing UI holographic deck...", success: false },
            { time: 1800, text: "[ OK ] Systems active. Ready for deployment.", success: true }
        ];

        // Print console statements sequentially
        consoleLogs.forEach(log => {
            setTimeout(() => {
                if (consoleEl) {
                    const line = document.createElement('div');
                    line.className = 'log-line';
                    if (log.success) {
                        line.innerHTML = `<span class="log-success">${log.text}</span>`;
                    } else {
                        line.innerText = log.text;
                    }
                    consoleEl.appendChild(line);
                    consoleEl.scrollTop = consoleEl.scrollHeight;
                }
            }, log.time);
        });

        // Percentage counter animation (0% -> 100%)
        let progress = 0;
        const duration = 2000; // 2 seconds
        const stepTime = 20; // 20ms steps
        const increments = duration / stepTime;
        const valueIncrement = 100 / increments;

        const progressInterval = setInterval(() => {
            progress += valueIncrement;
            if (progress >= 100) {
                progress = 100;
                clearInterval(progressInterval);
                
                // Dissolve loader
                setTimeout(() => {
                    if (window.gsap) {
                        gsap.to(loader, {
                            opacity: 0,
                            scale: 1.1,
                            duration: 0.8,
                            ease: "power2.inOut",
                            onComplete: () => {
                                loader.style.display = 'none';
                                initAnimations(); 
                            }
                        });
                    } else {
                        loader.style.opacity = '0';
                        setTimeout(() => {
                            loader.style.display = 'none';
                            initAnimations();
                        }, 800);
                    }
                }, 200);
            }
            if (percentEl) {
                percentEl.innerText = `${Math.floor(progress).toString().padStart(2, '0')}%`;
            }
        }, stepTime);
    } else {
        initAnimations();
    }

    // 3. Fluid Interactive Cursor Glow
    const cursorGlow = document.getElementById('cursor-glow');
    document.addEventListener('mousemove', (e) => {
        if (cursorGlow && window.gsap) {
            gsap.to(cursorGlow, {
                left: e.clientX,
                top: e.clientY,
                duration: 0.4,
                ease: 'power2.out'
            });
        }
    });

    // 4. Navbar Scroll Glow Effect
    const nav = document.getElementById('main-nav');
    window.addEventListener('scroll', () => {
        if (nav) {
            if (window.scrollY > 50) {
                nav.classList.add('scrolled');
            } else {
                nav.classList.remove('scrolled');
            }
        }
    });




    // 7. Toast System
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);

    window.showToast = (message, type = 'success') => {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icon = type === 'success' ? '✅' : '❌';
        
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${message}</span>
        `;
        
        toastContainer.appendChild(toast);
        setTimeout(() => toast.classList.add('active'), 10);
        
        setTimeout(() => {
            toast.classList.remove('active');
            setTimeout(() => toast.remove(), 600);
        }, 4000);
    };
});

// Initialize GSAP Entrances and custom Typist
function initAnimations() {
    // A. Run Custom Typing Engine with Sound effects
    initHeroTyping();

    if (!window.gsap) return;

    // B. Hero Content Entrance
    gsap.from(".hero-title", { y: 50, opacity: 0, duration: 1, delay: 0.1 });
    gsap.from(".hero-subtitle", { y: 30, opacity: 0, duration: 1, delay: 0.3 });
    gsap.from(".hero-btns", { y: 20, opacity: 0, duration: 1, delay: 0.5 });
    
}

// Recreated Typing Animation Engine (Cycles phrases, handles sound clicks, and glitch erase backspaces)
function initHeroTyping() {
    const el = document.getElementById('hero-typing');
    if (!el) return;
    
    const phrases = [
        "WELCOME TO MPSC IT CLUB",
        "EMPOWER YOURSELF THROUGH IT"
    ];
    
    let phraseIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    let typingSpeed = 100;
    
    const typeCycle = () => {
        const currentPhrase = phrases[phraseIndex];
        
        if (isDeleting) {
            el.innerText = currentPhrase.substring(0, charIndex - 1);
            charIndex--;
            typingSpeed = 35; // Backspacing speed is fast
            synth.playBackspace();
        } else {
            el.innerText = currentPhrase.substring(0, charIndex + 1);
            charIndex++;
            typingSpeed = 70 + Math.random() * 40; // Natural variable spacing
            synth.playClick();
        }
        
        // State transitions
        if (!isDeleting && charIndex === currentPhrase.length) {
            isDeleting = true;
            typingSpeed = 3000; // Pause showing complete text (3 seconds)
        } else if (isDeleting && charIndex === 0) {
            isDeleting = false;
            phraseIndex = (phraseIndex + 1) % phrases.length;
            typingSpeed = 500; // Pause before starting typing next text (0.5 seconds)
        }
        
        setTimeout(typeCycle, typingSpeed);
    };
    
    setTimeout(typeCycle, 800);
}
