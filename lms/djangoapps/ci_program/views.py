from django.contrib.auth.decorators import login_required
from edxmako.shortcuts import render_to_response
from ci_program.models import Program


@login_required
def show_programs(request, program_name):
    """
    Display the programs page
    """
    program = Program.objects.get(marketing_slug=program_name)
    program_descriptor = program.get_program_descriptor(request.user)
    # Any data passed to context need to be dict
    enrolled_course_codes = {
        enrollment.course_id : True 
        for enrollment in request.user.courseenrollment_set.all() }

    context = {}
    context["program"] = program_descriptor
    context["enrolled_course_codes"] = enrolled_course_codes
    return render_to_response('programs/programs.html', context)
