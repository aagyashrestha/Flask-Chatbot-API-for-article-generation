<img width="638" alt="Screenshot 2025-04-04 at 10 29 51 PM" src="https://github.com/user-attachments/assets/40f3c1e6-f506-46c1-a380-a4be6cc09a72" />
<img width="1013" alt="Screenshot 2025-04-04 at 10 30 13 PM" src="https://github.com/user-attachments/assets/cb18f3aa-6064-4ea3-a19c-e43b0f2a2a58" />
# 📝 Google Sheets + OpenAI Article Generator

This Python Flask app automates article generation using OpenAI's GPT model based on data from a Google Sheet and stores the results in a Google Drive folder as JSON files. It also updates the original sheet with the article status and link.

---

## 🚀 Features

- Extracts topics and descriptions from a Google Sheet
- Uses OpenAI GPT (gpt-3.5-turbo) to generate structured articles
- Saves generated articles as JSON files in a specified Google Drive folder
- Automatically updates the Google Sheet with:
  - Status of generation
  - Link to the saved JSON file

---

## 📦 Requirements

- Python 3.8+
- Google Cloud service account with:
  - Sheets API enabled
  - Drive API enabled
- OpenAI API key

---

## 🔧 Setup

1. **Clone the repository**

```bash
git clone https://github.com/your-repo/article-generator.git
cd article-generator

## 🔧 Install Dependencies

```bash
pip install -r requirements.txt


# 🔐 Set Up Your Service Account

1. Create a service account in **Google Cloud Console**.
2. Enable the following APIs:
   - Google Sheets API
   - Google Drive API
3. Download the service account **JSON key file**.
4. Rename it to `service_account.json`.
5. Share your Google Sheet and Google Drive folder with the **service account email**.

---

# 🔑 Configure Your OpenAI API Key

Replace the following line in your Python script with your actual OpenAI API key:

```python
client = OpenAI(api_key="your_openai_api_key")


## 📄 Google Sheet Format

Your sheet should have the following columns in **Sheet1**:

| Topic           | Description                             | Status        | Link                          |
|-----------------|-----------------------------------------|---------------|-------------------------------|
| AI in Healthcare | Discusses applications of AI in health | (auto-filled) | (auto-filled with Drive link) |

- **Topic** and **Description** are required.
- **Status** and **Link** will be auto-updated by the app.

---

## 📁 Google Drive Folder

- Must be a **valid Drive folder** shared with the service account.
- Generated **JSON articles** will be uploaded here automatically.


## 🧪 Example Request

Send a **POST** request to `/automate_all` with the following JSON body:

```json
{
  "sheet_url": "https://docs.google.com/spreadsheets/d/your_sheet_id/edit",
  "drive_folder_url": "https://drive.google.com/drive/folders/your_folder_id"
}


⚙️ How It Works
Extracts the Sheet ID and Folder ID from the URLs.

Reads topic and description data from the Google Sheet.

Generates an article using OpenAI's GPT model.

Saves the article as a JSON file in the specified Google Drive folder.

Updates the Google Sheet with:

✅ Status of generation

🔗 Link to the JSON file


📌 Notes
✅ Ensure your Google Sheet and Drive folder are shared with the service account.

⚠️ The app currently processes up to 999 rows (from row 2 to 1000).

🛠️ The make_google_sheet_editable() function is included but commented out — you can enable it if needed.



🐍 Run the App

Run using Python:

python app.py
