from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from flask_login import login_required, current_user
from backend.config.db import get_db
import datetime
import time
import os
from werkzeug.utils import secure_filename

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
    
    # In Supabase, we delete by ID
    # Before deleting from DB, we should delete from storage if applicable
    # To keep it simple, we'll just delete the record for now
    # Cleanup can be handled manually or via a more complex logic
    
    try:
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
    
    db = get_db()
    db.table("ec_members").insert({
        "name": data['name'],
        "designation": data['designation'],
        "category": data['category'],
        "image_path": image_url or '/static/assets/images/ec/default.jpg',
        "facebook": data.get('facebook', ''),
        "instagram": data.get('instagram', ''),
        "website": data.get('website', ''),
        "whatsapp": data.get('whatsapp', ''),
        "display_order": int(data.get('order', 99) or 99)
    }).execute()
    
    return jsonify({"success": "EC Member added"})

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

