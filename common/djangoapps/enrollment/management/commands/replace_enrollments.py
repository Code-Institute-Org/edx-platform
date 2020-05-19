import json
import pandas as pd

from enrollment.api import add_enrollment
from enrollment.errors import CourseEnrollmentExistsError
from opaque_keys import InvalidKeyError

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


def replace_course_enrollment(student, deactivate_enrollment,
                              replace_with_enrolment=None, mode=None):
    """ Method to set an existing enrollment to inactive and add 
    a new enrollment for another course if wanted
    
    Returns a boolean to indicate if the change was successful """
    changes_made = False
    student_enrollments = student.courseenrollment_set.all()
    for e in student_enrollments:
        if e.course_id.html_id() == deactivate_enrollment:
            e.update_enrollment(is_active=False)
    if replace_with_enrolment is not None:
        try:
            add_enrollment(user_id=student.username,
                        course_id=replace_with_enrolment,
                        mode=mode)
        except CourseEnrollmentExistsError as enrollmentExistsError:
            print("An error occurred: ", enrollmentExistsError.message)
            return changes_made
    changes_made = True
    return changes_made


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'
    
    def add_arguments(self, parser):
        parser.add_argument("-f", "--filepath", type=str)

    def handle(self, *args, **options):
        """ Replace specific enrollment with another
        """
        successful_changes = 0
        filepath = options.get('filepath')
        try:
            if filepath is None:
                raise IOError("No filepath specified. Please add the -f or --filepath flag.")

            df = pd.read_csv("replace_file.csv")
            # Needed to convert nan to None in case of missing values
            df = df.astype(object).where(pd.notnull(df), None)
            enrollment_changes = df.to_dict("records")
            for enrollment_change in enrollment_changes:
                try:
                    student = User.objects.get(email=enrollment_change.get('email'))
                    successful_change = replace_course_enrollment(
                        student=student,
                        deactivate_enrollment=enrollment_change.get('replace_course'),
                        replace_with_enrolment=enrollment_change.get('replace_with_course'),
                        mode="honor")
                    print("The change was successful: ", successful_change)
                    successful_changes += successful_change
                except User.DoesNotExist:
                    print("A user with the email %s could not be found" 
                          % enrollment_change.get('email'))
                except InvalidKeyError:
                    print("One or both of the CourseLocators are wrong.")
            print("%s changes out of %s successful."
                  % (str(successful_changes), str(len(enrollment_changes))))
        except IOError as ioError:
            print("An error occurred: ", ioError)
        except ValueError as vError:
            print("An error occurred: ", vError)
        except TypeError as tError:
            print("An error occurred: ", tError)
        