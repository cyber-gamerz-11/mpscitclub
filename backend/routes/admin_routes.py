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
admin_bp = Blueprint('admin', __name__)

# --- Admin-only password reset helpers ---
def _generate_reset_token(email):
    """Reuse the same token logic as auth_routes so the link works on /auth/reset-password."""
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='password-reset-salt')

def admin_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            if request.path.startswith('/admin/api') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "Unauthorized"}), 403
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

def upload_to_supabase(file, folder):
    if not file or not file.filename:
        return None
    
    file_content = file.read()
    # Add timestamp to prevent duplicate filename errors
    timestamp = int(time.time())
    filename = f"{timestamp}_{secure_filename(file.filename)}"
    storage_path = f"{folder}/{filename}"
    
    db = get_db()
    try:
        db.storage.from_('mpsc-it-club').upload(storage_path, file_content)
        # Use official method to get public URL
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
    
    events = db.table("events").select("*").order("created_at", desc=True).execute()
    programs = db.table("programs").select("*").order("created_at", desc=True).execute()
    gallery = db.table("gallery").select("*").order("created_at", desc=True).execute()
    users = db.table("users").select("id, full_name, email, role, join_date").order("join_date", desc=True).execute()
    ec_members = db.table("ec_members").select("*").order("display_order", desc=False).execute()

    return jsonify({
        "events": events.data,
        "programs": programs.data,
        "gallery": gallery.data,
        "users": users.data,
        "ec_members": ec_members.data
    })

@admin_bp.route('/api/delete/<collection>/<id>', methods=['DELETE'])
@login_required
@admin_required
def delete_item(collection, id):
    db = get_db()
    
    try:
        # 1. Fetch the record first to get the image URL
        res = db.table(collection).select("*").eq("id", id).execute()
        if res.data:
            item = res.data[0]
            # Check common image fields
            image_url = item.get('image_path') or item.get('banner') or item.get('url')
            if image_url:
                delete_file_from_supabase(image_url)
                
        # 2. Delete the record from DB
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

@admin_bp.route('/events/add', methods=['POST'])
@login_required
@admin_required
def add_event():
    data = request.form.to_dict()
    banner_url = upload_to_supabase(request.files.get('image'), 'events')
    
    db = get_db()
    db.table("events").insert({
        "title": data['title'],
        "description": data['description'],
        "date": data['date'],
        "venue": data['venue'],
        "status": data.get('status', 'Upcoming'),
        "banner": banner_url or '',
        "fee": int(data.get('fee', 0))
    }).execute()
    
    return jsonify({"success": "Event added"})

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
    
    # Category stored in DB is "{year}_{category}" (e.g. "2026_BVB")
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
        # Fetch all members to delete their images
        res = db.table("ec_members").select("image_path").like("category", f"{year}_%").execute()
        if res.data:
            for m in res.data:
                if m.get('image_path'):
                    delete_file_from_supabase(m['image_path'])
                    
        # Now delete from DB
        db.table("ec_members").delete().like("category", f"{year}_%").execute()
        return jsonify({"success": f"All members for year {year} deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/stats')
@login_required
@admin_required
def get_stats():
    db = get_db()
    
    users_count = db.table("users").select("id", count='exact').execute().count
    events_count = db.table("events").select("id", count='exact').execute().count
    
    # Calculate real revenue from approved payments
    payments = db.table("payments").select("event_id").eq("status", "approved").execute().data
    total_revenue = 0
    if payments:
        event_ids = list(set([p['event_id'] for p in payments if p.get('event_id')]))
        if event_ids:
            events = db.table("events").select("id, fee").in_("id", event_ids).execute().data
            fee_map = {e['id']: int(e.get('fee', 0) or 0) for e in events}
            for p in payments:
                total_revenue += fee_map.get(p['event_id'], 0)
    
    pending_count = db.table("payments").select("id", count='exact').eq("status", "pending").execute().count
    
    return jsonify({
        "total_users": users_count,
        "total_events": events_count,
        "total_revenue": total_revenue,
        "pending_payments": pending_count
    })

# ── Password Reset Tools (Admin Only) ──────────────────────────────────────

@admin_bp.route('/api/find_user')
@login_required
@admin_required
def find_user():
    """
    GET /admin/api/find_user?email=someone@email.com
    Returns the user's name, member ID, join date, and role so the admin
    can visually verify the person's identity before generating a reset link.
    Passwords are never exposed.
    """
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    db = get_db()
    try:
        result = db.table("users") \
            .select("id, full_name, email, role, join_date, student_id") \
            .eq("email", email) \
            .execute()

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
    """
    POST /admin/api/generate_reset_link   body: { "email": "..." }
    Generates a secure, time-limited (1 hour) reset link for the given email.
    The admin copies the link and sends it manually to the user.
    """
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
    # Build an absolute URL so the admin can copy-paste it anywhere
    reset_link = url_for('auth.reset_password', token=token, _external=True)

    # Also print to server console as a local dev convenience
    print(f"\n[ADMIN RESET] Link for {email}: {reset_link}\n")

    return jsonify({
        "success": True,
        "reset_link": reset_link,
        "expires_in": "1 hour"
    })

@admin_bp.route('/api/verified_payments')
@login_required
@admin_required
def get_verified_payments():
    db = get_db()
    
    # Get all approved payments
    payments_res = db.table("payments").select("*").eq("status", "approved").order("created_at", desc=True).execute()
    payments = payments_res.data if payments_res.data else []
    
    # Get users map
    users_res = db.table("users").select("id, full_name, email, student_id, phone").execute()
    users_map = {u['id']: u for u in users_res.data} if users_res.data else {}
    
    # Get events map
    events_res = db.table("events").select("id, title").execute()
    events_map = {e['id']: e['title'] for e in events_res.data} if events_res.data else {}
    
    result = []
    for p in payments:
        user = users_map.get(p.get('member_id'), {})
        event_title = events_map.get(p.get('event_id'), 'Unknown Event')
        verified_date = p.get('updated_at', p.get('created_at', ''))
        
        result.append({
            "payment_id": p.get('id', ''),
            "event_name": event_title,
            "member_name": user.get('full_name', 'Unknown'),
            "student_id": user.get('student_id', 'Unknown'),
            "phone": user.get('phone', 'N/A'),
            "email": user.get('email', 'Unknown'),
            "ref_email": p.get('ref_email', ''),
            "transaction_id": p.get('transaction_id', ''),
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

import uuid
import bcrypt

@admin_bp.route('/api/add_offline_payment', methods=['POST'])
@login_required
@admin_required
def add_offline_payment():
    data = request.json
    db = get_db()
    
    # 1. Create a dummy offline user to hold the name and ID
    dummy_email = f"offline_{uuid.uuid4().hex[:8]}@mpsc.local"
    user_data = {
        "email": dummy_email,
        "full_name": data.get('full_name', 'Offline User'),
        "student_id": data.get('student_id', 'N/A'),
        "phone": data.get('phone', 'N/A'),
        "password": bcrypt.hashpw(uuid.uuid4().hex.encode(), bcrypt.gensalt()).decode('utf-8'),
        "role": "member",
        "institution": "Offline Entry"
    }
    try:
        user_res = db.table("users").insert(user_data).execute()
        new_user_id = user_res.data[0]['id']
        
        # 2. Create the approved payment record
        payment_data = {
            "member_id": new_user_id,
            "event_id": data.get('event_id'),
            "transaction_id": data.get('transaction_id') or "OFFLINE-CASH",
            "ref_email": data.get('email') or "Added by Admin (Offline)",
            "status": "approved"
        }
        db.table("payments").insert(payment_data).execute()
        return jsonify({"success": "Offline record added successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/api/export_verified_payments')
@login_required
@admin_required
def export_verified_payments():
    db = get_db()
    
    # Get all approved payments
    payments_res = db.table("payments").select("*").eq("status", "approved").execute()
    if not payments_res.data:
        return jsonify({"error": "No verified payments found"}), 404
        
    payments = payments_res.data
    
    # Get all users and create a map
    users_res = db.table("users").select("id, full_name, email, student_id, phone").execute()
    users_map = {u['id']: u for u in users_res.data} if users_res.data else {}
    
    # Get all events and create a map
    events_res = db.table("events").select("id, title").execute()
    events_map = {e['id']: e['title'] for e in events_res.data} if events_res.data else {}
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Event Name',
        'Member Name',
        'Student ID',
        'Phone Number',
        'Registered Email',
        'Payment Reference Email',
        'Transaction ID',
        'Date Verified'
    ])
    
    for p in payments:
        user = users_map.get(p.get('member_id'), {})
        event_title = events_map.get(p.get('event_id'), 'Unknown Event')
        
        # created_at or updated_at for verified date. We'll use created_at or updated_at if available.
        verified_date = p.get('updated_at', p.get('created_at', ''))
        
        writer.writerow([
            event_title,
            user.get('full_name', 'Unknown'),
            user.get('student_id', 'Unknown'),
            user.get('phone', 'N/A'),
            user.get('email', 'Unknown'),
            p.get('ref_email', ''),
            p.get('transaction_id', ''),
            verified_date
        ])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=Verified_Payments_Report.csv"}
    )

