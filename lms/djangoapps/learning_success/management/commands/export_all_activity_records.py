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
BREADCRUMB_INDEX_URL = settings.BREADCRUMB_INDEX_URL
KEYS = ['module','section','lesson']

# TODO: Find a way how to retrieve these dynamically
PROJECTS = {
    'user_centric_frontend_development': 0.06,
    'interactive_frontend_development': 0.06,
    'data_centric_development': 0.07,
    'full_stack_frameworks_with_django': 0.08
}


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


def n_days_fractions(completed_fractions, days_ago=0):
    """Sum fractions completed for the n previous days
    If days_ago is 0 (by default) it will sum all completed fractions

    Returns the sum of fractions as float
    """
    period_start = timezone.now() - timedelta(days=days_ago)
    return sum(
        item['lesson_fraction'] 
        if item['time_completed'] > period_start or days_ago == 0 else 0 
        for item in completed_fractions)


def fractions_per_day(date_joined, completed_fractions):
        """Create a list of fractions completed for 
        each day since the student started

        1) Create a dict where the keys are all the days in the student life
        2) Loop through all completed fractions for the student and
        calculate on which day in their lifecyle each fraction was completed
        3) Add each fraction to that day in their lifecyle

        Returns a comma separated string of fractions 
        per day in the student lifecyle
        """
        days_since_joined = (timezone.now() - date_joined).days
        # Needs to be string, then cast to float for calculation
        # Then be converted back to string for join operation
        days = {str(day) : '0' for day in range(days_since_joined + 1)}
        for fraction in completed_fractions:
            days_in = str((fraction['time_completed'] - date_joined).days)
            days[days_in] = str(float(days[days_in]) 
                                            + fraction['lesson_fraction'])
        return ','.join(OrderedDict(sorted(days.items())).values())


def fractions_per_module(fractions, completed_fractions, days_ago=14):
    """Aggregate completed fractions witin last n days and the rest
        
    Returns a dict with module and the completed aggregations
    """
    n_days_ago = timezone.now() - timedelta(days=days_ago)
    for module, fraction in completed_fractions.items():
        accessor = (
            format_module_field(module[0], '_fraction_within_%sd' % (days_ago))
            if fraction['time_completed'] > n_days_ago 
            else format_module_field(module[0], 
                                        '_fraction_before_%sd' % (days_ago)))

        if accessor in fractions:
            fractions[accessor] += fraction['lesson_fraction']
    return fractions


def create_fractions_dict(syllabus):
    fractions = {format_module_field(x['module'],'_fraction_within_14d') : 0 for x in syllabus.values()}
    fractions.update({format_module_field(x['module'],'_fraction_before_14d') : 0 for x in syllabus.values()})
    return fractions


def completed_percent_per_module(suffix, fractions, module_fractions):
    for module, module_fraction in module_fractions.items():
        accessor = format_module_field(module, suffix)
        if accessor in fractions and module_fraction != 0:
            fractions[accessor] = fractions[accessor] / (module_fraction + (PROJECTS[module]
                                                            if module in PROJECTS else 0.0))
    return fractions


def all_student_data(program):
    """Yield a progress metadata dictionary for each of the students

    Input is a pregenerated dictionary mapping block IDs in LMS to breadcrumbs
    """
    all_components = harvest_program(program)
    lesson_fractions = requests.get(BREADCRUMB_INDEX_URL).json()['LESSONS']
    print(lesson_fractions)
    module_fractions = {item['module'] : item['fractions']['module_fraction'] 
                            for item in lesson_fractions.values()}

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
        all_fractions = create_fractions_dict(lesson_fractions)

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
                lesson_fraction = 0
                module_fraction = 0
                cumulative_fraction = 0                

                # Check if fractions for lesson exist, if keep default 0
                if block_id in lesson_fractions:
                    lesson_fraction = lesson_fractions[block_id]['fractions']['lesson_fraction']
                    module_fraction = lesson_fractions[block_id]['fractions']['module_fraction']
                    cumulative_fraction = lesson_fractions[block_id]['fractions']['cumulative_fraction']
                

                completed_fractions[breadcrumbs] = {
                    'time_completed' : activity.modified,
                    'lesson_fraction' : lesson_fraction,
                    'module_fraction' : module_fraction,
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
            'days_into_data': days_into_data(
                first_active, completed_units.values()),
            'completed_fractions_14d' : n_days_fractions(
                completed_fractions.values(), 14),
            'cumulative_completed_fractions' : n_days_fractions(
                completed_fractions.values()),
            'fractions_per_day': fractions_per_day(
                first_active, completed_fractions.values())
        }

        completed_fractions_per_module = fractions_per_module(all_fractions, completed_fractions)
        completed_percentage_per_module = completed_percent_per_module('_fraction_within_14d', 
                                                                        completed_fractions_per_module, 
                                                                        module_fractions)
        completed_percentage_per_module = completed_percent_per_module('_fraction_before_14d', 
                                                                        completed_fractions_per_module, 
                                                                        module_fractions)

        student_dict.update(completed_percentage_per_module)
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
        student_data = [x for x, _ in zip(all_students, range(50))]

        api_endpoint = settings.STRACKR_LMS_API_ENDPOINT
        resp = requests.post(api_endpoint, data=json.dumps(student_data))
        if resp.status_code != 200:
            raise CommandError(resp.text)
