from django.conf import settings
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from util.views import ensure_valid_course_key
from zoho.api import ZohoAPI

from opaque_keys.edx.keys import CourseKey
from courseware.courses import get_course_with_access
from edxmako.shortcuts import render_to_response
from openedx.features.enterprise_support.api import data_sharing_consent_required


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def mentor(request, course_id, student_id=None):
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    api = ZohoAPI(
        settings.ZOHO_ENDPOINT_PREFIX, settings.ZOHO_TOKEN, settings.ZOHO_RESPONSE_SIZE)

    zoho_record = api.get_a_student(request.user.email)

    return render_to_response('courseware/support/mentor_page.html', {
        "course": course,
        "student": request.user,
        "zoho_record": zoho_record
    })


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def slack(request, course_id, student_id=None):
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response('courseware/support/slack_page.html', {
        "course": course,
        "student": request.user
    })


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def tutor(request, course_id, student_id=None):
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response('courseware/support/tutor_page.html', {
        "course": course,
        "student": request.user
    })


@transaction.non_atomic_requests
@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@ensure_valid_course_key
@data_sharing_consent_required
def support(request, course_id, student_id=None):
    """Display the support page."""
    course_key = CourseKey.from_string(course_id)

    course = get_course_with_access(request.user, 'load', course_key)

    return render_to_response('courseware/support.html', {
        "course": course,
        "student": request.user
    })