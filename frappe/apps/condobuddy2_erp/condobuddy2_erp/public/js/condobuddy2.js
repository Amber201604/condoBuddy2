// CondoBuddy2 — Resident Portal JS

(function() {
	'use strict';

	const API_BASE = '';

	function init() {
		setupNav();
		loadDashboard();
		loadFacilities();
		setupForms();
	}

	function setupNav() {
		const navItems = document.querySelectorAll('.cb-nav-item');
		navItems.forEach(item => {
			item.addEventListener('click', (e) => {
				e.preventDefault();
				navItems.forEach(n => n.classList.remove('active'));
				item.classList.add('active');
				
				const target = item.getAttribute('href').slice(1);
				document.querySelectorAll('.cb-section').forEach(s => s.classList.remove('active'));
				document.getElementById(target).classList.add('active');
				
				if (target === 'cctv') loadCCTV();
			});
		});
	}

	async function loadDashboard() {
		try {
			const res = await fetch(`${API_BASE}/api/method/condobuddy2_erp.api.api.get_resident_portal_data`);
			const data = await res.json();
			if (!data.message) return;
			
			const d = data.message;
			renderList('bookings-list', d.bookings, b => 
				`${b.facility} — ${b.booking_date} ${b.start_time} (${b.status})`);
			renderList('visitors-list', d.visitors, v => 
				`${v.visitor_name} — ${v.visit_type} (${v.status})`);
			renderList('packages-list', d.packages, p => 
				`${p.tracking_number} — ${p.carrier} (${p.status})`);
			renderList('alerts-list', d.alerts, a => 
				`${a.camera_location} — ${a.event_type}`);
		} catch (e) {
			console.error('Dashboard load failed:', e);
		}
	}

	function renderList(id, items, formatter) {
		const el = document.getElementById(id);
		if (!el) return;
		if (!items || items.length === 0) {
			el.innerHTML = '<p class="cb-empty">No items</p>';
			return;
		}
		el.innerHTML = items.map(item => 
			`<div class="cb-list-item">${formatter(item)}</div>`
		).join('');
	}

	async function loadFacilities() {
		try {
			const res = await fetch(`${API_BASE}/api/resource/Facility?fields=["name","facility_name","facility_type"]`);
			const data = await res.json();
			const select = document.getElementById('booking-facility');
			if (!select || !data.data) return;
			select.innerHTML = data.data.map(f => 
				`<option value="${f.name}">${f.facility_name} (${f.facility_type})</option>`
			).join('');
		} catch (e) {
			console.error('Facilities load failed:', e);
		}
	}

	async function loadCCTV() {
		try {
			const res = await fetch(`${API_BASE}/api/method/condobuddy2_erp.api.api.get_cctv_feeds`);
			const data = await res.json();
			const el = document.getElementById('cctv-feeds');
			if (!el) return;
			const feeds = data.message?.feeds || [];
			if (feeds.length === 0) {
				el.innerHTML = '<p>No CCTV feeds available</p>';
				return;
			}
			el.innerHTML = feeds.map(f => 
				`<div class="cb-cctv-feed">${f.name}<br><small>${f.location}</small></div>`
			).join('');
		} catch (e) {
			console.error('CCTV load failed:', e);
		}
	}

	function setupForms() {
		// Booking form
		const bookingForm = document.getElementById('booking-form');
		if (bookingForm) {
			bookingForm.addEventListener('submit', async (e) => {
				e.preventDefault();
				const payload = {
					facility: document.getElementById('booking-facility').value,
					booking_date: document.getElementById('booking-date').value,
					start_time: document.getElementById('booking-start').value,
					end_time: document.getElementById('booking-end').value,
					purpose: document.getElementById('booking-purpose').value
				};
				try {
					const res = await fetch(`${API_BASE}/api/resource/Facility Booking`, {
						method: 'POST',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify(payload)
					});
					if (res.ok) {
						alert('Booking created!');
						loadDashboard();
					} else {
						const err = await res.json();
						alert('Booking failed: ' + (err.message || 'Unknown error'));
					}
				} catch (e) {
					alert('Network error: ' + e.message);
				}
			});
		}

		// Visitor form
		const visitorForm = document.getElementById('visitor-form');
		if (visitorForm) {
			visitorForm.addEventListener('submit', async (e) => {
				e.preventDefault();
				const payload = {
					visitor_name: document.getElementById('visitor-name').value,
					visitor_phone: document.getElementById('visitor-phone').value,
					visit_type: document.getElementById('visitor-type').value,
					expected_arrival: document.getElementById('visitor-arrival').value
				};
				try {
					const res = await fetch(`${API_BASE}/api/method/condobuddy2_erp.api.api.create_visitor`, {
						method: 'POST',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify(payload)
					});
					if (res.ok) {
						alert('Visitor registered!');
						loadDashboard();
					} else {
						const err = await res.json();
						alert('Registration failed: ' + (err.message || 'Unknown error'));
					}
				} catch (e) {
					alert('Network error: ' + e.message);
				}
			});
		}
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
