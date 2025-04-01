from flask import Flask, request, jsonify  # Importing necessary modules from Flask
import openai  # Importing OpenAI module for article generation
import json  # Importing JSON module for handling JSON data
import io  # Importing IO module for handling in-memory byte streams
from googleapiclient.discovery import build  # Importing build function from googleapiclient for Google API client
from googleapiclient.http import MediaIoBaseUpload  # Importing MediaIoBaseUpload for uploading files to Google Drive
from google.oauth2 import service_account  # Importing service_account for authenticating Google API access

# Initialize Flask app
app = Flask(__name__)  # Creating an instance of the Flask class for the web app

# OpenAI API Key
OPENAI_API_KEY = ""  # Store OpenAI API key for GPT-3.5 access
client = openai.OpenAI(api_key=OPENAI_API_KEY)  # Creating OpenAI client instance with the provided API key

SERVICE_ACCOUNT_FILE = "service_account.json"  # Path to the service account JSON file for Google API authentication
# Google Sheets spreadsheet ID and range
SPREADSHEET_ID = ''  # Google Sheets spreadsheet ID
RANGE_NAME = 'Sheet1!A2:B'  # Range in the spreadsheet (columns A and B for topic/description)
DRIVE_FOLDER_ID = ""  # Google Drive folder ID where generated articles will be saved

def authenticate_google():
    """ Authenticate Google Sheets and Google Drive services """
    try:
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]  # Define Google Sheets and Drive API scopes
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)  # Load credentials from service account file

        # Build the Google Sheets and Drive API services
        sheets_service = build("sheets", "v4", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)

        return sheets_service, drive_service  # Return both Google Sheets and Drive service instances
    except Exception as e:
        raise Exception(f"Google authentication error: {str(e)}")  # Handle authentication errors

def get_google_sheets_data():
    """ Retrieve topics and descriptions from Google Sheets """
    try:
        sheets_service, _ = authenticate_google()  # Authenticate Google services
        result = sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()  # Fetch data from Google Sheets
        values = result.get("values", [])  # Get the list of rows from the response

        # Create a list of dictionaries containing topic and description from the fetched rows
        topics_descriptions = [{"topic": row[0], "description": row[1]} for row in values if len(row) >= 2]
        return topics_descriptions  # Return the list of topics and descriptions
    except Exception as e:
        raise Exception(f"Failed to get Google Sheets data: {str(e)}")  # Handle errors when fetching data

def generate_article(topic, description):
    """ Generate an article using OpenAI GPT-3.5 Turbo """
    try:
        prompt = f"Write an article about {topic} based on this description: {description}. Provide clear sections with headings."  # Create the prompt for GPT-3.5

        # Make a request to OpenAI to generate the article
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional article writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,  # Limit response to 1500 tokens
            temperature=0.7  # Set creativity of the response (0.7 is a balanced setting)
        )

        article = response.choices[0].message.content.strip()  # Extract the generated article from the response
        sections = article.split("\n\n")  # Split article into sections based on double newlines
        # Structure the article into title and sections
        structured_article = {
            "title": topic,
            "sections": [{"heading": sec.split("\n")[0], "content": "\n".join(sec.split("\n")[1:])} for sec in sections if sec]
        }
        return structured_article  # Return the structured article
    except Exception as e:
        raise Exception(f"Failed to generate article: {str(e)}")  # Handle errors during article generation

def save_to_google_drive(article_json):
    """ Save generated article as a JSON file to a specific folder in Google Drive """
    try:
        _, drive_service = authenticate_google()  # Authenticate Google services

        file_metadata = {
            "name": f'{article_json["title"]}.json',  # Set the file name as the article title
            "mimeType": "application/json",  # Set MIME type to JSON
            "parents": [DRIVE_FOLDER_ID]  # Set the folder ID in which the file will be saved
        }

        media = MediaIoBaseUpload(io.BytesIO(json.dumps(article_json).encode()), mimetype="application/json")  # Convert article to JSON format and prepare for upload

        # Create and upload the file to Google Drive
        file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        return file.get("id")  # Return the file ID of the uploaded file
    except Exception as e:
        raise Exception(f"Failed to save to Google Drive: {str(e)}")  # Handle errors during file upload

# Endpoint to test fetching data from Google Sheets
@app.route("/get_google_sheets_data", methods=["GET"])
def test_get_google_sheets_data():
    try:
        topics_descriptions = get_google_sheets_data()  # Fetch topics and descriptions from Google Sheets
        if not topics_descriptions:
            return jsonify({"error": "No data found in Google Sheets"}), 400  # Return error if no data is found
        return jsonify({"data": topics_descriptions}), 200  # Return the data if successful
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error if any exception occurs

# Endpoint to test OpenAI article generation
@app.route("/generate_article", methods=["POST"])
def test_generate_article():
    try:
        data = request.get_json()  # Get JSON data from the POST request
        topic = data.get("topic")  # Extract topic from the request data
        description = data.get("description")  # Extract description from the request data
        
        if not topic or not description:
            return jsonify({"error": "Topic and description are required"}), 400  # Return error if topic or description is missing
        
        article_json = generate_article(topic, description)  # Generate the article based on the topic and description
        return jsonify({"article": article_json}), 200  # Return the generated article as JSON
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error if any exception occurs

# Endpoint to test saving to Google Drive
@app.route("/save_to_drive", methods=["POST"])
def test_save_to_drive():
    try:
        data = request.get_json()  # Get JSON data from the POST request
        if not data:
            return jsonify({"error": "Article data is required"}), 400  # Return error if article data is missing
        
        file_id = save_to_google_drive(data)  # Save the article data to Google Drive and get the file ID
        return jsonify({"message": "File saved successfully", "file_id": file_id}), 200  # Return success message and file ID
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error if any exception occurs

# Endpoint to automate the entire process
@app.route("/automate_all", methods=["GET"])
def automate_all():
    try:
        # Step 1: Fetch topics and descriptions from Google Sheets
        topics_descriptions = get_google_sheets_data()
        if not topics_descriptions:
            return jsonify({"error": "No data found in Google Sheets"}), 400  # Return error if no data is found

        results = []  # Initialize a list to store results
        
        # Step 2: Process all topics
        for topic_description in topics_descriptions:
            topic, description = topic_description["topic"], topic_description["description"]

            if not topic or not description:
                continue  # Skip if topic or description is missing

            # Step 3: Generate an article using OpenAI
            article_json = generate_article(topic, description)

            # Step 4: Save the article to Google Drive
            file_id = save_to_google_drive(article_json)

            # Step 5: Collect results for each processed article
            results.append({
                "topic": topic,
                "status": "Article generated and saved",
                "file_id": file_id
            })

        return jsonify({"message": "All articles processed", "results": results})  # Return summary of results
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error if any exception occurs

if __name__ == "__main__":
    app.run(debug=True)  # Run the Flask app in debug mode
