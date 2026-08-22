const pollingAlert = document.getElementById('payment-polling-alert');

if (pollingAlert) {
    setTimeout(() => {
        window.location.href = pollingAlert.dataset.pollUrl;
    }, 3000);
}
