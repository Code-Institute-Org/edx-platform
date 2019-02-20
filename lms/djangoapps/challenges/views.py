import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

from challenges.models import Challenge, ChallengeSubmission


@csrf_exempt
def hello(request):
    assignment_data = json.loads(request.body)
    student_email = assignment_data['student']['email']
    assignment_name = assignment_data['assignment']['name']
    assignment_score = assignment_data['submission']['status']
    assignment_created_timestamp = assignment_data['submission']['time_created']
    assignment_submitted_timestamp = assignment_data['submission']['time_submitted']
    assignment_passed = True if assignment_score == "complete" else False

    print(assignment_score)
    print(assignment_passed)

    try:
        student = User.objects.get(email="aaron@codeinstitute.net")
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