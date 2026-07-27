// Relative path to your Flask backend
const API_BASE_URL = "/api";

const form = document.getElementById('search-form');
const input = document.getElementById('matric-input');
const btn = document.getElementById('search-btn');
const statusMsg = document.getElementById('status-message');
const errorMsg = document.getElementById('error-message');
const container = document.getElementById('reviews-container');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const matricNo = input.value.trim();
    if (!matricNo) return;

    // 1. Reset UI state
    errorMsg.style.display = 'none';
    container.innerHTML = '';
    statusMsg.style.display = 'block';
    statusMsg.textContent = `Fetching reviews for ${matricNo}...`;
    btn.disabled = true;

    try {
        // 2. Fetch data from Flask API route
        const response = await fetch(`${API_BASE_URL}/reviews?matric_no=${encodeURIComponent(matricNo)}`);

        if (!response.ok) {
            throw new Error(`Server error (${response.status})`);
        }

        const data = await response.json();
        statusMsg.style.display = 'none';

        if (!data.reviews || data.reviews.length === 0) {
            container.innerHTML = `<div class="empty-state">No reviews found for ${matricNo}.</div>`;
            return;
        }

        // 3. Display reviews
        data.reviews.forEach(reviewText => {
            const li = document.createElement('li');
            li.className = 'review-item';
            li.textContent = reviewText;
            container.appendChild(li);
        });

    } catch (error) {
        console.error("Fetch error:", error);
        statusMsg.style.display = 'none';
        errorMsg.style.display = 'block';
        errorMsg.textContent = `Could not load reviews: ${error.message}`;
    } finally {
        btn.disabled = false;
    }
});