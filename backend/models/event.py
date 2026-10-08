from backend.config.db import get_db

class Event:
    @staticmethod
    def get_all():
        db = get_db()
        if not db: return []
        try:
            response = db.table("events").select("*").order("date", desc=False).execute()
            events = response.data if response.data else []
            for ev in events:
                if not ev.get('category'):
                    desc = ev.get('description', '') or ''
                    if desc.startswith('[') and ']' in desc:
                        cat_tag = desc[1:desc.index(']')].lower().strip()
                        ev['category'] = cat_tag
                    else:
                        ev['category'] = 'all'
            return events
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    @staticmethod
    def get_by_id(event_id):
        db = get_db()
        if not db: return None
        try:
            response = db.table("events").select("*").eq("id", event_id).execute()
            if response.data:
                ev = response.data[0]
                if not ev.get('category'):
                    desc = ev.get('description', '') or ''
                    if desc.startswith('[') and ']' in desc:
                        cat_tag = desc[1:desc.index(']')].lower().strip()
                        ev['category'] = cat_tag
                    else:
                        ev['category'] = 'all'
                return ev
            return None
        except Exception as e:
            print(f"Error fetching event by id: {e}")
            return None

    @staticmethod
    def create(data):
        db = get_db()
        if not db: return None
        try:
            response = db.table("events").insert(data).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            # If category column is not yet present in Supabase table schema, fallback
            if 'category' in data:
                clean_data = dict(data)
                cat = clean_data.pop('category', 'all')
                if cat and cat != 'all':
                    clean_data['description'] = f"[{cat.upper()}] " + (clean_data.get('description') or '')
                try:
                    response = db.table("events").insert(clean_data).execute()
                    return response.data[0]['id'] if response.data else None
                except Exception as err2:
                    print(f"Error creating event (fallback): {err2}")
                    return None
            print(f"Error creating event: {e}")
            return None

    @staticmethod
    def update_status(event_id, status):
        db = get_db()
        if not db: return
        try:
            db.table("events").update({"status": status}).eq("id", event_id).execute()
        except Exception as e:
            print(f"Error updating event status: {e}")
