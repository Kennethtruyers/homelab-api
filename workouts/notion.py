import requests
import os
import json

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28"
}

def fetch_notion_page(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    r = requests.get(url, headers=HEADERS)
    return r.json()

def fetch_all_rows(db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    results = []
    has_more = True
    payload = {}

    while has_more:
        res = requests.post(url, headers=HEADERS, json=payload).json()
        print(res)
        results.extend(res["results"])
        has_more = res.get("has_more", False)
        payload["start_cursor"] = res.get("next_cursor")

    return results

def fetch_all_workouts():
    return fetch_all_rows(os.getenv("NOTION_WORKOUTS_DB_ID"))

def fetch_all_exercises():
    return fetch_all_rows(os.getenv("NOTION_EXERCISES_DB_ID"))

def parse_workout(page):
    props = page["properties"]
    notion_id = page["id"].replace("-", "")
    date = props["Date"]["date"]["start"]
    personal_notes = get_rich_text(props["Personal Notes"])
    coach_notes = get_rich_text(props["Coach Notes"])
    metadata = flatten_notion_properties(page["properties"])
    return notion_id, date, personal_notes, coach_notes, metadata

def parse_exercise(page):
    props = page["properties"]
    exercise_name = props["Exercise"]["select"]["name"]

    # extract linked workout_id
    relation = props.get("Workout", {}).get("relation", [])
    if not relation:
        return None  # skip if unlinked

    workout_notion_id = relation[0]["id"].replace("-", "")

    variation = ' '.join(sorted(item["name"] for item in props["Variation"]["multi_select"]))
    sets = props["Sets"]["number"]
    reps = props["Reps"]["number"]
    weight = props["Weight"]["number"]
    rir = 0
    notes = get_rich_text(props["Notes"])
    metadata = flatten_notion_properties(page["properties"])

    return workout_notion_id, exercise_name, variation, sets, reps, weight, rir, notes, metadata

def get_rich_text(prop):
    texts = prop.get("rich_text", [])
    value = texts[0]["plain_text"] if texts else ""
    return value
    
def flatten_notion_properties(properties: dict) -> dict:
    """
    Flattens Notion property objects to a simple key-value dict based on type.
    """
    result = {}

    for key, prop in properties.items():
        prop_type = prop.get("type")
        value = None

        if prop_type == "rich_text":
            # Get first text block's plain_text
            texts = prop.get("rich_text", [])
            value = texts[0]["plain_text"] if texts else ""

        elif prop_type == "multi_select":
            value = [item["name"] for item in prop.get("multi_select", [])]

        elif prop_type == "select":
            selected = prop.get("select")
            value = selected["name"] if selected else None

        elif prop_type == "number":
            value = prop.get("number")

        elif prop_type == "date":
            date_obj = prop.get("date")
            value = date_obj.get("start") if date_obj else None

        elif prop_type == "checkbox":
            value = prop.get("checkbox")

        elif prop_type == "title":
            title = prop.get("title", [])
            value = title[0]["plain_text"] if title else ""

        elif prop_type == "url":
            value = prop.get("url")

        elif prop_type == "email":
            value = prop.get("email")

        elif prop_type == "phone_number":
            value = prop.get("phone_number")

        elif prop_type == "people":
            # Just extract names or emails (can be customized)
            people = prop.get("people", [])
            value = [person.get("name") or person.get("id") for person in people]

        elif prop_type == "relation":
            # Return list of related record IDs
            relations = prop.get("relation", [])
            value = [rel["id"] for rel in relations]

        elif prop_type == "status":
            value = prop.get("status", {}).get("name")

        elif prop_type in ["formula", "rollup", "created_by", "last_edited_by"]:
            # Ignore complex/computed/system fields
            continue

        else:
            print("Unsupported prop type" + prop_type)
            # If unsupported or unknown type, just ignore
            continue

        result[key.lower().replace(" ", "_")] = value

    return json.dumps(result)
