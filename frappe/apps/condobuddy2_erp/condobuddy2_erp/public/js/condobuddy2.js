// CondoBuddy2 — Resident Portal
// Only runs on the resident portal page (guarded by .cb-portal), so it never
// interferes with the Frappe Desk admin UI.

(function () {
	'use strict';

	const root = document.querySelector('.cb-portal');
	if (!root) return; // Not the resident portal — bail out (e.g. on Frappe Desk).

	const state = { resident: null, data: null };

	/* ------------------------------------------------------------------ utils */
	function $(id) { return document.getElementById(id); }

	function esc(value) {
		if (value === null || value === undefined) return '';
		return String(value).replace(/[&<>"']/g, (c) => ({
			'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
		}[c]));
	}

	function csrfHeaders() {
		const headers = { 'Content-Type': 'application/json' };
		if (window.csrf_token) headers['X-Frappe-CSRF-Token'] = window.csrf_token;
		return headers;
	}

	function fmtDate(value) {
		if (!value) return '';
		const d = new Date(value.replace(' ', 'T'));
		if (isNaN(d)) return esc(value);
		return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) +
			(value.length > 10 ? ', ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) : '');
	}

	function fmtTime(value) {
		if (!value) return '';
		return String(value).slice(0, 5);
	}

	function toast(message, kind) {
		const wrap = $('cb-toasts');
		const el = document.createElement('div');
		el.className = 'cb-toast' + (kind ? ' cb-toast--' + kind : '');
		el.textContent = message;
		wrap.appendChild(el);
		setTimeout(() => {
			el.style.transition = 'opacity .3s';
			el.style.opacity = '0';
			setTimeout(() => el.remove(), 300);
		}, 3200);
	}

	/* ------------------------------------------------------------- navigation */
	function go(view) {
		document.querySelectorAll('.cb-view').forEach((s) =>
			s.classList.toggle('is-active', s.id === view));
		document.querySelectorAll('.cb-tab').forEach((t) =>
			t.classList.toggle('is-active', t.dataset.go === view));
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	function setupNav() {
		document.querySelectorAll('[data-go]').forEach((el) => {
			el.addEventListener('click', (e) => {
				e.preventDefault();
				go(el.dataset.go);
			});
		});
	}

	/* ------------------------------------------------------------------ badges */
	const STATUS_KIND = {
		// Visitors
		'Pre-registered': 'info', 'Checked In': 'success', 'Checked Out': 'neutral',
		'Expired': 'neutral', 'Denied': 'danger',
		// Bookings
		'Pending': 'warning', 'Approved': 'success', 'Rejected': 'danger',
		'Cancelled': 'neutral', 'Completed': 'neutral',
		// Packages
		'Received': 'warning', 'Notified': 'info', 'Picked Up': 'success', 'Returned': 'neutral'
	};

	function badge(status) {
		const kind = STATUS_KIND[status] || 'neutral';
		return `<span class="cb-badge cb-badge--${kind}">${esc(status || '—')}</span>`;
	}

	function empty(icon, text) {
		return `<div class="cb-empty"><span class="cb-empty-icon">${icon}</span>${esc(text)}</div>`;
	}

	function item(icon, title, sub, right) {
		return `<div class="cb-item">
			<div class="cb-item-icon">${icon}</div>
			<div class="cb-item-body">
				<div class="cb-item-title">${title}</div>
				<div class="cb-item-sub">${sub}</div>
			</div>
			${right || ''}
		</div>`;
	}

	/* --------------------------------------------------------------- rendering */
	function renderHeader(r) {
		if (!r) return;
		const name = r.name || 'Resident';
		$('cb-user-name').textContent = name;
		$('cb-user-unit').textContent = r.unit ? 'Unit ' + r.unit : '';
		$('cb-avatar').textContent = (name[0] || 'R').toUpperCase();
		$('cb-greeting').textContent = 'Hello, ' + (r.first_name || name.split(' ')[0]);
	}

	function renderHome(d) {
		const upcomingBookings = (d.bookings || []).filter((b) =>
			['Pending', 'Approved'].includes(b.status));
		const openPackages = (d.packages || []).filter((p) =>
			['Received', 'Notified'].includes(p.status));
		const expectedVisitors = (d.visitors || []).filter((v) =>
			['Pre-registered', 'Checked In'].includes(v.status));

		$('stat-visitors').textContent = expectedVisitors.length;
		$('stat-packages').textContent = openPackages.length;
		$('stat-bookings').textContent = upcomingBookings.length;

		const activity = [];
		(d.access_logs || []).slice(0, 3).forEach((a) => activity.push(
			item('🔑', esc(a.event_type) + (a.access_granted ? '' : ' (denied)'),
				`${esc(a.device_location || a.method || 'Access point')} · ${fmtDate(a.timestamp)}`)));
		(d.packages || []).slice(0, 2).forEach((p) => activity.push(
			item('📦', 'Package ' + esc(p.tracking_number),
				`${esc(p.carrier || 'Carrier')} · ${fmtDate(p.received_at)}`, badge(p.status))));

		$('home-activity').innerHTML = activity.length
			? activity.join('')
			: empty('🌤️', 'No recent activity yet.');
	}

	function renderVisitors(list) {
		const el = $('visitor-history');
		if (!list || !list.length) {
			el.innerHTML = empty('👋', 'No visitors yet. Pre-register one above.');
			return;
		}
		el.innerHTML = list.map((v) => {
			const sub = `${esc(v.visit_type)} · ${v.expected_arrival ? fmtDate(v.expected_arrival) : 'No arrival set'}`;
			const showPass = ['Pre-registered', 'Checked In'].includes(v.status);
			const action = showPass
				? `<button class="cb-item-action" data-pass="${esc(v.name)}" data-vname="${esc(v.visitor_name)}">Pass</button>`
				: badge(v.status);
			return item('👤', esc(v.visitor_name), sub, action);
		}).join('');

		el.querySelectorAll('[data-pass]').forEach((btn) => {
			btn.addEventListener('click', () => openPass(btn.dataset.pass, btn.dataset.vname));
		});
	}

	function renderPackages(list) {
		const el = $('packages-all');
		if (!list || !list.length) {
			el.innerHTML = empty('📭', 'No packages waiting for you.');
			return;
		}
		el.innerHTML = list.map((p) => item(
			'📦', esc(p.tracking_number),
			`${esc(p.carrier || 'Carrier')} · ${fmtDate(p.received_at)}`,
			badge(p.status))).join('');
	}

	function renderBookings(list) {
		const el = $('booking-history');
		if (!list || !list.length) {
			el.innerHTML = empty('📅', 'No bookings yet.');
			return;
		}
		el.innerHTML = list.map((b) => item(
			'📅', esc(b.facility),
			`${fmtDate(b.booking_date)} · ${fmtTime(b.start_time)}–${fmtTime(b.end_time)}`,
			badge(b.status))).join('');
	}

	function renderAccess(list) {
		const el = $('access-history');
		if (!list || !list.length) {
			el.innerHTML = empty('🔓', 'No access events recorded.');
			return;
		}
		el.innerHTML = list.map((a) => item(
			a.access_granted ? '🔑' : '⛔',
			esc(a.event_type) + (a.access_granted ? '' : ' · Denied'),
			`${esc(a.device_location || a.method || 'Access point')} · ${fmtDate(a.timestamp)}`)).join('');
	}

	/* ----------------------------------------------------------- access pass */
	function openPass(visitorId, visitorName) {
		const visitor = (state.data.visitors || []).find((v) => v.name === visitorId);
		const code = (visitor && visitor.qr_code) || visitorId;
		$('cb-modal-body').innerHTML = `
			<h3 class="cb-pass-title">Visitor Access Pass</h3>
			<p class="cb-pass-sub">${esc(visitorName || '')}</p>
			<div class="cb-qr">${monogram(code)}</div>
			<div class="cb-pass-code">${esc(code)}</div>
			<p class="cb-pass-hint">Share this pass with your visitor. They scan it at the
			lobby and elevator. It expires automatically after the visit.</p>`;
		$('cb-modal').hidden = false;
	}

	// Lightweight visual code block derived from the pass string. (A scannable
	// QR image can be generated server-side and dropped in here later.)
	function monogram(code) {
		let hash = 0;
		for (let i = 0; i < code.length; i++) hash = (hash * 31 + code.charCodeAt(i)) >>> 0;
		const cells = [];
		const size = 7;
		for (let i = 0; i < size * size; i++) {
			hash = (hash * 1103515245 + 12345) >>> 0;
			cells.push((hash >> 8) & 1);
		}
		const rects = cells.map((on, i) => on
			? `<rect x="${(i % size) * 26 + 6}" y="${Math.floor(i / size) * 26 + 6}" width="24" height="24" rx="4" fill="#1f2433"/>`
			: '').join('');
		return `<svg viewBox="0 0 194 194" xmlns="http://www.w3.org/2000/svg">${rects}</svg>`;
	}

	function setupModal() {
		$('cb-modal-close').addEventListener('click', () => { $('cb-modal').hidden = true; });
		$('cb-modal').addEventListener('click', (e) => {
			if (e.target.id === 'cb-modal') $('cb-modal').hidden = true;
		});
	}

	/* --------------------------------------------------------------- loaders */
	async function loadDashboard() {
		try {
			const res = await fetch('/api/method/condobuddy2_erp.api.api.get_resident_portal_data');
			const json = await res.json();
			const d = json.message;
			if (!d) {
				toast('Could not load your data. Please sign in.', 'error');
				return;
			}
			state.data = d;
			state.resident = d.resident;
			renderHeader(d.resident);
			renderHome(d);
			renderVisitors(d.visitors);
			renderPackages(d.packages);
			renderBookings(d.bookings);
			renderAccess(d.access_logs);
		} catch (e) {
			console.error('Dashboard load failed:', e);
			toast('Network error loading your data.', 'error');
		}
	}

	async function loadFacilities() {
		try {
			const res = await fetch('/api/resource/Facility?fields=["name","facility_name","facility_type"]&filters=[["status","=","Available"]]');
			const json = await res.json();
			const select = $('booking-facility');
			if (!select) return;
			const facilities = json.data || [];
			select.innerHTML = facilities.length
				? facilities.map((f) => `<option value="${esc(f.name)}">${esc(f.facility_name)} · ${esc(f.facility_type)}</option>`).join('')
				: '<option value="" disabled>No facilities available</option>';
		} catch (e) {
			console.error('Facilities load failed:', e);
		}
	}

	/* ----------------------------------------------------------------- forms */
	function setupForms() {
		const visitorForm = $('visitor-form');
		visitorForm.addEventListener('submit', async (e) => {
			e.preventDefault();
			const btn = visitorForm.querySelector('button[type="submit"]');
			btn.disabled = true;
			try {
				const res = await fetch('/api/method/condobuddy2_erp.api.api.create_visitor', {
					method: 'POST',
					headers: csrfHeaders(),
					body: JSON.stringify({
						visitor_name: $('visitor-name').value.trim(),
						visit_type: $('visitor-type').value,
						visitor_phone: $('visitor-phone').value.trim(),
						expected_arrival: $('visitor-arrival').value || null
					})
				});
				const json = await res.json();
				if (res.ok && json.message) {
					toast('Visitor registered — access pass ready.', 'success');
					visitorForm.reset();
					await loadDashboard();
					openPassFromResponse(json.message);
				} else {
					toast(extractError(json) || 'Could not register visitor.', 'error');
				}
			} catch (err) {
				toast('Network error: ' + err.message, 'error');
			} finally {
				btn.disabled = false;
			}
		});

		const bookingForm = $('booking-form');
		bookingForm.addEventListener('submit', async (e) => {
			e.preventDefault();
			const btn = bookingForm.querySelector('button[type="submit"]');
			btn.disabled = true;
			try {
				const res = await fetch('/api/method/condobuddy2_erp.api.api.create_booking', {
					method: 'POST',
					headers: csrfHeaders(),
					body: JSON.stringify({
						facility: $('booking-facility').value,
						booking_date: $('booking-date').value,
						start_time: $('booking-start').value,
						end_time: $('booking-end').value,
						purpose: $('booking-purpose').value.trim()
					})
				});
				const json = await res.json();
				if (res.ok && json.message) {
					toast('Booking requested successfully.', 'success');
					bookingForm.reset();
					await loadDashboard();
				} else {
					toast(extractError(json) || 'Could not create booking.', 'error');
				}
			} catch (err) {
				toast('Network error: ' + err.message, 'error');
			} finally {
				btn.disabled = false;
			}
		});
	}

	function openPassFromResponse(msg) {
		$('cb-modal-body').innerHTML = `
			<h3 class="cb-pass-title">Visitor Access Pass</h3>
			<p class="cb-pass-sub">${esc(msg.visitor_name || '')}</p>
			<div class="cb-qr">${monogram(msg.qr_code || msg.visitor_id)}</div>
			<div class="cb-pass-code">${esc(msg.qr_code || msg.visitor_id)}</div>
			<p class="cb-pass-hint">Share this pass with your visitor. They scan it at the
			lobby and elevator. It expires automatically after the visit.</p>`;
		$('cb-modal').hidden = false;
	}

	function extractError(json) {
		if (!json) return '';
		if (json._server_messages) {
			try {
				const msgs = JSON.parse(json._server_messages);
				if (msgs.length) return JSON.parse(msgs[0]).message;
			} catch (e) { /* ignore */ }
		}
		return json.message || json.exc_type || '';
	}

	/* ------------------------------------------------------------------ init */
	function init() {
		setupNav();
		setupModal();
		setupForms();
		loadDashboard();
		loadFacilities();
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
