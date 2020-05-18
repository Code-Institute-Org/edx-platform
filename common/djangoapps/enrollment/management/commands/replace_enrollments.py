from enrollment.api import add_enrollment

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

emails = ['stefan@codeinstitute.net','cidummystudent@gmail.com']

students = User.objects.filter(email__in=emails)
REMOVE_COURSE = 'course-v1:CodeInstitute+F101+2017_T1'
REPLACE_WITH = 'course-v1:CodeInstitute+FSF_102+Q1_2020'

students = User.objects.filter(email__in=emails)
student = students[0]

student_enrollments = student.courseenrollment_set.all()


def replace_course_enrollment(student_enrollments, deactivate_enrollment,
                              replace_with_enrolment=None):
    for e in student_enrollments:
        if e.course_id.html_id() == REMOVE_COURSE:
            e.update_enrollment(is_active=False)
    if replace_with_enrolment is not None:
        add_enrollment(student.username, REPLACE_WITH)


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'

    def handle(self, *args, **options):
        """ Replace specific enrollment with another
        """

        print(args)