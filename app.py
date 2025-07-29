import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return "OK", 200


def find_target_date(day):    #find upcoming date for any day eg. date for next saturday
    
    today = datetime.now()
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_index = days_of_week.index(day)
    days_ahead = day_index - today.weekday()
    if days_ahead < 0:  # Target day has already passed this week
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def calculate_available_slots(day):  
    
    with open('data/schedules.json', 'r') as f:
        schedules = json.load(f)
    with open('data/appointments.json', 'r') as f:
        appointments = json.load(f)

    # Check if the requested day is in the schedule
    day_schedule = schedules.get(day)
    if not day_schedule:
        return {"error": f"No schedule found for {day}"}

    doctor = day_schedule.get("doctor")

    # Define working hours and lunch break
    work_start = datetime.strptime(day_schedule.get("start_time"), '%H:%M')
    work_end = datetime.strptime(day_schedule.get("end_time"), '%H:%M')
    slot_duration = timedelta(minutes=30)

    # Generate all possible slots for the day
    all_slots = []
    current_time = work_start
    while current_time < work_end:
        all_slots.append(current_time.strftime('%H:%M'))
        current_time += slot_duration
    
    #remove lunch slots
    all_slots.remove("13:00")
    all_slots.remove("13:30")

    target_date = find_target_date(day) #find upcoming date for requested day eg. date for next saturday

    # Filter out booked slots
    booked_times = []
    for appt in appointments:
        appt_start_time = datetime.fromisoformat(appt['start_time'])
        # Check if the appointment is on the same date we are checking for
        if appt_start_time.date() == target_date.date():
            booked_times.append(appt_start_time.strftime('%H:%M'))

    available_slots = [
        slot for slot in all_slots
        if slot not in booked_times
    ]

    return {"doctor": doctor, "available_slots": available_slots}


@app.route('/get_slots')
def get_slots():    #route to get available slots for a given day. Example: /get_slots?day=Saturday

   day = request.args.get('day')
   if not day:
       return jsonify({"error": "Please provide a 'day' parameter."}), 400

   day = day.capitalize()
  
   slots_data = calculate_available_slots(day)
   if "error" in slots_data:
       return jsonify(slots_data), 404
      
   return jsonify(slots_data)


@app.route('/log_booking', methods=['POST'])
def log_booking():    #Receives booking data as JSON and logs it to the console.
  
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    name = data.get('name')
    doctor = data.get('doctor')
    day = data.get('day')
    slot = data.get('slot')
    
    target_date = find_target_date(day)

    hour, minute = map(int, slot.split(':'))
    start_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    end_time = start_time + timedelta(minutes=30)
    
    new_appointment = {
        "name": name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    
    # Read the existing appointments, append the new one, and write back
    try:
        with open('data/appointments.json', 'r+') as f:
            appointments = json.load(f)
            appointments.append(new_appointment)
            f.seek(0)   #move back to start of file
            json.dump(appointments, f, indent=2)
    except FileNotFoundError:
        return jsonify({"error": "appointments.json not found"}), 500

    # Console log
    print(f"--- Appended new booking for {name} at {slot} on {day} with {doctor} ---")
    
    return jsonify({"status": "success", "message": "Booking successful", "details": new_appointment}), 201


if __name__ == '__main__':
    app.run(debug=True, port=5000)