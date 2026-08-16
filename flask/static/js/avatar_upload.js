const avatarUploadInput = document.getElementById('profile_picture');
const avatarUploadFilename = document.getElementById('avatar-upload-filename');
const avatarUploadPreview = document.getElementById('avatar-upload-preview');

let avatarUploadPreviewUrl = null;

avatarUploadInput.addEventListener('change', () => {
    const file = avatarUploadInput.files && avatarUploadInput.files[0];
    if (!file) {
        avatarUploadFilename.textContent = 'No file selected';
        return;
    }
    if (!file.type.startsWith('image/')) {
        avatarUploadFilename.textContent = 'No file selected';
        avatarUploadInput.value = '';
        return;
    }

    if (avatarUploadPreviewUrl) {
        URL.revokeObjectURL(avatarUploadPreviewUrl);
    }
    avatarUploadPreviewUrl = URL.createObjectURL(file);

    avatarUploadFilename.textContent = file.name;
    avatarUploadPreview.src = avatarUploadPreviewUrl;
});
