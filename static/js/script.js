document.addEventListener("DOMContentLoaded", () => {
    // Set the date input maximum to today's date where appropriate.
    const dateInput = document.querySelector('input[name="date_lost_found"]');
    if (dateInput) {
        dateInput.max = new Date().toISOString().split("T")[0];
    }

    // Confirm destructive actions.
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
});
