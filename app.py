
import os
import json
import re
from openai import OpenAI
from flask import Flask, request, jsonify
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io

client = OpenAI(api_key="")  # Replace with your actual OpenAI API key

app = Flask(__name__)

SPREADSHEET_ID = None
DRIVE_FOLDER_ID = None

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'

def get_google_sheets_service():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def get_google_drive_service():
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def extract_google_sheet_id(url):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    raise Exception("Invalid Google Sheets URL")

def extract_google_drive_folder_id(url):
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    raise Exception("Invalid Google Drive Folder URL")

def make_google_sheet_editable(sheet_id):
    drive = get_google_drive_service()
    permission = {'type': 'anyone', 'role': 'writer'}
    drive.permissions().create(fileId=sheet_id, body=permission, fields='id').execute()

def make_drive_folder_editable(folder_id):
    drive = get_google_drive_service()
    permission = {'type': 'anyone', 'role': 'writer'}
    drive.permissions().create(fileId=folder_id, body=permission, fields='id').execute()

def get_google_sheets_data():
    service = get_google_sheets_service()
    header = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='Sheet1!1:1').execute()
    header_row = header.get('values', [[]])[0]

    topic_idx = description_idx = status_idx = link_idx = None
    for i, col in enumerate(header_row):
        name = col.strip().lower()
        if name == 'topic':
            topic_idx = i
        elif name == 'description':
            description_idx = i
        elif name == 'status':
            status_idx = i
        elif name == 'link':
            link_idx = i

    if topic_idx is None or description_idx is None:
        raise Exception("Missing 'topic' or 'description' columns.")

    rows = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='Sheet1!2:1000').execute()
    values = rows.get('values', [])

    data = []
    for row in values:
        topic = row[topic_idx] if len(row) > topic_idx else None
        desc = row[description_idx] if len(row) > description_idx else None
        status = row[status_idx] if status_idx is not None and len(row) > status_idx else ""
        link = row[link_idx] if link_idx is not None and len(row) > link_idx else ""
        if topic and desc and (not status or not link):
            data.append({'topic': topic, 'description': desc})
    return data

def generate_article(topic, description):
    prompt = f"Write an article about {topic} based on this description: {description}. Provide clear sections with headings."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional article writer."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        temperature=0.7
    )
    content = response.choices[0].message.content.strip()
    sections = content.split("\n\n")
    return {
        "title": topic,
        "sections": [{"heading": sec.split("\n")[0], "content": "\n".join(sec.split("\n")[1:])} for sec in sections if sec]
    }

def save_to_google_drive(article_json):
    service = get_google_drive_service()
    file_name = f"{article_json['title']}_article.json"
    file_data = json.dumps(article_json).encode()
    media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype='application/json')
    metadata = {'name': file_name, 'parents': [DRIVE_FOLDER_ID]}
    file = service.files().create(body=metadata, media_body=media, fields='id').execute()
    return file['id']

def update_sheet_with_results_dynamic(results):
    service = get_google_sheets_service()

    headers = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Sheet1!1:1'
    ).execute().get('values', [[]])[0]

    topic_idx = status_idx = link_idx = None
    for i, col in enumerate(headers):
        name = col.strip().lower()
        if name == 'topic':
            topic_idx = i
        elif name == 'status':
            status_idx = i
        elif name == 'link':
            link_idx = i

    if topic_idx is None or status_idx is None or link_idx is None:
        raise Exception("Missing required columns: topic, status, or link.")

    rows = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Sheet1!2:1000'
    ).execute().get('values', [])

    updated_rows = []
    for row in rows:
        topic_cell = row[topic_idx].strip().lower() if len(row) > topic_idx else None
        match = next((r for r in results if r['topic'].strip().lower() == topic_cell), None)

        if match:
            while len(row) <= max(status_idx, link_idx):
                row.append("")
            row[status_idx] = match['status']
            row[link_idx] = match['link'] or ""
        updated_rows.append(row)

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f'Sheet1!2:{len(updated_rows)+1}',
        valueInputOption='RAW',
        body={'values': updated_rows}
    ).execute()

@app.route("/automate_all", methods=["POST"])
def automate_all():
    try:
        data = request.get_json()
        global SPREADSHEET_ID, DRIVE_FOLDER_ID
        SPREADSHEET_ID = extract_google_sheet_id(data.get("sheet_url"))
        DRIVE_FOLDER_ID = extract_google_drive_folder_id(data.get("drive_folder_url"))

        #make_google_sheet_editable(SPREADSHEET_ID)
        make_drive_folder_editable(DRIVE_FOLDER_ID)

        topics_descriptions = get_google_sheets_data()
        if not topics_descriptions:
            return jsonify({"error": "No data found"}), 400

        results = []
        for item in topics_descriptions:
            topic = item['topic']
            description = item['description']
            try:
                article = generate_article(topic, description)
                file_id = save_to_google_drive(article)
                results.append({
                    "topic": topic,
                    "status": "Article generated and saved",
                    "file_id": file_id,
                    "link": f"https://drive.google.com/file/d/{file_id}/view"
                })
            except Exception as e:
                print(f"[ERROR] Failed for topic '{topic}': {str(e)}")
                results.append({
                    "topic": topic,
                    "status": "Error while generating article",
                    "file_id": None,
                    "link": "Error while generating link"
                })

        update_sheet_with_results_dynamic(results)

        return jsonify({
            "message": "All articles processed",
            "results": results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
