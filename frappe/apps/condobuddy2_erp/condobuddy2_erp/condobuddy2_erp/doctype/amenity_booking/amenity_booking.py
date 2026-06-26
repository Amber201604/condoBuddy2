import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta

AMENITY_CONFIG = {
    "Party Room": {
        "start_hour": 9,
        "end_hour": 22,
        "slot_duration_minutes": 60,
        "max_slots_per_booking": 1,
    },
    "Rooftop Terrace": {
        "start_hour": 9,
        "end_hour": 22,
        "slot_duration_minutes": 60,
        "max_slots_per_booking": 1,
    }
}

class AmenityBooking(Document):
    pass

@frappe.whitelist()
def get_amenity_slots(amenity, date):
    config = AMENITY_CONFIG.get(amenity)
    if not config:
        return []

    slots = []
    slot_time = datetime.strptime(date, "%Y-%m-%d").replace(hour=config["start_hour"], minute=0, second=0)
    end_time = slot_time.replace(hour=config["end_hour"])
    duration = timedelta(minutes=config["slot_duration_minutes"])

    while slot_time < end_time:
        slots.append(slot_time.strftime("%H:%M"))
        slot_time += duration

    taken = frappe.db.get_all(
        "Amenity Booking",
        filters={
            "amenity": amenity,
            "booking_date": date,
            "booking_status": ["in", ["Pending", "Confirmed"]]
        },
        pluck="start_time"
    )

    taken_normalized = []
    for t in taken:
        if hasattr(t, "seconds"):
            total_seconds = int(t.seconds)
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            taken_normalized.append(f"{h:02d}:{m:02d}")
        else:
            taken_normalized.append(str(t)[:5])

    return [
        {"time": slot, "available": slot not in taken_normalized}
        for slot in slots
    ]


@frappe.whitelist()
def create_amenity_booking(amenity, booking_date, start_time):
    config = AMENITY_CONFIG.get(amenity)
    if not config:
        frappe.throw("Invalid amenity")

    taken = frappe.db.get_all(
        "Amenity Booking",
        filters={
            "amenity": amenity,
            "booking_date": booking_date,
            "start_time": start_time,
            "booking_status": ["in", ["Pending", "Confirmed"]]
        },
        pluck="name"
    )
    if taken:
        frappe.throw("This slot was just booked by someone else. Please select another.")

    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = start_dt + timedelta(minutes=config["slot_duration_minutes"])
    end_time = end_dt.strftime("%H:%M")

    # get resident record from logged-in user
    resident_name = frappe.db.get_value("Resident", {"user": frappe.session.user}, "name")

    if not resident_name:
        print("No resident record found for current user.")

    resident_doc = frappe.get_doc("Resident", resident_name)

    resident = resident_name
    unit = resident_doc.unit
    building = resident_doc.building

    doc = frappe.get_doc({
        "doctype": "Amenity Booking",
        "amenity": amenity,
        "booking_date": booking_date,
        "start_time": start_time,
        "end_time": end_time,
        "booking_status": "Pending",
        "resident": resident,
        "unit": unit,
        "building": building,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return doc.name

@frappe.whitelist()
def cancel_amenity_booking(name):
    doc = frappe.get_doc("Amenity Booking", name)
    
    # check 48hr cutoff
    if not _is_outside_cutoff(doc.booking_date, doc.start_time):
        frappe.throw("Cannot cancel within 48 hours of booking. Please contact management.")
    
    doc.booking_status = "Cancelled"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return "cancelled"


@frappe.whitelist()
def reschedule_amenity_booking(name, amenity, booking_date, start_time):
    doc = frappe.get_doc("Amenity Booking", name)
    
    # check 48hr cutoff on the ORIGINAL booking
    if not _is_outside_cutoff(doc.booking_date, doc.start_time):
        frappe.throw("Cannot reschedule within 48 hours of booking. Please contact management.")
    
    # check new slot is available
    taken = frappe.db.get_all(
        "Amenity Booking",
        filters={
            "amenity": amenity,
            "booking_date": booking_date,
            "start_time": start_time,
            "booking_status": ["in", ["Pending", "Confirmed"]],
            "name": ["!=", name]  # exclude current booking
        },
        pluck="name"
    )
    if taken:
        frappe.throw("This slot is already booked. Please select another.")

    config = AMENITY_CONFIG.get(amenity)
    if not config:
        frappe.throw("Invalid amenity.")

    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = start_dt + timedelta(minutes=config["slot_duration_minutes"])
    end_time = end_dt.strftime("%H:%M")

    doc.amenity = amenity
    doc.booking_date = booking_date
    doc.start_time = start_time
    doc.end_time = end_time
    doc.booking_status = "Pending"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return doc.name


def _is_outside_cutoff(booking_date, start_time, cutoff_hours=48):
    booking_dt = datetime.strptime(
        f"{booking_date} {start_time}", "%Y-%m-%d %H:%M"
    )
    now = datetime.now()
    delta = booking_dt - now
    return delta.total_seconds() > cutoff_hours * 3600
