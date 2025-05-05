from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import text

import os
#render_template loads and displays HTML templates, request allows use to access data sent by USER
#redirect sends to diff page, url_dor generates URLs
#sql alchemy is Flasks ORM
'''
app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))  # Get absolute path of project root
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'appointments.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False'''

db = SQLAlchemy()
def create_app():
    app = Flask(__name__)

    # Ensure database is stored in the project root
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'appointments.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)  # ✅ Now SQLAlchemy is properly initialized with the app

    return app

# Create Flask app
app = create_app()

#ORM part - config the db models
#Clients table *refer to database config
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
#Appointment table *refer to database config
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)  # index
    time = db.Column(db.Time, nullable=False)
    description = db.Column(db.Text, nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False, index=True)  # index
    status = db.Column(db.String(20), nullable=False, default="Scheduled", index=True)  # index

with app.app_context():
        print("Creating tables...")
        db.create_all()
        print("Tables created successfully!")

#requirement 1 - uses ORM !!
@app.route('/')
def index():
     appointments = Appointment.query.all()
     clients = Client.query.all()
     print("Appointments:", appointments)  
     print("Clients:", clients)
     return render_template('index.html', appointments=appointments, clients=clients)

@app.route('/add', methods=['POST'])
def add_appointment():
    date_str = request.form['date']
    time_str = request.form['time']
    description = request.form['description']
    client_id = request.form['client']
    status = request.form['status']

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date() 
    time_obj = datetime.strptime(time_str, "%H:%M").time()

    new_appointment = Appointment(date=date_obj, time=time_obj, description=description, client_id=client_id, status=status)
    db.session.add(new_appointment)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_appointment(id):
    appointment = Appointment.query.get(id)
    if appointment:
        db.session.delete(appointment)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>')
def edit_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    clients = Client.query.all()
    return render_template('edit.html', appointment=appointment, clients=clients)
@app.route('/update/<int:id>', methods=['POST'])
def update_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    
    appointment.date = datetime.strptime(request.form['date'], "%Y-%m-%d").date()
    appointment.time = datetime.strptime(request.form['time'], "%H:%M").time()
    appointment.description = request.form['description']
    appointment.client_id = request.form['client']
    appointment.status = request.form['status']

    db.session.commit()  
    return redirect(url_for('index'))

@app.route('/add_client', methods=['POST'])
def add_client():
    name = request.form['client_name']
    phone = request.form['client_phone']
    email = request.form['client_email']

    new_client = Client(name=name, phone=phone, email=email)
    db.session.add(new_client)
    db.session.commit()

    return redirect(url_for('index'))

#Prepared statements for req 2
@app.route('/report', methods=['GET'])
def report():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    status = request.args.get('status')
    client_id = request.args.get('client_id')

    sql_query = "SELECT * FROM Appointment WHERE 1=1"
    summary_query = "SELECT status, COUNT(*) as count FROM Appointment WHERE 1=1"
    avg_query = """
        SELECT AVG(cnt) FROM (
            SELECT COUNT(*) as cnt FROM Appointment WHERE 1=1
    """

    params = {}

    # applying filters to those summary stats
    if date_from and date_to:
        sql_query += " AND date BETWEEN :date_from AND :date_to"
        summary_query += " AND date BETWEEN :date_from AND :date_to"
        avg_query += " AND date BETWEEN :date_from AND :date_to"
        params["date_from"] = date_from
        params["date_to"] = date_to

    if status:
        sql_query += " AND status = :status"
        summary_query += " AND status = :status"
        avg_query += " AND status = :status"
        params["status"] = status

    if client_id:
        sql_query += " AND client_id = :client_id"
        summary_query += " AND client_id = :client_id"
        avg_query += " AND client_id = :client_id"
        params["client_id"] = client_id

    
    avg_query += " GROUP BY client_id)"

    appointments = db.session.execute(text(sql_query), params).fetchall()
    status_counts = db.session.execute(text(summary_query), params).fetchall()
    avg_per_client = db.session.execute(text(avg_query), params).scalar()

    summary = {row.status: row.count for row in status_counts}
    total = sum(summary.values())

    # drop down filters - makes sure updated dynamicall
    clients = Client.query.all()
    statuses = db.session.execute(text("SELECT DISTINCT status FROM Appointment")).fetchall()

    return render_template('report.html',
                           appointments=appointments,
                           summary=summary,
                           total=total,
                           avg_per_client=avg_per_client,
                           clients=clients,
                           statuses=[s[0] for s in statuses])

if __name__ == "__main__":

    app.run(debug=True)