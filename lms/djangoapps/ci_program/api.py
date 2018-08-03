"""
A convience API for handle common interactions with the Program model.

This is simply a set of functions that can be used elsewhere to abstract some
of the complexities in certain aspects of the codebase, but also to remove the
need to import the Program model elsewhere.
"""
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from gridfs.errors import FileExists

from xmodule.modulestore.django import modulestore
from xmodule.modulestore import ModuleStoreEnum
from opaque_keys.edx.locator import CourseLocator
from opaque_keys.edx.keys import CourseKey
from course_modes.models import CourseMode
#from instructor_task.api import generate_certificates_for_students
from student.roles import CourseInstructorRole, CourseStaffRole
from certificates import api as certs_api
from ci_program.models import Program

ORGANISATION = "CodeInstitute"


################### STANDARD DATABASE QUERIES ###################
def get_all_programs():
    """
    Get collection of all of program codes from the `Program` model
    """
    return Program.objects.all()


def get_program_by_program_code(code):
    """
    Query the database for a specific program based on the program code

    `code` is the code that we use to identify the program

    Returns an instance of the program. Raises a 404 if the program
        doesn't exist
    """
    return get_object_or_404(Program, program_code=code)


def get_courses_from_program(code):
    """
    Get courses from a given program
    
    `code` is the code that we use to identify the program
    
    Returns a list of CourseOverview objects
    """
    program = get_program_by_program_code(code)
    return program.get_courses()


################### COURSE KEYS AND LOCATORS ###################
def _strip_course_key_of_prefix(course_key):
    """
    Keys don't currently contain the `course-v1:` sections of the CourseKey
    instance. This is due to the fact that we didn't know what a full key
    was when we created the programs
    TODO: remove this
    """
    SECTION_TO_BE_TRIMMED = "course-v1:"
    
    return str(course_key).replace(SECTION_TO_BE_TRIMMED, "", 1)


def _convert_locator_to_key(locator):
    key = CourseKey.from_string(str(locator))
    return key


def get_course_locators_for_program(code):
    """
    Get a list of CourseLocator objects for each module in a program

    `code` is the course code used as an identifier for a program

    Returns a list of CourseLocator objects
    """
    program = get_program_by_program_code(code)
    return program.get_course_locators()


def get_course_locators_as_course_keys(code):
    """
    Get a list of `CourseKey` objects
    
    `code` is the course code used as an identifier for a program

    Returns a list of `CourseKey` objects
    """
    course_keys = []
    
    for locator in get_course_locators_for_program(code):
        course_keys.append(_convert_locator_to_key(locator))
    
    return course_keys


def generate_new_date_based_locator(
        existing_start_date,
        course_number,
        time_frame_in_days,
        as_key
    ):
    """
    Create a new CourseLocator based on the start days.
    
    `existing_start_date` is the start date for current module run
    `course_number` is the course number
    `time_frame_in_days` is the number of days the future that we want
        to offset the locator by
    `as_key` will allow the developer to choose if they want to return
        the locator as a CourseKey
    """
    new_start_date = (existing_start_date + timedelta(
        days=time_frame_in_days)).strftime("%d%m%y")
    
    new_locator = CourseLocator(
        ORGANISATION, course_number, str(new_start_date))
    
    if as_key:
        return _convert_locator_to_key(new_locator)
    
    return new_locator

################### PROGRAM MODIFICATIONS AND RERUNS ###################
def _switch_course_code(program, old_key, new_key):
    """
    Update the relevant CourseCode object to include the new module key
    
    `new_key` is the CourseKey for the new run of the course
    `old_key` is the CourseKey for the old run of the course
    """
    new_key = _strip_course_key_of_prefix(new_key)
    old_key = _strip_course_key_of_prefix(old_key)
    
    # Get the relevant CourseCode instance
    course_code = program.course_codes.get(key=old_key)
    
    # Update the key and save the instance
    course_code.key = new_key
    course_code.save()


def create_course_modes(course_key, display_name):
    """
    Create a new CourseMode so certificates can be enabled on a module.
    
    `course_key` is the CourseKey instance for the course that we wish
        to create the CourseMode record for
    """
    # In order to issue a certificate, the module must have a code of `honor`,
    # `verified`, etc.
    COURSE_MODE = "honor"
    
    CourseMode(COURSE_MODE, course_key, display_name, 0, "usd")


def clone_module(old_key, new_key):
    """
    Create a clone of an existing module.
    
    `new_key` is the CourseKey for the new run of the course
    `old_key` is the CourseKey for the old run of the course
    
    Returns the new module instance
    """
    mgmt_command_user = ModuleStoreEnum.UserID.mgmt_command
    
    # Get the modulestore
    store = modulestore()
    
    with store.bulk_operations(new_key):
        try:
            store.clone_course(old_key, new_key, mgmt_command_user)
            CourseInstructorRole(new_key).add_users(
                *CourseInstructorRole(old_key).users_with_role()
            )
            CourseStaffRole(new_key).add_users(
                *CourseStaffRole(old_key).users_with_role()
            )
        except FileExists as e:
            pass
    
    return store.get_course(new_key)
    

def rerun_all_modules(code, new_course_number, time_frame_in_days):
    """
    Create a re-run of each existing module within a given program.
    
    `code` is program code that will be used to retrieve the Program
    `new_course_number` is the new course number that will be given to a
        new module.
    `time_frame_in_days` the number of days in the future that we wish
        to give as the start date
    
    Returns a list of new module CourseKey objects.
    
    TODO - This will give every module in the program the course number
        and run. This should be updated in the future to allow for multiple
        course numbers and runs
    """
    # Get the modulestore
    store = modulestore()
    
    program = get_program_by_program_code(code)
    module_keys = get_course_locators_as_course_keys(code)
    
    new_module_keys = []
    
    for key in module_keys:
        # Get the module from the modulestore
        module = store.get_course(key)
        
        # Create a new locator based on the start date of the existing run
        new_key = generate_new_date_based_locator(
            module.start, new_course_number, time_frame_in_days, True)
        
        # Get the old locator
        old_key = _convert_locator_to_key(module.location.course_key)
        
        # Clone the module
        new_module = clone_module(old_key, new_key)
        
        # Newly created module key
        new_module_key = _convert_locator_to_key(
            new_module.location.course_key)
        
        # Update the CourseCode instance to reflect the new CourseKey
        _switch_course_code(program, old_key, new_module_key)
        
        new_module_keys.append(new_module_key)
    
    return new_module_keys


################### CERTIFICATE GENERATION ###################
def generate_module_certificates(request, course_key):
    """
    Generate module level certificates for each module of the program.
    
    `request` is the HTTP Request object. This is mostly used for the
        `user` object contained within the request object
    `course_key` is the key of the course that the certificates are
        to be generated for
    """
    generate_certificates_for_students(request, course_key)


def enable_module_certificates(course_key):
    """
    Allow students to generate their certificates
    
    `course_key` is the key for the course that we wish to allow students
        to generate certificates for
    """
    certs_api.set_cert_generation_enabled(course_key, True)