from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from backend.config.db import get_db
from backend.models.payment import Payment
from backend.models.event import Event

payment_bp = Blueprint('payments', __name__)

@payment_bp.route('/submit', methods=['POST'])
def submit_payment():
    """
    Accepts event registration & payment verification for:
    - Logged-in club members
    - Guest participants
    - Single or multiple selected events
    """
    try:
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
            if 'event_ids[]' in request.form:
                data['event_ids'] = request.form.getlist('event_ids[]')
            elif 'event_ids' in request.form:
                data['event_ids'] = request.form.getlist('event_ids')

        # Normalize event_ids
        event_ids = data.get('event_ids')
        if not event_ids:
            single_id = data.get('event_id')
            event_ids = [single_id] if single_id else []
        elif isinstance(event_ids, str):
            event_ids = [e.strip() for e in event_ids.split(',') if e.strip()]

        if not event_ids:
            return jsonify({"error": "Please select at least one event to participate."}), 400

        # Extract contact information
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip() or data.get('ref_email', '').strip()
        phone = data.get('phone', '').strip()
        institution = data.get('institution', '').strip()
        student_class = data.get('student_class', '').strip() or data.get('class', '').strip()
        txid = data.get('txid', '').strip() or data.get('transaction_id', '').strip()

        # If user is logged in, autofill missing fields
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
            if not full_name: full_name = getattr(current_user, 'full_name', '')
            if not email: email = getattr(current_user, 'email', '')
            if not phone: phone = getattr(current_user, 'phone', '')
            if not institution: institution = getattr(current_user, 'institution', 'MPSC')
            if not student_class: student_class = getattr(current_user, 'section', '')

        # Basic validations
        if not email or not phone or not full_name:
            return jsonify({"error": "Full Name, Email Address, and Phone/WhatsApp Number are required."}), 400

        # Verify whether payment is required
        total_fee = 0
        events_details = []
        for eid in event_ids:
            ev = Event.get_by_id(eid)
            if ev:
                fee = int(ev.get('fee', 0) or 0)
                total_fee += fee
                events_details.append({"id": ev.get('id'), "title": ev.get('title'), "fee": fee})

        if total_fee > 0 and not txid:
            return jsonify({"error": f"Transaction ID (TxID) is required for paid events (Total: {total_fee} BDT)."}), 400

        if total_fee == 0 and not txid:
            txid = "FREE-EVENT-REG"

        # Submit bulk payment records
        payload = {
            "event_ids": event_ids,
            "user_id": user_id,
            "full_name": full_name,
            "email": email,
            "ref_email": email,
            "phone": phone,
            "institution": institution,
            "student_class": student_class,
            "transaction_id": txid
        }

        created = Payment.create_bulk(payload)
        
        return jsonify({
            "success": True,
            "message": "Registration submitted successfully! Please wait for EC verification.",
            "total_fee": total_fee,
            "events_count": len(event_ids),
            "events": events_details,
            "participant": {
                "name": full_name,
                "email": email,
                "phone": phone,
                "institution": institution,
                "class": student_class,
                "txid": txid
            }
        }), 201

    except Exception as e:
        print(f"Error submitting payment: {e}")
        return jsonify({"error": str(e)}), 500

@payment_bp.route('/history')
@login_required
def payment_history():
    history = Payment.get_by_user(current_user.id)
    return jsonify(history)

# Admin Routes
@payment_bp.route('/all_pending')
@login_required
def all_pending():
    if current_user.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    payments = Payment.get_all()
    pending = [p for p in payments if p.get('status') == 'pending']
    return jsonify(pending)

@payment_bp.route('/verify', methods=['POST'])
@login_required
def verify_payment():
    if current_user.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    Payment.verify(data['id'], data['status'])
    return jsonify({"success": "Payment status updated"}), 200
