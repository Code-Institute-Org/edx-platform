import sys, time
from datetime import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import pandas as pd
import numpy as np
import sqlalchemy
from sqlalchemy import create_engine

# Need to create an engine using sqlalchemy to be able to
# connect with pandas .to_sql and .read_sql_query
# Pandas natively only supports sqlite3
RDS_CONNECTION_STRING = 'mysql+mysqldb://%s:%s@%s:%s/%s' % (
    settings.RDS_DB_USER,
    settings.RDS_DB_PASS,
    settings.RDS_DB_ENDPOINT,
    settings.RDS_DB_PORT,
    settings.RDS_LMS_DB)

MYSQL_CONNECTION_STRING = 'mysql+mysqldb://%s:%s@%s:%s/%s' % (
    settings.MYSQL_USER,
    settings.MYSQL_PASS,
    settings.MYSQL_HOST,
    settings.MYSQL_PORT,
    settings.MYSQL_DB)

SELECTED_COLUMNS = [
            'student_id',
            'student_email',
            'date_joined',
            'last_login',
            'first_activity',
            'latest_unit_completion',
            'latest_module',
            'latest_section',
            'latest_lesson',
            'latest_unit'
            ]
SELECTED_COLUMNS_DAYS = [
    'student_id',
    'module',
    'section',
    'lesson',
    'unit',
    'modified',
    'created',
    'days_into',
    'block_type',
    'days_into_units',
    'time_fraction'
]

ACTIVITIES_QUERY = """
SELECT 
    COALESCE(a.student_id, b.id) AS student_id, 
    b.email as student_email, 
    b.date_joined,
    b.last_login,
    a.module_id, 
    a.course_id, 
    a.module_type, 
    a.created, 
    a.modified 
FROM 
    courseware_studentmodule AS a
RIGHT OUTER JOIN 
    auth_user AS b
ON 
    a.student_id = b.id
WHERE 
    b.is_active = TRUE;
"""

ENROLLED_STUDENTS_QUERY = """
SELECT 
    user_end.id AS student_id
FROM 
    ci_program_program_enrolled_students s_p_junction
LEFT JOIN 
    ci_program_program program_end
ON 
    s_p_junction.program_id = program_end.id
LEFT JOIN 
    auth_user user_end
ON 
    s_p_junction.user_id = user_end.id
WHERE 
    user_end.is_active = 1
AND 
    program_end.program_code = "FS"
ORDER BY 
    user_end.id DESC;
"""

BREADCRUMBS_QUERY = 'SELECT * FROM lms_breadcrumbs_v3;'

def extract_activities(mysql_engine):
    """
    Queries the LMS MySQL database for all student module activity and pre-processes some data points
    Returns a DataFrame
    """
    start = time.time()
    df = pd.read_sql_query(ACTIVITIES_QUERY, con=mysql_engine)
    df['breadcrumb'] = df['module_id'].str.rsplit('@', n=None, expand=True)[2]
    df['breadcrumb_type'] = df['module_id'].str.extract(r'@(.*)[+]block')
    print('Execution time (in sec): %s' % (str(time.time() - start)))
    return df

def extract_enrolled_students(mysql_engine):
    """
    Queries the LMS MySQL database for all students enrolled in the FS course
    Returns a DataFrame
    """
    start = time.time()
    # Extracting all students who are in FS only
    # Using pandas instead of mysql because of server timeout
    df = pd.read_sql_query(ENROLLED_STUDENTS_QUERY, con=mysql_engine)
    print('Execution time (in sec): %s' % (str(time.time() - start)))
    return df

def remove_other_programs(df_lms, df_students):
    """
    Merges all student module activity with all enrolled students and removes any outliers
    Returns a DataFrame    
    """
    # Merging to then remove the non-overlapping student_emails
    start = time.time()
    print('Rows before: ' + str(df_lms.shape[0]))
    df = df_lms.merge(df_students.drop_duplicates(), on=['student_id'], how='left', indicator=True)
    print('Rows after: ' + str(df.shape[0]))
    print('Execution time (in sec): %s' % (str(time.time() - start)))
    return df.loc[df['_merge'] == 'both']

def get_breadcrumbs(rds_engine):
    """
    Queries the RDS database for the Breadcrumbs
    Returns a DataFrame
    """
    return pd.read_sql_query(BREADCRUMBS_QUERY, con=rds_engine)

def merge_lms_breadcumbs(df_lms, df_breadcrumbs):
    """
    Merges all student module activity with the breadcrumbs
    Returns a DataFrame
    """
    df_breadcrumbs.rename(columns={'block_id':'breadcrumb'}, inplace=True)
    return df_lms.merge(df_breadcrumbs, on=['breadcrumb'], how='left')

def get_first_activity(df):
    """ 
    Calculates first ever activity for all students
    Returns updated DataFrame
    """
    df_first = df.groupby(['student_email']).agg({'created': [np.min]})
    df_first.columns = df_first.columns.get_level_values(1)
    df_first = df_first.reset_index()
    df_first.rename(columns={'amin':'first_activity'}, inplace=True)
    return df.merge(df_first, on=['student_email'], how='left')

def get_latest_row(df, columns):
    """
    Calculates the latest row for each student
    Ordering based on columns parameter
    Returns a DataFrame with a row per each student
    """
    ordering = [False for col in range(len(columns))]
    df = df.sort_values(columns, ascending=ordering).drop_duplicates(['student_id'])
    df = df.add_prefix('latest_')
    df.rename(columns={'latest_student_id':'student_id'}, inplace=True)
    return df

def get_latest_activity(df):
    """ 
    Calculates latest_unit_completion and latest_module/section/lesson/unit for each student
    Returns updated DataFrame
    """
    # 1) Need to get row number for the latest created time (last module completion) 
    #    based on the order in the course material and created time
    # 2) Join to the original DataFrame (DF)
    # 3) Then we want to do the same, but for the modified date to get the most recently
    #    modified module, section, lesson and unit
    # 4) Then we want to join that one row back to the DF to join all the dimensions
    # 5) Merge all of the DFs
    df_all = df.loc[df['block_type'] == 'component',:]
    df_latest_date = get_latest_row(df_all.loc[:,('student_id', 'created','order_index')],['created','order_index']) 
    df_latest_unit = get_latest_row(df_all.loc[:,('student_id', 'modified','module','section','lesson','unit')],['modified'])
    
    df = df.merge(df_latest_date, on=['student_id'], how='left')
    df = df.merge(df_latest_unit, on=['student_id'], how='left')                        
    df.rename(columns={'latest_created':'latest_unit_completion'}, inplace=True)
    return df

def get_latest_modified_lesson(df):
    """
    Calculates the latest modified time for each LESSON for each student
    Returns an updated DataFrame
    """
    values = {'module':'', 'section':'', 'lesson':'', 'unit':''}
    df = df.fillna(value=values)
    df_module_latest = df.groupby(by=['student_id','module','section','lesson']).agg({'modified': [np.max]})
    df_module_latest.columns = df_module_latest.columns.get_level_values(1)
    df_module_latest = df_module_latest.reset_index()
    df_module_latest.rename(columns={'amin':'latest_lesson_modified','amax':'latest_lesson_modified'}, inplace=True)
    return df.merge(df_module_latest, on=['student_id','module','section','lesson'], how='left')

def get_latest_modified_unit(df):
    """
    Calculates the latest modified time for each UNIT for each student
    Returns an updated DataFrame
    """
    df_module_latest = df.groupby(by=['student_id','module','section','lesson','unit']).agg({'modified': [np.max]})
    df_module_latest.columns = df_module_latest.columns.get_level_values(1)
    df_module_latest = df_module_latest.reset_index()
    df_module_latest.rename(columns={'amin':'latest_unit_modified','amax':'latest_unit_modified'}, inplace=True)
    return df.merge(df_module_latest, on=['student_id','module','section','lesson','unit'], how='left')

def get_days_into(df):
    """
    Calculates days_into for lesson and unit in each row
    Returns updated DataFrame with added columns
    """
    df['days_into'] = (pd.to_datetime(df['latest_lesson_modified']) - pd.to_datetime(df['first_activity'])).dt.days
    df['days_into_units'] = (pd.to_datetime(df['latest_unit_modified']) - pd.to_datetime(df['first_activity'])).dt.days
    return df

def calculate_extra_columns(df):
    """
    Runs all functions to calculate first activity, latest activity, lesson/unit modified times and days into
    Returns updated DataFrame
    """
    df = get_first_activity(df)
    df = get_latest_activity(df)
    df = get_latest_modified_lesson(df)
    df = get_latest_modified_unit(df)
    df = get_days_into(df)
    return df

def columns_to_lower(df):
    """
    Changes DataFrame column headers to lowercase and replaces spaces with underscores
    Returns updated DataFrame
    """
    df.columns = map(str.lower, df.columns)
    df.columns = df.columns.str.replace(' ', '_')
    return df

def get_all_completed(df):
    lessons = get_completed(df, ['student_id','module','lesson'])
    units = get_completed(df, ['student_id','module','unit'])

    #df_last_thirty = df[dt.now() - pd.to_datetime(df['modified']) < pd.Timedelta(31,'D')]
    # For testing with old data
    df_last_thirty = df[dt.now() - pd.to_datetime(df['modified']) < pd.Timedelta(31,'D')]
    last_thirty = get_completed_last_thirty(df_last_thirty, ['student_id','unit'])
    df_last_fourteen = df[dt.now() - pd.to_datetime(df['modified']) < pd.Timedelta(15,'D')]
    # For testing with old data
    #df_last_fourteen = df[dt.now() - pd.to_datetime(df['modified']) < pd.Timedelta(55,'D')]
    last_fourteen_weighted = get_completed_last_fourteen(df_last_fourteen, ['student_id','lesson','time_fraction'])

    df = lessons.merge(units, on='student_id', how='left')
    df = df.merge(last_thirty, on='student_id', how='left')
    return df.merge(last_fourteen_weighted, on='student_id', how='left')

def get_completed(df, cols):
    df = df[cols]
    df = df.groupby(by=[cols[0],cols[1]])[cols[2]].nunique()
    df = df.reset_index()
    df = df.pivot_table(index=cols[0], columns=cols[1], values=cols[2], fill_value=0)
    df.columns = [str(col) + '_' + cols[2] + 's' for col in columns_to_lower(df).columns]
    return df.reset_index()

def get_completed_last_thirty(df, cols):
    df = df[cols]
    df = df.loc[df[cols[1]].isnull() == False]
    df = df.groupby(by=[cols[0]])[cols[1]].nunique()
    df = df.reset_index()
    df.rename(columns={cols[1] : cols[1] + 's_in_30d'}, inplace=True)
    return df.fillna(0)

def get_completed_last_fourteen(df, cols):
    df = df[cols]
    df = df.loc[df[cols[1]].isnull() == False]
    df = df.fillna(0)
    df = df.groupby(by=[cols[0], cols[1]]).agg({'time_fraction': [np.max]})
    df.columns = df.columns.get_level_values(1)
    df = df.reset_index()
    df['amax'] = df['amax'].astype(float)
    df = df.fillna(0)
    df = df.groupby(by=[cols[0]]).agg({'amax': [np.sum]})
    df.columns = df.columns.get_level_values(1)
    df = df.reset_index()
    df.rename(columns={'sum' : 'completed_in_14d'}, inplace=True)
    return df

def aggregate_lesson_days_into(df):
    df = df.loc[(df['block_type'] == 'lesson'),:]
    cols = ['student_id','module','lesson']
    print(cols)
    #df.fillna({'order_index':'0', 'unit':'1', 'section':'2'})
    #df.to_csv('aaron_records_v4.csv', index=False)
    df = df.groupby(by=cols).agg({'days_into': [np.max]})

    df.columns = df.columns.get_level_values(1)
    df = df.reset_index()
    df.rename(columns={'amin':'days_into','amax':'days_into'}, inplace=True)  
    
    df.sort_values(['days_into'] + cols, ascending=[True, True, True, True], inplace=True)
    df['days_into'] = df['days_into'].astype(int)
    df = df.groupby(cols[0:2]).apply(lambda x: ','.join(x.astype(str).days_into))
    df = df.to_frame()
    
    df.rename(columns={df.columns[0] : 'days_into'}, inplace=True)
    df = df.reset_index()
    
    df = df.pivot(index='student_id', columns='module', values='days_into')
    df.columns = [str(col) + '_days_into' for col in columns_to_lower(df).columns]
    return df.reset_index()

def aggregate_days_into(df):
    df = df.loc[(df['block_type'] == 'component'),:]
    cols = ['student_id','lesson_unit']
    df = df.groupby(by=cols).agg({'days_into_units': [np.max]})

    df.columns = df.columns.get_level_values(1)
    df = df.reset_index()
    df.rename(columns={'amin':'days_into','amax':'days_into'}, inplace=True)  
    df.sort_values(['days_into'] + cols, ascending=[True, True, True], inplace=True)
    df['days_into'] = df['days_into'].astype(int)
    df = df.groupby(cols[0]).apply(lambda x: ','.join(x.astype(str).days_into))
    #df.columns = [str(col) + '_days_into' for col in columns_to_lower(df).columns]
    df.reset_index()
    df = df.to_frame()
    df.rename(columns={df.columns[0] : 'days_into'}, inplace=True)
    return df

class Command(BaseCommand):
    help = 'Extract student data from the open-edX server 7for use in Strackr'

    def handle(self, *args, **options):
        try:
            total_start = time.time()
            mysql_engine = create_engine(MYSQL_CONNECTION_STRING, echo=False)
            
            df_lms = extract_activities(mysql_engine)
            df_students = extract_enrolled_students(mysql_engine)
            df_all = remove_other_programs(df_lms, df_students)
            rds_engine = create_engine(RDS_CONNECTION_STRING, echo=False, 
                                        max_overflow=0, pool_size=100, pool_pre_ping=True, 
                                        pool_recycle=3600)

            df_breadcrumbs = get_breadcrumbs(rds_engine)
            df_merged = merge_lms_breadcumbs(df_all, df_breadcrumbs)
            df = calculate_extra_columns(df_merged)

            ## Select only wanted columns
            df_latest = df.loc[:, SELECTED_COLUMNS]
            df_latest.drop_duplicates(inplace=True)
            df_latest.to_sql(name='lms_students_test', con=rds_engine, 
                                if_exists='replace',index_label='id')

            ## Only select relevant columns
            df = df.loc[:,SELECTED_COLUMNS_DAYS]

            df_lessons_days_into = aggregate_lesson_days_into(df)
            df_units = df
            df_units['lesson_unit'] = df_units['lesson'] + df_units['unit']
            df_units_days_into = aggregate_days_into(df_units)
            df_completed = get_all_completed(df)
            df_days = df_units_days_into.merge(df_lessons_days_into, on='student_id', how='left')
            df_days_all = df_latest.merge(df_days, on='student_id', how='left')
            df = df_days_all.merge(df_completed, on='student_id', how='left')

            count = 0
            # Reset Timer
            start = time.time()
            while count < df.shape[0]:
                temp = df.loc[count:df.shape[0]] if (count + 10000) > df.shape[0] else df.loc[count:(count + 10000)]
                # temp['breadcrumb'] = temp['module_id'].str.rsplit('@', n=None, expand=True)[2]
                insert_type = 'replace' if count == 0 else 'append'
                temp.to_sql(name='lms_activity', con=rds_engine, if_exists=insert_type,
                            #dtype={'student_email': sqlalchemy.types.VARCHAR(length=255)},
                            index_label='id')
                print(str(count) + ' done.')
                count += 10000
            print('Execution time (in sec): %s' % (str(time.time() - start)))
            print('Total Execution time (in sec): %s' % (str(time.time() - total_start)))
        except KeyboardInterrupt:
            sys.exit(1)
