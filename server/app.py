import os

from flask import Flask, jsonify, request
from flask_migrate import Migrate
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from models import db, Exercise, Workout, WorkoutExercise
from schemas import (exercise_schema, exercises_schema, workout_schema,
                     workouts_schema, workout_exercise_schema)

app = Flask(__name__)
# DATABASE_URL is only set by the tests so they don't touch the real database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

migrate = Migrate(app, db)
db.init_app(app)


# ---------- Helpers ----------

def json_error(message, status):
    """Every error goes back in the same shape: {"error": "..."}"""
    return jsonify({'error': message}), status


def get_json_body():
    """Return the JSON body if it is an object like {...}, otherwise None.
    silent=True means bad JSON gives None instead of crashing."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


def save(item):
    """Add the item and commit. Returns an error response if something
    went wrong, or None if it worked."""
    try:
        db.session.add(item)
        db.session.commit()
    except IntegrityError:
        # a table constraint was broken (for example a duplicate)
        db.session.rollback()
        return json_error('That breaks a database rule, '
                          'for example a duplicate or a value that is not allowed.', 409)
    except SQLAlchemyError:
        db.session.rollback()
        return json_error('Database error, please try again.', 500)
    return None


def remove(item):
    """Delete the item and commit. Same idea as save()."""
    try:
        db.session.delete(item)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return json_error('Database error, please try again.', 500)
    return None


# ---------- Error handlers (so errors come back as JSON, not HTML) ----------

@app.errorhandler(HTTPException)
def handle_http_error(error):
    # covers 404 (bad URL), 405 (wrong method), 500 (crash) and so on
    db.session.rollback()
    return json_error(error.description, error.code)

if __name__ == '__main__':
    app.run(port=5555, debug=True)