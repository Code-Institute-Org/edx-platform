import requests
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.cache import cache_control
from django.conf import settings
from django.core.context_processors import csrf
from django.core.mail import send_mail
from util.views import ensure_valid_course_key
from openedx.features.enterprise_support.api import data_sharing_consent_required
from opaque_keys.edx.keys import CourseKey
from courseware.courses import get_course_with_access
from edxmako.shortcuts import render_to_response


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def support(request, course_id, student_id=None):
    """ Display the support page. """
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response(
        'courseware/support.html',
        {"course": course, 'student': request.user})


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def tutor(request, course_id, student_id=None):
    """ Display the tutor page. """
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response(
        'courseware/support/tutor_page.html',
        {"course": course, 'student': request.user})


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def mentor(request, course_id, student_id=None):
    """ Display the mentor page. """
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response(
        "courseware/support/mentor.html",
        {
            "course": course,
            "student": request.user,
            "mentor": mentor
        })


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def slack(request, course_id, student_id=None):
    """ Display the slack page. """
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response(
        'courseware/support/slack.html',
        {"course": course, 'student': request.user})


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def troubleshooting(request, course_id, student_id=None):
    """ Display the troubleshooting page. """
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response(
        'courseware/support/troubleshooting.html',
        {"course": course, 'student': request.user})
        

@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def studentcare(request, course_id, student_id=None):
    """ Display the studentcare page. """
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response(
        "courseware/support/student_care.html",
        {
            "course": course,
            "student": request.user,
            "csrftoken": csrf(request)["csrf_token"]
        })