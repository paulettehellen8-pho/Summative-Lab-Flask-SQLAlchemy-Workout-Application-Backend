#!/usr/bin/env python3

from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from app import app
from models import db, Exercise, Workout, WorkoutExercise

with app.app_context():
    try:
        # Clear the tables first so running this file again never makes
        # duplicates. The join table goes first because it points at the others.
        print('Clearing old data...')
        WorkoutExercise.query.delete()
        Workout.query.delete()
        Exercise.query.delete()

        print('Creating exercises...')
        pushups = Exercise(name='Push-ups', category='Strength', equipment_needed=False)
        squats = Exercise(name='Squats', category='Strength', equipment_needed=False)
        deadlift = Exercise(name='Deadlift', category='Strength', equipment_needed=True)
        plank = Exercise(name='Plank', category='Core', equipment_needed=False)
        jump_rope = Exercise(name='Jump Rope', category='Cardio', equipment_needed=True)
        db.session.add_all([pushups, squats, deadlift, plank, jump_rope])
        db.session.commit()

        print('Creating workouts...')
        w1 = Workout(date=date(2026, 10, 5), duration_minutes=45,
                     notes='Full body strength')
        w2 = Workout(date=date(2026, 10, 7), duration_minutes=30,
                     notes='Core and cardio')
        w3 = Workout(date=date(2026, 10, 9), duration_minutes=60,
                     notes='Heavy lift day')
        db.session.add_all([w1, w2, w3])
        db.session.commit()

        print('Adding exercises to workouts...')
        db.session.add_all([
            WorkoutExercise(workout=w1, exercise=pushups, reps=15, sets=3),
            WorkoutExercise(workout=w1, exercise=squats, reps=12, sets=4),
            WorkoutExercise(workout=w2, exercise=plank, sets=3, duration_seconds=60),
            WorkoutExercise(workout=w2, exercise=jump_rope, duration_seconds=300),
            WorkoutExercise(workout=w3, exercise=deadlift, reps=5, sets=5),
            WorkoutExercise(workout=w3, exercise=squats, reps=8, sets=4),
        ])
        db.session.commit()

        print('Done! Database seeded.')

    except SQLAlchemyError as err:
        # undo everything so we don't leave the database half filled
        db.session.rollback()
        print(f'Seeding failed: {err}')