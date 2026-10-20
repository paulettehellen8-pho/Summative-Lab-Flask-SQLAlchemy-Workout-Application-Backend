import os

# Use a throwaway in-memory database for the tests. This has to be set
# BEFORE app is imported, otherwise the tests would use the real app.db.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import app
from models import db, Exercise, Workout, WorkoutExercise


@pytest.fixture
def client():
    """Fresh empty database for every test."""
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def make_exercise(client, name='Squats', category='Strength', **extra):
    body = {'name': name, 'category': category}
    body.update(extra)
    return client.post('/exercises', json=body)


def make_workout(client, **extra):
    body = {'date': '2026-10-20', 'duration_minutes': 45, 'notes': 'Legs'}
    body.update(extra)
    return client.post('/workouts', json=body)


def add_link(client, workout_id=1, exercise_id=1, **body):
    url = f'/workouts/{workout_id}/exercises/{exercise_id}/workout_exercises'
    return client.post(url, json=body)


# ---------- Table constraints (checked with raw SQL, skipping the model) ----------

def test_table_blocks_blank_exercise_name(client):
    with pytest.raises(IntegrityError):
        db.session.execute(text(
            "INSERT INTO exercises (name, category, equipment_needed) "
            "VALUES ('   ', 'Core', 0)"))
    db.session.rollback()


def test_table_blocks_duplicate_exercise_name(client):
    make_exercise(client, name='Plank')
    with pytest.raises(IntegrityError):
        db.session.execute(text(
            "INSERT INTO exercises (name, category, equipment_needed) "
            "VALUES ('Plank', 'Core', 0)"))
    db.session.rollback()


def test_table_blocks_bad_workout_duration(client):
    with pytest.raises(IntegrityError):
        db.session.execute(text(
            "INSERT INTO workouts (date, duration_minutes) "
            "VALUES ('2026-10-20', 0)"))
    db.session.rollback()


def test_table_blocks_row_with_no_reps_or_duration(client):
    make_exercise(client)
    make_workout(client)
    with pytest.raises(IntegrityError):
        db.session.execute(text(
            "INSERT INTO workout_exercises (workout_id, exercise_id) "
            "VALUES (1, 1)"))
    db.session.rollback()


def test_table_blocks_same_exercise_twice_in_workout(client):
    make_exercise(client)
    make_workout(client)
    add_link(client, reps=10, sets=3)
    with pytest.raises(IntegrityError):
        db.session.execute(text(
            "INSERT INTO workout_exercises (workout_id, exercise_id, reps, sets) "
            "VALUES (1, 1, 5, 5)"))
    db.session.rollback()


# ---------- Model validations ----------

def test_model_rejects_blank_name():
    with pytest.raises(ValueError):
        Exercise(name='   ', category='Core')


def test_model_trims_name():
    assert Exercise(name='  Plank  ', category='Core').name == 'Plank'


def test_model_rejects_bad_duration():
    for bad in (0, -5, 1441, 'ten', 2.5, True):
        with pytest.raises(ValueError):
            Workout(duration_minutes=bad)


def test_model_rejects_bad_reps():
    for bad in (0, -1, 'five', 1.5):
        with pytest.raises(ValueError):
            WorkoutExercise(reps=bad)


# ---------- Schema validations (through the API) ----------

def test_schema_rejects_missing_fields(client):
    response = client.post('/exercises', json={})
    assert response.status_code == 400
    assert 'name' in response.json['errors']
    assert 'category' in response.json['errors']


def test_schema_rejects_blank_name(client):
    response = make_exercise(client, name='   ')
    assert response.status_code == 400


def test_schema_rejects_wrong_types(client):
    assert make_exercise(client, name=123).status_code == 400
    assert make_exercise(client, equipment_needed=None).status_code == 400
    assert make_workout(client, duration_minutes='45').status_code == 400
    assert make_workout(client, duration_minutes=45.5).status_code == 400


def test_schema_rejects_bad_workout_values(client):
    assert make_workout(client, duration_minutes=0).status_code == 400
    assert make_workout(client, duration_minutes=5000).status_code == 400
    assert make_workout(client, date='not-a-date').status_code == 400
    assert make_workout(client, date='1850-01-01').status_code == 400
    assert make_workout(client, date='2026-02-31').status_code == 400
    assert make_workout(client, notes='x' * 1001).status_code == 400


def test_schema_rejects_unknown_and_readonly_fields(client):
    assert make_exercise(client, colour='red').status_code == 400
    assert make_exercise(client, id=99).status_code == 400


def test_schema_needs_reps_or_duration(client):
    make_exercise(client)
    make_workout(client)
    assert add_link(client).status_code == 400
    assert add_link(client, sets=3).status_code == 400
    assert add_link(client, reps=10).status_code == 400   # reps need sets
    assert add_link(client, reps=0, sets=3).status_code == 400


def test_bad_json_bodies(client):
    # not JSON at all
    response = client.post('/exercises', data='hello',
                           content_type='application/json')
    assert response.status_code == 400
    # JSON but not an object
    assert client.post('/exercises', json=[1, 2]).status_code == 400
    # no body
    assert client.post('/workouts').status_code == 400


# ---------- Exercises ----------

def test_create_and_get_exercise(client):
    response = make_exercise(client, equipment_needed=True)
    assert response.status_code == 201
    assert response.json['equipment_needed'] is True

    assert client.get('/exercises').json[0]['name'] == 'Squats'
    one = client.get('/exercises/1')
    assert one.status_code == 200
    assert one.json['workout_exercises'] == []


def test_equipment_needed_defaults_to_false(client):
    assert make_exercise(client).json['equipment_needed'] is False


def test_duplicate_exercise_name_is_409_even_with_different_case(client):
    make_exercise(client, name='Squats')
    assert make_exercise(client, name='squats').status_code == 409
    assert make_exercise(client, name='  SQUATS ').status_code == 409


def test_exercise_not_found(client):
    assert client.get('/exercises/999').status_code == 404
    assert client.delete('/exercises/999').status_code == 404


# ---------- Workouts ----------

def test_create_and_get_workout(client):
    response = make_workout(client)
    assert response.status_code == 201
    assert response.json['date'] == '2026-10-20'

    assert len(client.get('/workouts').json) == 1
    assert client.get('/workouts/1').json['workout_exercises'] == []


def test_workout_notes_are_optional(client):
    response = client.post('/workouts', json={
        'date': '2026-10-20', 'duration_minutes': 30})
    assert response.status_code == 201
    assert response.json['notes'] is None


def test_workout_not_found(client):
    assert client.get('/workouts/999').status_code == 404
    assert client.delete('/workouts/999').status_code == 404


# ---------- Adding an exercise to a workout ----------

def test_add_exercise_to_workout(client):
    make_exercise(client)
    make_workout(client)
    response = add_link(client, reps=10, sets=3)
    assert response.status_code == 201
    assert response.json['reps'] == 10

    # shows up on the workout (with reps/sets) and on the exercise
    workout = client.get('/workouts/1').json
    assert workout['workout_exercises'][0]['exercise']['name'] == 'Squats'
    assert workout['workout_exercises'][0]['sets'] == 3
    exercise = client.get('/exercises/1').json
    assert exercise['workout_exercises'][0]['workout']['id'] == 1


def test_duration_only_exercise_is_allowed(client):
    make_exercise(client, name='Plank')
    make_workout(client)
    response = add_link(client, duration_seconds=60)
    assert response.status_code == 201
    assert response.json['reps'] is None


def test_same_exercise_twice_in_one_workout_is_409(client):
    make_exercise(client)
    make_workout(client)
    add_link(client, reps=10, sets=3)
    assert add_link(client, reps=5, sets=5).status_code == 409


def test_same_exercise_can_be_in_many_workouts(client):
    make_exercise(client)
    make_workout(client)
    make_workout(client, date='2026-10-21')
    assert add_link(client, 1, 1, reps=10, sets=3).status_code == 201
    assert add_link(client, 2, 1, reps=8, sets=4).status_code == 201
    assert len(client.get('/exercises/1').json['workout_exercises']) == 2


def test_add_with_missing_workout_or_exercise_is_404(client):
    make_exercise(client)
    make_workout(client)
    assert add_link(client, 99, 1, reps=1, sets=1).status_code == 404
    assert add_link(client, 1, 99, reps=1, sets=1).status_code == 404


# ---------- Deleting (stretch goal: join rows go too) ----------

def test_delete_workout_also_deletes_its_join_rows(client):
    make_exercise(client)
    make_workout(client)
    add_link(client, reps=10, sets=3)

    assert client.delete('/workouts/1').status_code == 204
    assert client.get('/workouts/1').status_code == 404
    assert WorkoutExercise.query.count() == 0
    # the exercise itself must still be there for other workouts
    assert client.get('/exercises/1').status_code == 200


def test_delete_exercise_also_deletes_its_join_rows(client):
    make_exercise(client)
    make_workout(client)
    add_link(client, reps=10, sets=3)

    assert client.delete('/exercises/1').status_code == 204
    assert WorkoutExercise.query.count() == 0
    assert client.get('/workouts/1').json['workout_exercises'] == []


# ---------- Errors come back as JSON ----------

def test_unknown_url_and_wrong_method_return_json(client):
    response = client.get('/nothing-here')
    assert response.status_code == 404
    assert 'error' in response.json

    response = client.put('/workouts')
    assert response.status_code == 405
    assert 'error' in response.json


def test_ids_that_are_not_positive_whole_numbers_are_404(client):
    assert client.get('/workouts/abc').status_code == 404
    assert client.get('/workouts/-1').status_code == 404