/* ============================================================
   Emergency Information — JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ==========================================
     CONFIRM DIALOGS (data-confirm-message)
  ========================================== */

  document.querySelectorAll('[data-confirm-message]').forEach(button => {
    button.addEventListener('click', (e) => {
      const message = button.getAttribute('data-confirm-message');
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  /* ==========================================
     COPY TO CLIPBOARD (data-copy-target)
  ========================================== */

  document.querySelectorAll('[data-copy-target]').forEach(button => {
    button.addEventListener('click', () => {
      const targetId = button.getAttribute('data-copy-target');
      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      const text = targetEl.value || targetEl.textContent;

      navigator.clipboard.writeText(text).then(() => {
        const original = button.textContent;
        button.textContent = '✓ Copied';
        button.style.color = 'var(--ei-success)';
        setTimeout(() => {
          button.textContent = original;
          button.style.color = '';
        }, 2000);
      }).catch(() => {
        /* Fallback for older browsers */
        targetEl.select();
        document.execCommand('copy');
      });
    });
  });

  /* ==========================================
     AUTO-DISMISS ALERTS
  ========================================== */

  document.querySelectorAll('.ei-alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-4px)';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

});
