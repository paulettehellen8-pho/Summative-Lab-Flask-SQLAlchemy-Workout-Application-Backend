from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates
from sqlalchemy import CheckConstraint, UniqueConstraint

db = SQLAlchemy()

def check_whole_number(field_name, value, maximum):
    """Shared check for reps, sets, durations etc.
    Must be a whole number (not True/False) between 1 and maximum."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{field_name} must be a whole number.')
    if value < 1 or value > maximum:
        raise ValueError(f'{field_name} must be between 1 and {maximum}.')
    return value


def check_text(field_name, value, max_length):
    """Shared check for required text: must be a string, not blank,
    and not too long. Returns the text with spaces trimmed off."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field_name} is required and cannot be blank.')
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f'{field_name} must be {max_length} characters or fewer.')
    return value


class Exercise(db.Model):
    __tablename__ = 'exercises'

    # Table constraints: the database itself refuses blank text
    __table_args__ = (
        db.CheckConstraint('length(trim(name)) > 0',
                           name='ck_exercise_name_not_blank'),
        db.CheckConstraint('length(trim(category)) > 0',
                           name='ck_exercise_category_not_blank'),
    )

    id = db.Column(db.Integer, primary_key=True)
    # unique=True is also a table constraint: no two exercises with the same name
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=False)
    equipment_needed = db.Column(db.Boolean, nullable=False, default=False)

    # An Exercise has many WorkoutExercises.
    # delete-orphan + cascade means deleting an exercise also deletes its
    # WorkoutExercises rows, so we never leave rows pointing at nothing.
    workout_exercises = db.relationship(
        'WorkoutExercise', back_populates='exercise',
        cascade='all, delete-orphan')

    # An Exercise has many Workouts through WorkoutExercises
    workouts = association_proxy('workout_exercises', 'workout')

    # Model validations (these run as soon as a value is set)
    @validates('name')
    def validate_name(self, key, value):
        return check_text('Exercise name', value, 100)

    @validates('category')
    def validate_category(self, key, value):
        return check_text('Exercise category', value, 50)

    @validates('equipment_needed')
    def validate_equipment_needed(self, key, value):
        if not isinstance(value, bool):
            raise ValueError('equipment_needed must be true or false.')
        return value

    def __repr__(self):
        return f'<Exercise {self.id}: {self.name}>'


# class Exercise(db.Model):
#     __tablename__ = 'exercises'

#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String, nullable=False)
#     category = db.Column(db.String, nullable=False)
#     equipment_needed = db.Column(
#         db.Boolean,
#         nullable=False,
#         default=False
#     )

#     # Relationships
#     workout_exercises = db.relationship(
#         'WorkoutExercise',
#         back_populates='exercise',
#         cascade='all, delete-orphan'
#     )

#     workouts = db.relationship(
#         'Workout',
#         secondary='workout_exercises',
#         back_populates='exercises',
#         viewonly=True
#     )

#     # Model validations
#     @validates('name')
#     def validate_name(self, key, value):
#         if not value or not value.strip():
#             raise ValueError('Exercise name cannot be empty.')

#         return value.strip()

#     @validates('category')
#     def validate_category(self, key, value):
#         if not value or not value.strip():
#             raise ValueError('Exercise category cannot be empty.')

#         return value.strip()


class Workout(db.Model):
    __tablename__ = 'workouts'

    # Table constraint: a workout must last between 1 minute and 24 hours
    __table_args__ = (
        db.CheckConstraint('duration_minutes > 0 AND duration_minutes <= 1440',
                           name='ck_workout_duration_range'),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)

    # A Workout has many WorkoutExercises
    workout_exercises = db.relationship(
        'WorkoutExercise', back_populates='workout',
        cascade='all, delete-orphan')

    # A Workout has many Exercises through WorkoutExercises
    exercises = association_proxy('workout_exercises', 'exercise')

    @validates('date')
    def validate_date(self, key, value):
        if not isinstance(value, date):
            raise ValueError('date must be a real date.')
        return value

    @validates('duration_minutes')
    def validate_duration_minutes(self, key, value):
        return check_whole_number('duration_minutes', value, 1440)

    @validates('notes')
    def validate_notes(self, key, value):
        # notes are optional, so None is fine
        if value is None:
            return value
        if not isinstance(value, str):
            raise ValueError('notes must be text.')
        if len(value) > 1000:
            raise ValueError('notes must be 1000 characters or fewer.')
        return value

    def __repr__(self):
        return f'<Workout {self.id}: {self.date}>'


class WorkoutExercise(db.Model):
    __tablename__ = 'workout_exercises'

    # Database constraints
    __table_args__ = (
        UniqueConstraint(
            'workout_id',
            'exercise_id',
            name='unique_exercise_per_workout'
        ),
        CheckConstraint(
            'reps IS NULL OR reps > 0',
            name='check_reps_positive'
        ),
        CheckConstraint(
            'sets IS NULL OR sets > 0',
            name='check_sets_positive'
        ),
        CheckConstraint(
            'duration_seconds IS NULL OR duration_seconds > 0',
            name='check_duration_seconds_positive'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    workout_id = db.Column(
        db.Integer,
        db.ForeignKey('workouts.id'),
        nullable=False
    )

    exercise_id = db.Column(
        db.Integer,
        db.ForeignKey('exercises.id'),
        nullable=False
    )

    reps = db.Column(db.Integer)
    sets = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)

    # Relationships
    workout = db.relationship(
        'Workout',
        back_populates='workout_exercises'
    )

    exercise = db.relationship(
        'Exercise',
        back_populates='workout_exercises'
    )

    # Model validation
    @validates('reps', 'sets', 'duration_seconds')
    def validate_positive_values(self, key, value):
        if value is not None and value <= 0:
            raise ValueError(
                f'{key} must be greater than zero.'
            )

        return value




