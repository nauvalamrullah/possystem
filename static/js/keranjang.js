function updateCartBadge() {
    fetch('/cart/count')
      .then(response => response.json())
      .then(data => {
        document.getElementById('cart-badge').innerText = data.count;
      });
  }
  
  // Panggil saat halaman dimuat
  document.addEventListener('DOMContentLoaded', updateCartBadge);
  

// Jalankan saat halaman selesai dimuat
document.addEventListener("DOMContentLoaded", updateCartCount);
<script>
    function updateCartCount() {
        fetch('/cart/count')
            .then(response => response.json())
            .then(data => {
                const cartCount = document.getElementById('cart-count');
                const currentCount = parseInt(cartCount.textContent);
                
                // Update jika jumlah berubah
                if (data.count !== currentCount) {
                    cartCount.textContent = data.count;

                    // Trigger ulang animasi bounce
                    cartCount.classList.remove('animate-bounce');
                    void cartCount.offsetWidth; // trigger reflow
                    cartCount.classList.add('animate-bounce');
                }
            })
    }

    setInterval(updateCartCount, 3000); // update tiap 3 detik
</script>
