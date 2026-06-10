from flask import Blueprint, request, jsonify, redirect, url_for, render_template, current_app
from flask_login import login_user, logout_user, login_required
from backend.models.user import User
from backend.config.db import get_db
from backend.utils.email_sender import send_reset_email
from itsdangerous import URLSafeTimedSerializer
import datetime
import os

auth_bp = Blueprint('auth', __name__)

def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt')

def verify_reset_token(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600) # 1 hour
        return email
    except:
        return None

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    db = get_db()
    if db is None:
        return jsonify({"error": "Database offline"}), 500

    data = request.form.to_dict()
    
    if User.get_by_email(data['email']):
        return jsonify({"error": "Email already registered"}), 400
    
    # Get total count for member_id
    response = db.table("users").select("id", count='exact').execute()
    count = response.count if response.count is not None else 0
    member_id = f"MPSC-2026-{str(count + 1).zfill(5)}"
    
    # Default profile pic
    pfp_url = "https://lqpcauxverkvkzuxzenn.supabase.co/storage/v1/object/public/mpsc-it-club/defaults/pfp.png"
    
    user_data = {
        "full_name": data['full_name'],
        "email": data['email'],
        "phone": data['phone'],
        "password": data['password'],
        "student_id": member_id,
        "section": data.get('class', ''),
        "institution": data.get('institution', ''),
        "role": "member",
        "join_date": datetime.datetime.now().isoformat()
    }
    
    # We will need to update the SQL schema to include these if we want them:
    # member_id, institution, skills, profile_pic
    # For now, let's keep it simple or use JSONB if PostgreSQL allowed.
    # But since I provided a strict schema, I'll stick to it.
    
    try:
        User.create_user(user_data)
        return jsonify({"success": "Welcome to the club!", "member_id": member_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
        
    data = request.form
    db = get_db()
    if db is None:
        return jsonify({"error": "Database offline"}), 500
    
    try:
        response = db.table("users").select("*").eq("email", data['email']).execute()
        user_data = response.data[0] if response.data else None
        
        if user_data and User.verify_password(user_data['password'], data['password']):
            user = User(user_data)
            login_user(user, remember=True)
            return jsonify({"success": "Access Granted"}), 200
    except:
        pass
    
    return jsonify({"error": "Invalid email or password"}), 401

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot-password.html')
    
    email = request.form.get('email')
    user = User.get_by_email(email)
    
    if user:
        token = generate_reset_token(email)
        reset_link = url_for('auth.reset_password', token=token, _external=True)
        send_reset_email(email, reset_link)
        print(f"\n[DEV] RESET LINK: {reset_link}\n")
        return jsonify({"success": "Reset link generated! (Check Email/Terminal)"}), 200
            
    return jsonify({"error": "Account not found"}), 404

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email: return "Token invalid/expired", 400
    if request.method == 'GET': return render_template('reset-password.html', token=token)
    
    new_password = request.form.get('password')
    User.update_password(email, new_password)
    return jsonify({"success": "Password updated!"}), 200

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')
