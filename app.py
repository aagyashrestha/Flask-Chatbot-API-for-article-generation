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
DRIVE_FOLDER_ID = ""

def authenticate_google():
    """ Authenticate Google Sheets and Google Drive services """
    try:
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

        sheets_service = build("sheets", "v4", credentials=creds)  # Build Google Sheets service
        drive_service = build("drive", "v3", credentials=creds)  # Build Google Drive service

        return sheets_service, drive_service
    except Exception as e:
        raise Exception(f"Google authentication error: {str(e)}")

def get_google_sheets_data():
    """ Retrieve topics and descriptions from Google Sheets """
    try:
        sheets_service, _ = authenticate_google()  # Authenticate and get sheets service
        result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()  # Fetch data from Google Sheets
        values = result.get("values", [])

        topics_descriptions = [{"topic": row[0], "description": row[1]} for row in values if len(row) >= 2]  # Organize rows into dictionary
        return topics_descriptions
    except Exception as e:
        raise Exception(f"Failed to get Google Sheets data: {str(e)}")

def generate_article(topic, description):
    """ Generate an article using OpenAI GPT-3.5 Turbo """
    try:
        prompt = f"Write an article about {topic} based on this description: {description}. Provide clear sections with headings."

        response = client.chat.completions.create(  # Request completion from OpenAI's GPT-3.5 model
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional article writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )

        article = response.choices[0].message.content.strip()  # Extract article content from response
        sections = article.split("\n\n")  # Split article into sections
        structured_article = {
            "title": topic,
            "sections": [{"heading": sec.split("\n")[0], "content": "\n".join(sec.split("\n")[1:])} for sec in sections if sec]
        }
        return structured_article
    except Exception as e:
        raise Exception(f"Failed to generate article: {str(e)}")

def save_to_google_drive(article_json):
    """ Save generated article as a JSON file to a specific folder in Google Drive """
    try:
        _, drive_service = authenticate_google()  # Authenticate and get drive service

        file_metadata = {
            "name": f'{article_json["title"]}.json',  # Set the file name
            "mimeType": "application/json",
            "parents": [DRIVE_FOLDER_ID]  # Google Drive Folder ID to save the file in
        }

        media = MediaIoBaseUpload(io.BytesIO(json.dumps(article_json).encode()), mimetype="application/json")  # Convert article to JSON and upload

        file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()  # Create the file on Google Drive
        return file.get("id")  # Return the file ID
    except Exception as e:
        raise Exception(f"Failed to save to Google Drive: {str(e)}")

@app.route("/automate_all", methods=["GET"])
def automate_all():
    """ Automates the entire process: Fetch from Sheets -> Generate Article -> Save to Drive """
    try:
        # Step 1: Fetch topics and descriptions from Google Sheets
        topics_descriptions = get_google_sheets_data()
        if not topics_descriptions:
            return jsonify({"error": "No data found in Google Sheets"}), 400

        results = []
        
        # Step 2: Process all topics
        for topic_description in topics_descriptions:
            topic, description = topic_description["topic"], topic_description["description"]

            if not topic or not description:
                continue  # Skip if data is incomplete

            # Step 3: Generate an article using OpenAI
            article_json = generate_article(topic, description)

            # Step 4: Save the article to Google Drive
            file_id = save_to_google_drive(article_json)

            # Step 5: Collect results
            results.append({
                "topic": topic,
                "status": "Article generated and saved",
                "file_id": file_id
            })

        return jsonify({"message": "All articles processed", "results": results})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)  # Run Flask app in debug mode
