document.querySelectorAll('.auto-submit-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', () => {
        checkbox.closest('form').submit();
    });
});