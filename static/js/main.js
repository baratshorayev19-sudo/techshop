const navToggle = document.querySelector("[data-nav-toggle]");
const nav = document.querySelector("[data-nav]");

if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
        nav.classList.toggle("open");
    });
}

const catalogWrap = document.querySelector(".catalog-wrap");
const catalogToggle = document.querySelector("[data-catalog-toggle]");
const catalogMega = document.querySelector("[data-catalog-mega]");

if (catalogWrap && catalogToggle && catalogMega) {
    const setCatalogOpen = (open) => {
        catalogWrap.classList.toggle("is-open", open);
        catalogMega.hidden = !open;
        catalogToggle.setAttribute("aria-expanded", String(open));
    };

    catalogToggle.addEventListener("click", (event) => {
        event.preventDefault();
        setCatalogOpen(catalogMega.hidden);
    });

    document.addEventListener("click", (event) => {
        if (!catalogWrap.contains(event.target)) {
            setCatalogOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setCatalogOpen(false);
        }
    });
}

const accountMenu = document.querySelector("[data-account-menu]");
const accountToggle = document.querySelector("[data-account-toggle]");
const accountDropdown = document.querySelector("[data-account-dropdown]");

if (accountMenu && accountToggle && accountDropdown) {
    let accountCloseTimer;

    const setAccountOpen = (open) => {
        window.clearTimeout(accountCloseTimer);
        accountMenu.classList.toggle("is-open", open);
        accountDropdown.hidden = !open;
        accountToggle.setAttribute("aria-expanded", String(open));
    };

    accountToggle.addEventListener("click", (event) => {
        event.preventDefault();
        setAccountOpen(accountDropdown.hidden);
    });

    accountMenu.addEventListener("mouseenter", () => {
        window.clearTimeout(accountCloseTimer);
    });

    accountMenu.addEventListener("mouseleave", () => {
        accountCloseTimer = window.setTimeout(() => setAccountOpen(false), 120);
    });

    document.addEventListener("click", (event) => {
        if (!accountMenu.contains(event.target)) {
            setAccountOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            setAccountOpen(false);
        }
    });
}

document.querySelectorAll(".message").forEach((message) => {
    window.setTimeout(() => {
        message.style.opacity = "0";
        message.style.transform = "translateY(-8px)";
    }, 3600);
});

document.querySelectorAll("[data-quantity-stepper]").forEach((stepper) => {
    const input = stepper.querySelector("input");
    const buttons = stepper.querySelectorAll("[data-step]");

    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const step = Number(button.dataset.step);
            const min = Number(input.min || 0);
            const max = Number(input.max || 99);
            const current = Number(input.value || min);
            const next = Math.min(max, Math.max(min, current + step));

            input.value = next;
            input.dispatchEvent(new Event("change", { bubbles: true }));

            const autoUpdateForm = stepper.closest("[data-auto-update-cart]");
            if (autoUpdateForm) {
                autoUpdateForm.requestSubmit();
            }
        });
    });
});

const favoriteCount = document.querySelector("[data-favorites-count]");

const setFavoriteCount = (count) => {
    if (!favoriteCount) {
        return;
    }
    favoriteCount.textContent = count;
    favoriteCount.classList.toggle("hidden", Number(count) === 0);
};

document.querySelectorAll("[data-favorite-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = form.querySelector("[data-favorite-button]");
        const data = new FormData(form);

        if (button) {
            button.disabled = true;
        }

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: data,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                throw new Error("Favorite request failed");
            }

            const result = await response.json();
            if (button) {
                button.classList.toggle("active", Boolean(result.is_favorite));
            }
            setFavoriteCount(result.favorites_count);
        } catch (error) {
            form.submit();
        } finally {
            if (button) {
                button.disabled = false;
            }
        }
    });
});

const loginModal = document.querySelector("[data-login-modal]");
const loginOpen = document.querySelector("[data-login-open]");
const loginClose = document.querySelector("[data-login-close]");
const showPhone = document.querySelector("[data-show-phone]");

const removeLoginParam = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete("login");
    window.history.replaceState({}, "", url.toString());
};

if (loginModal && loginOpen) {
    loginOpen.addEventListener("click", () => {
        loginModal.classList.add("open");
    });
}

if (loginModal && loginClose) {
    loginClose.addEventListener("click", () => {
        loginModal.classList.remove("open");
        removeLoginParam();
    });
}

if (loginModal) {
    loginModal.addEventListener("click", (event) => {
        if (event.target === loginModal) {
            loginModal.classList.remove("open");
            removeLoginParam();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && loginModal.classList.contains("open")) {
            loginModal.classList.remove("open");
            removeLoginParam();
        }
    });
}

if (showPhone) {
    showPhone.addEventListener("click", () => {
        const url = new URL(window.location.href);
        url.searchParams.set("login", "phone");
        window.location.href = url.toString();
    });
}

document.querySelectorAll('input[name="phone"]').forEach((input) => {
    const formatPhone = () => {
        const digits = input.value.replace(/\D/g, "").replace(/^998/, "").slice(0, 9);
        let value = "+998";
        if (digits.length > 0) {
            value += `(${digits.slice(0, 2)}`;
        }
        if (digits.length >= 2) {
            value += ")";
        }
        if (digits.length > 2) {
            value += digits.slice(2, 5);
        }
        if (digits.length > 5) {
            value += `-${digits.slice(5, 7)}`;
        }
        if (digits.length > 7) {
            value += `-${digits.slice(7, 9)}`;
        }
        input.value = value;
    };

    input.addEventListener("input", () => {
        if (!input.value.startsWith("+998")) {
            input.value = "+998 ";
        }
        formatPhone();
    });

    input.addEventListener("focus", formatPhone);
});

const galleryMain = document.querySelector("[data-gallery-main]");
const galleryThumbs = Array.from(document.querySelectorAll("[data-gallery-thumb]"));

const setGalleryImage = (index) => {
    if (!galleryMain || !galleryThumbs.length) {
        return;
    }

    const normalizedIndex = (index + galleryThumbs.length) % galleryThumbs.length;
    const button = galleryThumbs[normalizedIndex];
    galleryMain.src = button.dataset.src;
    galleryThumbs.forEach((thumb, thumbIndex) => {
        thumb.classList.toggle("active", thumbIndex === normalizedIndex);
    });
};

galleryThumbs.forEach((button, index) => {
    button.addEventListener("click", () => {
        setGalleryImage(index);
    });
});

const galleryPrev = document.querySelector("[data-gallery-prev]");
const galleryNext = document.querySelector("[data-gallery-next]");

if (galleryPrev) {
    galleryPrev.addEventListener("click", () => {
        const activeIndex = Math.max(0, galleryThumbs.findIndex((thumb) => thumb.classList.contains("active")));
        setGalleryImage(activeIndex - 1);
    });
}

if (galleryNext) {
    galleryNext.addEventListener("click", () => {
        const activeIndex = Math.max(0, galleryThumbs.findIndex((thumb) => thumb.classList.contains("active")));
        setGalleryImage(activeIndex + 1);
    });
}
