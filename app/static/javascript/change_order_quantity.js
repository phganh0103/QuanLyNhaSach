document.addEventListener('DOMContentLoaded', function () {
    const quantityInputs = document.querySelectorAll('#typeNumber');
    let debounceTimer;

    quantityInputs.forEach(input => {
        input.addEventListener('input', function (event) {
            const quantityInput = event.target;
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const newQuantity = parseInt(quantityInput.value);

                if (isNaN(newQuantity) || newQuantity < 1) {
                    quantityInput.value = 1;
                }

                changeQuantity(quantityInput);
            }, 500);
        });
    });
});

function changeQuantity(inputElement) {
    const newQuantity = parseInt(inputElement.value);
    const cartDetailId = inputElement.getAttribute('cart_detail_id');

    fetch('/update-cart', {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            product_in_cart_id: cartDetailId,
            quantity: newQuantity,
        }),
    })
        .then(response => {
            console.log(response)
            if (response.ok) {
                return response.json();
            } else {
                return response.json().then(errorData => {
                    throw new Error(errorData.message);
                });
            }
        })
        .then(data => {
            console.log(data.message);
            location.reload();
        })
        .catch(error => {
            console.error(error);
            alert(error);
        });
}