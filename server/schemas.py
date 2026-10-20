from datetime import date

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


def not_too_old(value):
    """Schema validator for dates: stops silly values like 0001-01-01."""
    if value < date(2000, 1, 1):
        raise ValidationError('date must be 2000-01-01 or later.')


class ExerciseSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    category = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    equipment_needed = fields.Bool(load_default=False)

    # Shown when we look at ONE exercise: which workouts it is in
    workout_exercises = fields.Nested(
        'WorkoutExerciseSchema', many=True, dump_only=True,
        only=('id', 'workout', 'reps', 'sets', 'duration_seconds'))

    @validates_schema
    def no_blank_text(self, data, **kwargs):
        # "   " passes the Length check above, so catch it here
        for field in ('name', 'category'):
            if field in data and not data[field].strip():
                raise ValidationError('Must not be blank.', field)


class WorkoutSchema(Schema):
    id = fields.Int(dump_only=True)
    date = fields.Date(required=True, validate=not_too_old)
    duration_minutes = fields.Int(
        required=True, strict=True, validate=validate.Range(min=1, max=1440))
    notes = fields.Str(allow_none=True, validate=validate.Length(max=1000))

    # Shown when we look at ONE workout: its exercises with reps/sets/duration
    workout_exercises = fields.Nested(
        'WorkoutExerciseSchema', many=True, dump_only=True,
        only=('id', 'exercise', 'reps', 'sets', 'duration_seconds'))


class WorkoutExerciseSchema(Schema):
    id = fields.Int(dump_only=True)
    workout_id = fields.Int(dump_only=True)
    exercise_id = fields.Int(dump_only=True)
    reps = fields.Int(strict=True, allow_none=True,
                      validate=validate.Range(min=1, max=1000))
    sets = fields.Int(strict=True, allow_none=True,
                      validate=validate.Range(min=1, max=100))
    duration_seconds = fields.Int(strict=True, allow_none=True,
                                  validate=validate.Range(min=1, max=86400))

    # only= stops the two schemas from nesting inside each other forever
    exercise = fields.Nested(
        ExerciseSchema, dump_only=True,
        only=('id', 'name', 'category', 'equipment_needed'))
    workout = fields.Nested(
        WorkoutSchema, dump_only=True,
        only=('id', 'date', 'duration_minutes', 'notes'))

    @validates_schema
    def need_reps_or_duration(self, data, **kwargs):
        has_reps = data.get('reps') is not None
        has_duration = data.get('duration_seconds') is not None

        if not has_reps and not has_duration:
            raise ValidationError('Give reps (with sets) or duration_seconds.')
        if has_reps and data.get('sets') is None:
            raise ValidationError('sets is required when reps is given.', 'sets')


# Ready-made schema objects used by the routes in app.py.
# The list versions leave out the nested data so the lists stay short.
exercise_schema = ExerciseSchema()
exercises_schema = ExerciseSchema(many=True, exclude=('workout_exercises',))
workout_schema = WorkoutSchema()
workouts_schema = WorkoutSchema(many=True, exclude=('workout_exercises',))
workout_exercise_schema = WorkoutExerciseSchema()