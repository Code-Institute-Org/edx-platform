import json
import pandas as pd

from enrollment.api import add_enrollment
from enrollment.errors import CourseEnrollmentExistsError
from opaque_keys import InvalidKeyError

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


def replace_course_enrollment(student, deactivate_enrollment,
                              replace_with_enrollment=None, mode=None):
    """ Sets an existing enrollment to inactive and adds 
    a new enrollment for another course if wanted

    If replace_with_enrollment is None, then no new enrollment will be added
    
    Returns a boolean to indicate if the change was successful """
    changes_made = False
    student_enrollments = student.courseenrollment_set.all()
    for e in student_enrollments:
        if e.course_id.html_id() == deactivate_enrollment:
            e.update_enrollment(is_active=False)
    if replace_with_enrollment is not None:
        try:
            add_enrollment(user_id=student.username,
                        course_id=replace_with_enrollment,
                        mode=mode)
        except CourseEnrollmentExistsError as enrollmentExistsError:
            print('An error occurred: ', enrollmentExistsError.message)
            return changes_made
    changes_made = True
    return changes_made


class Command(BaseCommand):
    help = 'Deactivate existing enrollment and add a new course enrollment'
    
    def add_arguments(self, parser):
        """ Adds a custom command line argument """
        parser.add_argument('-f', '--filepath', type=str)

    def handle(self, *args, **options):
        """ Replaces an enrolled course by deactivating an existing enrollment
        and adding a new course to the enrollments
        
        Takes a CSV file as input with the following columns: 

            'email' with the student's email in the LMS
            'replace_course' the course id that should be deactivated
            'replace_with_course' the course id that should be added to the
            enrollments

            Example course id: 'course-v1:CodeInstitute+F101+2017_T1'

        """
        successful_changes = 0
        filepath = options.get('filepath')
        try:
            if filepath is None:
                raise IOError('No filepath specified. Please add the -f or --filepath flag.')

            df = pd.read_csv(filepath)
            # Needed to convert nan to None in case of missing values
            df = df.astype(object).where(pd.notnull(df), None)
            enrollment_changes = df.to_dict('records')
            for enrollment_change in enrollment_changes:
                try:
                    student = User.objects.get(email=enrollment_change.get('email'))
                    successful_change = replace_course_enrollment(
                        student=student,
                        deactivate_enrollment=enrollment_change.get('replace_course'),
                        replace_with_enrollment=enrollment_change.get('replace_with_course'),
                        mode='honor')
                    print('The change was successful: ', successful_change)
                    successful_changes += successful_change
                except User.DoesNotExist:
                    print('A user with the email %s could not be found' 
                          % enrollment_change.get('email'))
                except InvalidKeyError:
                    print('One or both of the CourseLocators are wrong.')
            print('%s changes out of %s successful.'
                  % (str(successful_changes), str(len(enrollment_changes))))
        except IOError as ioError:
            print('An error occurred: ', ioError)
        except ValueError as vError:
            print('An error occurred: ', vError)
        except TypeError as tError:
            print('An error occurred: ', tError)
        