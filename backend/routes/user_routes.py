from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from backend.config.db import get_db

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile_data')
@login_required
def profile_data():
    return jsonify({
        "full_name": current_user.full_name,
        "email": current_user.email,
        "student_id": current_user.student_id,
        "section": current_user.section,
        "phone": current_user.phone,
        "join_date": current_user.join_date
    })

@user_bp.route('/ec_list')
def get_ec_list():
    db = get_db()
    if not db: return jsonify([])
    response = db.table("ec_members").select("*").order("display_order", desc=False).execute()
    
    parsed_members = []
    for m in response.data:
        cat = m.get('category') or 'BVB'
        year = '2026' # Fallback
        actual_category = cat
        if '_' in cat:
            parts = cat.split('_', 1)
            if parts[0].isdigit() and len(parts[0]) == 4:
                year = parts[0]
                actual_category = parts[1]
        
        m_copy = dict(m)
        m_copy['year'] = year
        m_copy['category'] = actual_category
        parsed_members.append(m_copy)
        
    return jsonify(parsed_members)


@user_bp.route('/gallery_list')
def get_gallery_list():
    db = get_db()
    if not db: return jsonify([])
    response = db.table("gallery").select("*").order("created_at", desc=True).execute()
    return jsonify(response.data)

@user_bp.route('/programs_list')
def get_programs_list():
    db = get_db()
    if not db: return jsonify([])
    response = db.table("programs").select("*").order("date", desc=True).execute()
    return jsonify(response.data)

@user_bp.route('/public_stats')
def get_public_stats():
    db = get_db()
    if not db: return jsonify({})
    
    users_count = db.table("users").select("id", count='exact').execute().count
    programs_count = db.table("programs").select("id", count='exact').execute().count
    events_count = db.table("events").select("id", count='exact').execute().count
    ec_count = db.table("ec_members").select("id", count='exact').execute().count
    
    return jsonify({
        "members": users_count,
        "events": programs_count, # Matching current frontend mapping
        "projects": events_count, # Matching current frontend mapping
        "ec": ec_count
    })
