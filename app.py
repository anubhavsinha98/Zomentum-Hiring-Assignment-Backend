from flask import Flask,request, jsonify
from flask_sqlalchemy import SQLAlchemy 
from flask_marshmallow import Marshmallow
from hashlib import sha1
import datetime
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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

class TicketSchema(ma.Schema):
    class Meta:
        fields = ('id', 'user_name', 'timings', 'phone_no')

ticket_schema = TicketSchema()
tickets_schema = TicketSchema(many=True)

@app.route('/book', methods=['POST'])
def book_ticket():
    user_name = request.json['user_name']
    timings = datetime.datetime.strptime(request.json['timings'], '%H:%M')
    phone_no =  request.json['phone_no']

    new_ticket = Ticket(user_name, timings, phone_no)
    db.session.add(new_ticket)
    db.session.commit()

    return ticket_schema.jsonify(new_ticket)


@app.route('/tickets', methods=['GET'])
def get_tickets():
    all_tickets = Ticket.query.all()
    result = tickets_schema.dump(all_tickets)
    return jsonify(result)

@app.route('/tickets/<id>', methods=['GET'])
def get_ticket_from_id(id):
    ticket = Ticket.query.get(id)
    return ticket_schema.jsonify(ticket)

if __name__ == "__main__":
    app.run(debug=True)