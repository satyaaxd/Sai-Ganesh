from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# ─── CONFIGURATION ────────────────────────────────────
app.config['SECRET_KEY'] = 'nexus_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexus_ems.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── MODELS (Database Schema) ─────────────────────────

class Employee(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    personal_email = db.Column(db.String(120)) # ADD THIS LINE
    password = db.Column(db.String(100), nullable=False, default='password123')
    department = db.Column(db.String(50))
    role = db.Column(db.String(20), default='employee')
    designation = db.Column(db.String(100), default='Associate')
    joined_date = db.Column(db.String(20))

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), db.ForeignKey('employee.id'))
    leave_type = db.Column(db.String(50))
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    days = db.Column(db.Integer)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending') # 'pending', 'approved', 'rejected'
    rejection_reason = db.Column(db.Text)

# ─── ROUTES ───────────────────────────────────────────

@app.get('/')
@app.get('/dashboard')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Use the modern get method to avoid the legacy warning
    user = db.session.get(Employee, session['user_id'])
    
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # REDIRECT BASED ON ROLE
    if user.role == 'hr':
        return render_template('hr/dashboard.html', user=user)
    elif user.role == 'employee':
        # This ensures the employee lands on their specific page
        return render_template('employee/profile.html', user=user)
    
    return render_template('hr/dashboard.html', user=user)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    selected_role = data.get('role') # Get the role from the button clicked

    user = Employee.query.filter_by(email=email).first()

    if user and user.password == password:
        # Check if the database role matches the selected tab role
        if user.role.lower() != selected_role.lower():
            return jsonify({
                "status": "error", 
                "message": f"Unauthorized. This account is registered as {user.role}."
            }), 401

        session['user_id'] = user.id
        session['user_role'] = user.role.lower()
        return jsonify({
            "status": "success",
            "user": {"name": user.name, "role": user.role, "id": user.id}
        })
    
    return jsonify({"status": "error", "message": "Invalid Credentials"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ─── VIEW ROUTES ──────────────────────────────────────

@app.route('/employees')
def manage_employees():
    # Check if the user is logged in
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    # Get the user from the database to check the current role
    user = db.session.get(Employee, user_id)
    
    # Verify the role is 'hr'
    if not user or user.role.lower() != 'hr':
        return "Unauthorized", 403
        
    employees = Employee.query.all()
    # Pass 'user' to the template so your sidebar initials and names work
    return render_template('hr/employees.html', employees=employees, user=user)

@app.route('/leave-requests')
def view_leave_requests():
    if session.get('user_role') not in ['hr', 'supervisor']:
        return "Unauthorized", 403
    requests = LeaveRequest.query.all()
    return render_template('supervisor/leave_requests.html', leave_requests=requests)

@app.route('/profile')
def my_profile():
    user = Employee.query.get(session.get('user_id'))
    return render_template('employee/profile.html', user=user)

# ─── API ACTIONS ──────────────────────────────────────

@app.route('/api/employees/add', methods=['POST'])
def add_employee():
    data = request.json
    
    new_emp = Employee(
        id=data.get('id'),
        name=data.get('name'),
        email=data.get('email'),
        personal_email=data.get('personal_email'), # NEW
        password="password123", # Default password to avoid IntegrityError
        department=data.get('department'),
        role=data.get('role', 'employee'),
        designation=data.get('designation', 'Associate'),
        joined_date=datetime.now().strftime("%b %d, %Y")
    )
    
    try:
        db.session.add(new_emp)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/leave/update', methods=['POST'])
def update_leave():
    data = request.json
    leave = LeaveRequest.query.get(data.get('id'))
    if leave:
        leave.status = data.get('status')
        leave.rejection_reason = data.get('reason', '')
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

# ─── INITIALIZE DATABASE ──────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        # Seed initial HR User if none exists
        if not Employee.query.filter_by(id='EMP-2001').first():
            hr_user = Employee(
                id='EMP-2001',
                name='Priya Sharma',
                email='p.sharma@nexus-corp.com',
                password='password123',
                department='Engineering',
                role='hr',
                designation='HR Administrator',
                joined_date='Jan 12, 2024'
            )
            db.session.add(hr_user)
            db.session.commit()

if __name__ == '__main__':

    init_db()
    app.run(debug=True)
    #hello
    
