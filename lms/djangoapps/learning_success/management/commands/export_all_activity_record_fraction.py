from ci_program.api import get_program_by_program_code
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from opaque_keys.edx.locator import CourseLocator
from xmodule.modulestore.django import modulestore

from collections import Counter, defaultdict, OrderedDict
from datetime import datetime, timedelta
import json

import requests

PROGRAM_CODE = 'FS'  # Our Full-Stack program
BREADCRUMB_INDEX_URL = settings.LMS_SYLLABUS
KEYS = ['module','section','lesson']


def harvest_course_tree(tree, output_dict, prefix=()):
    """Recursively harvest the breadcrumbs for each component in a tree

    Populates output_dict
    """
    block_name = tree.display_name
    block_breadcrumbs = prefix + (tree.display_name,)
    block_id = tree.location.block_id

    output_dict[block_id] = block_breadcrumbs

    children = tree.get_children()
    for subtree in children:
        harvest_course_tree(subtree, output_dict, prefix=block_breadcrumbs)


def harvest_program(program):
    """Harvest the breadcrumbs from all components in the program

    Returns a dictionary mapping block IDs to the matching breadcrumbs
    """
    all_blocks = {}
    for course_locator in program.get_course_locators():
        course = modulestore().get_course(course_locator)
        harvest_course_tree(course, all_blocks)
    return all_blocks


def get_lesson_fractions(url):
    """Retrieve the course syllabus from Google Sheet with the ordering

    Returns a Dataframe to join to the rest of the breadcumbs
    """
    fractions = {}
    syllabus = requests.get(url).json()['LESSONS']
    #fractions = dict([(item['module'], item['fraction']) for item in syllabus])
    for item in syllabus.values():
        #print(item)
        fractions[' - '.join([item[x] for x in KEYS])] = {
            'time_fraction' : item['time_fraction'],
            'cumulative_fraction' : item['cumulative_fraction']}
    return fractions


def format_date(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def thirty_day_units(completion_timestamps):
    thirty_days_ago = timezone.now() - timedelta(days=30)
    return sum(date > thirty_days_ago for date in completion_timestamps)


def days_into_data(first_active, completion_timestamps):
    days_into_generator = (
        (date - first_active).days for date in completion_timestamps)
    return ','.join(map(str, sorted(days_into_generator)))


def format_module_field(module_name, suffix):
    return module_name.lower().replace(' ', '_') + suffix


def completed_lessons_per_module(breadcrumb_dict):
    return Counter(format_module_field(breadcrumbs[0], '_lessons')
                   for breadcrumbs in breadcrumb_dict.keys())


def completed_units_per_module(breadcrumb_dict):
    return Counter(format_module_field(breadcrumbs[0], '_units')
                   for breadcrumbs in breadcrumb_dict.keys())


def lessons_days_into_per_module(first_active, breadcrumb_dict):
    # there's a bit of voodoo here, to split the breadcrumb_dict into separate
    # timestamp lists, one per module
    per_module_lessons_times = defaultdict(list)
    for tup, timestamp in breadcrumb_dict.items():
        module = tup[0]
        per_module_lessons_times[module].append(timestamp)
    return {format_module_field(module, '_days_into'):
            days_into_data(first_active, timestamps)
            for module, timestamps in per_module_lessons_times.items()}

def fourteen_days_fractions(completed_fractions):
    fourteen_days_ago = timezone.now() - timedelta(days=14)
    return sum(item['time_fraction'] if item['time_completed'] > fourteen_days_ago else 0 for item in completed_fractions)

def cumulative_days_fractions(completed_fractions):
    return sum(item['time_fraction'] for item in completed_fractions)

def fractions_per_day(date_joined, limit, completed_fractions):

        range_limit = (timezone.now() - date_joined).days
        fractions_days = {i : 0 for i in range(range_limit+1)}
        for item in completed_fractions:
            days_in = (item['time_completed'] - date_joined).days
            fractions_days[days_in] += item['time_fraction']

        return ','.join(OrderedDict(sorted(fractions_days.items())).values())

def all_student_data(program):
    """Yield a progress metadata dictionary for each of the students

    Input is a pregenerated dictionary mapping block IDs in LMS to breadcrumbs
    """
    all_components = harvest_program(program)
    lesson_fractions = get_lesson_fractions(BREADCRUMB_INDEX_URL)

    for student in program.enrolled_students.all():
        # A short name for the activities queryset
        student_activities = student.studentmodule_set.filter(
            course_id__in=program.get_course_locators())

        # remember details of the first activity
        first_activity = student_activities.order_by('created').first()
        first_active = (
            first_activity.created if first_activity else student.date_joined)

        # We care about the lesson level (depth 3) and unit level (depth 4).
        # Dictionaries of breadcrumbs to timestamps of completion
        completed_lessons = {}
        completed_fractions = {}
        completed_units = {}
        # Provide default values in cases where student hasn't started
        latest_unit_started = None
        latest_unit_breadcrumbs = (u'',) * 4
        for activity in student_activities.order_by('modified'):
            block_id = activity.module_state_key.block_id
            breadcrumbs = all_components.get(block_id)
            if breadcrumbs and len(breadcrumbs) == 3:  # lesson
                # for each lesson learned, store latest timestamp
                completed_lessons[breadcrumbs] = activity.modified

                #Calculate fractions
                fraction_key = ' - '.join(breadcrumbs[0:3])
                time_fraction = 0
                cumulative_fraction = 0                

                # Check if fractions for lesson exist, if not attribute 0
                if fraction_key in lesson_fractions:
                    time_fraction = lesson_fractions[' - '.join(breadcrumbs[0:3])]['time_fraction']
                    cumulative_fraction = lesson_fractions[' - '.join(breadcrumbs[0:3])]['cumulative_fraction']

                completed_fractions[breadcrumbs] = {
                    'time_completed' : activity.modified,
                    'time_fraction' : time_fraction,
                    'cumulative_fraction' : cumulative_fraction}

            if breadcrumbs and len(breadcrumbs) >= 4:  # unit or inner block
                unit_breadcrumbs = breadcrumbs[:4]
                # for each unit learned, store latest timestamp
                completed_units[unit_breadcrumbs] = activity.modified

                # remember details of the latest unit overall
                # we use 'created' (not 'modified') to ignore backward leaps
                # to old units; sadly, there's no way to ignore forward leaps
                latest_unit_started = activity.created
                latest_unit_breadcrumbs = unit_breadcrumbs

        days_into = days_into_data(first_active, completed_units.values())
        student_dict = {
            'email': student.email,
            'date_joined': format_date(first_active),
            'last_login': format_date(student.last_login),
            'latest_unit_completion': format_date(latest_unit_started),
            'latest_module': latest_unit_breadcrumbs[0].encode('utf-8'),
            'latest_section': latest_unit_breadcrumbs[1].encode('utf-8'),
            'latest_lesson': latest_unit_breadcrumbs[2].encode('utf-8'),
            'latest_unit': latest_unit_breadcrumbs[3].encode('utf-8'),
            'units_in_30d': thirty_day_units(completed_units.values()),
            'days_into_data': days_into,
            'completed_fractions_14d' : fourteen_days_fractions(completed_fractions.values()),
            'cumulative_completed_fractions' : cumulative_days_fractions(completed_fractions.values()),
            'fractions_per_day': str(fractions_per_day(first_active, max(days_into.split(',')), completed_fractions.values())
        }

        student_dict.update(completed_lessons_per_module(completed_lessons))
        student_dict.update(completed_units_per_module(completed_units))
        student_dict.update(
            lessons_days_into_per_module(first_active, completed_lessons))

        yield student_dict


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'

    def handle(self, *args, **options):
        """POST the collected data to the api endpoint from the settings
        """
        program = get_program_by_program_code(PROGRAM_CODE)
        all_students = all_student_data(program)
        student_data = [x for x, _ in zip(all_students, range(500))]
        print(student_data)

        api_endpoint = 'https://script.google.com/macros/s/AKfycbxszIgBOWeJpyUO9ucU7fF0JmkdOEjyawsPoweE-5qJAaUh5wkv/exec'
        resp = requests.post(api_endpoint, data=json.dumps(student_data))
        if resp.status_code != 200:
            raise CommandError(resp.text)
