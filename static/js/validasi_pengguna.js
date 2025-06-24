document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".btn-validasi, .btn-tolak").forEach(button => {
        button.addEventListener("click", function () {
            let userId = this.getAttribute("data-id");
            let action = this.classList.contains("btn-validasi") ? "validasi" : "tolak";

            fetch(`/update_user/${userId}/${action}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`User berhasil di-${action}`);
                    location.reload();
                } else {
                    alert(`Gagal memproses user: ${data.error || 'Unknown error'}`);
                }
            })
            .catch(error => console.error("Error:", error));
        });
    });
});
