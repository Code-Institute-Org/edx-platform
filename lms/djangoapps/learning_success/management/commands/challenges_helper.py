from challenges.models import Challenge

from collections import Counter, defaultdict
import json


def index_challenge_to_module_and_level():
    """ Collects all Challeges in the LMS

    TODO: Consider limiting it only to get a speficied program

    Returns a dict of all challenges with its PK and category"""
    challenge_index = {}
    for challenge in Challenge.objects.all():
        module = challenge.block_locator.split('+')[1].lower()
        module_level = "_".join((module, challenge.level)).lower()
        challenge_index[challenge.pk] = module_level
    return challenge_index


def single_student_challenge_history(student, challenge_counter,
                                     challenge_index):
    """ Creates the challenge history for one student

    Returns a dict with with passed, attempted and unattempted counts """
    challenge_activities = {module: defaultdict(int) for module
                            in challenge_counter.keys()}

    for submission in student.challengesubmission_set.all():
        module = challenge_index[submission.challenge_id]
        if submission.passed:
            challenge_activities[module]['passed'] += 1
        else:
            challenge_activities[module]['attempted'] += 1

    for module_level, total_challenges in challenge_counter.items():
        activities = challenge_activities[module_level]
        activities['unattempted'] = (
            total_challenges - activities['passed'] - activities['attempted'])
        activities = json.dumps(activities)

    return challenge_activities


def extract_all_student_challenges(program):
    """ Calculates the historical challenge data for all students

    Returns a dict with email and challenge history for each student """
    challenge_index = index_challenge_to_module_and_level()
    challenge_counter = Counter(challenge_index.values())
    students = program.enrolled_students.all()
    challenge_history = {
        student.email: single_student_challenge_history(
            student, challenge_counter, challenge_index)
        for student in students.prefetch_related('challengesubmission_set')
    }
    return challenge_history
