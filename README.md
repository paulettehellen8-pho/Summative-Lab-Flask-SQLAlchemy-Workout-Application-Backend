# Workout Tracker API

A backend API for a workout app used by personal trainers. Trainers can create workouts
and exercises, and add the same exercise to many workouts with its sets, reps or duration.
Built with Flask, SQLAlchemy and Marshmallow.

## Installation

1. Clone the repo and `cd` into it.
2. Install the packages and open the virtual environment:
```
   pipenv install --dev
   pipenv shell
```
3. Set up the database (run these from the `server/` folder):
```
   cd server
   flask db upgrade head
   python seed.py
```
   (`flask db upgrade head` uses the migration that is already in the repo.)

## Running the app

From the `server/` folder:
```
python app.py
```
The API runs at http://127.0.0.1:5555 (you can also use `flask run`, which uses port 5000).

Run the tests with `pytest -q` from the `server/` folder.

## Data

- **Exercise**: `name` (unique), `category`, `equipment_needed`
- **Workout**: `date`, `duration_minutes` (1 to 1440), `notes`
- **WorkoutExercise** (join table): `workout_id`, `exercise_id`, `reps`, `sets`, `duration_seconds`.
  Needs reps (with sets) or a duration. The same exercise can only be in a workout once.

## Endpoints

| Method | URL | What it does |
|--------|-----|--------------|
| GET | `/workouts` | List all workouts |
| GET | `/workouts/<id>` | Show one workout with its exercises, including reps, sets and duration |
| POST | `/workouts` | Create a workout. Body: `date` (YYYY-MM-DD), `duration_minutes`, optional `notes` |
| DELETE | `/workouts/<id>` | Delete a workout and its workout exercises |
| GET | `/exercises` | List all exercises |
| GET | `/exercises/<id>` | Show one exercise with the workouts it is in |
| POST | `/exercises` | Create an exercise. Body: `name`, `category`, optional `equipment_needed` |
| DELETE | `/exercises/<id>` | Delete an exercise and its workout exercises |
| POST | `/workouts/<workout_id>/exercises/<exercise_id>/workout_exercises` | Add an exercise to a workout. Body: `reps` + `sets`, and/or `duration_seconds` |

## Status codes and errors

Errors are always JSON. `400` bad data, `404` not found, `409` duplicate
(same exercise name, or exercise already in the workout), `405` wrong method.
Successful deletes return `204` with no body.

## Validations

- **Table constraints**: unique exercise name, no blank text, workout duration 1 to 1440,
  reps/sets/duration must be positive, each row needs reps or a duration, no duplicate
  exercise in a workout.
- **Model validations**: text is trimmed and cannot be blank, numbers must be whole numbers in range,
  notes max 1000 characters.
- **Schema validations**: required fields, correct types, valid date, number ranges, no unknown
  fields, reps need sets.