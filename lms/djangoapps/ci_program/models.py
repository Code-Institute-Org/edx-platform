from logging import getLogger
from uuid import uuid4
from django.db import models
from django_extensions.db.models import TimeStampedModel
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.mail import send_mail
from opaque_keys.edx.locator import CourseLocator
from openedx.core.djangoapps.xmodule_django.models import CourseKeyField
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from lms.djangoapps.courseware.courses import get_course
from openedx.core.lib.courses import course_image_url

log = getLogger(__name__)


def _choices(*values):
    """
    Helper for use with model field 'choices'.
    """
    return [(value, ) * 2 for value in values]


def code_to_locator(course_code):
    """
    Helper to get the course locator object based on the course code
    """
    course_identifiers = course_code.key.split('+')
    return CourseLocator(*course_identifiers)


class Program(TimeStampedModel):
    """
    Representation of a Program.
    """

    uuid = models.UUIDField(
        blank=True,
        default=uuid4,
        editable=False,
        unique=True,
    )

    name = models.CharField(
        help_text=_('The user-facing display name for this Program.'),
        max_length=255,
        unique=True,
    )

    subtitle = models.CharField(
        help_text=_('A brief, descriptive subtitle for the Program.'),
        max_length=255,
        blank=True,
    )

    marketing_slug = models.CharField(
        help_text=_('Slug used to generate links to the marketing site'),
        blank=True,
        max_length=255
    )

    length_of_program = models.CharField(max_length=25, null=True, blank=True)
    effort = models.CharField(max_length=25, null=True, blank=True)
    full_description = models.TextField(null=True, blank=True)
    image = models.URLField(null=True, blank=True)
    video = models.URLField(null=True, blank=True)
    program_code = models.CharField(max_length=50, null=True, blank=True)
    enrolled_students = models.ManyToManyField(
        User, blank=True)
    program_code_friendly_name = models.CharField(max_length=50, null=True, blank=True)

    @property
    def number_of_modules(self):
        """
        Get the length of a program - i.e. the number of modules
        """
        return len(self.get_courses())

    def __unicode__(self):
        return unicode(self.name)

    def get_program_descriptor(self, user):
        """
        The program descriptor will return all of necessary courseware
        info for a given program. The information contained in the descriptor
        should include -

          - Name
          - Subtitle
          - Full description
          - Image
          - Video
          - Length
          - Effort
          - Number of modules
          - Modules
            - Name
            - Short Description
            - Key
            - Image
        """
        # Gather the modules (course objects) in the program
        modules = []
        if self.program_code == "5DCC":
            # TODO: there has to be a better way
            users_five_day_module = user.courseenrollment_set.filter(
                course_id__icontains="dcc").order_by('created').last()
            course_id = users_five_day_module.course_id
            course_overview = CourseOverview.objects.get(id=course_id)
            course_descriptor = get_course(course_id)

            modules.append({
                    "course_key": course_id,
                    "course": course_overview,
                    "course_image": course_image_url(course_descriptor)
                })
        else:
            for course_overview in self.get_courses():
                course_id = course_overview.id
                course_descriptor = get_course(course_id)

                modules.append({
                    "course_key": course_id,
                    "course": course_overview,
                    "course_image": course_image_url(course_descriptor)
                })

        return {
            "name": self.name,
            "subtitle": self.subtitle,
            "full_description": self.full_description,
            "image": self.image,
            "video": self.video,
            "length": self.length,
            "effort": self.effort,
            "number_of_modules": self.number_of_modules,
            "modules": modules
        }

    def get_course_locators(self):
        """
        Get the list of locators for each of the modules in a program
        """
        return [code_to_locator(code) for code in self.course_codes.all()]

    def get_courses(self):
        """
        Get the list of courses in the program

        Returns the list of children courses
        """
        return [CourseOverview.objects.get(id=locator)
                for locator in self.get_course_locators()]


class CourseCode(models.Model):
    """
    Store the key and display names for each course that belongs to a program
    """
    key = models.CharField(
        help_text="The 'course' part of course_keys associated with this course code, "
                  "for example 'DemoX' in 'edX/DemoX/Demo_Course'.",
        max_length=128
    )
    display_name = models.CharField(
        help_text=_('The display name of this course code.'),
        max_length=128,
    )
    programs = models.ManyToManyField(
        Program, related_name='course_codes', through='ProgramCourseCode')

    def __unicode__(self):
        return unicode(self.display_name)


class ProgramCourseCode(TimeStampedModel):
    """
    Represent the many-to-many association of a course code with a program.
    """
    program = models.ForeignKey(Program)
    course_code = models.ForeignKey(CourseCode)
    position = models.IntegerField()

    class Meta(object):  # pylint: disable=missing-docstring
        ordering = ['position']

    def __unicode__(self):
        return unicode(self.course_code)
