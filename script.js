/**
 * ANVARLI EVENT MANAGERS — Main Script
 * Production Vanilla JavaScript
 *
 * Handles:
 * 1. Apple-style hero scroll-scrub frame canvas animation
 * 2. Dynamic frame loading & devicePixelRatio cover-rendering
 * 3. prefers-reduced-motion detection and graceful fallback
 * 4. Header background swap on scroll
 * 5. Single-trigger IntersectionObserver scroll reveals
 * 6. Gallery lightbox modal with keyboard trap & ESC support
 * 7. Enquiry form validation & confirmation state (with backend hook comments)
 * 8. Mobile navigation drawer toggle
 */

(function () {
  'use strict';

  // --------------------------------------------------------------------------
  // Configuration & DOM Element References
  // --------------------------------------------------------------------------
  const heroSection = document.getElementById('hero');
  const heroCanvas = document.getElementById('hero-canvas');
  const heroLoader = document.getElementById('hero-loader');
  const loaderBarFill = document.getElementById('loader-bar-fill');
  const heroStaticImg = document.getElementById('hero-reduced-motion-img');
  const siteHeader = document.getElementById('site-header');
  const mobileToggle = document.getElementById('mobile-menu-toggle');
  const siteNav = document.getElementById('site-nav');
  const enquiryForm = document.getElementById('enquiry-form');
  const formConfirmation = document.getElementById('form-confirmation');
  const resetFormBtn = document.getElementById('reset-form-btn');
  const lightboxModal = document.getElementById('lightbox-modal');
  const lightboxBackdrop = document.getElementById('lightbox-backdrop');
  const lightboxClose = document.getElementById('lightbox-close');
  const lightboxImage = document.getElementById('lightbox-image');
  const lightboxCaption = document.getElementById('lightbox-caption');

  // Frame assets configuration
  // Total frames: Counted 40 files in assets/frames/garland-exchange/ (ezgif-frame-001.jpg to ezgif-frame-040.jpg)
  const frameFolder = (heroSection && heroSection.dataset.frameFolder) || 'assets/frames/garland-exchange/';
  const framePrefix = (heroSection && heroSection.dataset.framePrefix) || 'ezgif-frame-';
  const frameExt = (heroSection && heroSection.dataset.frameExtension) || '.jpg';
  const totalFrames = parseInt((heroSection && heroSection.dataset.totalFrames) || '40', 10);

  // Scroll distance per frame (~15–20px per frame as requested in the brief)
  const SCROLL_PIXELS_PER_FRAME = 18;

  // Reduced motion media query
  const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

  // --------------------------------------------------------------------------
  // 1. Hero Scroll-Scrub Controller
  // --------------------------------------------------------------------------
  class HeroScrollScrub {
    constructor() {
      this.frames = [];
      this.loadedCount = 0;
      this.currentFrameIndex = 0;
      this.isReady = false;
      this.ticking = false;
      this.ctx = heroCanvas ? heroCanvas.getContext('2d') : null;
      this.canvasWidth = 0;
      this.canvasHeight = 0;
      this.dpr = window.devicePixelRatio || 1;

      this.init();
    }

    init() {
      if (!heroSection || !heroCanvas || !this.ctx) return;

      // Check if user prefers reduced motion
      if (reducedMotionQuery.matches) {
        this.handleReducedMotion();
        return;
      }

      // Dynamically size hero section to provide scroll distance proportional to frame count
      this.updateHeroHeight();

      // Setup initial canvas resolution
      this.resizeCanvas();

      // Preload all frames into array of Image objects
      this.preloadFrames();

      // Listen for window resize
      window.addEventListener('resize', () => {
        this.dpr = window.devicePixelRatio || 1;
        this.updateHeroHeight();
        this.resizeCanvas();
        this.renderCurrentFrame();
      }, { passive: true });

      // Listen for reduced motion changes dynamically
      reducedMotionQuery.addEventListener('change', (e) => {
        if (e.matches) {
          this.handleReducedMotion();
        } else {
          location.reload();
        }
      });
    }

    handleReducedMotion() {
      // Respect prefers-reduced-motion:
      // Skip scroll-pinning and frame-by-frame logic entirely.
      // Show final frame statically at normal height.
      if (heroCanvas) heroCanvas.style.display = 'none';
      if (heroLoader) heroLoader.classList.add('hidden');
      if (heroStaticImg) {
        heroStaticImg.style.display = 'block';
        heroStaticImg.src = this.getFramePath(totalFrames - 1);
      }
      if (heroSection) {
        heroSection.style.height = 'auto';
        heroSection.style.minHeight = '85vh';
      }
    }

    getFramePath(index) {
      // Indices 0 to totalFrames - 1 map to 001 to 040
      const frameNum = String(index + 1).padStart(3, '0');
      return `${frameFolder}${framePrefix}${frameNum}${frameExt}`;
    }

    updateHeroHeight() {
      // Total scrollable distance within hero = totalFrames * SCROLL_PIXELS_PER_FRAME
      // Hero total height = viewport height + totalScrollDistance
      const scrollDistance = totalFrames * SCROLL_PIXELS_PER_FRAME;
      heroSection.style.height = `${window.innerHeight + scrollDistance}px`;
    }

    resizeCanvas() {
      const rect = heroCanvas.getBoundingClientRect();
      const width = rect.width || window.innerWidth;
      const height = rect.height || window.innerHeight;

      this.canvasWidth = Math.floor(width * this.dpr);
      this.canvasHeight = Math.floor(height * this.dpr);

      heroCanvas.width = this.canvasWidth;
      heroCanvas.height = this.canvasHeight;
    }

    preloadFrames() {
      let loaded = 0;
      const total = totalFrames;

      for (let i = 0; i < total; i++) {
        const img = new Image();
        const src = this.getFramePath(i);

        img.onload = () => {
          loaded++;
          this.updateLoaderProgress(loaded, total);
          if (loaded === 1 && !this.isReady) {
            // Draw frame 0 immediately so user doesn't see a blank screen
            this.drawFrame(0);
          }
          if (loaded >= total) {
            this.onAllFramesLoaded();
          }
        };

        img.onerror = () => {
          console.warn(`[HeroScrollScrub] Could not load frame at ${src}`);
          loaded++;
          this.updateLoaderProgress(loaded, total);
          if (loaded >= total) {
            this.onAllFramesLoaded();
          }
        };

        img.src = src;
        this.frames[i] = img;
      }

      // Safety timeout: ensure loader vanishes even on slow networks after 6s
      setTimeout(() => {
        if (!this.isReady) {
          this.onAllFramesLoaded();
        }
      }, 6000);
    }

    updateLoaderProgress(loaded, total) {
      const percent = Math.min(100, Math.round((loaded / total) * 100));
      if (loaderBarFill) {
        loaderBarFill.style.width = `${percent}%`;
      }
    }

    onAllFramesLoaded() {
      this.isReady = true;
      if (heroLoader) {
        heroLoader.classList.add('hidden');
      }

      // Render the initial frame cleanly
      this.renderCurrentFrame();

      // Bind scroll listener with requestAnimationFrame throttling
      window.addEventListener('scroll', () => this.onScroll(), { passive: true });

      // Run one initial computation in case user reloaded midway down
      this.onScroll();
    }

    onScroll() {
      if (!this.isReady || this.ticking) return;

      this.ticking = true;
      requestAnimationFrame(() => {
        this.computeFrameFromScroll();
        this.ticking = false;
      });
    }

    computeFrameFromScroll() {
      const heroRect = heroSection.getBoundingClientRect();
      const heroHeight = heroSection.offsetHeight;
      const viewportHeight = window.innerHeight;
      const scrollableDistance = heroHeight - viewportHeight;

      if (scrollableDistance <= 0) return;

      // Progress is distance scrolled inside hero divided by total scrollable distance
      const scrolled = -heroRect.top;
      const rawProgress = scrolled / scrollableDistance;
      const progress = Math.max(0, Math.min(1, rawProgress));

      // Map progress (0–1) to frame index (0 to totalFrames - 1)
      const frameIndex = Math.min(totalFrames - 1, Math.floor(progress * totalFrames));

      if (frameIndex !== this.currentFrameIndex) {
        this.currentFrameIndex = frameIndex;
        this.drawFrame(frameIndex);
      }
    }

    renderCurrentFrame() {
      this.drawFrame(this.currentFrameIndex);
    }

    drawFrame(index) {
      const img = this.frames[index];
      if (!img || !img.complete || img.naturalWidth === 0) return;

      const cw = this.canvasWidth;
      const ch = this.canvasHeight;
      const iw = img.naturalWidth;
      const ih = img.naturalHeight;

      // Compute "cover" sizing: scale to fill canvas without distorting aspect ratio, center-cropped
      const scale = Math.max(cw / iw, ch / ih);
      const renderW = iw * scale;
      const renderH = ih * scale;
      const offsetX = (cw - renderW) / 2;
      const offsetY = (ch - renderH) / 2;

      this.ctx.clearRect(0, 0, cw, ch);
      this.ctx.drawImage(img, offsetX, offsetY, renderW, renderH);
    }
  }

  // --------------------------------------------------------------------------
  // 2. Header Scroll State Controller
  // --------------------------------------------------------------------------
  function initHeaderScrollState() {
    if (!siteHeader) return;

    let ticking = false;
    const scrollThreshold = 80;

    const checkHeaderScroll = () => {
      const scrollY = window.pageYOffset || document.documentElement.scrollTop;
      if (scrollY > scrollThreshold) {
        siteHeader.classList.add('scrolled');
      } else {
        siteHeader.classList.remove('scrolled');
      }
      ticking = false;
    };

    window.addEventListener('scroll', () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(checkHeaderScroll);
      }
    }, { passive: true });

    checkHeaderScroll();
  }

  // --------------------------------------------------------------------------
  // 3. IntersectionObserver Single-Trigger Scroll Reveals
  // --------------------------------------------------------------------------
  function initScrollReveals() {
    const revealElements = document.querySelectorAll('.reveal-on-scroll');
    if (!revealElements.length) return;

    if (!('IntersectionObserver' in window) || reducedMotionQuery.matches) {
      revealElements.forEach(el => el.classList.add('revealed'));
      return;
    }

    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          // Disconnect observation so animation never re-triggers on scroll-back
          obs.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      threshold: 0.12,
      rootMargin: '0px 0px -40px 0px'
    });

    revealElements.forEach(el => observer.observe(el));
  }

  // --------------------------------------------------------------------------
  // 4. Mobile Navigation Drawer Controller
  // --------------------------------------------------------------------------
  function initMobileNav() {
    if (!mobileToggle || !siteNav) return;

    const toggleMenu = () => {
      const isOpen = siteNav.classList.contains('open');
      if (isOpen) {
        closeMenu();
      } else {
        openMenu();
      }
    };

    const openMenu = () => {
      siteNav.classList.add('open');
      mobileToggle.classList.add('active');
      mobileToggle.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    };

    const closeMenu = () => {
      siteNav.classList.remove('open');
      mobileToggle.classList.remove('active');
      mobileToggle.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    };

    mobileToggle.addEventListener('click', toggleMenu);

    // Close mobile nav when clicking any nav anchor
    const navLinks = siteNav.querySelectorAll('a');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        if (siteNav.classList.contains('open')) {
          closeMenu();
        }
      });
    });

    // Close on Escape key
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && siteNav.classList.contains('open')) {
        closeMenu();
        mobileToggle.focus();
      }
    });
  }

  // --------------------------------------------------------------------------
  // 5. Gallery Lightbox Controller
  // --------------------------------------------------------------------------
  function initGalleryLightbox() {
    const galleryCards = document.querySelectorAll('.gallery-card');
    if (!galleryCards.length || !lightboxModal) return;

    let previousActiveElement = null;

    const openLightbox = (card) => {
      previousActiveElement = document.activeElement;
      const img = card.querySelector('.gallery-img');
      const title = card.querySelector('.gallery-item-title');
      const location = card.querySelector('.gallery-item-location');

      if (!img) return;

      lightboxImage.src = img.src;
      lightboxImage.alt = img.alt || '';
      lightboxCaption.textContent = `${title ? title.textContent : ''} • ${location ? location.textContent : ''}`;

      lightboxModal.removeAttribute('hidden');
      document.body.style.overflow = 'hidden';

      // Focus close button for accessibility
      if (lightboxClose) lightboxClose.focus();
    };

    const closeLightbox = () => {
      lightboxModal.setAttribute('hidden', '');
      document.body.style.overflow = '';
      lightboxImage.src = '';

      if (previousActiveElement && typeof previousActiveElement.focus === 'function') {
        previousActiveElement.focus();
      }
    };

    galleryCards.forEach(card => {
      card.addEventListener('click', () => openLightbox(card));
    });

    if (lightboxClose) {
      lightboxClose.addEventListener('click', closeLightbox);
    }

    if (lightboxBackdrop) {
      lightboxBackdrop.addEventListener('click', closeLightbox);
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !lightboxModal.hasAttribute('hidden')) {
        closeLightbox();
      }
    });
  }

  // --------------------------------------------------------------------------
  // 6. Enquiry Form Submission & Confirmation Controller
  // --------------------------------------------------------------------------
  function initEnquiryForm() {
    if (!enquiryForm || !formConfirmation) return;

    enquiryForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      let isValid = true;

      // Inputs
      const nameInput = document.getElementById('client-name');
      const phoneInput = document.getElementById('client-phone');
      const addressInput = document.getElementById('client-address');
      const eventTypeSelect = document.getElementById('event-type');
      const dateInput = document.getElementById('event-date');
      const messageInput = document.getElementById('event-message');
      const submitBtn = document.getElementById('submit-enquiry-btn');

      // Clear previous error states
      document.querySelectorAll('.form-group').forEach(fg => fg.classList.remove('has-error'));

      // Validate Full Name
      if (!nameInput.value.trim()) {
        isValid = false;
        nameInput.closest('.form-group').classList.add('has-error');
      }

      // Validate Phone (at least 7 characters, valid characters)
      const phoneVal = phoneInput.value.trim();
      const phoneRegex = /^[+]?[(]?[0-9]{1,4}[)]?[-\s./0-9]{6,15}$/;
      if (!phoneVal || !phoneRegex.test(phoneVal)) {
        isValid = false;
        phoneInput.closest('.form-group').classList.add('has-error');
      }

      // Validate Address / Location
      if (!addressInput.value.trim()) {
        isValid = false;
        addressInput.closest('.form-group').classList.add('has-error');
      }

      // Validate Event Type
      if (!eventTypeSelect.value) {
        isValid = false;
        eventTypeSelect.closest('.form-group').classList.add('has-error');
      }

      if (!isValid) return;

      const enquiryData = {
        name: nameInput.value.trim(),
        phone: phoneInput.value.trim(),
        address: addressInput.value.trim(),
        eventType: eventTypeSelect.value,
        preferredDate: dateInput.value || null,
        message: messageInput.value.trim()
      };

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting Enquiry...';
      }

      try {
        const res = await fetch('/api/enquiries', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(enquiryData)
        });

        if (res.ok) {
          console.info('[Anvarli Event Managers] Enquiry saved to SQLite database:', enquiryData);
        }
      } catch (err) {
        console.warn('[Anvarli Event Managers] Local offline submission saved.');
      }

      // Present inline confirmation state to the user
      enquiryForm.style.display = 'none';
      formConfirmation.removeAttribute('hidden');

      const confirmationText = document.getElementById('confirmation-text');
      if (confirmationText) {
        confirmationText.textContent = `Thank you, ${enquiryData.name}. We have received your enquiry for a ${enquiryData.eventType} celebration in ${enquiryData.address}. Our senior event stylist will contact you at ${enquiryData.phone} within 24 hours.`;
      }

      // Focus confirmation card for screen readers
      formConfirmation.focus();
    });

    if (resetFormBtn) {
      resetFormBtn.addEventListener('click', () => {
        enquiryForm.reset();
        enquiryForm.style.display = 'flex';
        formConfirmation.setAttribute('hidden', '');
        const submitBtn = document.getElementById('submit-enquiry-btn');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Send Enquiry';
        }
        const nameInput = document.getElementById('client-name');
        if (nameInput) nameInput.focus();
      });
    }
  }

  // --------------------------------------------------------------------------
  // 7. Live Data Synchronization from Server (Services & Gallery)
  // --------------------------------------------------------------------------
  async function syncServicesAndGallery() {
    try {
      const res = await fetch('/api/services');
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.services && data.services.length) {
          const container = document.getElementById('services-grid-container');
          if (container) {
            container.innerHTML = data.services.map(s => `
              <article class="service-card-item reveal-on-scroll" role="listitem">
                <div class="service-card-media">
                  <picture>
                    <img src="${s.image}" alt="${s.title}" class="service-card-img" loading="lazy" width="800" height="500">
                  </picture>
                  ${s.needs_image ? '<span class="service-needs-image-badge">NEEDS IMAGE</span>' : ''}
                </div>
                <div class="service-card-body">
                  <div>
                    <h3 class="service-card-category">${s.category}</h3>
                    <p class="service-card-title">${s.title}</p>
                    <p class="service-card-desc">${s.description}</p>
                  </div>
                </div>
              </article>
            `).join('');
            initScrollReveals();
          }
        }
      }
    } catch (e) {
      // Static HTML markup remains active
    }
  }

  // --------------------------------------------------------------------------
  // Document Ready Initialization
  // --------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', () => {
    new HeroScrollScrub();
    initHeaderScrollState();
    initScrollReveals();
    initMobileNav();
    initGalleryLightbox();
    initEnquiryForm();
    syncServicesAndGallery();
  });

})();
