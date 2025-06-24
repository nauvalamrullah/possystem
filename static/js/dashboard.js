document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".dropdown-btn").forEach(button => {
        button.addEventListener("click", function() {
            // Tutup dropdown lain sebelum membuka yang baru
            document.querySelectorAll(".dropdown-btn").forEach(btn => {
                if (btn !== this) {
                    btn.classList.remove("active");
                    btn.nextElementSibling.classList.remove("show");
                }
            });

            // Toggle dropdown yang diklik
            this.classList.toggle("active");
            this.nextElementSibling.classList.toggle("show");
        });
    });
});
