/* ============================================================
   Confirm dialogs (data-confirm-message)
   Replaces the browser's native confirm() with a styled <dialog>
   consistent with the rest of the design system.
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  const triggers = document.querySelectorAll('[data-confirm-message]');
  if (!triggers.length) return;

  const dialog = document.createElement('dialog');
  dialog.className = 'confirm-dialog';
  dialog.innerHTML = `
    <div class="confirm-dialog__body">
      <h3 class="confirm-dialog__title">Please confirm</h3>
      <p class="confirm-dialog__message"></p>
      <div class="confirm-dialog__actions">
        <button type="button" class="btn btn--secondary" data-action="cancel">Cancel</button>
        <button type="button" class="btn" data-action="confirm">Confirm</button>
      </div>
    </div>
  `;
  document.body.appendChild(dialog);

  const messageEl = dialog.querySelector('.confirm-dialog__message');
  const cancelBtn = dialog.querySelector('[data-action="cancel"]');
  const confirmBtn = dialog.querySelector('[data-action="confirm"]');
  let pendingButton = null;

  triggers.forEach(button => {
    button.addEventListener('click', (e) => {
      e.preventDefault();
      pendingButton = button;
      messageEl.textContent = button.getAttribute('data-confirm-message');
      confirmBtn.textContent = button.textContent.trim() || 'Confirm';
      confirmBtn.className = button.classList.contains('btn--danger') ? 'btn btn--danger' : 'btn';
      dialog.showModal();
    });
  });

  cancelBtn.addEventListener('click', () => {
    pendingButton = null;
    dialog.close();
  });

  confirmBtn.addEventListener('click', () => {
    dialog.close();
    const button = pendingButton;
    pendingButton = null;
    if (!button) return;
    const form = button.closest('form');
    if (form && typeof form.requestSubmit === 'function') {
      form.requestSubmit(button);
    } else if (form) {
      form.submit();
    } else if (button.tagName === 'A') {
      window.location.href = button.href;
    }
  });
});
