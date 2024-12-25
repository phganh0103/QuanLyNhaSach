document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function () {
            const bookId = this.getAttribute('data-book-id');
            const bookPrice = this.getAttribute('data-book-price');
            const quantityInput = document.querySelector('#typeNumber');
            let quantity = quantityInput ? parseInt(quantityInput.value) : 1;

            if (isNaN(quantity) || quantity < 1) {
                quantity = 1;
            }

            const body = new URLSearchParams({
                quantity: quantity,
                book_id: bookId,
            }).toString();

            fetch('/cart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: body
            })
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    } else {
                        throw new Error('Không thể thêm vào giỏ hàng!');
                    }
                })
                .then(data => {
                    alert(data.message)
                    if (data.success){
                        location.reload()
                    }
                })
                .catch(error => {
                    console.error(error);
                    alert('Có lỗi xảy ra khi thêm vào giỏ hàng.');
                });
        });
    });
});
