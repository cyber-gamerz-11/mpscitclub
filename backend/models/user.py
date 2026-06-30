from flask_login import UserMixin
from backend.config.db import get_db
import bcrypt

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['id'])
        self.email = user_data['email']
        self.full_name = user_data['full_name']
        self.role = user_data.get('role', 'member')
        self.phone = user_data.get('phone', '')
        self.section = user_data.get('section', '')
        self.student_id = user_data.get('student_id', '')
        self.institution = user_data.get('institution', '')
        self.join_date = user_data.get('join_date', '')

    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        if not db: return None
        try:
            response = db.table("users").select("*").eq("id", user_id).execute()
            user_data = response.data[0] if response.data else None
            return User(user_data) if user_data else None
        except:
            return None

    @staticmethod
    def get_by_email(email):
        db = get_db()
        if not db: return None
        try:
            response = db.table("users").select("*").eq("email", email).execute()
            user_data = response.data[0] if response.data else None
            return User(user_data) if user_data else None
        except:
            return None

    @staticmethod
    def create_user(data):
        db = get_db()
        if not db: return None
        # Hash password
        data['password'] = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert
        response = db.table("users").insert(data).execute()
        return response.data[0]['id'] if response.data else None

    @staticmethod
    def update_profile(user_id, update_data):
        db = get_db()
        if not db: return False
        try:
            db.table("users").update(update_data).eq("id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False

    @staticmethod
    def verify_password(stored_password, provided_password):
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))

    @staticmethod
    def update_password(email, new_password):
        db = get_db()
        if not db: return None
        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.table("users").update({"password": hashed_pw}).eq("email", email).execute()
