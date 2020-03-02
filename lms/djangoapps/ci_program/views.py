from django.contrib.auth.decorators import login_required
from edxmako.shortcuts import render_to_response
from ci_program.models import Program
import logging

logger = logging.getLogger(__name__)

@login_required
def show_programs(request, program_name):
    """
    Display the programs page
    """
    program = Program.objects.get(marketing_slug=program_name)
    program_descriptor = program.get_program_descriptor(request.user)
    student_enrollment = [
        enrollment.course_id 
        for enrollment in request.user.courseenrollment_set.all()]
    logger.error('Student Enrollment')
    logger.error(student_enrollment)

    context = {}
    context["program"] = program_descriptor
    context["student_enrollement"] = student_enrollment
    return render_to_response('programs/programs.html', context)
