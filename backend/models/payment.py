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

def parse_payment_meta(payment_row_or_ref, payment_id=None, txid=None, user_dict=None):
    """
    Recovers participant name, phone, email, class, and institution from:
    1. Dedicated Supabase columns (full_name, phone, institution, student_class)
    2. Cloud-persisted JSON in ref_email
    3. Local metadata cache
    4. Linked User profile
    """
    p_dict = payment_row_or_ref if isinstance(payment_row_or_ref, dict) else {}
    ref_email_raw = p_dict.get('ref_email') if isinstance(payment_row_or_ref, dict) else payment_row_or_ref

    meta = {}
    # Check if ref_email has JSON string
    if ref_email_raw and isinstance(ref_email_raw, str) and ref_email_raw.strip().startswith('{'):
        try:
            parsed = json.loads(ref_email_raw)
            if isinstance(parsed, dict):
                meta = parsed
        except Exception:
            pass

    # Check local file metadata backup
    if not meta.get('participant_name') or not meta.get('phone'):
        local_meta = get_registration_metadata(payment_id or p_dict.get('id'), txid or p_dict.get('transaction_id')) or {}
        for k, v in local_meta.items():
            if k not in meta or not meta[k]:
                meta[k] = v

    user = user_dict or {}
    
    # Priority: Dedicated DB Column -> Cloud JSON -> User profile -> Default
    name = p_dict.get('full_name') or meta.get('participant_name') or meta.get('name') or user.get('full_name') or 'Participant'
    phone = p_dict.get('phone') or meta.get('phone') or user.get('phone') or 'N/A'
    
    raw_clean_email = ref_email_raw if (ref_email_raw and not str(ref_email_raw).startswith('{')) else None
    email = meta.get('email') or raw_clean_email or user.get('email') or 'N/A'
    student_class = p_dict.get('student_class') or meta.get('student_class') or meta.get('class') or user.get('section') or 'N/A'
    institution = p_dict.get('institution') or meta.get('institution') or meta.get('inst') or user.get('institution') or 'Mohammadpur Preparatory School & College'
    
    effective_tx = txid or p_dict.get('transaction_id') or ''
    source = meta.get('source') or ('offline' if str(effective_tx).upper().startswith('OFFLINE') else 'online')

    return {
        "participant_name": name,
        "phone": phone,
        "email": email,
        "student_class": student_class,
        "institution": institution,
        "source": source
    }

from backend.config.db import get_db
import datetime
import uuid
import bcrypt

class Payment:
    @staticmethod
    def create(data):
        db = get_db()
        if not db: return None
        
        full_name = data.get('full_name') or data.get('participant_name')
        phone = data.get('phone')
        institution = data.get('institution')
        student_class = data.get('student_class') or data.get('class')
        ref_email = data.get('ref_email')
        txid = data.get('transaction_id') or data.get('txid')
        user_id = data.get('user_id') or data.get('member_id')
        event_id = data.get('event_id')
        status = data.get('status', 'pending')

        # 1. Attempt insert with dedicated columns (full_name, phone, institution, student_class)
        sql_data = {
            "event_id": event_id,
            "member_id": user_id,
            "ref_email": ref_email,
            "transaction_id": txid,
            "status": status,
            "full_name": full_name,
            "phone": phone,
            "institution": institution,
            "student_class": student_class
        }
        
        try:
            response = db.table("payments").insert(sql_data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            # 2. Fallback to basic columns if custom columns not yet executed in Supabase SQL Editor
            try:
                fallback_data = {
                    "event_id": event_id,
                    "member_id": user_id,
                    "ref_email": ref_email,
                    "transaction_id": txid,
                    "status": status
                }
                response = db.table("payments").insert(fallback_data).execute()
                return response.data[0]['id'] if response.data else None
            except Exception as e2:
                print(f"Fallback insert error: {e2}")
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
        institution = data.get('institution', '').strip() or 'Mohammadpur Preparatory School & College'
        student_class = data.get('student_class', '').strip() or 'N/A'
        txid = data.get('transaction_id', '').strip() or data.get('txid', '').strip() or 'FREE-EVENT-REG'

        # If not logged in, check if an existing member account matches this email
        if not user_id and email:
            try:
                user_res = db.table("users").select("id, role").eq("email", email).execute()
                if user_res.data and user_res.data[0].get('role') != 'guest':
                    user_id = user_res.data[0]['id']
            except Exception as u_err:
                print(f"User lookup note: {u_err}")

        # Metadata dictionary for accurate tracking
        meta_dict = {
            "participant_name": full_name,
            "phone": phone,
            "email": email,
            "student_class": student_class,
            "institution": institution,
            "transaction_id": txid,
            "source": "online",
            "submitted_at": datetime.datetime.now().isoformat()
        }

        # Save metadata to local file as backup cache
        save_registration_metadata(None, txid, meta_dict)

        # Store JSON string in ref_email as double-protection in Supabase
        cloud_ref_payload = json.dumps(meta_dict)

        # Insert a payment record for each selected event
        created_ids = []
        for ev_id in event_ids:
            payment_item = {
                "event_id": ev_id,
                "user_id": user_id,
                "full_name": full_name,
                "phone": phone,
                "institution": institution,
                "student_class": student_class,
                "ref_email": cloud_ref_payload,
                "transaction_id": txid,
                "status": "pending"
            }
            try:
                res = Payment.create(payment_item)
                if res:
                    created_ids.append(res)
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
