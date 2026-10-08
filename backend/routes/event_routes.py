from flask import Blueprint, jsonify, request
from backend.models.event import Event
from backend.config.db import get_db
from flask_login import login_required, current_user
import os
import json

event_bp = Blueprint('events', __name__)

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
        "title": "MPSC IT Fest & Competitions 2026",
        "description": "Welcome to the flagship event of MPSC IT Club! Explore all segment competitions organized under this program below. Select the events tailored to your class and confirm your participation.",
        "date": "Upcoming Season / 2026",
        "venue": "MPSC Main Campus",
        "banner": ""
    }

@event_bp.route('/main_fest', methods=['GET'])
def main_fest():
    return jsonify(get_main_fest_data())

@event_bp.route('/', methods=['GET'])
def get_events():
    user_cat = request.args.get('category', '').lower().strip()
    events = Event.get_all()
    
    if user_cat and user_cat != 'all':
        filtered = []
        for ev in events:
            ev_cat = (ev.get('category') or 'all').lower().strip()
            cats = [c.strip() for c in ev_cat.split(',') if c.strip()]
            if 'all' in cats or 'open' in cats or 'open for all' in cats or not cats:
                filtered.append(ev)
            elif user_cat in cats:
                filtered.append(ev)
        return jsonify(filtered)
    
    return jsonify(events)

@event_bp.route('/<event_id>', methods=['GET'])
def get_single_event(event_id):
    event = Event.get_by_id(event_id)
    if event:
        return jsonify(event)
    return jsonify({"error": "Event not found"}), 404
