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

CONNECTION_STRING = 'mysql+mysqldb://%s:%s@%s:%d/%s%s' % (
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

    output_dict[block_id] = block_breadcrumbs

    children = tree.get_children()
    #if len(children) > 0:
    #    harvest_course_tree(children.pop(), output_dict, prefix=block_breadcrumbs)
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

def get_breadcrumb_index(URL):
    """Retrieve the course syllabus from Google Sheet with the ordering

    Returns a Dataframe to join to the rest of the breadcumbs
    """
    breadcrumb_index = requests.get(URL).json()
    df_breadcrumb_idx = pd.DataFrame(breadcrumb_index['lessons'])
    df_breadcrumb_idx = df_breadcrumb_idx.T
    df_breadcrumb_idx = df_breadcrumb_idx.reset_index()
    df_breadcrumb_idx.rename(columns={'index':'order_index'}, inplace=True)
    # Temporary until this is being renamed in the LMS
    df_breadcrumb_idx['module'] = df_breadcrumb_idx['module'].replace('Careers','Careers [Beta]')
    df_breadcrumb_idx = df_breadcrumb_idx.reset_index()
    return df_breadcrumb_idx[['module','lesson','order_index']]


class Command(BaseCommand):
    help = 'Extract student data from the open-edX server for use in Strackr'

    def handle(self, *args, **options):

        program = get_program_by_program_code(PROGRAM_CODE)
        all_components = harvest_program(program)
        
        # Looping through the results because you cannot convert 
        # Variable length dict list to DataFrame, but list of lists
        components = []
        for k,v in all_components.iteritems():
            temp = []
            temp.append(k)
            for item in v:
                temp.append(item)
            components.append(temp)

        df = pd.DataFrame(components)
        # Need to assign headers
        df.columns = ['uuid','module','section','lesson','unit','type','unknown_col']
        
        # Need to get lesson order from syllabus for ordering the modules
        # And not going back
        df_breadcrumb_idx = get_breadcrumb_index(BREADCRUMB_INDEX_URL)
        df = df.merge(df_breadcrumb_idx, on=['module', 'lesson'], how='left')
        
        engine = create_engine(CONNECTION_STRING, echo=False)
        df.to_sql(name='lms_breadcrumbs_v2', con=engine, if_exists='replace',
                    dtype={'uuid': types.VARCHAR(length=255),
                            'order_index': types.INT
                    })

