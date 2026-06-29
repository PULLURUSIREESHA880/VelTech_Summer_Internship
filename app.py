from flask import Flask, render_template, request, redirect, flash
from flask_login import LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import os

from config import Config
from models import db, User, Patient, Prescription, Bill
from services.ocr_service import extract_text
from flask_migrate import Migrate
MEDICINE_PRICES = {
    "Paracetamol": 50,
    "Amoxicillin": 120,
    "Ibuprofen": 80,
    "Vitamin C": 30
}

app = Flask(__name__)
app.config.from_object(Config)

# ================= Upload Folder =================
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already exists!")
            return redirect("/register")

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash("Registration Successful!")
        return redirect("/login")

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect("/dashboard")

        flash("Invalid Email or Password")

    return render_template("login.html")


# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# ================= PATIENT LIST =================
@app.route("/patients")
@login_required
def patients():
    patients = Patient.query.all()
    return render_template("patients.html", patients=patients)


# ================= ADD PATIENT =================
@app.route("/add_patient", methods=["GET", "POST"])
@login_required
def add_patient():
    if request.method == "POST":
        patient = Patient(
            name=request.form["name"],
            age=request.form["age"],
            gender=request.form["gender"],
            phone=request.form["phone"],
            disease=request.form["disease"]
        )
        db.session.add(patient)
        db.session.commit()
        flash("Patient Added Successfully!")
        return redirect("/patients")

    return render_template("add_patient.html")


# ================= SEARCH PATIENT =================
@app.route("/patients/search")
@login_required
def search_patient():
    keyword = request.args.get("keyword", "")
    patients = Patient.query.filter(Patient.name.contains(keyword)).all()
    return render_template("patients.html", patients=patients, keyword=keyword)


# ================= EDIT PATIENT =================
@app.route("/edit_patient/<int:id>", methods=["GET", "POST"])
@login_required
def edit_patient(id):
    patient = Patient.query.get_or_404(id)
    if request.method == "POST":
        patient.name = request.form["name"]
        patient.age = request.form["age"]
        patient.gender = request.form["gender"]
        patient.phone = request.form["phone"]
        patient.disease = request.form["disease"]

        db.session.commit()
        flash("Patient Updated Successfully!")
        return redirect("/patients")

    return render_template("edit_patient.html", patient=patient)


# ================= DELETE PATIENT =================
@app.route("/delete_patient/<int:id>")
@login_required
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()
    flash("Patient Deleted Successfully!")
    return redirect("/patients")


# ================= UPLOAD PRESCRIPTION =================
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_prescription():
    if request.method == "POST":
        patient_name = request.form.get("patient_name")
        file = request.files.get("file")

        if file and patient_name:
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(upload_path)

            # Save prescription
            prescription = Prescription(patient_name=patient_name, image=filename)
            db.session.add(prescription)
            db.session.commit()

            # ✅ OCR extract text
            text = extract_text(upload_path)

            # Example: "Paracetamol 2, Ibuprofen 1"
            items = text.split(",")
            total_amount = 0
            for item in items:
                parts = item.strip().split()
                if len(parts) == 2:
                    med_name, qty = parts[0], int(parts[1])
                    price = MEDICINE_PRICES.get(med_name, 0)
                    total_amount += price * qty

                    bill = Bill(
                        patient_name=patient_name,
                        medicine_name=med_name,
                        quantity=qty,
                        total=price * qty
                    )
                    db.session.add(bill)

            db.session.commit()

            flash("Prescription uploaded & bill generated successfully!")
            return redirect(f"/bill_pdf/{patient_name}")
        else:
            flash("Please fill all fields!")

    return render_template("upload.html")



# ================= PRESCRIPTION LIST =================
@app.route("/prescription")
@login_required
def prescription():
    prescriptions = Prescription.query.all()
    return render_template("prescription.html", prescriptions=prescriptions)



# ================= BILLING =================
@app.route("/billing")
@login_required
def billing():
    bills = Bill.query.filter(Bill.patient_name != None).all()
    return render_template("billing.html", bills=bills)


@app.route("/generate_bill", methods=["POST"])
@login_required
def generate_bill():
    patient_name = request.form.get("patient_name")
    medicine_name = request.form.get("medicine_name")
    quantity = request.form.get("quantity")
    total_amount = request.form.get("total_amount")

    if not patient_name or not medicine_name or not quantity or not total_amount:
        flash("Please fill all fields!")
        return redirect("/billing")

    bill = Bill(
        patient_name=patient_name,
        medicine_name=medicine_name,
        quantity=int(quantity),
        total=float(total_amount)
    )
    db.session.add(bill)
    db.session.commit()

    flash("Bill generated successfully!")
    bills = Bill.query.filter(Bill.patient_name != None).all()
    return render_template("billing.html", bills=bills)


# ================= AUTO BILL GENERATION =================
@app.route("/generate_bill_auto/<patient_name>")
@login_required
def generate_bill_auto(patient_name):
    # Example: fixed medicine and price logic
    medicine_name = "Paracetamol"
    quantity = 5
    price_per_unit = 50
    total_amount = quantity * price_per_unit

    # Create and save the new bill
    bill = Bill(
        patient_name=patient_name,
        medicine_name=medicine_name,
        quantity=quantity,
        total=total_amount
    )
    db.session.add(bill)
    db.session.commit()

    flash(f"Bill generated automatically for {patient_name}!")

    # ✅ Only show the latest bill for this patient
    bills = Bill.query.filter_by(patient_name=patient_name).order_by(Bill.id.desc()).limit(1).all()
    return render_template("billing.html", bills=bills)



# ================= CLEANUP OLD BILLS =================
@app.route("/cleanup_bills")
def cleanup_bills():
    Bill.query.filter(Bill.patient_name == None).delete()
    db.session.commit()   # ✅ fixed commit call
    return "Old test bills removed!"


# ================= HISTORY =================
# ================= HISTORY =================
@app.route("/history")
@login_required
def history():
    # Fetch all patients, prescriptions, and bills
    patients = Patient.query.all()
    prescriptions = Prescription.query.all()
    bills = Bill.query.filter(Bill.patient_name != None).all()

    return render_template(
        "history.html",
        patients=patients,
        prescriptions=prescriptions,
        bills=bills
    )



# ================= MAIN =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
