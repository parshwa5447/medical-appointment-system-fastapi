from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import math

app = FastAPI()
#DATA
doctors = [
    {"id": 1, "name": "Dr. Sharma", "specialization": "Cardiologist", "fee": 800, "experience_years": 10, "is_available": True},
    {"id": 2, "name": "Dr. Mehta", "specialization": "Dermatologist", "fee": 500, "experience_years": 7, "is_available": True},
    {"id": 3, "name": "Dr. Patel", "specialization": "Pediatrician", "fee": 600, "experience_years": 8, "is_available": False},
    {"id": 4, "name": "Dr. Singh", "specialization": "General", "fee": 300, "experience_years": 5, "is_available": True},
    {"id": 5, "name": "Dr. Khan", "specialization": "Cardiologist", "fee": 900, "experience_years": 15, "is_available": True},
    {"id": 6, "name": "Dr. Iyer", "specialization": "Dermatologist", "fee": 450, "experience_years": 6, "is_available": False},
]

appointments = []
appt_counter = 1

#MODELS
class AppointmentRequest(BaseModel):
    patient_name: str = Field(..., min_length=2)
    doctor_id: int = Field(..., gt=0)
    date: str = Field(..., min_length=8)
    reason: str = Field(..., min_length=5)
    appointment_type: str = "in-person"
    senior_citizen: bool = False


class NewDoctor(BaseModel):
    name: str = Field(..., min_length=2)
    specialization: str = Field(..., min_length=2)
    fee: int = Field(..., gt=0)
    experience_years: int = Field(..., gt=0)
    is_available: bool = True

#HELPERS
def find_doctor(doctor_id):
    for doc in doctors:
        if doc["id"] == doctor_id:
            return doc
    return None


def calculate_fee(base_fee, appointment_type, senior=False):
    if appointment_type == "video":
        fee = base_fee * 0.8
    elif appointment_type == "emergency":
        fee = base_fee * 1.5
    else:
        fee = base_fee

    original = fee

    if senior:
        fee = fee * 0.85

    return int(original), int(fee)


def filter_doctors_logic(specialization, max_fee, min_experience, is_available):
    result = doctors
    if specialization is not None:
        result = [d for d in result if d["specialization"] == specialization]
    if max_fee is not None:
        result = [d for d in result if d["fee"] <= max_fee]
    if min_experience is not None:
        result = [d for d in result if d["experience_years"] >= min_experience]
    if is_available is not None:
        result = [d for d in result if d["is_available"] == is_available]
    return result


#BASIC ROUTES
@app.get("/")
def home():
    return {"message": "Welcome to MediCare Clinic"}


@app.get("/doctors")
def get_doctors():
    available = [d for d in doctors if d["is_available"]]
    return {
        "doctors": doctors,
        "total": len(doctors),
        "available_count": len(available)
    }


@app.get("/doctors/summary")
def doctors_summary():
    most_exp = max(doctors, key=lambda x: x["experience_years"])
    cheapest = min(doctors, key=lambda x: x["fee"])

    spec_count = {}
    for d in doctors:
        spec_count[d["specialization"]] = spec_count.get(d["specialization"], 0) + 1

    return {
        "total": len(doctors),
        "available": len([d for d in doctors if d["is_available"]]),
        "most_experienced": most_exp["name"],
        "cheapest_fee": cheapest["fee"],
        "specialization_count": spec_count
    }


@app.get("/doctors/{doctor_id}")
def get_doctor(doctor_id: int):
    doc = find_doctor(doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doc


@app.get("/appointments")
def get_appointments():
    return {"appointments": appointments, "total": len(appointments)}

#APPOINTMENTS
@app.post("/appointments")
def create_appointment(req: AppointmentRequest):
    global appt_counter

    doc = find_doctor(req.doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found")

    if not doc["is_available"]:
        raise HTTPException(status_code=400, detail="Doctor not available")

    original_fee, final_fee = calculate_fee(doc["fee"], req.appointment_type, req.senior_citizen)

    appt = {
        "appointment_id": appt_counter,
        "patient": req.patient_name,
        "doctor": doc["name"],
        "doctor_id": doc["id"],
        "date": req.date,
        "type": req.appointment_type,
        "original_fee": original_fee,
        "final_fee": final_fee,
        "status": "scheduled"
    }

    appointments.append(appt)
    appt_counter += 1
    doc["is_available"] = False

    return appt

#FILTER
@app.get("/doctors/filter")
def filter_doctors(
    specialization: Optional[str] = None,
    max_fee: Optional[int] = None,
    min_experience: Optional[int] = None,
    is_available: Optional[bool] = None
):
    return filter_doctors_logic(specialization, max_fee, min_experience, is_available)


#CRUD DOCTOR
@app.post("/doctors")
def add_doctor(new_doc: NewDoctor):
    for d in doctors:
        if d["name"] == new_doc.name:
            raise HTTPException(status_code=400, detail="Duplicate doctor")

    doc = new_doc.dict()
    doc["id"] = len(doctors) + 1
    doctors.append(doc)
    return doc


@app.put("/doctors/{doctor_id}")
def update_doctor(doctor_id: int, fee: Optional[int] = None, is_available: Optional[bool] = None):
    doc = find_doctor(doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    if fee is not None:
        doc["fee"] = fee
    if is_available is not None:
        doc["is_available"] = is_available

    return doc


@app.delete("/doctors/{doctor_id}")
def delete_doctor(doctor_id: int):
    doc = find_doctor(doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    for a in appointments:
        if a["doctor_id"] == doctor_id and a["status"] == "scheduled":
            raise HTTPException(status_code=400, detail="Doctor has active appointments")

    doctors.remove(doc)
    return {"message": "Doctor deleted"}


#APPOINTMENT STATUS
def find_appt(appt_id):
    for a in appointments:
        if a["appointment_id"] == appt_id:
            return a
    return None


@app.post("/appointments/{appointment_id}/confirm")
def confirm_appt(appointment_id: int):
    a = find_appt(appointment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    a["status"] = "confirmed"
    return a


@app.post("/appointments/{appointment_id}/cancel")
def cancel_appt(appointment_id: int):
    a = find_appt(appointment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Not found")

    a["status"] = "cancelled"
    doc = find_doctor(a["doctor_id"])
    if doc:
        doc["is_available"] = True

    return a


@app.post("/appointments/{appointment_id}/complete")
def complete_appt(appointment_id: int):
    a = find_appt(appointment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Not found")

    a["status"] = "completed"
    return a


@app.get("/appointments/active")
def active_appts():
    return [a for a in appointments if a["status"] in ["scheduled", "confirmed"]]


@app.get("/appointments/by-doctor/{doctor_id}")
def appt_by_doc(doctor_id: int):
    return [a for a in appointments if a["doctor_id"] == doctor_id]

#SEARCH + SORT + PAGINATION
@app.get("/doctors/search")
def search_doctors(keyword: str):
    result = [d for d in doctors if keyword.lower() in d["name"].lower() or keyword.lower() in d["specialization"].lower()]
    if not result:
        return {"message": "No doctors found"}
    return {"results": result, "total_found": len(result)}


@app.get("/doctors/sort")
def sort_doctors(sort_by: str = "fee"):
    if sort_by not in ["fee", "name", "experience_years"]:
        raise HTTPException(status_code=400, detail="Invalid sort")

    return sorted(doctors, key=lambda x: x[sort_by])


@app.get("/doctors/page")
def paginate_doctors(page: int = 1, limit: int = 3):
    total = len(doctors)
    total_pages = math.ceil(total / limit)

    start = (page - 1) * limit
    end = start + limit

    return {
        "page": page,
        "total_pages": total_pages,
        "data": doctors[start:end]
    }


@app.get("/appointments/search")
def search_appt(name: str):
    return [a for a in appointments if name.lower() in a["patient"].lower()]


@app.get("/appointments/sort")
def sort_appt(sort_by: str = "date"):
    return sorted(appointments, key=lambda x: x[sort_by])


@app.get("/appointments/page")
def paginate_appt(page: int = 1, limit: int = 3):
    total = len(appointments)
    total_pages = math.ceil(total / limit)

    start = (page - 1) * limit
    end = start + limit

    return appointments[start:end]


@app.get("/doctors/browse")
def browse_doctors(
    keyword: Optional[str] = None,
    sort_by: str = "fee",
    order: str = "asc",
    page: int = 1,
    limit: int = 4
):
    result = doctors

    if keyword:
        result = [d for d in result if keyword.lower() in d["name"].lower() or keyword.lower() in d["specialization"].lower()]

    result = sorted(result, key=lambda x: x[sort_by], reverse=(order == "desc"))

    total = len(result)
    total_pages = math.ceil(total / limit)

    start = (page - 1) * limit
    end = start + limit

    return {
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "results": result[start:end]
    }