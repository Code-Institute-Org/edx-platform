from ci_program.api import get_program_by_program_code
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from opaque_keys.edx.locator import CourseLocator
from xmodule.modulestore.django import modulestore
import pandas as pd
from sqlalchemy import create_engine, types

from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json

import requests

# Need to create an engine using sqlalchemy to be able to
# connect with pandas .to_sql
# Pandas natively only supports sqlite3
# '?charset=utf8' used to specify utf-8 encoding to avoid encoding errors

LMS_TABLE = 'lms_breadcrumbs_v3'

CONNECTION_STRING = 'mysql+mysqldb://%s:%s@%s:%s/%s%s' % (
    settings.RDS_DB_USER,
    settings.RDS_DB_PASS,
    settings.RDS_DB_ENDPOINT,
    settings.RDS_DB_PORT,
    settings.RDS_LMS_DB,
    '?charset=utf8')

BREADCRUMB_INDEX_URL = settings.LMS_SYLLABUS

PROGRAM_CODE = 'FS'  # Our Full-Stack program

def harvest_course_tree(tree, output_dict, prefix=()):
    """Recursively harvest the breadcrumbs for each component in a tree

    Populates output_dict
    """
    block_name = tree.display_name
    block_breadcrumbs = prefix + (tree.display_name,)
    block_id = tree.location.block_id
    category = (tree.category,)
    output_dict[block_id] = block_breadcrumbs + category

    children = tree.get_children()
    for subtree in children:
        harvest_course_tree(subtree, output_dict, prefix=block_breadcrumbs)

def harvest_course_tree_new(tree, output_list, prefix=()):
    """Recursively harvest the breadcrumbs for each component in a tree

    Populates output_dict
    """
    block_name = tree.display_name
    block_category = tree.category
    block_breadcrumbs = prefix + (tree.display_name,)
    block_id = tree.location.block_id
    module = None
    section = None
    lesson = None
    unit = None

    breadcrumbs = block_breadcrumbs

    if block_category == 'course':
        block_type = 'module'
        module = block_name
    elif block_category == 'chapter':
        block_type = 'section'
        module = breadcrumbs[0]
        section = block_name
    elif block_category == 'sequential':
        print(breadcrumbs)
        block_type = 'lesson'
        module = breadcrumbs[0]
        section = breadcrumbs[1]
        lesson = block_name
    elif block_category == 'vertical':
        block_type = 'unit'
        module = breadcrumbs[0]
        section = breadcrumbs[1]
        lesson = breadcrumbs[2]
        unit = block_name
    else:
        block_type = 'component'
        module = breadcrumbs[0]
        section = breadcrumbs[1]
        lesson = breadcrumbs[2]
        unit = breadcrumbs[3]
    
    temp_dict = {}
    temp_dict['block_id'] = block_id
    temp_dict['block_name'] = block_name
    temp_dict['block_type'] = block_type
    temp_dict['module'] = module
    temp_dict['section'] = section
    temp_dict['lesson'] = lesson
    temp_dict['unit'] = unit
    temp_dict['breadcrumbs'] = ' - '.join(block_breadcrumbs)

    output_list.append(temp_dict)

    children = tree.get_children()
    for subtree in children:
        harvest_course_tree_new(subtree, output_list, prefix=block_breadcrumbs)
    

def harvest_program(program):
    """Harvest the breadcrumbs from all components in the program

    Returns a dictionary mapping block IDs to the matching breadcrumbs
    """
    all_blocks = []
    for course_locator in program.get_course_locators():
        course = modulestore().get_course(course_locator)
        harvest_course_tree_new(course, all_blocks)
    return all_blocks

def get_breadcrumb_index(URL):
    """Retrieve the course syllabus from Google Sheet with the ordering

    Returns a Dataframe to join to the rest of the breadcumbs
    """
    breadcrumb_index = requests.get(URL).json()
    df_breadcrumb_idx = pd.DataFrame(breadcrumb_index['LESSONS'])
    df_breadcrumb_idx = df_breadcrumb_idx.T
    df_breadcrumb_idx = df_breadcrumb_idx.reset_index()
    df_breadcrumb_idx.rename(columns={'index':'order_index'}, inplace=True)
    # TODO: remove following line, once the [beta] suffix is removed in the LMS
    df_breadcrumb_idx['module'] = df_breadcrumb_idx['module'].replace('Careers','Careers [Beta]')
    df_breadcrumb_idx = df_breadcrumb_idx.reset_index()
    return df_breadcrumb_idx[['module','lesson','order_index','time_fraction']]


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'

    def handle(self, *args, **options):

        program = get_program_by_program_code(PROGRAM_CODE)
        all_components = harvest_program(program)        
        df = pd.DataFrame(all_components)
        
        # Need to get lesson order from syllabus for ordering the modules
        # And course fractions
        df_breadcrumb_idx = get_breadcrumb_index(BREADCRUMB_INDEX_URL)
        df = df.merge(df_breadcrumb_idx, on=['module', 'lesson'], how='left')
        
        engine = create_engine(CONNECTION_STRING, echo=False)
        df.to_sql(name='lms_breadcrumbs_v3', con=engine, if_exists='replace', dtype={'order_index': types.INT})
