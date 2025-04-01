from flask import Flask, request, jsonify
import openai
import json
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# Initialize Flask app
app = Flask(__name__)

# OpenAI API Key
OPENAI_API_KEY = ""  # Replace with your actual API key
client = openai.OpenAI(api_key=OPENAI_API_KEY)

SERVICE_ACCOUNT_FILE = "service_account.json" 
# Google Sheets spreadsheet ID and range
SPREADSHEET_ID = ''  # Replace with your Google Sheets spreadsheet ID
RANGE_NAME = 'Sheet1!A2:B'  # Replace with the appropriate range in your sheet (columns A and B for topic/description)

def authenticate_google():
    """ Authenticate Google Sheets and Google Drive services """
    try:
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        sheets_service = build("sheets", "v4", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)

        return sheets_service, drive_service
    except Exception as e:
        raise Exception(f"Google authentication error: {str(e)}")

def get_google_sheets_data():
    """ Retrieve topics and descriptions from Google Sheets """
    try:
        sheets_service, _ = authenticate_google()
        result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])

        topics_descriptions = [{"topic": row[0], "description": row[1]} for row in values if len(row) >= 2]
        return topics_descriptions
    except Exception as e:
        raise Exception(f"Failed to get Google Sheets data: {str(e)}")

def generate_article(topic, description):
    """ Generate an article using OpenAI GPT-3.5 Turbo """
    try:
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

        article = response.choices[0].message.content.strip()
        sections = article.split('\n\n')
        structured_article = {
            "title": topic,
            "sections": [{"heading": sec.split('\n')[0], "content": '\n'.join(sec.split('\n')[1:])} for sec in sections if sec]
        }
        return structured_article
    except Exception as e:
        raise Exception(f"Failed to generate article: {str(e)}")

def save_to_google_drive(article_json):
    """ Save generated article as a JSON file to a specific folder in Google Drive """
    try:
        _, drive_service = authenticate_google()

        file_metadata = {
            'name': f'{article_json["title"]}.json',
            'mimeType': 'application/json',
            'parents': ['1HfcSM7LFWcqtbWzQsPxmLiOroYKPnfHc']  # Replace with your Google Drive Folder ID
        }
        
        media = MediaIoBaseUpload(io.BytesIO(json.dumps(article_json).encode()), mimetype='application/json')

        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        raise Exception(f"Failed to save to Google Drive: {str(e)}")


@app.route("/generate_article", methods=["GET"])
def generate_and_save_article():
    """ API to generate an article and save it to Google Drive """
    try:
        # Fetch topics and descriptions from Google Sheets
        topics_descriptions = get_google_sheets_data()

        if not topics_descriptions:
            return jsonify({"error": "No data found in Google Sheets"}), 400

        # Select the first topic and description (or loop through all to generate multiple articles)
        topic_description = topics_descriptions[0]
        topic, description = topic_description["topic"], topic_description["description"]

        if not topic or not description:
            return jsonify({"error": "Topic and description are required"}), 400

        # Generate article using OpenAI
        article_json = generate_article(topic, description)
        
        # Save article to Google Drive
        file_id = save_to_google_drive(article_json)

        return jsonify({"message": "Article generated and saved to Google Drive", "file_id": file_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_sheets_data", methods=["GET"])
def get_sheets_data():
    """ API to fetch Google Sheets data """
    try:
        data = get_google_sheets_data()
        return jsonify({"topics_descriptions": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/test_openai", methods=["GET"])
def test_openai():
    """ Test OpenAI connection """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10
        )
        return jsonify({"status": "OpenAI connection successful", "response": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": f"OpenAI connection failed: {str(e)}"}), 500

@app.route("/test_sheets", methods=["GET"])
def test_sheets():
    """ Test Google Sheets connection """
    try:
        data = get_google_sheets_data()
        return jsonify({"status": "Google Sheets connection successful", "data": data})
    except Exception as e:
        return jsonify({"error": f"Google Sheets connection failed: {str(e)}"}), 500

@app.route("/test_google_auth", methods=["GET"])
def test_google_auth():
    """ Test Google authentication """
    try:
        sheets_service, drive_service = authenticate_google()
        return jsonify({
            "status": "Google authentication successful", 
            "sheets_service": "Connected" if sheets_service else "Failed",
            "drive_service": "Connected" if drive_service else "Failed"
        })
    except Exception as e:
        return jsonify({"error": f"Google authentication failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)