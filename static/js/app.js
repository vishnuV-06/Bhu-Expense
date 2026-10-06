/**
 * FinTrack - Client-side utilities
 */

document.addEventListener('DOMContentLoaded', function () {
  // Initialize Bootstrap tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Auto-dismiss alert banners after 6 seconds
  const autoDismissAlerts = document.querySelectorAll('.alert-dismissible:not(.alert-permanent)');
  autoDismissAlerts.forEach(function (alertEl) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 6000);
  });

  // Month selector auto-submit when changed
  const monthFilterSelect = document.getElementById('monthSelectorInput');
  if (monthFilterSelect) {
    monthFilterSelect.addEventListener('change', function () {
      const form = this.closest('form');
      if (form) {
        form.submit();
      }
    });
  }

  // Double-check dangerous deletes
  const dangerDeleteButtons = document.querySelectorAll('.btn-confirm-action');
  dangerDeleteButtons.forEach(function (button) {
    button.addEventListener('click', function (e) {
      const message = this.getAttribute('data-confirm-message') || 'Are you sure you want to perform this action?';
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });
});
