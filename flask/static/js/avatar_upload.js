const avatarUploadInput = document.getElementById('profile_picture');
const avatarUploadFilename = document.getElementById('avatar-upload-filename');
const avatarUploadPreview = document.getElementById('avatar-upload-preview');

avatarUploadInput.addEventListener('change', () => {
    const file = avatarUploadInput.files && avatarUploadInput.files[0];
    if (!file) {
        avatarUploadFilename.textContent = 'No file selected';
        return;
    }
    avatarUploadFilename.textContent = file.name;
    avatarUploadPreview.src = URL.createObjectURL(file);
});
