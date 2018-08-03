from logging import getLogger

from lms.djangoapps.student_enrollment.models import StudentEnrollment
from ci_program.api import get_program_by_program_code

log = getLogger(__name__)


def enroll_student_in_program(code, user):
    """
    Enroll a student in a program.

    `code` is the code of the program that we want to enroll the
        student in
    `user` is the instance of the user that we wish to enroll
    Note that the student must already be registered to the platform

    Returns the status of the enrollment
    """
    program = get_program_by_program_code(code)
    student_enrollment = StudentEnrollment.objects.get_or_create(
        program=program, student=user, is_active=True)

    student_enrollment.save()
    enrollment_status = student_enrollment.enroll()
    
    if enrollment_status:
        log.info("%s successfully enrolled" % (user.email))
        return enrollment_status
    
    log.warn("Enrollment for %s failed" % (user.email))
    return enrollment_status


def get_enrolled_students(code):
    """
    Gets a list of the enrolled students enrolled in a given program

    `code` is the code of the program that we want to get the list
        of enrolled users from

    Returns a collection of all `user` objects
    """
    program = get_program_by_program_code(code)
    return program.enrolled_students.all()


def is_student_enrolled_in_program(code, email):
    """
    Check whether a given student is enrolled in a given program

    `code` is the course code used as an identifier for a program
    `email` is the email of the user that we want to check for

    Returns True or False based on whether or not a student is enrolled
        in the program
    """
    program = get_program_by_program_code(code)
    return program.enrolled_students.filter(email=email).exists()


def number_of_enrolled_students(code):
    """
    Get the number of students that are enrolled in a given program

    `code` is the code of the program that we're interested in

    Returns the total number of students enrolled
    """
    program = get_program_by_program_code(code)
    return program.enrolled_students.count()


def number_of_students_logged_into_access_program(code):
    """
    Get the number of students that have logged into the LMS to get
    access to their course content.

    `code` is the code of the program we are interested in.

    Returns the total number of students that have logged
        per-program
    """
    program = get_program_by_program_code(code)
    return program.enrolled_students.exclude(last_login__isnull=True).count()