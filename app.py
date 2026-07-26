import os
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

from models import (
    db, User, Patient, LabRequest, Sample, LabResult,
    ResultValidation, ResultApproval
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "eldoret-lab-dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'eldoret_lab.db')}"
)
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace(
        "postgres://", "postgresql://", 1
    )
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def next_code(prefix, count):
    return f"{prefix}{str(count + 1).zfill(3 if prefix != 'SMP' else 4)}"


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["fullname"] = user.fullname
            return redirect(url_for("dashboard"))

        flash("Invalid Username or Password", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    patient_count = Patient.query.count()
    sample_count = Sample.query.count()
    approved_count = ResultApproval.query.count()
    recent_activity = (
        ResultApproval.query.order_by(ResultApproval.created_at.desc()).limit(10).all()
    )
    return render_template(
        "dashboard.html",
        fullname=session.get("fullname"),
        patient_count=patient_count,
        sample_count=sample_count,
        approved_count=approved_count,
        recent_activity=recent_activity,
    )


# ---------------------------------------------------------------------------
# Patient Management
# ---------------------------------------------------------------------------

@app.route("/patients")
@login_required
def patients():
    search = request.args.get("q", "").strip()
    query = Patient.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Patient.fullname.ilike(like)) | (Patient.patient_number.ilike(like))
        )
    all_patients = query.order_by(Patient.id).all()
    return render_template("patients.html", patients=all_patients, search=search)


@app.route("/patients/add", methods=["GET", "POST"])
@login_required
def add_patient():
    next_number = f"PAT{str(Patient.query.count() + 1).zfill(3)}"

    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        national_id = request.form.get("nationalId", "").strip()
        gender = request.form.get("gender", "")
        dob = request.form.get("dob", "")
        phone = request.form.get("phone", "").strip()

        if not all([fullname, national_id, gender, dob, phone]):
            flash("Please complete all required patient information.", "danger")
            return redirect(url_for("add_patient"))

        patient = Patient(
            patient_number=next_number,
            fullname=fullname,
            national_id=national_id,
            gender=gender,
            dob=dob,
            phone=phone,
            sub_county=request.form.get("subCounty", "").strip(),
            address=request.form.get("address", "").strip(),
            emergency_contact=request.form.get("emergencyContact", "").strip(),
            emergency_phone=request.form.get("emergencyPhone", "").strip(),
        )
        db.session.add(patient)
        db.session.commit()
        flash("Patient Registered Successfully.", "success")
        return redirect(url_for("patients"))

    return render_template("add_patient.html", next_number=next_number)


@app.route("/patients/<int:patient_id>/delete", methods=["POST"])
@login_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted.", "success")
    return redirect(url_for("patients"))


# ---------------------------------------------------------------------------
# Laboratory Requests
# ---------------------------------------------------------------------------

@app.route("/lab-request", methods=["GET", "POST"])
@login_required
def lab_request():
    next_number = f"LAB{str(LabRequest.query.count() + 1).zfill(3)}"
    all_patients = Patient.query.order_by(Patient.id).all()

    if request.method == "POST":
        patient_id = request.form.get("patient")
        doctor = request.form.get("doctor", "").strip()
        test = request.form.get("testType", "")
        priority = request.form.get("priority", "")
        request_date = request.form.get("requestDate", "")

        if not all([patient_id, doctor, test, priority]):
            flash("Please complete all required laboratory request details.", "danger")
            return redirect(url_for("lab_request"))

        patient = Patient.query.get(patient_id)
        req = LabRequest(
            request_number=next_number,
            patient_id=patient.id if patient else None,
            patient_name=patient.fullname if patient else "",
            doctor=doctor,
            test=test,
            priority=priority,
            request_date=request_date,
            clinical_notes=request.form.get("clinicalNotes", "").strip(),
        )
        db.session.add(req)
        db.session.commit()
        flash("Laboratory Request Submitted Successfully.", "success")
        return redirect(url_for("lab_request"))

    return render_template("lab_request.html", next_number=next_number, patients=all_patients)


@app.route("/lab-request-list")
@login_required
def lab_request_list():
    requests_ = LabRequest.query.order_by(LabRequest.id).all()
    return render_template("lab_request_list.html", requests=requests_)


# ---------------------------------------------------------------------------
# Sample Tracking
# ---------------------------------------------------------------------------

@app.route("/sample-tracking", methods=["GET", "POST"])
@login_required
def sample_tracking():
    next_id = f"SMP{str(Sample.query.count() + 1).zfill(4)}"
    open_requests = LabRequest.query.order_by(LabRequest.id).all()

    if request.method == "POST":
        request_id = request.form.get("requestNumber")
        sample_type = request.form.get("sampleType", "")
        collection_date = request.form.get("collectionDate", "")
        collection_time = request.form.get("collectionTime", "")
        technician = request.form.get("technician", "").strip()
        status = request.form.get("status", "")

        if not all([request_id, sample_type, collection_date, collection_time, technician, status]):
            flash("Please complete all sample tracking information.", "danger")
            return redirect(url_for("sample_tracking"))

        lab_req = LabRequest.query.get(request_id)
        sample = Sample(
            sample_id=next_id,
            request_id=lab_req.id if lab_req else None,
            patient_name=lab_req.patient_name if lab_req else "",
            sample_type=sample_type,
            collection_date=collection_date,
            collection_time=collection_time,
            technician=technician,
            status=status,
        )
        db.session.add(sample)
        db.session.commit()
        flash("Sample information saved successfully.", "success")
        return redirect(url_for("sample_tracking"))

    return render_template(
        "sample_tracking.html", next_id=next_id, requests=open_requests
    )


@app.route("/api/lab-request/<int:request_id>/patient")
@login_required
def api_request_patient(request_id):
    lab_req = LabRequest.query.get_or_404(request_id)
    return jsonify({"patient_name": lab_req.patient_name})


# ---------------------------------------------------------------------------
# Result Entry
# ---------------------------------------------------------------------------

@app.route("/result-entry", methods=["GET", "POST"])
@login_required
def result_entry():
    all_samples = Sample.query.order_by(Sample.id).all()

    if request.method == "POST":
        sample_id = request.form.get("resultSample", "")
        patient_name = request.form.get("resultPatient", "")
        test = request.form.get("labTest", "")
        status = request.form.get("resultStatus", "")
        result_text = request.form.get("result", "").strip()
        tested_by = request.form.get("testedBy", "").strip()
        date_tested = request.form.get("dateTested", "")

        if not all([sample_id, patient_name, test, status, result_text, tested_by, date_tested]):
            flash("Please complete all laboratory result details.", "danger")
            return redirect(url_for("result_entry"))

        lab_result = LabResult(
            sample_id=sample_id,
            patient_name=patient_name,
            test=test,
            status=status,
            result=result_text,
            tested_by=tested_by,
            date_tested=date_tested,
        )
        db.session.add(lab_result)
        db.session.commit()
        flash("Laboratory Result Saved Successfully.", "success")
        return redirect(url_for("result_entry"))

    return render_template("result_entry.html", samples=all_samples)


@app.route("/api/sample/<sample_id>")
@login_required
def api_sample(sample_id):
    sample = Sample.query.filter_by(sample_id=sample_id).first_or_404()
    return jsonify({"patient_name": sample.patient_name})


# ---------------------------------------------------------------------------
# Result Validation
# ---------------------------------------------------------------------------

@app.route("/result-validation", methods=["GET", "POST"])
@login_required
def result_validation():
    latest_result = LabResult.query.order_by(LabResult.id.desc()).first()

    if request.method == "POST":
        decision = request.form.get("validationStatus", "")
        validator = request.form.get("validator", "").strip()
        comments = request.form.get("comments", "").strip()

        if not latest_result or not all([decision, validator, comments]):
            flash("Please complete the validation process.", "danger")
            return redirect(url_for("result_validation"))

        validation = ResultValidation(
            result_id=latest_result.id,
            sample_id=latest_result.sample_id,
            patient_name=latest_result.patient_name,
            test=latest_result.test,
            result=latest_result.result,
            decision=decision,
            validator=validator,
            comments=comments,
        )
        db.session.add(validation)
        db.session.commit()
        flash("Laboratory Result Successfully Validated.", "success")
        return redirect(url_for("result_validation"))

    return render_template("result_validation.html", latest_result=latest_result)


# ---------------------------------------------------------------------------
# Result Approval
# ---------------------------------------------------------------------------

@app.route("/result-approval", methods=["GET", "POST"])
@login_required
def result_approval():
    latest_validation = ResultValidation.query.order_by(ResultValidation.id.desc()).first()

    if request.method == "POST":
        status = request.form.get("approvalStatus", "")
        manager = request.form.get("approvedBy", "").strip()
        remarks = request.form.get("approvalRemarks", "").strip()

        if not latest_validation or not all([status, manager, remarks]):
            flash("Complete the approval process.", "danger")
            return redirect(url_for("result_approval"))

        approval = ResultApproval(
            validation_id=latest_validation.id,
            sample_id=latest_validation.sample_id,
            patient_name=latest_validation.patient_name,
            test=latest_validation.test,
            validation_decision=latest_validation.decision,
            result_summary=latest_validation.result,
            decision=status,
            approved_by=manager,
            remarks=remarks,
        )
        db.session.add(approval)
        db.session.commit()
        flash("Laboratory Result Approved Successfully.", "success")
        return redirect(url_for("result_approval"))

    return render_template("result_approval.html", latest_validation=latest_validation)


# ---------------------------------------------------------------------------
# Notifications & Reports
# ---------------------------------------------------------------------------

@app.route("/notifications")
@login_required
def notifications():
    counts = {
        "patients": Patient.query.count(),
        "requests": LabRequest.query.count(),
        "samples": Sample.query.count(),
        "results": LabResult.query.count(),
        "validations": ResultValidation.query.count(),
        "approvals": ResultApproval.query.count(),
    }
    return render_template("notifications.html", counts=counts)


@app.route("/reports")
@login_required
def reports():
    counts = {
        "Patients": Patient.query.count(),
        "Lab Requests": LabRequest.query.count(),
        "Samples": Sample.query.count(),
        "Results": LabResult.query.count(),
        "Validated Results": ResultValidation.query.count(),
        "Approved Results": ResultApproval.query.count(),
    }
    return render_template("reports.html", counts=counts)


# ---------------------------------------------------------------------------
# Bootstrap / seed
# ---------------------------------------------------------------------------

def seed_default_user():
    if not User.query.filter_by(username="Lazarus").first():
        user = User(username="Lazarus", fullname="Lazarus")
        user.set_password("Donrover")
        db.session.add(user)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_default_user()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
