import os
import logging
import random
import string
from datetime import timedelta, datetime, timezone
from flask_jwt_extended import JWTManager, create_access_token, decode_token, jwt_required, get_jwt, get_jwt_identity, verify_jwt_in_request, set_access_cookies
from flask import Flask, request, jsonify, make_response
from flask_socketio import SocketIO, emit, disconnect
from werkzeug.security import generate_password_hash, check_password_hash

from db_storage import DBStorage, Session
from models.main_models import Design, Comment, User
from utils.s3_utils import upload_to_s3

# Setup logging
logging.basicConfig(
    filename='app.log',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

# Instantiate a storage object and flush all classes that needs to be mapped to database tables
storage = DBStorage()
storage.initialize_storage()

app = Flask(__name__)

socketio = SocketIO(app, cors_allowed_origins='*')  # initialize SocketIO

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config["JWT_SECRET_KEY"] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_COOKIE_SECURE'] = False  # Set to True in production with HTTPS

app.config['WTF_CSRF_TIME_LIMIT'] = None # Setting this to None makes the csrf token valid for the life of the session

jwt = JWTManager(app)

@app.before_request
def create_session():
    # This ensures that each request gets its own session
    request.db_session = Session()
    request.storage = DBStorage(request.db_session)

@app.teardown_request
def close_session(exception=None):
    if exception: # Handle any uncaught exceptions
        request.db_session.rollback()
    Session.remove()

@socketio.on('connect')
def handle_connect(auth):
    token = auth.get('token')
    
    if not token:
        disconnect()
        return
    try:
        decode_token(token)
        print('login success')
    except Exception as e:
        disconnect()
        app.logger.error(f"Error: {e}", exc_info=True)
        return jsonify(error='Backend error, invalid acces token'), 401

@jwt_required()
@app.route('/api/v1/test', methods=['GET'], strict_slashes=False)
def landing():
    try:
        return jsonify(success = "test successful"), 200
    except Exception as e:
        app.logger.error(f"Error: {e}", exc_info=True)
        return jsonify(error='Backend error'), 500
    
@app.route('/api/v1/reg_temp_user', methods=['GET'], strict_slashes=False)
def create_temp_user():
    """Create temporary username and password"""
    def generate_username(length=8):
        """Generate a random username."""
        username = 'user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        return username

    def generate_password(length=12):
        """Generate a random password."""
        characters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(random.choices(characters, k=length))
        return password
    
    username = generate_username()
    password = generate_password()

    try:
        # Check if username already exists
        if request.storage.get_user(username):
            return jsonify({"error": "Username already exists"}), 400

        password_hashed = generate_password_hash(password)

        new_user = User(
            user_name=username,
            password=password_hashed,
        )
        request.storage.new(new_user)
        request.storage.save()

        access_token = create_access_token(
            identity=new_user.id,
            expires_delta=False
        )

        return jsonify(
            access_token=access_token,
            username=username,
            password=password,
            visited=1
        )
    except Exception as e:
        request.db_session.rollback()
        app.logger.error(f"Error: {e}", exc_info=True)
        return jsonify(error='Backend error, failed to create anonymous user'), 500

@jwt_required()
@app.route('/api/v1/designs', methods=['GET', 'POST'])
def handle_designs():
    if request.method == 'POST':
        try:
            image_url = upload_to_s3(request.files['image'])
            new_design = Design(designer_email_address=request.json.get('email_address'), image_url=image_url)
            request.storage.new(new_design)
            request.storage.save()
        except Exception as e:
            request.db_session.rollback()
            app.logger.error(f"Error: {e}", exc_info=True)
            return jsonify(error='Backend error, failed to upload design'), 500
        else:
            return jsonify({'message': 'Design uploaded successfully'}), 200
    else:
        try:
            designs = request.storage.all_designs()
            return jsonify(designs)
        except Exception as e:
            app.logger.error(f"Error: {e}", exc_info=True)
            return jsonify(error='Backend error, failed to retrieve designs'), 500


@socketio.on('vote') # Listen for vote event
def handle_vote(design_id):
    try:
        socketio_db_session = Session()
        socketio_storage = DBStorage(socketio_db_session)
        design = socketio_storage.get_object_by_id(Design, design_id)
        design.votes += 1
        socketio_storage.save()
        emit('vote_success', {'votes':design.votes}, broadcast=True) # Send new total votes to all connected clients
    except Exception as e:
        socketio_db_session.rollback()
        app.logger.error(f"Error: {e}", exc_info=True)
        emit('vote_error', {'error':'Backend error, failed to update vote'})
    finally:
        Session.remove()

@jwt_required()
@app.route('/api/v1/comments', methods=['GET', 'POST'])
def comment():
    if request.method == 'POST':
        user_id = get_jwt_identity()
        try:
            design_id = request.json['design_id']
            comment = request.json['comment']
            parent_id = request.json.get('parent_id', None)
            new_comment = Comment(design_id=design_id,
                comment=comment,
                user_id=user_id,
                parent_id=parent_id
            )
            request.storage.new(new_comment)
            request.storage.save()
            return jsonify(success=1)
        except Exception as e:
            request.db_session.rollback()
            app.logger.error(f"Error: {e}", exc_info=True)
            return jsonify(error='Backend error, failed to post comment'), 500
    else:
        try:
            design_id = request.json.get('design_id')
            page = request.json.get('page', 1)
            page_size = request.json.get('page_size', 10)

            # Retrieve comments
            return jsonify(data=request.storage.get_comments(design_id, page, page_size))
        except Exception as e:
            app.logger.error(f"Error: {e}", exc_info=True)
            return jsonify(error='Backend error, failed to retrieve comments'), 500


@jwt_required()
@app.route('/api/v1/replies', methods=['GET'])
def reply():
    """Handle replies"""
    try:
        comment_id = request.json['comment_id']
        page = request.json.get('page', 1)
        page_size = request.json.get('page_size', 10)
        return jsonify(data=request.storage.get_paginated_replies(comment_id, page, page_size))
    except Exception as e:
        app.logger.error(f"Error: {e}", exc_info=True)
        return jsonify(error='Backend error, failed to retrieve replies'), 500



if __name__ == "__main__":
    socketio.run(app, port=5000, debug=True)