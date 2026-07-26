from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    fullname = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    patient_number = db.Column(db.String(20), unique=True)
    national_id = db.Column(db.String(50))
    fullname = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(10))
    dob = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    sub_county = db.Column(db.String(80))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(120))
    emergency_phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LabRequest(db.Model):
    __tablename__ = "lab_requests"
    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(20), unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"))
    patient_name = db.Column(db.String(150))
    doctor = db.Column(db.String(120))
    test = db.Column(db.String(120))
    priority = db.Column(db.String(20))
    request_date = db.Column(db.String(20))
    clinical_notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Sample(db.Model):
    __tablename__ = "samples"
    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.String(20), unique=True)
    request_id = db.Column(db.Integer, db.ForeignKey("lab_requests.id"))
    patient_name = db.Column(db.String(150))
    sample_type = db.Column(db.String(50))
    collection_date = db.Column(db.String(20))
    collection_time = db.Column(db.String(20))
    technician = db.Column(db.String(120))
    status = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LabResult(db.Model):
    __tablename__ = "lab_results"
    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.String(20))
    patient_name = db.Column(db.String(150))
    test = db.Column(db.String(120))
    status = db.Column(db.String(20))
    result = db.Column(db.Text)
    tested_by = db.Column(db.String(120))
    date_tested = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResultValidation(db.Model):
    __tablename__ = "result_validations"
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey("lab_results.id"))
    sample_id = db.Column(db.String(20))
    patient_name = db.Column(db.String(150))
    test = db.Column(db.String(120))
    result = db.Column(db.Text)
    decision = db.Column(db.String(30))
    validator = db.Column(db.String(120))
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResultApproval(db.Model):
    __tablename__ = "result_approvals"
    id = db.Column(db.Integer, primary_key=True)
    validation_id = db.Column(db.Integer, db.ForeignKey("result_validations.id"))
    sample_id = db.Column(db.String(20))
    patient_name = db.Column(db.String(150))
    test = db.Column(db.String(120))
    validation_decision = db.Column(db.String(30))
    result_summary = db.Column(db.Text)
    decision = db.Column(db.String(30))
    approved_by = db.Column(db.String(120))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
