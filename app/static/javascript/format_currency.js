document.addEventListener('DOMContentLoaded', () => {
    const priceElements = document.querySelectorAll('.price');
    priceElements.forEach(priceElement => {
        const rawPrice = parseFloat(priceElement.getAttribute('data-price'));
        if (!isNaN(rawPrice)) {
            // Format số với dấu phân cách hàng nghìn
            const formattedPrice = new Intl.NumberFormat('vi-VN', {
                minimumFractionDigits: 0
            }).format(rawPrice);

            // Thêm "VND" vào cuối
            priceElement.textContent = `${formattedPrice} VND`;
        }
    });
});
