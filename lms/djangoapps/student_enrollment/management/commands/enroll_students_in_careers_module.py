from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from ci_program.models import Program
from student_enrollment.zoho import (
    get_students_to_be_enrolled_in_careers_module
)
from opaque_keys import InvalidKeyError
"""
Students on the Full Stack Developer course are enrolled in the Careers module
following submission of their Interactive milestone project. Students eligible to 
be enrolled will have a status of 'Enroll' for the 'Access to Careers Module' field
on their CRM profile.
"""


class Command(BaseCommand):
    help = 'Enroll students in the careers module'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        """
        This will retrieve all of the users from the Zoho CRM API and
        with an 'Access to Careers Module' status of 'Enroll'.
        """
        careers_course_id = 'course-v1:code_institute+cc_101+2018_T1'
        students = get_students_to_be_enrolled_in_careers_module()

        for student in students:
            if not student['Email']:
                continue

            user = User.objects.get(email=student['Email'])
            print(user)
            program = Program.objects.get(program_code='FS')
            print(program)

            # Enroll the student in the program
            enroll_in_careers_module = program.enroll_student_in_a_specific_module(
                user.email, course_id)

            print(enroll_in_careers_module)
