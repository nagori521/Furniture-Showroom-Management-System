document.querySelectorAll(".js-confirm-delete").forEach((button) => {
    button.addEventListener("click", (event) => {
        const confirmed = window.confirm("Delete this record?");
        if (!confirmed) {
            event.preventDefault();
        }
    });
});

document.querySelectorAll("form").forEach((form) => {
    const choiceInputs = form.querySelectorAll(".js-customer-choice");
    if (!choiceInputs.length) {
        return;
    }

    const existingBlock = form.querySelector(".js-customer-existing");
    const newBlock = form.querySelector(".js-customer-new");
    const existingSelect = existingBlock?.querySelector("select");
    const newInputs = newBlock?.querySelectorAll("input, textarea");

    const syncCustomerMode = () => {
        const selectedMode = form.querySelector(".js-customer-choice:checked")?.value;
        const isNewCustomer = selectedMode === "new";

        existingBlock?.classList.toggle("d-none", isNewCustomer);
        newBlock?.classList.toggle("d-none", !isNewCustomer);

        if (existingSelect) {
            existingSelect.required = !isNewCustomer;
        }

        newInputs?.forEach((input) => {
            input.required = isNewCustomer;
        });
    };

    choiceInputs.forEach((input) => {
        input.addEventListener("change", syncCustomerMode);
    });

    syncCustomerMode();
});

document.querySelectorAll("form").forEach((form) => {
    const productSelect = form.querySelector(".js-sale-product");
    const quantityInput = form.querySelector(".js-sale-quantity");
    const discountInput = form.querySelector(".js-sale-discount");
    const advanceInput = form.querySelector(".js-sale-advance");
    const subtotalOutput = form.querySelector(".js-sale-subtotal");
    const discountOutput = form.querySelector(".js-sale-discount-label");
    const finalOutput = form.querySelector(".js-sale-final");
    const advanceOutput = form.querySelector(".js-sale-advance-label");
    const pendingOutput = form.querySelector(".js-sale-pending");

    if (
        !productSelect ||
        !quantityInput ||
        !discountInput ||
        !advanceInput ||
        !subtotalOutput ||
        !discountOutput ||
        !finalOutput ||
        !advanceOutput ||
        !pendingOutput
    ) {
        return;
    }

    const formatCurrency = (value) => `Rs. ${value.toFixed(2)}`;

    const updateSalePreview = () => {
        const selectedOption = productSelect.selectedOptions[0];
        const unitPrice = Number.parseFloat(selectedOption?.dataset.price || "0");
        const quantity = Number.parseInt(quantityInput.value || "0", 10);
        const discount = Number.parseFloat(discountInput.value || "0");
        const advance = Number.parseFloat(advanceInput.value || "0");
        const subtotal = unitPrice * Math.max(quantity, 0);
        const safeDiscount = Math.min(Math.max(discount, 0), subtotal);
        const finalAmount = Math.max(subtotal - safeDiscount, 0);
        const safeAdvance = Math.min(Math.max(advance, 0), finalAmount);
        const pendingAmount = Math.max(finalAmount - safeAdvance, 0);

        subtotalOutput.textContent = formatCurrency(subtotal);
        discountOutput.textContent = formatCurrency(safeDiscount);
        finalOutput.textContent = formatCurrency(finalAmount);
        advanceOutput.textContent = formatCurrency(safeAdvance);
        pendingOutput.textContent = formatCurrency(pendingAmount);
    };

    [productSelect, quantityInput, discountInput, advanceInput].forEach((input) => {
        input.addEventListener("input", updateSalePreview);
        input.addEventListener("change", updateSalePreview);
    });

    updateSalePreview();
});

document.querySelectorAll("form").forEach((form) => {
    const productSelect = form.querySelector(".js-preorder-product");
    const quantityInput = form.querySelector(".js-preorder-quantity");
    const discountInput = form.querySelector(".js-preorder-discount");
    const advanceInput = form.querySelector(".js-preorder-advance");
    const subtotalOutput = form.querySelector(".js-preorder-subtotal");
    const discountOutput = form.querySelector(".js-preorder-discount-label");
    const finalOutput = form.querySelector(".js-preorder-final");
    const advanceOutput = form.querySelector(".js-preorder-advance-label");
    const pendingOutput = form.querySelector(".js-preorder-pending");

    if (
        !productSelect ||
        !quantityInput ||
        !discountInput ||
        !advanceInput ||
        !subtotalOutput ||
        !discountOutput ||
        !finalOutput ||
        !advanceOutput ||
        !pendingOutput
    ) {
        return;
    }

    const formatCurrency = (value) => `Rs. ${value.toFixed(2)}`;

    const updatePreorderPreview = () => {
        const selectedOption = productSelect.selectedOptions[0];
        const unitPrice = Number.parseFloat(selectedOption?.dataset.price || "0");
        const quantity = Number.parseInt(quantityInput.value || "0", 10);
        const discount = Number.parseFloat(discountInput.value || "0");
        const advance = Number.parseFloat(advanceInput.value || "0");
        const subtotal = unitPrice * Math.max(quantity, 0);
        const safeDiscount = Math.min(Math.max(discount, 0), subtotal);
        const finalAmount = Math.max(subtotal - safeDiscount, 0);
        const safeAdvance = Math.min(Math.max(advance, 0), finalAmount);
        const pendingAmount = Math.max(finalAmount - safeAdvance, 0);

        subtotalOutput.textContent = formatCurrency(subtotal);
        discountOutput.textContent = formatCurrency(safeDiscount);
        finalOutput.textContent = formatCurrency(finalAmount);
        advanceOutput.textContent = formatCurrency(safeAdvance);
        pendingOutput.textContent = formatCurrency(pendingAmount);
    };

    [productSelect, quantityInput, discountInput, advanceInput].forEach((input) => {
        input.addEventListener("input", updatePreorderPreview);
        input.addEventListener("change", updatePreorderPreview);
    });

    updatePreorderPreview();
});
