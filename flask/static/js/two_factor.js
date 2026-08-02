document.addEventListener("DOMContentLoaded", () => {
    const inputs = document.querySelectorAll(".code-inputs input");
    const hiddenInput = document.getElementById("code");

    inputs.forEach((input, index) => {

        input.addEventListener("input", () => {
            input.value = input.value.replace(/[^0-9]/g, "");

            if (input.value && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }

            hiddenInput.value = Array.from(inputs)
                .map(i => i.value)
                .join("");
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Backspace" && !input.value && index > 0) {
                inputs[index - 1].focus();
            }
        });

    });
});
