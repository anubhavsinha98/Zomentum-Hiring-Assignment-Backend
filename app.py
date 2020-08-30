from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask,request, jsonify
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy 
from hashlib import sha1
import atexit
import datetime
import os

# Maximum number of tickets that can be booked for a particular show timings
MAX_TICKET_LIMIT = 20

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

scheduler = BackgroundScheduler()


class Ticket(db.Model):
    id = db.Column(db.String(200), primary_key=True)
    user_name = db.Column(db.String(200))
    timings = db.Column(db.DateTime)
    phone_no = db.Column(db.Integer)

    def get_id(self, phone_no):
        parameter = str(phone_no) + str(datetime.datetime.now())
        preproceesed_id = sha1(parameter.encode())
        return preproceesed_id.hexdigest()
    
    def __init__(self, user_name, timings, phone_no):
        self.user_name = user_name
        self.timings = timings
        self.phone_no = phone_no
        self.id = self.get_id(phone_no)

class TicketCount(db.Model):
    timings = db.Column(db.DateTime, primary_key=True)
    count = db.Column(db.Integer, default=0)

    def __init__(self, timings, count):
        self.timings = timings
        self.count = count

class TicketSchema(ma.Schema):
    class Meta:
        fields = ('id', 'user_name', 'timings', 'phone_no')

class TicketCountSchema(ma.Schema):
    class Meta:
        fields = ('timings','count')

ticket_schema = TicketSchema()
tickets_schema = TicketSchema(many=True)

ticket_count_schema = TicketCountSchema()

def get_ticket_count_from_timings(timings):
    """Returns the count of the tickets booked according to the timings

    Args:
        timings: Python datetime object. The timings for which we want the count
            of tickets booked.
        
    Returns:
        count: int. The number of tickets booked for the particular timings.
    """

    ticket = TicketCount.query.filter_by(timings=timings).all()
    if not ticket:
        return 0
    else:
        return ticket[0].count

def update_ticket_count_from_timings(timings, param):
    """Update the booked tickets count, if the ticket is deleted or booked.

    Args:
        timings: Python datetime object. The timings for the show.
        param: str('+'|'-'). Used to decide the update of the count. 
    """

    ticket = TicketCount.query.filter_by(timings=timings).all()
    if param == '+':
        if not ticket:
            new_ticket_count = TicketCount(timings, 1)
            db.session.add(new_ticket_count)
        else:
            ticket[0].count = ticket[0].count + 1
    elif param == '-':
        ticket[0].count = ticket[0].count - 1

@app.route('/book', methods=['POST'])
def book_ticket():
    """Book tickets, with user_name, timings and phone number."""

    user_name = request.json['user_name']
    timings = datetime.datetime.strptime(request.json['timings'], '%H:%M')
    phone_no =  request.json['phone_no']

    ticket_count = get_ticket_count_from_timings(timings)

    if ticket_count >= MAX_TICKET_LIMIT:
        return jsonify(["Max limit of booked tickets reached in the slot"])

    new_ticket = Ticket(user_name, timings, phone_no)
    update_ticket_count_from_timings(timings, '+')
    db.session.add(new_ticket)
    db.session.commit()

    return ticket_schema.jsonify(new_ticket)


@app.route('/tickets', methods=['GET'])
def get_tickets():
    """Get all the tickets booked."""

    all_tickets = Ticket.query.all()
    result = tickets_schema.dump(all_tickets)
    return jsonify(result)

@app.route('/ticket/<id>', methods=['GET'])
def get_ticket_from_id(id):
    """Get ticket details from id."""

    ticket = Ticket.query.get(id)
    return ticket_schema.jsonify(ticket)

@app.route('/tickets/<timings>', methods=['GET'])
def get_tickets_from_timing(timings):
    """Get all the tickets booked at a particular time."""
    
    timings = datetime.datetime.strptime(timings, '%H:%M')
    tickets = Ticket.query.filter_by(timings=timings).all()
    result = tickets_schema.dump(tickets)
    return jsonify(result)

@app.route('/ticket/<id>', methods=['PUT'])
def update_ticket(id):
    """Update the timings of the ticket."""

    ticket = Ticket.query.get(id)
    update_ticket_count_from_timings(ticket.timings, '-')
    ticket.timings = datetime.datetime.strptime(request.json['timings'], '%H:%M')
    update_ticket_count_from_timings(ticket.timings, '+')
    db.session.commit()

    return ticket_schema.jsonify(ticket)

@app.route('/ticket/<id>', methods=['DELETE'])
def delete_ticket(id):
    """Delete the ticket entry."""

    ticket = Ticket.query.get(id)
    update_ticket_count_from_timings(ticket.timings, '-')
    db.session.delete(ticket)
    db.session.commit()

    return ticket_schema.jsonify(ticket)

def delete_expired_ticket():
    """A scheduler job which runs after every 2 hours, and remove the expired tickets from the database."""

    all_tickets = Ticket.query.all()
    for ticket in all_tickets:
        if (datetime.datetime.now() - ticket.timings) >= datetime.timedelta(hours=8):
            db.session.delete(ticket)
    db.session.commit()

if __name__ == "__main__":
    # Added the scheduler job, which will execute after every 7200 seconds i.e. 2 hours.
    scheduler.add_job(func=delete_expired_ticket, trigger='interval', seconds=7200)
    scheduler.start()
    app.run(debug=True, use_reloader=False)
    atexit.register(lambda: scheduler.shutdown())