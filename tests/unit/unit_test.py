import io
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.utils import secure_filename
from wtforms import Form
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, ValidationError


class DummyForm(Form):
    date = DateTimeLocalField('Date', format="%Y-%m-%dT%H:%M", validators=[DataRequired()])

def test_random_image_filename():
    image_filename_list = [
        "test.jpg", "test.jpg", "test.png",
        "test.png", "test.jpeg", "test.jpeg"
    ]
    unique_filenames = []

    for filename in image_filename_list:
        _, ext = os.path.splitext(secure_filename(filename))
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        unique_filenames.append(unique_filename)

    # Uniqueness
    assert len(unique_filenames) == len(set(unique_filenames)), "Filenames are not unique"

    # Valid UUID
    for fname in unique_filenames:
        base, ext = os.path.splitext(fname)
        assert len(base) == 32, f"UUID length incorrect: {base}"
        assert all(c in "0123456789abcdef" for c in base), f"Invalid character in UUID: {base}"

    # Extension matches
    for fname, original in zip(unique_filenames, image_filename_list):
        _, orig_ext = os.path.splitext(original)
        _, ext = os.path.splitext(fname)
        assert ext == orig_ext, f"Extension mismatch: {ext} vs {orig_ext}"

    assert len(unique_filenames) == 6, "Expected 6 unique filenames, got {len(unique_filenames)}"

def test_image_size_over_1mb():
    fake_image = io.BytesIO(b"x" * (1 * 1024 * 1024 + 1))  # >1MB
    fake_image.filename = "test.jpg"

    def validate_image():
        if hasattr(fake_image, "filename") and fake_image.filename:
            fake_image.seek(0, 2)  # move to end
            file_length = fake_image.tell()
            fake_image.seek(0)

            max_size = 1 * 1024 * 1024
            if file_length > max_size:
                raise ValidationError("Image size must be less than 1MB.")

    with pytest.raises(ValidationError) as excinfo:
        validate_image()

    assert "Image size must be less than 1MB" in str(excinfo.value), "Did not raise expected ValidationError for image size"

def test_image_size_below_1mb():
    fake_image = io.BytesIO(b"x" * (1 * 1024 * 1024 - 100))  # <1MB
    fake_image.filename = "test.jpg"

    def validate_image():
        if hasattr(fake_image, "filename") and fake_image.filename:
            fake_image.seek(0, 2)  # move to end
            file_length = fake_image.tell()
            fake_image.seek(0)

            max_size = 1 * 1024 * 1024
            if file_length > max_size:
                raise ValidationError("Image size must be less than 1MB.")

    # assert that no ValidationError happens
    try:
        validate_image()
        success = True
    except ValidationError:
        success = False

    assert success, "ValidationError was raised even though the image is <1MB"

def test_host_activity_date_in_past():
    # Check if error is raised when date is in the past
    # Simulate form field
    form = DummyForm()
    form.process(formdata=None, data={})  # initialize properly

    # manually set field.data as datetime
    field = form.date
    field.data = datetime.strptime("2019-07-08T15:30", "%Y-%m-%dT%H:%M")
    def validate_date():
        GMT8 = timezone(timedelta(hours=8))
        user_dt = field.data.replace(tzinfo=GMT8)
        now_gmt8 = datetime.now(GMT8)
        if user_dt <= now_gmt8:
            raise ValidationError("Date cannot be in the past (GMT+8).")
    
    with pytest.raises(ValidationError) as excinfo:
        validate_date()

    assert "Date cannot be in the past (GMT+8)." in str(excinfo.value), "Did not raise expected ValidationError for date in past"

def test_host_activity_date_in_future():
    # Check if no error is raised when date is in the future
    # Simulate form field
    form = DummyForm()
    form.process(formdata=None, data={})  # initialize properly

    # manually set field.data as datetime
    field = form.date
    field.data = datetime.strptime("2026-07-08T15:30", "%Y-%m-%dT%H:%M")
    def validate_date():
        GMT8 = timezone(timedelta(hours=8))
        user_dt = field.data.replace(tzinfo=GMT8)
        now_gmt8 = datetime.now(GMT8)
        if user_dt <= now_gmt8:
            raise ValidationError("Date cannot be in the past (GMT+8).")

    # assert that no ValidationError happens
    try:
        validate_date()
        success = True
    except ValidationError:
        success = False

    assert success, "ValidationError was raised even though the date is in the future"
    
    
if __name__ == "__main__":
    test_random_image_filename()
    test_image_size_over_1mb()
    test_image_size_below_1mb()
    test_host_activity_date_in_past()
    test_host_activity_date_in_future()
    print("All tests passed!")  # This will only run if the script is executed directly

