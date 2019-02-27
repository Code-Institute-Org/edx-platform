import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db.models import Q

from challenges.models import Challenge, ChallengeSubmission


@csrf_exempt
def challenge_handler(request):
    assignment_data = json.loads(request.body)

    student_email = assignment_data['student']['email']
    student_name = "{} {}".format(
        assignment_data['student']['first_name'],
        assignment_data['student']['last_name']
        )

    assignment_name = assignment_data['assignment']['name']
    assignment_score = assignment_data['submission']['status']
    assignment_created_timestamp = assignment_data['submission']['time_created']
    assignment_submitted_timestamp = assignment_data['submission']['time_submitted']
    assignment_passed = True if assignment_score == "complete" else False

    try:
        student = User.objects.get(Q(email=student_email) | Q())
    except User.DoesNotExist:
        print("Fuuuuuuuuuuuuuck")
    
    try:
        challenge = Challenge.objects.get(name=assignment_name)
        print(challenge.block_locator)
    except Challenge.DoesNotExist:
        print("Challenge fuuuuuuuuck")
    
    submission = ChallengeSubmission(
        student=student, challenge=challenge,
        time_challenge_started=assignment_created_timestamp,
        time_challenge_submitted=assignment_submitted_timestamp,
        passed=assignment_passed
    )

    print(submission.passed)
    submission.save()
    
    return HttpResponse(status=200)