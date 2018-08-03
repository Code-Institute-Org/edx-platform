from datetime import date
from logging import getLogger

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from ci_program.api import get_program_by_program_code
from student_enrollment.utils import register_student, get_or_register_student
from student_enrollment.serializers import EnrollmentSerializer
from student_enrollment.api import enroll_student_in_program

log = getLogger(__name__)

FAILURE_CODES = (
    (0, "Email already exists"),
    (1, "Program code not found"),
    (2, "User creation failed"),
    (3, "Failed to enroll student in program"),
    (4, "Failed to send email"),
    (5, "Invalid API key")
)


class Student:
    """
    A convenience class that we'll deserialize the student object
    so we can store the data in this `Student` object
    """

    def __init__(
        self, email, course_code, full_name, api_key, manual_override=False
    ):
        self.email = email
        self.course_code = course_code
        self.full_name = full_name
        self.api_key = api_key
        self.manual_override = manual_override


class StudentEnrollment(APIView):
    """
    The main API handler view class for the enrollment API. This API
    will enroll a given student in a program using the email address
    and program code provided.
    """

    def post(self, request):
        
        log.info("Received request from enrollment API")
        data = request.data
        serializer = EnrollmentSerializer(data=data)

        if serializer.is_valid():
            
            # Bind the deserialised data to an instance of the above
            # `Student` object
            student = Student(
                serializer.data['email'],
                serializer.data['course_code'],
                serializer.data['full_name'],
                serializer.data['api_key'],
                serializer.data['manual_override']
            )
            
            print(serializer.data)
            
            if student.api_key != settings.API_KEY:
                return Response(
                    {
                        "enrollment_status": FAILURE_CODES[5][0],
                        "reason": FAILURE_CODES[5][1]
                    },
                    status=status.HTTP_401_UNAUTHORIZED)
            
            # Create the user and get their password so they can be
            # emailed to the student later
            log.info("Creating user for %s" % student.email)
            user, password, _ = get_or_register_student(student.email, student.full_name)
            
            # If `None` was returned instead of a user instance then
            # respond with a 500 error and the corresponding failure
            # reason
            if not user:
                return Response(
                    {
                        "enrollment_status": FAILURE_CODES[4][0],
                        "reason": FAILURE_CODES[4][1]
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Enroll the new student into the chosen program
            log.info("Enrolling %s" % (student.email))
            program_enrollment_status = enroll_student_in_program(
                student.course_code, user)
            
            # If the enrollment was successful then continue as usual,
            # otherwise issue a 500 response
            if not program_enrollment_status:
                return Response(
                    {
                        "enrollment_status": FAILURE_CODES[5][0],
                        "reason": FAILURE_CODES[5][1]
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Send the email to the student
            log.info("Sending login credentials to %s" % student.email)
            email_sent_status = program.send_email(
                user, 0, password)
            
            # Check to see if the email was sent and if theyn't then
            # respond with a 500 error
            if email_sent_status:
                log.info("Email was successfully sent from the LMS")
            else:
                log.info("Email sending failure")
                return Response(
                    {
                        "enrollment_status": FAILURE_CODES[6][0],
                        "reason": FAILURE_CODES[6][1]
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Everything went well so return a status of 201 as well
            # as some basic information
            return Response(
                {
                    "enrollment_success": bool(program_enrollment_status),
                    "email_success": bool(email_sent_status)
                },
                status=status.HTTP_201_CREATED
            )
        else:
            log.warn("Data deserialisation unsuccessful - %s" % request.data)
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )
