from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# ---------------- USER ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


# ---------------- PATIENT ----------------
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    disease = db.Column(db.String(200))


# ---------------- PRESCRIPTION ----------------
class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer)

    image = db.Column(db.String(255))

    extracted_text = db.Column(db.Text)

    doctor_name = db.Column(db.String(100))

    patient_name = db.Column(db.String(100))

    medicines = db.Column(db.Text)

    diagnosis = db.Column(db.Text)

    tests = db.Column(db.Text)


# ---------------- BILL ----------------
class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100))
    medicine_name = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    total = db.Column(db.Float)

