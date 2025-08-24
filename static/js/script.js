document.addEventListener("DOMContentLoaded", () => {
  const mainImage = document.getElementById("mainPreview");
  const thumbnails = document.querySelectorAll(".thumbnails img");
  const prevBtn = document.querySelector(".nav-btn.left");
  const nextBtn = document.querySelector(".nav-btn.right");
  const quantityInput = document.querySelector('input[name="quantity"]');
  let currentIndex = 0;
  let startX = 0;

  if (mainImage && thumbnails.length > 0) {
    thumbnails[0].classList.add("active-thumb");
    mainImage.src = thumbnails[0].src;

    function changeImage(index) {
      thumbnails.forEach(t => t.classList.remove("active-thumb"));
      thumbnails[index].classList.add("active-thumb");
      mainImage.src = thumbnails[index].src;
      currentIndex = index;
    }

    thumbnails.forEach((thumb, index) => {
      thumb.addEventListener("click", () => changeImage(index));
    });

    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        currentIndex = (currentIndex - 1 + thumbnails.length) % thumbnails.length;
        changeImage(currentIndex);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        currentIndex = (currentIndex + 1) % thumbnails.length;
        changeImage(currentIndex);
      });
    }

    // 🛠 Swipe only on image, prevent scrolling
    mainImage.addEventListener("touchstart", (e) => {
      startX = e.touches[0].clientX;
    }, { passive: true });

    mainImage.addEventListener("touchmove", (e) => {
      // prevent vertical scroll ONLY when swipe is horizontal
      const dx = e.touches[0].clientX - startX;
      if (Math.abs(dx) > 10) {
        e.preventDefault(); // Stop whole-page scroll
      }
    }, { passive: false });

    mainImage.addEventListener("touchend", (e) => {
      const endX = e.changedTouches[0].clientX;
      const diff = endX - startX;

      if (Math.abs(diff) > 50) {
        if (diff < 0) {
          currentIndex = (currentIndex + 1) % thumbnails.length;
        } else {
          currentIndex = (currentIndex - 1 + thumbnails.length) % thumbnails.length;
        }
        changeImage(currentIndex);
      }
    });
  }

  // Quantity safeguard
  if (quantityInput) {
    quantityInput.addEventListener("input", () => {
      let val = parseInt(quantityInput.value);
      if (isNaN(val) || val < 1) quantityInput.value = 1;
    });
  }

  // Mobile menu
  const menuToggle = document.querySelector(".menu-toggle");
  const navMenu = document.querySelector(".nav-links");
  if (menuToggle && navMenu) {
    menuToggle.addEventListener("click", () => {
      navMenu.classList.toggle("show");
    });
  }

  // Search toggle
  const searchBtn = document.querySelector(".search-btn");
  const searchForm = document.querySelector(".search-form");
  if (searchBtn && searchForm) {
    searchBtn.addEventListener("click", () => {
      searchForm.classList.toggle("visible");
    });
  }

  // Add-to-cart alert (placeholder)
  const addToCartBtn = document.querySelector(".add-to-cart-btn");
  if (addToCartBtn) {
    addToCartBtn.addEventListener("click", () => {
      alert("Item added to cart!");
    });
  }

  
});