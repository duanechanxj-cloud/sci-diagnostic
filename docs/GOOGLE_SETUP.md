# Google setup — V2.4.1 on macOS

V2.4.1 uses your chosen Google account to create one class-specific Form per class and fetch responses later.

## Google Cloud

1. Open Google Cloud Console.
2. Create a project for the Science Diagnostic app.
3. Enable **Google Forms API**.
4. Enable **Google Drive API**.
5. Configure the Google Auth Platform / OAuth consent screen.
6. For a personal account, create an **External** OAuth app and add your own account as a test user while developing.
7. Create an **OAuth client ID → Desktop app**.
8. Download the JSON file.

## In Streamlit

Open **Google Connection**, upload the Desktop OAuth JSON, then click **Connect Google account**. Your browser handles Google consent and the resulting token is stored locally under `private_data/google_auth/`.

## Requested scopes

- `forms.body` — create and manage Forms.
- `forms.responses.readonly` — retrieve submitted responses.
- `drive` — allow Admin to choose an existing Drive project folder and manage Sci Diagnostic files inside it.

## What V2.4.1 does when launching a class Form

1. Creates a new unpublished Google Form.
2. Disables email collection.
3. Keeps the Form as a normal Form rather than a Google Quiz.
4. Adds required **Class index number** as a dropdown using that class's configured index range.
5. Adds the selected Science MCQs.
6. Saves the Google question-ID ↔ local `Question_ID` mapping.
7. Publishes the Form and enables response collection.
8. Sets the published responder permission to **Anyone with the link**.
9. Generates a QR code from the responder URL.

The Form itself stores no pupil name and does not know the correct answers. Python marks responses locally from the approved Question Bank.


RC8+: reconnect Google once after upgrading from an older token because the Drive scope changed from `drive.file` to `drive`.
