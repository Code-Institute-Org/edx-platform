"""
A management command that will run every week to create a new run of the
5DCC challenge.
"""
from django.core.management.base import BaseCommand, CommandError
from django.test import RequestFactory
from django.contrib.auth.models import User
from ci_program.api import (
    rerun_all_modules, create_course_modes,
    generate_module_certificates, enable_module_certificates
)


class Command(BaseCommand):
    
    help = 'Rerun the 5DCC module'
    
    def handle(self, *args, **options):
        
        # The certificate generation requires a request object that contains
        # a user, so we'll fake it here using `RequestFactory`
        REQUEST_META_INFO = {"REMOTE_ADDR": "0.0.0.0",
                             "SERVER_NAME": "courses.codeinstitute.net"}
        request = RequestFactory(**REQUEST_META_INFO)
        request.user = User.objects.get(email="aaron@codeinstitute.net")
        
        
        # For the 5DCC, the program code just happens to be the same as the
        # course number
        PROGRAM_CODE = "5DCC"
        COURSE_NUMBER = PROGRAM_CODE
        
        MODULE_DISPLAY_NAME = "5 Day Coding Challenge"
        
        new_course_keys = rerun_all_modules(PROGRAM_CODE, COURSE_NUMBER, 7)
        
        new_fdcc_key = new_course_keys[0]
        
        create_course_modes(new_fdcc_key, MODULE_DISPLAY_NAME)
        
        generate_module_certificates(request, new_fdcc_key)
        enable_module_certificates(new_fdcc_key)