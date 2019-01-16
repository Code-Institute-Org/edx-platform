from django.db import models
from django.contrib.auth.models import User

from opaque_keys.edx.locator import CourseLocator, BlockUsageLocator
from openedx.core.djangoapps.xmodule_django.models import LocationKeyField
from xmodule.modulestore.django import modulestore
from courseware.models import StudentModule, StudentModuleHistory


class Tag(models.Model):

    name = models.CharField(max_length=20)
    sort_key = models.IntegerField()

    class Meta:
        ordering = ('sort_key',)

    def __str__(self):
        return self.name


class Challenge(models.Model):
    """
    This model is used to map the challenges to the assignments in repl.it.
    Because our challenges are all created outside of our LMS, we have no
    internal record of them.

    This model will allow us to store the name of the repl.it assignment 
    and the locator for the block that the iframe was added to.

    When a student submits a challenge in repl.it, repl.it will send
    metadata about the challenge to our webhook. Our webhook handler will
    parse the data, extract the name of the assignment and use that
    assignment name to lookup the location of the challenge block.

    This will allow us to update the StudentModule with the correct
    block location, thus tying the external assignments to our own
    internal `xblock` system.
    """

    LEVEL = (
        (1, 'Required'),
        (2, 'Optional'),
        (3, 'Bonus'),
    )

    name = models.CharField(max_length=120, blank=False, null=False)
    block_locator = LocationKeyField(max_length=120, blank=False, null=False)
    tags = models.ManyToManyField(Tag, blank=False, null=False)
    level = models.CharField(max_length=50, choices=LEVEL, blank=False, null=False)

    @property
    def get_course_and_block_locators(self):
        """
        Parse the `block_locator` value to extract the course and block
        ids, and then use this information to get the course and block
        locators.
        """
        course_key_partition, _, block_id_partition = str(
            self.block_locator).replace("block-v1:", "").replace(
                "+type@problem+block", "").partition("@")
        block_type = 'problem'
        course_locator = CourseLocator(*course_key_partition.split('+'))
        block_locator = BlockUsageLocator(
            course_locator, block_type, block_id_partition)
        return course_locator, block_locator
    
    @property
    def get_course_key_and_block_location(self):
        course_locator, block_locator = self.get_course_and_block_locators
        course_key = modulestore().get_course(
            course_locator).location.course_key
        block_location = modulestore().get_item(block_locator).location

        return course_key, block_location
    
    def __str__(self):
        return "%s -> %s" % (self.name, self.block_locator)


class ChallengeSubmission(models.Model):

    student = models.ForeignKey(User)
    challenge = models.ForeignKey(Challenge)
    time_challenge_started = models.DateTimeField()
    time_challenge_submitted = models.DateTimeField()
    passed = models.BooleanField()
