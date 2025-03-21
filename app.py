from flask import Flask, request, jsonify, render_template, send_from_directory
import gspread
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

# Google Sheets API Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("../backend/key-design-364010-67c57aa990bb.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Copy of Lead Management").sheet1  # Change to your sheet name

@app.route('/')
def home():
    print("Serving index.html from:", os.path.abspath("../frontend/templates/index.html"))
    return render_template('index3.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    static_path = os.path.abspath("../frontend/static")
    print(f"Serving {filename} from {static_path}")
    return send_from_directory(static_path, filename)

"""@app.route("/")
def home():
    return render_template("index.html")  # Serve UI"""

@app.route("/add_lead", methods=["POST"])
def add_lead():
    data = request.json

    # Validate contact number (must be 10 digits)
    contact_number = str(data.get("Contact Number", "")).strip()
    if not contact_number.isdigit() or len(contact_number) != 10:
        return jsonify({"error": "Contact number must be exactly 10 digits."}), 400

    # Proceed with adding lead
    all_leads = sheet.get_all_values()
    last_id = 1 if len(all_leads) == 1 else max(
        int(lead[0].strip("'")) for lead in all_leads[1:] if lead[0].strip("'").isdigit()
    ) + 1

    # Date formatting
    date_of_entry = data.get("Date of Entry", "").strip()
    try:
        date_of_entry = datetime.strptime(date_of_entry, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        date_of_entry = datetime.now().strftime("%Y-%m-%d")

    new_lead = [
        last_id,  
        str(data.get("Full Name", "")).title().strip(),
        contact_number,  # Already validated
        str(data.get("Email", "")).strip(),
        str(data.get("Location", "")).strip(),
        str(data.get("Address", "")).strip(),
        str(data.get("Lead Source", "")).strip(),
        str(data.get("Lead Status", "")).strip(),
        date_of_entry,
        str(data.get("Assigned Sales Rep", "")).strip(),
        str(data.get("Notes", "")).strip(),
    ]

    sheet.append_row(new_lead)
    return jsonify({"message": "Lead added successfully"}), 201


@app.route("/get_leads", methods=["GET"])
def get_leads():
    leads = sheet.get_all_values()[1:]  # Skip header row
    cleaned_leads = []

    for lead in leads:
        cleaned_leads.append({
            "Lead ID": int(lead[0].lstrip("'").strip()) if lead[0].lstrip("'").strip().isdigit() else lead[0].strip(),
            "Full Name": lead[1].title().strip(),
            "Contact Number": lead[2].lstrip("'").strip(),
            "Email": lead[3].strip(),
            "Location": lead[4].strip(),
            "Address": lead[5].strip(),
            "Lead Source": lead[6].strip(),
            "Lead Status": lead[7].strip(),
            "Date of Entry": lead[8].lstrip("'").strip(),
            "Assigned Sales Rep": lead[9].strip(),
            "Notes": lead[10].strip(),
        })

    return jsonify(cleaned_leads)


@app.route("/update_lead", methods=["POST"])
def update_lead():
    data = request.json
    leads = sheet.get_all_records()
    for i, lead in enumerate(leads, start=2):  # Row starts from 2 (excluding headers)
        if lead["Lead ID"] == data.get("Lead ID"):
            sheet.update_cell(i, 7, data.get("Lead Status"))  # Update status column
            return jsonify({"message": "Lead updated successfully"})
    return jsonify({"error": "Lead not found"}), 404


@app.route("/search_leads", methods=["GET"])
def search_leads():
    lead_id = request.args.get("lead_id")
    name = request.args.get("name")
    contact = request.args.get("contact")

    leads = sheet.get_all_records()
    filtered_leads = []

    for lead in leads:
        if (lead_id and str(lead["Lead ID"]) == lead_id) or \
           (name and name.lower() in lead["Full Name"].lower()) or \
           (contact and str(lead["Contact Number"]) == contact):
            filtered_leads.append(lead)

    if filtered_leads:
        return jsonify(filtered_leads)
    else:
        return jsonify({"message": "No matching leads found"}), 404


@app.route('/filter_leads', methods=['GET'])
def filter_leads():
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not (start_date and end_date):
        return jsonify({'error': 'Missing date parameters'}), 400

    # Ensure the correct date format
    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    # Fetch all leads from Google Sheets
    leads_data = sheet.get_all_records()

    # Filter leads based on the date range and status
    filtered_leads = []
    for lead in leads_data:
        try:
            lead_date = datetime.strptime(lead['Date of Entry'], "%Y-%m-%d")
            if start_date <= lead_date <= end_date and (not status or lead['Lead Status'] == status):
                filtered_leads.append(lead)
        except ValueError:
            continue  # Skip records with invalid date formats

    return jsonify(filtered_leads)

@app.route("/delete_lead", methods=["POST"])
def delete_lead():
    data = request.json
    lead_id = data.get("Lead ID")

    if not lead_id:
        return jsonify({"error": "Lead ID is required"}), 400

    leads = sheet.get_all_records()
    for i, lead in enumerate(leads, start=2):  # Rows start at index 2 (excluding headers)
        if str(lead["Lead ID"]) == str(lead_id):
            sheet.delete_rows(i)
            return jsonify({"message": "Lead deleted successfully"}), 200

    return jsonify({"error": "Lead not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
