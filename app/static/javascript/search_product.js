document.getElementById('search_input').addEventListener('submit', function (event) {
        event.preventDefault()
        const inputElement = event.target.querySelector('input[type="search"]'); // Tìm ô input trong form
        const query = inputElement.value.trim()
        const queryString = new URLSearchParams(window.location.search);
        if (query.trim()) {
            queryString.set('query', query);
        } else {
            queryString.delete('query');
        }
        const newUrl = query ? `?query=${encodeURIComponent(query)}` : '?';
        window.history.pushState(null, '', newUrl);
        location.reload()
    })