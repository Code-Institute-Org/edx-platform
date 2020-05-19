import json
import pandas as pd

from enrollment.api import add_enrollment

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

DEFAULT_PATH = "replace_file.csv"


def replace_course_enrollment(student, deactivate_enrollment,
                              replace_with_enrolment=None):
    changes_made = False
    student_enrollments = student.courseenrollment_set.all()
    for e in student_enrollments:
        if e.course_id.html_id() == deactivate_enrollment:
            e.update_enrollment(is_active=False)
    if replace_with_enrolment is not None:
        add_enrollment(student.username, replace_with_enrolment)
        changes_made = True
    return changes_made


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'
    
    def add_arguments(self, parser):
        parser.add_argument("-f", "--filepath", type=str)

    def handle(self, *args, **options):
        """ Replace specific enrollment with another
        """
        filepath = options.get('filepath') or DEFAULT_PATH
        try:
            enrollment_changes = pd.read_csv("replace_file.csv").to_dict("records")
            for enrollment_change in enrollment_changes:
                student = User.objects.get(email=enrollment_change.get('email'))
                successful_change = replace_course_enrollment(
                    student=student,
                    deactivate_enrollment=enrollment_change.get('replace_course'),
                    replace_with_enrolment=enrollment_change.get('replace_with_course'))
                print("The change was successful: ", successful_change)
        except IOError as ioError:
            print(ioError)
        except ValueError as vError:
            print(vError)
        except TypeError as tError:
            print(tError)