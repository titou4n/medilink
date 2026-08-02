document.addEventListener("DOMContentLoaded", function () {

    const parents = document.querySelectorAll(".parent-checkbox");
    const children = document.querySelectorAll(".child-checkbox");

    // Quand on clique sur un parent
    parents.forEach(parent => {
        parent.addEventListener("change", function () {
            const type = this.dataset.type;
            const relatedChildren = document.querySelectorAll(
                '.child-checkbox[data-type="' + type + '"]'
            );

            relatedChildren.forEach(child => {
                child.checked = this.checked;
            });
        });
    });

    // Quand on clique sur un enfant
    children.forEach(child => {
        child.addEventListener("change", function () {
            const type = this.dataset.type;
            const relatedChildren = document.querySelectorAll(
                '.child-checkbox[data-type="' + type + '"]'
            );
            const parent = document.querySelector(
                '.parent-checkbox[data-type="' + type + '"]'
            );

            const allChecked = Array.from(relatedChildren)
                                    .every(c => c.checked);

            parent.checked = allChecked;
        });
    });

});