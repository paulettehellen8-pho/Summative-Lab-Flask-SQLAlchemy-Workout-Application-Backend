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

# ---------- Workouts ----------

@app.get('/workouts')
def get_workouts():
    workouts = Workout.query.order_by(Workout.date, Workout.id).all()
    return jsonify(workouts_schema.dump(workouts)), 200


@app.get('/workouts/<int:id>')
def get_workout(id):
    workout = db.session.get(Workout, id)
    if workout is None:
        return json_error('Workout not found.', 404)
    return jsonify(workout_schema.dump(workout)), 200


@app.post('/workouts')
def create_workout():
    data = get_json_body()
    if data is None:
        return json_error('Request body must be a JSON object.', 400)

    try:
        data = workout_schema.load(data)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400

    try:
        workout = Workout(**data)
    except ValueError as err:
        # the model validations are a second safety net
        return json_error(str(err), 400)

    error = save(workout)
    if error:
        return error
    return jsonify(workout_schema.dump(workout)), 201


@app.delete('/workouts/<int:id>')
def delete_workout(id):
    workout = db.session.get(Workout, id)
    if workout is None:
        return json_error('Workout not found.', 404)

    # the cascade on the model also deletes this workout's WorkoutExercises
    error = remove(workout)
    if error:
        return error
    return '', 204


# ---------- Exercises ----------

@app.get('/exercises')
def get_exercises():
    exercises = Exercise.query.order_by(Exercise.name).all()
    return jsonify(exercises_schema.dump(exercises)), 200


@app.get('/exercises/<int:id>')
def get_exercise(id):
    exercise = db.session.get(Exercise, id)
    if exercise is None:
        return json_error('Exercise not found.', 404)
    return jsonify(exercise_schema.dump(exercise)), 200


@app.post('/exercises')
def create_exercise():
    data = get_json_body()
    if data is None:
        return json_error('Request body must be a JSON object.', 400)

    try:
        data = exercise_schema.load(data)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400

    # "Squats" and "squats" should count as the same exercise
    name = data['name'].strip()
    duplicate = Exercise.query.filter(
        db.func.lower(Exercise.name) == name.lower()).first()
    if duplicate:
        return json_error(f'An exercise called "{duplicate.name}" already exists.', 409)

    try:
        exercise = Exercise(**data)
    except ValueError as err:
        return json_error(str(err), 400)

    error = save(exercise)
    if error:
        return error
    return jsonify(exercise_schema.dump(exercise)), 201


@app.delete('/exercises/<int:id>')
def delete_exercise(id):
    exercise = db.session.get(Exercise, id)
    if exercise is None:
        return json_error('Exercise not found.', 404)

    # the cascade on the model also deletes this exercise's WorkoutExercises
    error = remove(exercise)
    if error:
        return error
    return '', 204

# ---------- Add an exercise to a workout ----------

@app.post('/workouts/<int:workout_id>/exercises/<int:exercise_id>/workout_exercises')
def add_exercise_to_workout(workout_id, exercise_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        return json_error('Workout not found.', 404)

    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        return json_error('Exercise not found.', 404)

    data = get_json_body()
    if data is None:
        return json_error('Request body must be a JSON object.', 400)

    try:
        data = workout_exercise_schema.load(data)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400

    # the same exercise can only be in a workout once
    already_there = WorkoutExercise.query.filter_by(
        workout_id=workout_id, exercise_id=exercise_id).first()
    if already_there:
        return json_error('This exercise is already in this workout.', 409)

    try:
        workout_exercise = WorkoutExercise(
            workout_id=workout_id, exercise_id=exercise_id, **data)
    except ValueError as err:
        return json_error(str(err), 400)

    error = save(workout_exercise)
    if error:
        return error
    return jsonify(workout_exercise_schema.dump(workout_exercise)), 201

if __name__ == '__main__':
    app.run(port=5555, debug=True)