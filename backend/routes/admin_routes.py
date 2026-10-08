import json
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from flask_login import login_required, current_user
from backend.config.db import get_db
import datetime
import time
import os
from werkzeug.utils import secure_filename
import csv
import io
from flask import Response
import uuid
import bcrypt

admin_bp = Blueprint('admin', __name__)

# --- Admin-only password reset helpers ---
def _generate_reset_token(email):
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='password-reset-salt')

def admin_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            # If requesting via API / AJAX / Form submit or non-GET, return JSON 403
            if request.method != 'GET' or request.path.startswith('/admin/api') or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({"error": "Admin access required. Please login with an administrator account."}), 403
            if request.path != '/admin/':
                return jsonify({"error": "Admin access required."}), 403
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

def upload_to_supabase(file, folder):
    if not file or not file.filename:
        return None
    
    file_content = file.read()
    timestamp = int(time.time())
    filename = f"{timestamp}_{secure_filename(file.filename)}"
    storage_path = f"{folder}/{filename}"
    
    db = get_db()
    try:
        db.storage.from_('mpsc-it-club').upload(storage_path, file_content)
        url = db.storage.from_('mpsc-it-club').get_public_url(storage_path)
        return url
    except Exception as e:
        print(f"Supabase Upload Error: {e}")
        return None

def delete_file_from_supabase(url):
    if not url or 'supabase.co' not in url:
        return
    try:
        parts = url.split('/public/mpsc-it-club/')
        if len(parts) == 2:
            file_path = parts[1]
            db = get_db()
            db.storage.from_('mpsc-it-club').remove([file_path])
    except Exception as e:
        print(f"Supabase Delete Error: {e}")

@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin.html')

@admin_bp.route('/api/all_data')
@login_required
@admin_required
def get_all_data():
    db = get_db()
    if not db:
        return jsonify({"events": [], "programs": [], "gallery": [], "users": [], "ec_members": []})
        
    events_res = db.table("events").select("*").order("created_at", desc=True).execute()
    events = events_res.data if events_res.data else []
    for ev in events:
        if not ev.get('category'):
            desc = ev.get('description', '') or ''
            if desc.startswith('[PRIMARY]'): ev['category'] = 'primary'
            elif desc.startswith('[JUNIOR]'): ev['category'] = 'junior'
            elif desc.startswith('[SECONDARY]'): ev['category'] = 'secondary'
            elif desc.startswith('[HIGHER_SECONDARY]'): ev['category'] = 'higher_secondary'
            else: ev['category'] = 'all'

    programs = db.table("programs").select("*").order("created_at", desc=True).execute()
    gallery = db.table("gallery").select("*").order("created_at", desc=True).execute()
    users_res = db.table("users").select("id, full_name, email, role, join_date, student_id, phone, section, institution").order("join_date", desc=True).execute()
    # Filter out any guest entries so only registered members/admins appear in the Users tab
    clean_users = [u for u in (users_res.data or []) if u.get('role') != 'guest' and not (u.get('email') or '').endswith('@mpsc.guest')]
    ec_members = db.table("ec_members").select("*").order("display_order", desc=False).execute()

    return jsonify({
        "events": events,
        "programs": programs.data if programs.data else [],
        "gallery": gallery.data if gallery.data else [],
        "users": clean_users,
        "ec_members": ec_members.data if ec_members.data else []
    })

@admin_bp.route('/api/delete/<collection>/<id>', methods=['DELETE'])
@login_required
@admin_required
def delete_item(collection, id):
    db = get_db()
    try:
        res = db.table(collection).select("*").eq("id", id).execute()
        if res.data:
            item = res.data[0]
            image_url = item.get('image_path') or item.get('banner') or item.get('url')
            if image_url:
                delete_file_from_supabase(image_url)
                
        db.table(collection).delete().eq("id", id).execute()
        return jsonify({"success": "Deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/users/update_role', methods=['POST'])
@login_required
@admin_required
def update_user_role():
    data = request.json
    db = get_db()
    db.table("users").update({"role": data['role']}).eq("id", data['user_id']).execute()
    return jsonify({"success": "Role updated"})

def _save_event_helper():
    data = request.form.to_dict()
    event_id = data.get('event_id', '').strip()
    image_file = request.files.get('image')
    banner_url = upload_to_supabase(image_file, 'events') if image_file and image_file.filename else None
    
    # Handle multi-select category checkboxes
    categories = request.form.getlist('categories')
    if not categories:
        single_cat = data.get('category', '').strip()
        categories = [single_cat] if single_cat else ['all']
    
    cats_cleaned = [c.lower().strip() for c in categories if c.strip()]
    if 'all' in cats_cleaned or not cats_cleaned:
        final_category = 'all'
    else:
        final_category = ",".join(cats_cleaned)
    
    event_payload = {
        "title": data.get('title', '').strip(),
        "description": data.get('description', ''),
        "date": data.get('date', ''),
        "venue": data.get('venue', ''),
        "status": data.get('status', 'Upcoming'),
        "fee": int(data.get('fee', 0) or 0),
        "category": final_category
    }
    if banner_url:
        event_payload["banner"] = banner_url

    if not event_payload['title']:
        return jsonify({"error": "Event title is required."}), 400

    db = get_db()
    if not db:
        return jsonify({"error": "Database offline. Check Supabase connection."}), 500

    try:
        if event_id:
            db.table("events").update(event_payload).eq("id", event_id).execute()
            return jsonify({"success": "Event updated successfully!"})
        else:
            if not banner_url:
                event_payload["banner"] = ''
            db.table("events").insert(event_payload).execute()
            return jsonify({"success": "Event added successfully!"})
    except Exception as e:
        print(f"Initial event save note: {e}")
        event_payload.pop('category', None)
        if final_category and final_category != 'all':
            event_payload['description'] = f"[{final_category.upper()}] " + (event_payload.get('description') or '')
        try:
            if event_id:
                db.table("events").update(event_payload).eq("id", event_id).execute()
                return jsonify({"success": "Event updated successfully!"})
            else:
                db.table("events").insert(event_payload).execute()
                return jsonify({"success": "Event added successfully!"})
        except Exception as e2:
            print(f"Fallback event save error: {e2}")
            return jsonify({"error": f"Database Error: {str(e2)}"}), 500

@admin_bp.route('/events/add', methods=['POST'])
@login_required
@admin_required
def add_event():
    return _save_event_helper()

@admin_bp.route('/add_event', methods=['POST'])
@login_required
@admin_required
def add_event_alias():
    return _save_event_helper()

@admin_bp.route('/programs/add', methods=['POST'])
@login_required
@admin_required
def add_program():
    data = request.form.to_dict()
    banner_url = upload_to_supabase(request.files.get('image'), 'programs')
    
    db = get_db()
    db.table("programs").insert({
        "title": data['title'],
        "description": data['description'],
        "date": data.get('date', ''),
        "banner": banner_url or ''
    }).execute()
    
    return jsonify({"success": "Program added"})

@admin_bp.route('/add_program', methods=['POST'])
@login_required
@admin_required
def add_program_alias():
    return add_program()

@admin_bp.route('/gallery/add', methods=['POST'])
@login_required
@admin_required
def add_gallery_item():
    image_url = upload_to_supabase(request.files.get('image'), 'gallery')
    if not image_url:
        return jsonify({"error": "No image uploaded"}), 400

    db = get_db()
    db.table("gallery").insert({
        "url": image_url,
        "caption": request.form.get('caption', ''),
        "category": request.form.get('category', 'General')
    }).execute()
    
    return jsonify({"success": "Gallery item added"})

@admin_bp.route('/ec/add', methods=['POST'])
@login_required
@admin_required
def add_ec_member():
    data = request.form.to_dict()
    image_url = upload_to_supabase(request.files.get('image'), 'ec')
    
    year = data.get('year', '2026').strip()
    category = data['category']
    full_category = f"{year}_{category}"
    
    db = get_db()
    db.table("ec_members").insert({
        "name": data['name'],
        "designation": data['designation'],
        "category": full_category,
        "image_path": image_url or '/static/assets/images/ec/default.jpg',
        "facebook": data.get('facebook', ''),
        "instagram": data.get('instagram', ''),
        "website": data.get('website', ''),
        "whatsapp": data.get('whatsapp', ''),
        "display_order": int(data.get('order', 99) or 99)
    }).execute()
    
    return jsonify({"success": "EC Member added"})

@admin_bp.route('/ec/delete_year', methods=['POST'])
@login_required
@admin_required
def delete_ec_year():
    data = request.json
    year = str(data.get('year', '')).strip()
    if not year:
        return jsonify({"error": "Year is required"}), 400
        
    db = get_db()
    try:
        res = db.table("ec_members").select("image_path").like("category", f"{year}_%").execute()
        if res.data:
            for m in res.data:
                if m.get('image_path'):
                    delete_file_from_supabase(m['image_path'])
                    
        db.table("ec_members").delete().like("category", f"{year}_%").execute()
        return jsonify({"success": f"All members for year {year} deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/stats')
@login_required
@admin_required
def get_stats():
    db = get_db()
    if not db:
        return jsonify({"total_users": 0, "total_events": 0, "total_revenue": 0, "pending_payments": 0})
        
    users_count = db.table("users").select("id", count='exact').execute().count or 0
    events_count = db.table("events").select("id", count='exact').execute().count or 0
    
    payments = db.table("payments").select("event_id").eq("status", "approved").execute().data or []
    total_revenue = 0
    if payments:
        event_ids = list(set([p['event_id'] for p in payments if p.get('event_id')]))
        if event_ids:
            events = db.table("events").select("id, fee").in_("id", event_ids).execute().data or []
            fee_map = {e['id']: int(e.get('fee', 0) or 0) for e in events}
            for p in payments:
                total_revenue += fee_map.get(p['event_id'], 0)
    
    pending_count = db.table("payments").select("id", count='exact').eq("status", "pending").execute().count or 0
    
    return jsonify({
        "total_users": users_count,
        "total_events": events_count,
        "total_revenue": total_revenue,
        "pending_payments": pending_count
    })

# Password Reset Tools
@admin_bp.route('/api/find_user')
@login_required
@admin_required
def find_user():
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    db = get_db()
    try:
        result = db.table("users").select("id, full_name, email, role, join_date, student_id").eq("email", email).execute()
        if not result.data:
            return jsonify({"error": "No account found with that email"}), 404

        user = result.data[0]
        return jsonify({
            "found": True,
            "full_name": user.get("full_name", "—"),
            "email": user.get("email", "—"),
            "member_id": user.get("student_id", "—"),
            "role": user.get("role", "member"),
            "joined": user.get("join_date", "—")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/generate_reset_link', methods=['POST'])
@login_required
@admin_required
def admin_generate_reset_link():
    data = request.get_json()
    email = (data or {}).get('email', '').strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    db = get_db()
    try:
        result = db.table("users").select("id").eq("email", email).execute()
        if not result.data:
            return jsonify({"error": "No account with that email"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    token = _generate_reset_token(email)
    reset_link = url_for('auth.reset_password', token=token, _external=True)

    return jsonify({
        "success": True,
        "reset_link": reset_link,
        "expires_in": "1 hour"
    })

@admin_bp.route('/api/verified_payments')
@login_required
@admin_required
def get_verified_payments():
    from backend.models.payment import get_registration_metadata
    db = get_db()
    if not db: return jsonify([])
    
    payments_res = db.table("payments").select("*").eq("status", "approved").order("created_at", desc=True).execute()
    payments = payments_res.data if payments_res.data else []
    
    users_res = db.table("users").select("id, full_name, email, student_id, phone, section, institution").execute()
    users_map = {u['id']: u for u in users_res.data} if users_res.data else {}
    
    events_res = db.table("events").select("*").execute()
    events_map = {e['id']: e for e in events_res.data} if events_res.data else {}
    
    result = []
    for p in payments:
        p_id = p.get('id', '')
        tx = p.get('transaction_id') or p.get('tx_id') or ''
        meta = get_registration_metadata(p_id, tx) or {}
        
        u_id = p.get('member_id') or p.get('user_id')
        user = users_map.get(u_id, {})
        ev = events_map.get(p.get('event_id'), {})
        event_title = ev.get('title', 'Unknown Event')
        verified_date = p.get('updated_at', p.get('created_at', ''))
        
        # Use exact submitted metadata first, fallback to user account
        m_name = meta.get('participant_name') or user.get('full_name') or p.get('full_name') or 'Participant'
        m_phone = meta.get('phone') or user.get('phone') or p.get('phone') or 'N/A'
        m_email = meta.get('email') or p.get('ref_email') or user.get('email') or 'N/A'
        m_class = meta.get('student_class') or user.get('section') or 'N/A'
        m_inst = meta.get('institution') or user.get('institution') or 'MPSC'

        is_offline = str(tx).upper().startswith('OFFLINE') or meta.get('source') == 'offline'
        result.append({
            "payment_id": p_id,
            "event_name": event_title,
            "event_category": ev.get('category', 'all'),
            "event_fee": ev.get('fee', 0),
            "member_name": m_name,
            "student_id": user.get('student_id', 'OFFLINE' if is_offline else 'ONLINE'),
            "phone": m_phone,
            "email": m_email,
            "institution": m_inst,
            "student_class": m_class,
            "ref_email": m_email,
            "transaction_id": tx,
            "registration_type": "offline" if is_offline else "online",
            "date_verified": verified_date
        })
        
    return jsonify(result)

@admin_bp.route('/api/delete_payment/<payment_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_payment(payment_id):
    db = get_db()
    try:
        db.table("payments").delete().eq("id", payment_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/delete_all_payments', methods=['DELETE'])
@login_required
@admin_required
def delete_all_payments():
    db = get_db()
    try:
        db.table("payments").delete().eq("status", "approved").execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/add_offline_payment', methods=['POST'])
@login_required
@admin_required
def add_offline_payment():
    data = request.json or {}
    db = get_db()
    
    full_name = data.get('full_name', '').strip() or 'Offline Participant'
    phone = data.get('phone', '').strip() or 'N/A'
    email = data.get('email', '').strip() or f"offline_{uuid.uuid4().hex[:6]}@mpsc.local"
    student_class = data.get('class', '').strip() or data.get('student_class', '').strip() or 'N/A'
    institution = data.get('institution', '').strip() or 'Mohammadpur Preparatory School & College'
    event_id = data.get('event_id')
    txid = data.get('transaction_id') or f"OFFLINE-{uuid.uuid4().hex[:6].upper()}"
    
    # Check if a real registered user exists with this email
    user_id = None
    if email and not email.startswith('offline'):
        try:
            u_check = db.table("users").select("id, role").eq("email", email).execute()
            if u_check.data and u_check.data[0].get('role') != 'guest':
                user_id = u_check.data[0]['id']
        except:
            pass

    payment_data = {
        "member_id": user_id,
        "event_id": event_id,
        "transaction_id": txid,
        "ref_email": email,
        "status": "approved"
    }
    try:
        p_res = db.table("payments").insert(payment_data).execute()
        payment_id = p_res.data[0]['id'] if p_res.data else None
        
        # Save exact submitted metadata for slip, dispatch & export
        meta_dict = {
            "participant_name": full_name,
            "phone": phone,
            "email": email,
            "student_class": student_class,
            "institution": institution,
            "transaction_id": txid,
            "submitted_at": datetime.datetime.now().isoformat()
        }
        from backend.models.payment import save_registration_metadata
        save_registration_metadata(payment_id, txid, meta_dict)
        
        return jsonify({"success": "Offline record added successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/export_verified_payments')
@login_required
@admin_required
def export_verified_payments():
    db = get_db()
    if not db: return jsonify({"error": "DB offline"}), 500
    
    payments_res = db.table("payments").select("*").eq("status", "approved").execute()
    if not payments_res.data:
        return jsonify({"error": "No verified payments found"}), 404
        
    payments = payments_res.data
    users_res = db.table("users").select("id, full_name, email, student_id, phone, section, institution").execute()
    users_map = {u['id']: u for u in users_res.data} if users_res.data else {}
    
    events_res = db.table("events").select("*").execute()
    events_map = {e['id']: e for e in events_res.data} if events_res.data else {}
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Payment ID", "Participant Name", "Phone / WhatsApp", "Email", 
        "Institution", "Class / Group", "Event Name", "Event Category", 
        "Fee (BDT)", "Transaction ID", "Status", "Date"
    ])
    
    for p in payments:
        p_id = p.get('id', '')
        tx = p.get('transaction_id') or p.get('tx_id') or ''
        meta = get_registration_metadata(p_id, tx) or {}

        u_id = p.get('member_id') or p.get('user_id')
        user = users_map.get(u_id, {})
        ev = events_map.get(p.get('event_id'), {})
        
        m_name = meta.get('participant_name') or user.get('full_name') or p.get('full_name') or 'N/A'
        m_phone = meta.get('phone') or user.get('phone') or p.get('phone') or 'N/A'
        m_email = meta.get('email') or p.get('ref_email') or user.get('email') or 'N/A'
        m_inst = meta.get('institution') or user.get('institution', 'MPSC')
        m_class = meta.get('student_class') or user.get('section', 'N/A')

        writer.writerow([
            p_id,
            m_name,
            m_phone,
            m_email,
            m_inst,
            m_class,
            ev.get('title', 'Unknown Event'),
            ev.get('category', 'All'),
            ev.get('fee', 0),
            tx,
            p.get('status', 'approved'),
            p.get('updated_at') or p.get('created_at', '')
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=mpsc_verified_event_registrations.csv"}
    )


# ── Main Fest Banner & Settings ───────────────────────────────────────
MAIN_FEST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'main_fest.json')

def get_main_fest_data():
    db = get_db()
    if db:
        try:
            res = db.table("main_fest").select("*").eq("id", "current").execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception:
            pass
            
    if os.path.exists(MAIN_FEST_FILE):
        try:
            with open(MAIN_FEST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "title": "MPSC IT Carnival & Competitions 2026",
        "description": "Step into the grandest tech arena of MPSC IT Club! Explore all competitions, workshops, and segment events below. Select the events matching your class level and register now.",
        "date": "Coming Soon / 2026",
        "venue": "MPSC Main Campus",
        "banner": ""
    }

@admin_bp.route('/api/main_fest', methods=['GET'])
@login_required
@admin_required
def get_admin_main_fest():
    return jsonify(get_main_fest_data())

@admin_bp.route('/api/update_main_fest', methods=['POST'])
@login_required
@admin_required
def update_main_fest():
    title = request.form.get('title', '').strip() or "MPSC IT Carnival & Competitions 2026"
    description = request.form.get('description', '').strip()
    date = request.form.get('date', '').strip()
    venue = request.form.get('venue', '').strip()
    
    current_data = get_main_fest_data()
    banner_url = upload_to_supabase(request.files.get('image'), 'events')
    if not banner_url:
        banner_url = current_data.get('banner', '')

    updated_data = {
        "id": "current",
        "title": title,
        "description": description,
        "date": date,
        "venue": venue,
        "banner": banner_url
    }

    # Save to Supabase main_fest table if exists
    db = get_db()
    if db:
        try:
            db.table("main_fest").upsert(updated_data).execute()
        except Exception as e:
            print(f"Supabase main_fest table sync note: {e}")

    os.makedirs(os.path.dirname(MAIN_FEST_FILE), exist_ok=True)
    with open(MAIN_FEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2)

    return jsonify({"success": True, "message": "Main Fest Banner & Info updated in database & system!", "data": updated_data})


@admin_bp.route('/api/queries', methods=['GET'])
@login_required
@admin_required
def get_queries():
    db = get_db()
    if not db: return jsonify([])
    try:
        res = db.table("queries").select("*").order("created_at", desc=True).execute()
        return jsonify(res.data if res.data else [])
    except Exception as e:
        print(f"Error fetching queries: {e}")
        return jsonify([])
