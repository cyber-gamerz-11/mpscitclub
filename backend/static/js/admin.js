// Admin Command Center Logic
let allEcMembers = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchStats();
    loadAllData();

    // Navigation Logic
    const menuItems = document.querySelectorAll('.sidebar-menu li');
    const sections = document.querySelectorAll('.dash-section');

    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const link = item.querySelector('a');
            if (!link || link.getAttribute('href') === '/') return;
            
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);

            menuItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            sections.forEach(sec => {
                sec.style.display = sec.id === `${targetId}-section` ? 'block' : 'none';
            });
        });
    });

    // Form Submissions
    handleAdminForm('add-event-form', '/admin/add_event');
    handleAdminForm('add-program-form', '/admin/add_program');
    handleAdminForm('add-ec-form', '/admin/ec/add');
    handleAdminForm('add-gallery-form', '/admin/gallery/add');

    const offlineForm = document.getElementById('offline-payment-form');
    if (offlineForm) {
        offlineForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = offlineForm.querySelector('button[type="submit"]');
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner"></span>Saving...`;
            
            try {
                const formData = new FormData(offlineForm);
                const dataObj = {};
                formData.forEach((value, key) => { dataObj[key] = value; });
                
                const res = await fetch('/admin/api/add_offline_payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dataObj)
                });
                
                if (res.ok) {
                    window.showToast('Offline record saved successfully!', 'success');
                    offlineForm.reset();
                    toggleModal('offline-payment-modal');
                    fetchVerifiedPayments();
                    fetchStats();
                } else {
                    const err = await res.json();
                    window.showToast(err.error || 'Server Error', 'error');
                }
            } catch (err) {
                window.showToast('Network Error', 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    }
});

async function fetchStats() {
    const res = await fetch('/admin/stats');
    const data = await res.json();
    document.getElementById('stat-members').innerText = data.total_users;
    document.getElementById('stat-events').innerText = data.total_events;
    document.getElementById('stat-payments').innerText = `${data.total_revenue} BDT`;
}

async function loadAllData() {
    const res = await fetch('/admin/api/all_data');
    const data = await res.json();

    // Render Events
    const eventsList = document.getElementById('events-list');
    eventsList.innerHTML = data.events.map(ev => `
        <tr>
            <td>${ev.title}</td>
            <td>${ev.date}</td>
            <td>${ev.venue}</td>
            <td>
                <button class="action-btn delete-btn" onclick="deleteItem('events', '${ev.id}')">Delete</button>
            </td>
        </tr>
    `).join('');

    // Render Programs
    const programsList = document.getElementById('programs-list');
    programsList.innerHTML = data.programs.map(pg => `
        <tr>
            <td><img src="${pg.banner || 'https://via.placeholder.com/50'}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;"></td>
            <td>${pg.title}</td>
            <td>${pg.date || 'N/A'}</td>
            <td>${pg.description ? pg.description.substring(0, 40) + '...' : ''}</td>
            <td>
                <button class="action-btn delete-btn" onclick="deleteItem('programs', '${pg.id}')">Delete</button>
            </td>
        </tr>
    `).join('');

    // Render Users
    const usersList = document.getElementById('users-list');
    usersList.innerHTML = data.users.map(u => `
        <tr>
            <td>${u.full_name}</td>
            <td>${u.email}</td>
            <td><span class="role-badge role-${u.role}">${u.role}</span></td>
            <td>
                <select onchange="updateRole('${u.id}', this.value)" class="action-btn">
                    <option value="member" ${u.role === 'member' ? 'selected' : ''}>Member</option>
                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                    <option value="ec" ${u.role === 'ec' ? 'selected' : ''}>EC</option>
                </select>
            </td>
        </tr>
    `).join('');

    // Render Payments
    fetchPendingPayments();
    fetchVerifiedPayments();

    // Render EC
    allEcMembers = data.ec_members;
    updateYearDropdownOptions();
    renderECList();

    // Render Gallery
    const galleryList = document.getElementById('gallery-list');
    galleryList.innerHTML = data.gallery.map(img => `
        <tr>
            <td><img src="${img.url}" style="width: 50px; border-radius: 4px;"></td>
            <td>${img.caption || 'No Caption'}</td>
            <td>${img.category}</td>
            <td>
                <button class="action-btn delete-btn" onclick="deleteItem('gallery', '${img.id}')">Remove</button>
            </td>
        </tr>
    `).join('');
}

async function fetchPendingPayments() {
    const res = await fetch('/payments/all_pending');
    const data = await res.json();
    const list = document.getElementById('payments-list');
    list.innerHTML = data.map(p => `
        <tr>
            <td>${p.member_id}</td>
            <td>${p.ref_email}</td>
            <td>${p.transaction_id}</td>
            <td>
                <button class="action-btn" onclick="verifyPayment('${p.id}', 'approved')" style="border-color: var(--emerald-green);">Approve</button>
                <button class="action-btn delete-btn" onclick="verifyPayment('${p.id}', 'rejected')">Reject</button>
            </td>
        </tr>
    `).join('');
}

async function verifyPayment(id, status) {
    const res = await fetch('/payments/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, status: status })
    });
    if (res.ok) {
        window.showToast(`Payment ${status}`, 'success');
        fetchPendingPayments();
        fetchVerifiedPayments();
    }
}

async function fetchVerifiedPayments() {
    try {
        const res = await fetch('/admin/api/verified_payments');
        if (!res.ok) throw new Error('Failed to fetch');
        const data = await res.json();
        
        const list = document.getElementById('verified-payments-list');
        if (!list) return;

        if (data.length === 0) {
            list.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--soft-gray);">No verified records found.</td></tr>';
            return;
        }

        list.innerHTML = data.map(p => {
            const d = new Date(p.date_verified);
            const dateStr = isNaN(d) ? (p.date_verified || '—') : d.toLocaleDateString();
            const name    = p.member_name   || '—';
            const phone   = p.phone         || '—';
            const event   = p.event_name    || '—';
            return `
            <tr>
                <td>${name}</td>
                <td>${phone}</td>
                <td>${event}</td>
                <td>${dateStr}</td>
                <td><button class="action-btn delete-btn" onclick="deleteVerifiedPayment('${p.payment_id}')">Delete</button></td>
            </tr>
            `;
        }).join('');
    } catch (err) {
        console.error(err);
        const list = document.getElementById('verified-payments-list');
        if (list) list.innerHTML = '<tr><td colspan="5" style="text-align:center; color: #ff4d4d;">Failed to load records.</td></tr>';
    }
}

async function deleteVerifiedPayment(paymentId) {
    if (!confirm('Delete this payment record permanently?')) return;
    try {
        const res = await fetch(`/admin/api/delete_payment/${paymentId}`, { method: 'DELETE' });
        if (res.ok) {
            window.showToast('Record deleted', 'success');
            fetchVerifiedPayments();
        } else {
            const err = await res.json();
            window.showToast(err.error || 'Failed to delete', 'error');
        }
    } catch (e) {
        window.showToast('Network error', 'error');
    }
}

async function deleteAllVerifiedPayments() {
    if (!confirm('Delete ALL verified payment records permanently? This cannot be undone.')) return;
    try {
        const res = await fetch('/admin/api/delete_all_payments', { method: 'DELETE' });
        if (res.ok) {
            window.showToast('All records deleted', 'success');
            fetchVerifiedPayments();
        } else {
            const err = await res.json();
            window.showToast(err.error || 'Failed to delete all', 'error');
        }
    } catch (e) {
        window.showToast('Network error', 'error');
    }
}

async function deleteItem(collection, id) {
    if (!confirm('Are you sure you want to delete this permanent?')) return;
    const res = await fetch(`/admin/api/delete/${collection}/${id}`, { method: 'DELETE' });
    if (res.ok) {
        window.showToast('Successfully removed', 'success');
        loadAllData();
        fetchStats();
    }
}

async function updateRole(userId, newRole) {
    const res = await fetch('/admin/api/users/update_role', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, role: newRole })
    });
    if (res.ok) {
        window.showToast('User role updated', 'success');
        loadAllData();
    }
}

function handleAdminForm(formId, url) {
    const form = document.getElementById(formId);
    if (!form) return;
    const btn = form.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner"></span>Processing...`;
        
        try {
            const res = await fetch(url, { method: 'POST', body: new FormData(form) });
            if (res.ok) {
                window.showToast('Content Published!', 'success');
                form.reset();
                toggleModal(formId.replace('add-', '').replace('-form', '-modal'));
                loadAllData();
                fetchStats();
            } else {
                const err = await res.json();
                window.showToast(err.error || 'Server Error', 'error');
            }
        } catch (err) {
            console.error("Form Submit Error:", err);
            window.showToast('Network Error - Please check connection', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });
}

function toggleModal(id) {
    const modal = document.getElementById(id);
    modal.style.display = modal.style.display === 'none' ? 'block' : 'none';
}

async function openOfflineModal() {
    toggleModal('offline-payment-modal');
    
    // Fetch events if not already fetched
    const select = document.getElementById('offline-event-select');
    if (select && select.options.length <= 1) {
        try {
            const res = await fetch('/events/');
            if (res.ok) {
                const events = await res.json();
                select.innerHTML = '<option value="">Select Event / Program</option>';
                events.forEach(e => {
                    select.innerHTML += `<option value="${e.id}">${e.title}</option>`;
                });
            } else {
                select.innerHTML = '<option value="">Failed to load events</option>';
            }
        } catch (err) {
            select.innerHTML = '<option value="">Failed to load events</option>';
        }
    }
}

// ==========================================
// Password Reset Tool Logic
// ==========================================

async function adminFindUser() {
    const emailInput = document.getElementById('reset-email-input').value.trim();
    if (!emailInput) {
        window.showToast('Please enter an email address.', 'error');
        return;
    }

    const btn = document.getElementById('find-user-btn');
    btn.innerHTML = `<span class="spinner"></span>...`;
    btn.disabled = true;

    // Reset visibility of elements
    document.getElementById('user-identity-card').style.display = 'none';
    document.getElementById('user-not-found').style.display = 'none';
    document.getElementById('reset-link-section').style.display = 'none';
    document.getElementById('reset-link-result').style.display = 'none';

    try {
        const res = await fetch(`/admin/api/find_user?email=${encodeURIComponent(emailInput)}`);
        const data = await res.json();

        if (res.ok && data.found) {
            // Populate the identity card
            document.getElementById('ri-name').innerText = data.full_name;
            document.getElementById('ri-member-id').innerText = data.member_id;
            document.getElementById('ri-email').innerText = data.email;
            
            // Format join date nicely
            const d = new Date(data.joined);
            document.getElementById('ri-joined').innerText = isNaN(d) ? data.joined : d.toLocaleDateString();

            // Show identity card and link generation section
            document.getElementById('user-identity-card').style.display = 'block';
            document.getElementById('reset-link-section').style.display = 'block';
        } else {
            // Show not found error
            document.getElementById('user-not-found').style.display = 'block';
        }
    } catch (err) {
        console.error('Error finding user:', err);
        window.showToast('Error looking up user', 'error');
    } finally {
        btn.innerHTML = 'Look Up';
        btn.disabled = false;
    }
}

async function adminGenerateReset() {
    const email = document.getElementById('ri-email').innerText;
    if (!email || email === '—') return;

    const btn = document.getElementById('gen-link-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span>Generating Secure Link...`;
    btn.disabled = true;

    try {
        const res = await fetch('/admin/api/generate_reset_link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        
        const data = await res.json();
        
        if (res.ok && data.success) {
            const linkBox = document.getElementById('reset-link-box');
            linkBox.value = data.reset_link;
            
            // Hide the generate button, show the result section
            btn.style.display = 'none';
            document.getElementById('reset-link-result').style.display = 'block';
            window.showToast('Reset link generated successfully!', 'success');
        } else {
            window.showToast(data.error || 'Failed to generate link', 'error');
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (err) {
        console.error('Error generating link:', err);
        window.showToast('Network error while generating link', 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function copyResetLink() {
    const linkBox = document.getElementById('reset-link-box');
    linkBox.select();
    linkBox.setSelectionRange(0, 99999); /* For mobile devices */

    navigator.clipboard.writeText(linkBox.value).then(() => {
        const confirmMsg = document.getElementById('copy-confirm');
        confirmMsg.style.display = 'block';
        
        // Hide confirmation after a few seconds
        setTimeout(() => {
            confirmMsg.style.display = 'none';
        }, 3000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
        window.showToast('Failed to copy to clipboard', 'error');
    });
}

// Year Management Functions for EC Members
function updateYearDropdownOptions() {
    const yearSelect = document.getElementById('admin-ec-year-select');
    if (!yearSelect) return;
    
    const currentYr = new Date().getFullYear().toString();
    const years = new Set([]);
    
    if (allEcMembers.length > 0) {
        allEcMembers.forEach(m => {
            let year = currentYr;
            if (m.category && m.category.includes('_')) {
                const parts = m.category.split('_');
                if (parts[0].length === 4 && !isNaN(parts[0])) {
                    year = parts[0];
                }
            }
            years.add(year);
        });
    }
    
    const currentVal = yearSelect.value || '2026';
    const sortedYears = Array.from(years).sort((a, b) => b - a);
    
    if (sortedYears.length > 0) {
        yearSelect.innerHTML = sortedYears.map(yr => `<option value="${yr}">${yr}</option>`).join('');
        if (sortedYears.includes(currentVal)) {
            yearSelect.value = currentVal;
        } else {
            yearSelect.value = sortedYears[0];
        }
    } else {
        yearSelect.innerHTML = '<option value="" disabled selected>No Years Found</option>';
    }
}

function renderECList() {
    const yearSelect = document.getElementById('admin-ec-year-select');
    const ecList = document.getElementById('ec-list');
    if (!ecList || !yearSelect) return;
    
    const selectedYear = yearSelect.value;
    const currentYr = new Date().getFullYear().toString();
    const filtered = allEcMembers.filter(m => {
        let year = currentYr;
        if (m.category && m.category.includes('_')) {
            const parts = m.category.split('_');
            if (parts[0].length === 4 && !isNaN(parts[0])) {
                year = parts[0];
            }
        }
        return year === selectedYear;
    });
    
    ecList.innerHTML = filtered.map(m => {
        let displayCat = m.category || 'N/A';
        let year = currentYr;
        if (m.category && m.category.includes('_')) {
            const parts = m.category.split('_');
            if (parts[0].length === 4 && !isNaN(parts[0])) {
                year = parts[0];
                displayCat = m.category.substring(m.category.indexOf('_') + 1);
            }
        }
        return `
            <tr>
                <td>${m.name}</td>
                <td>${m.designation}</td>
                <td>${displayCat}</td>
                <td>${year}</td>
                <td>${m.display_order}</td>
                <td>
                    <button class="action-btn delete-btn" onclick="deleteItem('ec_members', '${m.id}')">Remove</button>
                </td>
            </tr>
        `;
    }).join('');
}

function filterECByYear() {
    renderECList();
}

function openAddECModal() {
    const yearSelect = document.getElementById('admin-ec-year-select');
    const modalYear = document.getElementById('ec-modal-year');
    if (yearSelect && modalYear) {
        modalYear.value = yearSelect.value || new Date().getFullYear().toString();
    }
    toggleModal('ec-modal');
}

function adminAddYearPrompt() {
    const newYear = prompt("Enter new year (4 digits):");
    if (!newYear) return;
    if (newYear.length !== 4 || isNaN(newYear)) {
        window.showToast("Please enter a valid 4-digit year", "error");
        return;
    }
    
    const yearSelect = document.getElementById('admin-ec-year-select');
    if (yearSelect) {
        let exists = false;
        for (let i = 0; i < yearSelect.options.length; i++) {
            if (yearSelect.options[i].value === newYear) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            const opt = document.createElement('option');
            opt.value = newYear;
            opt.innerHTML = newYear;
            yearSelect.insertBefore(opt, yearSelect.firstChild);
            
            const sortedVals = Array.from(yearSelect.options)
                .map(o => o.value)
                .sort((a, b) => b - a);
            yearSelect.innerHTML = sortedVals.map(yr => `<option value="${yr}">${yr}</option>`).join('');
        }
        yearSelect.value = newYear;
        renderECList();
        window.showToast(`Year ${newYear} added. Add members to this year now!`, "success");
    }
}

async function adminDeleteYearPrompt() {
    const yearSelect = document.getElementById('admin-ec-year-select');
    if (!yearSelect) return;
    const year = yearSelect.value;
    
    if (!year) {
        window.showToast("No active year to delete", "error");
        return;
    }
    
    if (!confirm(`Are you sure you want to delete all EC members for the year ${year}?`)) {
        return;
    }
    
    try {
        const res = await fetch('/admin/ec/delete_year', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ year: year })
        });
        if (res.ok) {
            window.showToast(`Deleted all EC members for year ${year}`, 'success');
            loadAllData();
        } else {
            const err = await res.json();
            window.showToast(err.error || 'Failed to delete year', 'error');
        }
    } catch (err) {
        console.error("Delete Year Error:", err);
        window.showToast('Network error', 'error');
    }
}

