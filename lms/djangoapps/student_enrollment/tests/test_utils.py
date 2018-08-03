import unittest
from django.contrib.auth.models import User
from student_enrollment.utils import register_student, get_or_register_student


class TestUtils:
    
    def test_creation_of_new_student(self):
        """
        """
        email_address = "text_email@example.com"
        user, password, enrollment_type = get_or_register_student(email_address)
        assert User.objects.get(email=email_address)
        