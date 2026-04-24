# Deployment Plan

Status: Draft

## Scope
- Update the Flask app for Azure App Service Linux Container compatibility.
- Use absolute filesystem paths for the database and generated ticket images.
- Update the WhatsApp media URL to the Azure production base URL.
- Add `gunicorn` to the Python dependencies.

## Current Decisions
- App type: existing Flask web app
- Hosting target: Azure App Service Linux Container
- File storage: local container filesystem at `static/Tickets`
- Database: SQLite file stored at the application base directory

## Next Steps
- Update `requirements.txt`
- Refactor `app.py` path constants and database/image references
- Update Twilio media URL construction to use the Azure base URL
