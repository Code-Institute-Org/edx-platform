from lms.djangoapps.challenges.models import Challenge

from collections import Counter, defaultdict


class ChallengeAggregator:

    def __init__(self):
        self.CHALLENGE_INDEX = self.index_challenge_to_module_and_level()
        self.CHALLENGE_COUNT_IN_MODULE_LEVEL = Counter(self.CHALLENGE_INDEX.values())


    def index_challenge_to_module_and_level(self):
        challenge_index = {}
        for challenge in Challenge.objects.all():
            module = challenge.block_locator.split('+')[1].lower()
            challenge_index[challenge.pk] = "_".join((module, challenge.level)).lower()
        return challenge_index


    def calculate_unattempted(self, module, passed, attempted):
        total = self.CHALLENGE_COUNT_IN_MODULE_LEVEL[module]
        return total - passed - attempted


    def single_student_challenge_history(self, student):
        challenge_activities = {module: defaultdict(int) for module
                                in self.CHALLENGE_COUNT_IN_MODULE_LEVEL.keys()}

        for submission in student.challengesubmission_set.all():
            module = self.CHALLENGE_INDEX[submission.challenge_id]
            if submission.passed:
                challenge_activities[module]['passed'] += 1
            else:
                challenge_activities[module]['attempted'] += 1

        for module_level in self.CHALLENGE_COUNT_IN_MODULE_LEVEL.keys():
            activities = challenge_activities[module_level]
            activities['unattempted'] = self.calculate_unattempted(
                module_level, activities['passed'], activities['attempted'])

        return challenge_activities


    def extract_student_challenges(self, program):
        students = program.enrolled_students.all()
        challenge_history = {
            student.email: self.single_student_challenge_history(student)
            for student in students.prefetch_related('challengesubmission_set')
        }
        return challenge_history
