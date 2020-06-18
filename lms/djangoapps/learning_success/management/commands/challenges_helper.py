from challenges.models import Challenge

from collections import Counter, defaultdict
import json

from lms.djangoapps.learning_success.management.commands.export_all_breadcrumbs import get_safely

DEFAULT_SKILL = {
    "achieved": 0,
    "total": 0,
}


def increment_student_skill_tags(challenge_skills, skill_tags, incrementor):
    """ Increments the student's achieved skill tags based on the skill tags
    of the challenge
    
    Modifies dict inplace """ 
    for skill in skill_tags:
        challenge_skills.set_default(skill, DEFAULT_SKILL)
        challenge_skills[skill]['achieved'] += incrementor
        challenge_skills[skill]['total'] += 1


def index_challenge_to_module_and_level():
    """ Collects all Challeges in the LMS

    TODO: Consider limiting it only to get a speficied program

    Returns a dict of all challenges with its PK and category"""
    challenge_index = {}
    skill_tags = {}
    for challenge in Challenge.objects.all():
        update_skills_tags(skill_tags, challenge)
        module = challenge.block_locator.split('+')[1].lower()
        module_level = "_".join((module, challenge.level)).lower()
        challenge_index[challenge.pk] = {
            'module_name': module_level,
            'tags': [tag.name for tag in challenge.tags.all()]
    return challenge_index


def single_student_challenge_history(student, challenge_counter,
                                     challenge_index):
    """ Creates the challenge history for one student

    Returns a dict with with passed, attempted and unattempted counts """
    challenge_activities = {module: defaultdict(int) for module
                            in challenge_counter.keys()}
    student_skills = {}
    for submission in student.challengesubmission_set.all():
        module = challenge_index[submission.challenge_id].get('module_name')
        skill_tags = challenge_index[submission.challenge_id].get('tags')
        incrementor = 0
        if submission.passed:
            challenge_activities[module]['passed'] += 1
            incrementor = 1
        else:
            challenge_activities[module]['attempted'] += 1
        increment_student_skill_tags(increment_student_skill_tags,
                                     skill_tags, incrementor)

    for module_level, total_challenges in challenge_counter.items():
        activities = challenge_activities[module_level]
        activities['unattempted'] = (
            total_challenges - activities['passed'] - activities['attempted'])
    
    challenge_activities = {
        module: json.dumps(challenges)
        for module, challenges in challenge_activities.items()
    }
    challenge_activities['student_skills'] = skill_tags
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
