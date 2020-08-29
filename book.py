from flask import Blueprint, jsonify
from datetime import datetime
import hashlib

book_bp = Blueprint('book', __name__)

@book_bp.route('/<string:user_name>/<int:phone_no>')
def book(user_name, phone_no):
    current_time = datetime.now()
    preprocess_id = str(phone_no) + str(current_time)
    ticket_id_hash_object = hashlib.sha1(preprocess_id.encode())
    ticket_id = ticket_id_hash_object.hexdigest()
    return jsonify([user_name, phone_no, current_time, ticket_id])


