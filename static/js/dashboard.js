/* dashboard.js - Logic for the Analytics Dashboard */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Data Parsing
    const placesDataInput = document.getElementById('places-data');
    if (!placesDataInput) return;
    
    let allPlaces = [];
    try {
        const rawData = placesDataInput.value;
        allPlaces = JSON.parse(rawData);
        
        // Pre-calculate Average Rating for each place if it has visits
        allPlaces.forEach(p => {
            const ratings = (p.visits || []).map(v => v.rating).filter(r => r != null);
            p.average_rating = ratings.length > 0 ? ratings.reduce((a, b) => a + b, 0) / ratings.length : 0;
        });
        
        if (allPlaces.length > 0) {
            console.log("Dashboard: Sample data structure:", allPlaces[0]);
        }
        console.log("Dashboard: Loaded", allPlaces.length, "places");
    } catch (e) {
        console.error("Dashboard: Error parsing places data:", e);
        return;
    }
    
    let filteredPlaces = [...allPlaces];

    // 2. Chart Instances
    let visitTimelineChart, categoryBreakdownChart, ratingProfileChart, statusOverviewChart, tagLandscapeChart;

    // 3. UI Elements
    const dateRangePreset = document.getElementById('date-range-preset');
    const customDatePickerInput = document.getElementById('custom-date-picker');
    const completedOnlyCheckbox = document.getElementById('completed-visits-only');
    const categoryFilter = document.getElementById('category-filter');
    const minRatingRange = document.getElementById('min-rating');
    const ratingValue = document.getElementById('rating-value');
    
    const statTotalPlaces = document.getElementById('stat-total-places');
    const statVisitedTotal = document.getElementById('stat-visited-total');

    // 4. Initialize Filters
    function initFilters() {
        // Load from URL
        const params = new URLSearchParams(window.location.search);
        if (params.has('date')) dateRangePreset.value = params.get('date');
        if (params.has('cat')) categoryFilter.value = params.get('cat');
        if (params.has('completed')) completedOnlyCheckbox.checked = params.get('completed') === 'true';
        if (params.has('rating')) {
            minRatingRange.value = params.get('rating');
            ratingValue.textContent = params.get('rating') + '+';
        }

        // Populate Categories
        const categories = [...new Set(allPlaces.map(p => p.category))].filter(Boolean).sort();
        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
            categoryFilter.appendChild(option);
        });

        // Initialize Custom Date Picker
        const fp = flatpickr(customDatePickerInput, {
            mode: "range",
            dateFormat: "Y-m-d",
            onClose: (selectedDates) => {
                if (selectedDates.length === 2) {
                    updateDashboard();
                }
            }
        });

        if (dateRangePreset.value === 'custom') {
            customDatePickerInput.style.display = 'block';
        }

        // Event Listeners
        dateRangePreset.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                customDatePickerInput.style.display = 'block';
            } else {
                customDatePickerInput.style.display = 'none';
                updateDashboard();
            }
        });

        completedOnlyCheckbox.addEventListener('change', updateDashboard);
        categoryFilter.addEventListener('change', updateDashboard);
        minRatingRange.addEventListener('input', (e) => {
            ratingValue.textContent = e.target.value + '+';
            updateDashboard();
        });
    }

    function updateURL() {
        const params = new URLSearchParams();
        params.set('date', dateRangePreset.value);
        params.set('cat', categoryFilter.value);
        params.set('rating', minRatingRange.value);
        params.set('completed', completedOnlyCheckbox.checked);
        const newURL = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, '', newURL);
    }

    function getFilterRange() {
        const preset = dateRangePreset.value;
        const now = new Date();
        const completedOnly = completedOnlyCheckbox.checked;
        
        let start = new Date(now.getTime());
        let end = new Date(now.getTime());

        if (preset === 'last-7-days') {
            start.setDate(now.getDate() - 7);
        } else if (preset === 'last-30-days') {
            start.setDate(now.getDate() - 30);
        } else if (preset === 'last-month') {
            start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            end = new Date(now.getFullYear(), now.getMonth(), 0);
            end.setHours(23, 59, 59, 999);
        } else if (preset === 'last-12-months') {
            start.setFullYear(now.getFullYear() - 1);
        } else if (preset === 'this-year') {
            start = new Date(now.getFullYear(), 0, 1);
            end = new Date(now.getFullYear(), 11, 31, 23, 59, 59, 999);
        } else if (preset === 'last-year') {
            start = new Date(now.getFullYear() - 1, 0, 1);
            end = new Date(now.getFullYear() - 1, 11, 31, 23, 59, 59);
        } else if (preset === 'custom') {
            const dates = customDatePickerInput._flatpickr.selectedDates;
            if (dates.length === 2) {
                start = dates[0];
                end = new Date(dates[1]);
                end.setHours(23, 59, 59, 999);
            }
        } else if (preset === 'all') {
            start = new Date(0);
            end = new Date(2099, 11, 31);
        }

        // Clamp to TODAY if only showing completed visits
        if (completedOnly) {
            const todayEnd = new Date(now.getTime());
            todayEnd.setHours(23, 59, 59, 999);
            if (end > todayEnd) {
                end = todayEnd;
            }
        }

        return { start, end };
    }

    function isVisitInRange(visit, range) {
        const dateStr = visit.visit_datetime || visit.created_at;
        if (!dateStr) return false;
        const d = new Date(dateStr);
        return d >= range.start && d <= range.end;
    }

    // 5. Filtering Logic
    function applyFilters() {
        const categorySelection = categoryFilter.value;
        const minRating = parseFloat(minRatingRange.value);
        const range = getFilterRange();
        const completedOnly = completedOnlyCheckbox.checked;
        
        filteredPlaces = allPlaces.filter(p => {
            // Category Filter
            if (categorySelection !== 'all' && p.category !== categorySelection) return false;
            
            // Rating Filter (Place level average)
            if (p.average_rating < minRating) return false;

            // Date & Completion Filter
            const visits = p.visits || [];
            
            if (completedOnly) {
                // Must have at least one visit matching the range
                if (visits.length === 0) return false;
                if (dateRangePreset.value !== 'all') {
                    return visits.some(v => isVisitInRange(v, range));
                }
            } else {
                // If no visits, use creation date
                if (visits.length === 0) {
                    return isVisitInRange({ visit_datetime: p.created_at }, range);
                }
                // If has visits, check if any (or all, but user implies any/separate entries) match
                if (dateRangePreset.value !== 'all') {
                    return visits.some(v => isVisitInRange(v, range));
                }
            }
            
            return true;
        });
    }

    // 6. Chart Rendering
    function updateCharts() {
        const ctxTimeline = document.getElementById('chart-visit-timeline');
        const ctxCategory = document.getElementById('chart-category-breakdown');
        const ctxRating = document.getElementById('chart-rating-profile');
        const ctxStatus = document.getElementById('chart-status-overview');
        const ctxTags = document.getElementById('chart-tag-landscape');

        if (!ctxTimeline || !ctxCategory || !ctxRating) return;

        // Shared Theme
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = "'Outfit', sans-serif";

        const range = getFilterRange();
        const colors = [
            '#6366f1', '#a855f7', '#ec4899', '#f43f5e', 
            '#ef4444', '#f59e0b', '#10b981', '#06b6d4'
        ];

        // --- Visit Velocity ---
        const visitsByMonth = {};
        const completedOnly = completedOnlyCheckbox.checked;
        
        filteredPlaces.forEach(p => {
            const visits = p.visits || [];
            if (visits.length > 0) {
                visits.forEach(v => {
                    if (isVisitInRange(v, range)) {
                        const month = v.visit_datetime.substring(0, 7);
                        visitsByMonth[month] = (visitsByMonth[month] || 0) + 1;
                    }
                });
            } else if (!completedOnly) {
                // Place with no visits, use creation date
                if (isVisitInRange({ visit_datetime: p.created_at }, range)) {
                    const month = p.created_at.substring(0, 7);
                    visitsByMonth[month] = (visitsByMonth[month] || 0) + 1;
                }
            }
        });
        const sortedMonths = Object.keys(visitsByMonth).sort();
        const tileTimeline = document.getElementById('tile-visit-timeline');
        
        if (sortedMonths.length === 0) {
            if (tileTimeline) tileTimeline.style.display = 'none';
        } else {
            if (tileTimeline) tileTimeline.style.display = 'flex';
            if (visitTimelineChart) visitTimelineChart.destroy();
            visitTimelineChart = new Chart(ctxTimeline, {
                type: 'bar',
                data: {
                    labels: sortedMonths,
                    datasets: [{
                        label: 'Activity',
                        data: sortedMonths.map(m => visitsByMonth[m]),
                        backgroundColor: 'rgba(99, 102, 241, 0.4)',
                        borderColor: '#6366f1',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        // --- Category Palette ---
        const catCounts = {};
        filteredPlaces.forEach(p => {
            if (p.category) catCounts[p.category] = (catCounts[p.category] || 0) + 1;
        });
        
        const tileCategory = document.getElementById('tile-category-breakdown');
        if (Object.keys(catCounts).length === 0) {
            if (tileCategory) tileCategory.style.display = 'none';
        } else {
            if (tileCategory) tileCategory.style.display = 'flex';
            if (categoryBreakdownChart) categoryBreakdownChart.destroy();
            categoryBreakdownChart = new Chart(ctxCategory, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(catCounts).map(c => c.charAt(0).toUpperCase() + c.slice(1)),
                    datasets: [{
                        data: Object.values(catCounts),
                        backgroundColor: colors,
                        hoverOffset: 10,
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '75%',
                    plugins: {
                        legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true } }
                    }
                }
            });
        }

        // --- Rating Profile ---
        const catRatings = {};
        filteredPlaces.forEach(p => {
            const ratings = (p.visits || [])
                .filter(v => isVisitInRange(v, range))
                .map(v => v.rating)
                .filter(r => r != null);
                
            if (ratings.length > 0) {
                const avgRating = ratings.reduce((a, b) => a + b, 0) / ratings.length;
                if (!catRatings[p.category]) catRatings[p.category] = { sum: 0, count: 0 };
                catRatings[p.category].sum += avgRating;
                catRatings[p.category].count += 1;
            }
        });

        const labels = Object.keys(catRatings).map(c => c.charAt(0).toUpperCase() + c.slice(1));
        const ratingsData = Object.keys(catRatings).map(l => catRatings[l].sum / catRatings[l].count);
        const tileRating = document.getElementById('tile-rating-profile');

        if (labels.length < 3) {
            // Radar charts look better with 3+ points. If not, maybe show/hide or use Bar
            if (tileRating) tileRating.style.display = 'none';
        } else {
            if (tileRating) tileRating.style.display = 'flex';
            if (ratingProfileChart) ratingProfileChart.destroy();
            ratingProfileChart = new Chart(ctxRating, {
                type: 'radar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Average Rating',
                        data: ratingsData,
                        backgroundColor: 'rgba(217, 70, 239, 0.2)',
                        borderColor: '#d946ef',
                        pointBackgroundColor: '#d946ef',
                        borderWidth: 2
                    }]
                },
                options: { 
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            min: 0,
                            max: 5,
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            angleLines: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { display: false },
                            pointLabels: { color: '#94a3b8', font: { size: 12 } }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        // --- Status Overview ---
        const statusCounts = {};
        filteredPlaces.forEach(p => {
            statusCounts[p.status] = (statusCounts[p.status] || 0) + 1;
        });

        const tileStatus = document.getElementById('tile-status-overview');
        if (Object.keys(statusCounts).length === 0) {
            if (tileStatus) tileStatus.style.display = 'none';
        } else {
            if (tileStatus) tileStatus.style.display = 'flex';
            if (statusOverviewChart) statusOverviewChart.destroy();
            statusOverviewChart = new Chart(ctxStatus, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(statusCounts).map(s => s.replace(/_/g, ' ').charAt(0).toUpperCase() + s.replace(/_/g, ' ').slice(1)),
                    datasets: [{
                        data: Object.values(statusCounts),
                        backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#ef4444'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 15 } }
                    }
                }
            });
        }

        // --- Tag Landscape ---
        const tagCounts = {};
        filteredPlaces.forEach(p => {
            (p.tags || []).forEach(t => {
                tagCounts[t.name] = (tagCounts[t.name] || 0) + 1;
            });
        });

        const topTags = Object.entries(tagCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8);

        const tileTags = document.getElementById('tile-tag-landscape');
        if (topTags.length === 0) {
            if (tileTags) tileTags.style.display = 'none';
        } else {
            if (tileTags) tileTags.style.display = 'flex';
            if (tagLandscapeChart) tagLandscapeChart.destroy();
            tagLandscapeChart = new Chart(ctxTags, {
                type: 'bar',
                data: {
                    labels: topTags.map(t => t[0]),
                    datasets: [{
                        label: 'Count',
                        data: topTags.map(t => t[1]),
                        backgroundColor: 'rgba(6, 182, 212, 0.4)',
                        borderColor: '#06b6d4',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { stepSize: 1 } },
                        y: { grid: { display: false } }
                    }
                }
            });
        }
    }

    function updateStats() {
        if (statTotalPlaces) statTotalPlaces.textContent = filteredPlaces.length;
        const range = getFilterRange();
        const visitedCount = filteredPlaces.filter(p => 
            (p.visits || []).some(v => isVisitInRange(v, range))
        ).length;
        if (statVisitedTotal) statVisitedTotal.textContent = visitedCount;
    }

    function updateGallery() {
        const galleryContainer = document.getElementById('gallery-carousel-inner');
        const tileGallery = document.getElementById('tile-photo-landscape');
        if (!galleryContainer || !tileGallery) return;

        const photos = [];
        const range = getFilterRange();
        
        filteredPlaces.forEach(p => {
            (p.visits || []).forEach(v => {
                if (!isVisitInRange(v, range)) return;

                let mainPhotoUrl = null;
                
                // 1. Try to find the photo marked as 'is_main'
                const mainPhoto = (v.photos || []).find(photo => photo.is_main);
                if (mainPhoto) {
                    mainPhotoUrl = mainPhoto.image_url || mainPhoto.url;
                }
                
                // 2. Fallback to the first photo in the array
                if (!mainPhotoUrl && (v.photos || []).length > 0) {
                    const firstPhoto = v.photos[0];
                    mainPhotoUrl = firstPhoto.image_url || firstPhoto.url;
                }
                
                // 3. Fallback to legacy image_url
                if (!mainPhotoUrl && v.image_url) {
                    mainPhotoUrl = v.image_url;
                }

                if (mainPhotoUrl) {
                    photos.push({
                        url: mainPhotoUrl,
                        place: p.name,
                        date: v.visit_datetime ? new Date(v.visit_datetime).toLocaleDateString() : 'N/A',
                        placeId: p.id,
                        visitId: v.id
                    });
                }
            });
        });

        if (photos.length === 0) {
            console.log("Dashboard: No photos found for gallery filtering.");
            tileGallery.style.display = 'none';
            return;
        }

        console.log("Dashboard: Found", photos.length, "photos for gallery.");

        tileGallery.style.display = 'flex';
        galleryContainer.innerHTML = '';
        
        photos.forEach((photo, index) => {
            const slide = document.createElement('div');
            slide.className = `gallery-slide ${index === 0 ? 'active' : ''}`;
            slide.innerHTML = `
                <img src="${photo.url}" alt="${photo.place}">
                <div class="gallery-caption">
                    <div class="caption-info">
                        <strong>${photo.place}</strong>
                        <span>${photo.date}</span>
                    </div>
                    <button class="view-visit-link" onclick="openVisitModal('${photo.placeId}', '${photo.visitId}')">
                        View Visit <i class="fas fa-external-link-alt"></i>
                    </button>
                </div>
            `;
            galleryContainer.appendChild(slide);
        });

        // Simple carousel auto-play or manual navigation could be added here
        // For now, let's just show them and add basic nav logic if needed
        let currentSlide = 0;
        const slides = galleryContainer.querySelectorAll('.gallery-slide');
        
        if (slides.length > 1) {
            const prevBtn = document.getElementById('gallery-prev');
            const nextBtn = document.getElementById('gallery-next');
            
            const showSlide = (n) => {
                slides[currentSlide].classList.remove('active');
                currentSlide = (n + slides.length) % slides.length;
                slides[currentSlide].classList.add('active');
            };

            if (prevBtn) prevBtn.onclick = () => showSlide(currentSlide - 1);
            if (nextBtn) nextBtn.onclick = () => showSlide(currentSlide + 1);
        }
    }

    // --- Modal Handling ---
    const modal = document.getElementById('dashboard-visit-modal');
    const closeBtn = document.getElementById('close-dashboard-modal');
    let modalSlideIndex = 0;

    window.openVisitModal = function(placeId, visitId) {
        const place = allPlaces.find(p => p.id == placeId);
        if (!place) return;
        
        const visit = (place.visits || []).find(v => v.id == visitId);
        if (!visit) return;

        // Populate Modal
        document.getElementById('modal-place-name').textContent = place.name;
        document.getElementById('modal-visit-date').innerHTML = `<i class="fas fa-calendar-alt"></i> ${new Date(visit.visit_datetime).toLocaleDateString()}`;
        document.getElementById('modal-review-title').textContent = visit.review_title || 'No Title';
        document.getElementById('modal-review-text').textContent = visit.review_text || 'No review text provided.';
        
        // Rating Stars
        const ratingDisplay = document.getElementById('modal-rating-display');
        ratingDisplay.innerHTML = '';
        const rating = parseInt(visit.rating) || 0;
        for (let i = 1; i <= 5; i++) {
            const star = document.createElement('i');
            star.className = `${i <= rating ? 'fas' : 'far'} fa-star`;
            ratingDisplay.appendChild(star);
        }

        // Carousel Photos
        const carousel = document.getElementById('modal-carousel');
        const carouselInner = document.getElementById('modal-carousel-inner');
        const dotsContainer = document.getElementById('modal-dots');
        carouselInner.innerHTML = '';
        dotsContainer.innerHTML = '';
        modalSlideIndex = 0;

        const photos = [];
        (visit.photos || []).forEach(p => photos.push(p.image_url || p.url));
        if (photos.length === 0 && visit.image_url) photos.push(visit.image_url);

        if (photos.length > 0) {
            carousel.style.display = 'block';
            photos.forEach((url, idx) => {
                const img = document.createElement('img');
                img.src = url;
                carouselInner.appendChild(img);

                const dot = document.createElement('span');
                dot.className = `dot ${idx === 0 ? 'active' : ''}`;
                dot.onclick = () => goToModalSlide(idx);
                dotsContainer.appendChild(dot);
            });
            updateModalCarousel();
        } else {
            carousel.style.display = 'none';
        }

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };

    function updateModalCarousel() {
        const inner = document.getElementById('modal-carousel-inner');
        inner.style.transform = `translateX(-${modalSlideIndex * 100}%)`;
        
        const dots = document.querySelectorAll('#modal-dots .dot');
        dots.forEach((dot, idx) => {
            dot.classList.toggle('active', idx === modalSlideIndex);
        });
    }

    function goToModalSlide(n) {
        const inner = document.getElementById('modal-carousel-inner');
        const total = inner.children.length;
        if (total === 0) return;
        modalSlideIndex = (n + total) % total;
        updateModalCarousel();
    }

    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        };
    }

    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    };

    document.getElementById('modal-prev').onclick = () => goToModalSlide(modalSlideIndex - 1);
    document.getElementById('modal-next').onclick = () => goToModalSlide(modalSlideIndex + 1);

    function updateDashboard() {
        applyFilters();
        updateCharts();
        updateStats();
        updateGallery();
        updateURL();
    }

    // Initialize
    initFilters();
    updateDashboard();
});
