/**
 * Cinematic Effects - Vanilla JS inspired by React Bits
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // 1. Decrypted Text Effect
    // Usage: <span class="decrypted-text" data-text="CLASSIFIED INFO"></span>
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*';
    document.querySelectorAll('.decrypted-text').forEach(el => {
        const originalText = el.getAttribute('data-text') || el.innerText;
        el.innerText = '';
        el.setAttribute('data-text', originalText);
        
        let iteration = 0;
        let interval = null;
        
        const startDecryption = () => {
            clearInterval(interval);
            iteration = 0;
            interval = setInterval(() => {
                el.innerText = originalText.split('')
                    .map((letter, index) => {
                        if(index < iteration) return originalText[index];
                        return characters[Math.floor(Math.random() * characters.length)];
                    })
                    .join('');
                
                if(iteration >= originalText.length) {
                    clearInterval(interval);
                }
                iteration += 1 / 3;
            }, 30);
        };
        
        // Start on load or on hover/scroll into view depending on preference
        startDecryption();
        
        // Optional: replay on hover
        el.addEventListener('mouseenter', startDecryption);
    });

    // 2. Spotlight Card Effect for Glass Surfaces
    // Tracks mouse movement to update CSS variables for the radial gradient glow
    document.querySelectorAll('.glass-surface').forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });

    // 3. Staggered Animated Lists
    // Usage: <div class="animated-list"> <div class="animated-list-item">...</div> </div>
    document.querySelectorAll('.animated-list').forEach(list => {
        const items = list.querySelectorAll('.animated-list-item');
        items.forEach((item, index) => {
            item.style.animationDelay = `${index * 0.08}s`;
        });
    });
});
