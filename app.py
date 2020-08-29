from flask import Flask,request, jsonify
from flask_sqlalchemy import SQLAlchemy 
from flask_marshmallow import Marshmallow
from hashlib import sha1
import datetime
import os

MAX_TICKET_LIMIT = 20

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

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
    ticket = TicketCount.query.filter_by(timings=timings).all()
    if not ticket:
        return 0
    else:
        return ticket[0].count

def update_ticket_count_from_timings(timings, param):
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
    all_tickets = Ticket.query.all()
    result = tickets_schema.dump(all_tickets)
    return jsonify(result)

@app.route('/ticket/<id>', methods=['GET'])
def get_ticket_from_id(id):
    ticket = Ticket.query.get(id)
    return ticket_schema.jsonify(ticket)

@app.route('/tickets/<timings>', methods=['GET'])
def get_tickets_from_timing(timings):
    timings = datetime.datetime.strptime(timings, '%H:%M')
    tickets = Ticket.query.filter_by(timings=timings).all()
    result = tickets_schema.dump(tickets)
    return jsonify(result)

@app.route('/ticket/<id>', methods=['PUT'])
def update_ticket(id):
    ticket = Ticket.query.get(id)
    update_ticket_count_from_timings(ticket.timings, '-')
    ticket.timings = datetime.datetime.strptime(request.json['timings'], '%H:%M')
    update_ticket_count_from_timings(ticket.timings, '+')
    db.session.commit()

    return ticket_schema.jsonify(ticket)

@app.route('/ticket/<id>', methods=['DELETE'])
def delete_ticket(id):
    ticket = Ticket.query.get(id)
    update_ticket_count_from_timings(ticket.timings, '-')
    db.session.delete(ticket)
    db.session.commit()

    return ticket_schema.jsonify(ticket)

if __name__ == "__main__":
    app.run(debug=True)