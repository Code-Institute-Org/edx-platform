from ci_program.models import Program


def unenroll_all_enrolled_students(program_code):
    """
    For a given program code, unenroll all students
    enrolled in said program.
    """
    program = Program.objects.get(program_code=program_code)
    enrolled_students = program.enrolled_students.all()
    for student in enrolled_students:
        program.unenroll_student_from_program(student)


class Command(BaseCommand):
    help = 'Unenroll all enrolled students from a specific program'

    def add_arguments(self, parser):
        parser.add_argument('program_code', type=str)

    def handle(self, program_code, **kwargs):
        unenroll_all_enrolled_students(program_code)
