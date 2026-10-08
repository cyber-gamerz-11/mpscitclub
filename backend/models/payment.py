import json
import os

REG_META_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'registrations_meta.json')

def save_registration_metadata(payment_id, txid, meta):
    try:
        os.makedirs(os.path.dirname(REG_META_FILE), exist_ok=True)
        data = {}
        if os.path.exists(REG_META_FILE):
            try:
                with open(REG_META_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = {}
        if payment_id:
            data[payment_id] = meta
        if txid:
            data[f"tx_{txid}"] = meta
        with open(REG_META_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving registration metadata: {e}")

def get_registration_metadata(payment_id=None, txid=None):
    if not os.path.exists(REG_META_FILE):
        return None
    try:
        with open(REG_META_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if payment_id and payment_id in data:
            return data[payment_id]
        if txid and f"tx_{txid}" in data:
            return data[f"tx_{txid}"]
    except:
        pass
    return None

from backend.config.db import get_db
import datetime
import uuid
import bcrypt

class Payment:
    @staticmethod
    def create(data):
        db = get_db()
        if not db: return None
        
        # In SQL: member_id is the user's UUID (or created guest UUID / None)
        sql_data = {
            "event_id": data.get('event_id'),
            "member_id": data.get('user_id'),
            "ref_email": data.get('ref_email'),
            "transaction_id": data.get('transaction_id') or data.get('txid'),
            "status": 'pending'
        }
        
        try:
            response = db.table("payments").insert(sql_data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            print(f"Error inserting payment: {e}")
            # Try alternate column name if user_id instead of member_id
            try:
                alt_data = {
                    "event_id": data.get('event_id'),
                    "user_id": data.get('user_id'),
                    "ref_email": data.get('ref_email'),
                    "transaction_id": data.get('transaction_id') or data.get('txid'),
                    "status": 'pending'
                }
                response = db.table("payments").insert(alt_data).execute()
                return response.data[0]['id'] if response.data else None
            except Exception as e2:
                print(f"Error inserting payment with user_id: {e2}")
                return None

    @staticmethod
    def create_bulk(data):
        """
        Handles registration for single or multiple selected events,
        for either a logged-in user or a guest user.
        """
        db = get_db()
        if not db: return None

        event_ids = data.get('event_ids', [])
        if isinstance(event_ids, str):
            event_ids = [e.strip() for e in event_ids.split(',') if e.strip()]

        user_id = data.get('user_id')
        full_name = data.get('full_name', '').strip() or 'Guest Participant'
        email = data.get('email', '').strip() or data.get('ref_email', '').strip()
        phone = data.get('phone', '').strip() or 'N/A'
        institution = data.get('institution', '').strip() or 'MPSC'
        student_class = data.get('student_class', '').strip() or 'N/A'
        txid = data.get('transaction_id', '').strip() or data.get('txid', '').strip() or 'FREE-EVENT-REG'

        # If not logged in, check if an existing member account matches this email, otherwise keep user_id as None (NO guest account is created in users table)
        if not user_id and email:
            try:
                user_res = db.table("users").select("id, role").eq("email", email).execute()
                if user_res.data and user_res.data[0].get('role') != 'guest':
                    user_id = user_res.data[0]['id']
            except Exception as u_err:
                print(f"User lookup note: {u_err}")

        # Metadata dictionary for accurate tracking of this exact submission
        meta_dict = {
            "participant_name": full_name,
            "phone": phone,
            "email": email,
            "student_class": student_class,
            "institution": institution,
            "transaction_id": txid,
            "submitted_at": datetime.datetime.now().isoformat()
        }

        # Save metadata indexed by transaction id
        save_registration_metadata(None, txid, meta_dict)

        # Insert a payment record for each selected event
        created_ids = []
        for ev_id in event_ids:
            payment_item = {
                "event_id": ev_id,
                "user_id": user_id,
                "ref_email": email,
                "transaction_id": txid,
                "status": "pending"
            }
            try:
                res = Payment.create(payment_item)
                if res:
                    created_ids.append(res)
                    # Save metadata indexed by payment id
                    save_registration_metadata(res, txid, meta_dict)
            except Exception as p_err:
                print(f"Payment record insert error for {ev_id}: {p_err}")

        return created_ids

    @staticmethod
    def get_by_user(user_id):
        db = get_db()
        if not db: return []
        try:
            response = db.table("payments").select("*").eq("member_id", user_id).order("created_at", desc=True).execute()
            return response.data if response.data else []
        except:
            try:
                response = db.table("payments").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
                return response.data if response.data else []
            except Exception as e:
                print(f"Error fetching user payments: {e}")
                return []

    @staticmethod
    def get_all():
        db = get_db()
        if not db: return []
        try:
            response = db.table("payments").select("*").order("created_at", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching payments: {e}")
            return []

    @staticmethod
    def verify(payment_id, status):
        db = get_db()
        if not db: return
        try:
            db.table("payments").update({"status": status}).eq("id", payment_id).execute()
        except Exception as e:
            print(f"Error verifying payment: {e}")
