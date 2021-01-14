from datetime import datetime, timedelta
import pymongo
import requests
import json

from ci_program.api import get_program_by_program_code

HOST = "127.0.0.1"
PORT = "27017"

HUBSPOT_CONTACTS_ENDPOINT = settings.HUBSPOT_CONTACTS_ENDPOINT

# key is challenge name in sandbox, value is field in HubSpot
# appended OLD as agreed with Programme/Mktg to make the names consistent
CODING_CHALLENGES_OLD = {
    "1_Day_1_Challenge_1": "lesson_1_challenge_1",
    "2_Day_1_Challenge_2": "lesson_1_challenge_1",   
    "3_Day_2_Challenge_1": "lesson_2_challenge_1",
    "4_Day_2_Challenge_2": "lesson_2_challenge_2",
    "5_Day_2_Challenge_3": "lesson_2_challenge_3",
    "6_Day_2_Challenge_4": "lesson_2_challenge_4",
    "7_Day_3_Challenge_1": "lesson_3_challenge_1",
    "8_Day_3_Challenge_2": "lesson_3_challenge_2",
    "9_Day_3_Challenge_3": "lesson_3_challenge_3",
    "10_Day_4_Challenge_1": "lesson_4_challenge_1",
    "11_Day_4_Challenge_2": "lesson_4_challenge_2",
    "12_Day_4_Challenge_3": "lesson_4_challenge_3",
    "13_Day_5_Challenge_1": "lesson_5_challenge_1",
    "14_Day_5_Challenge_2": "lesson_5_challenge_2",
    "15_Lesson_5_Challenge_3": "lesson_5_challenge_3"
}

# Agreed list of names for coding challenges, will replace CODING_CHALLENGES_OLD
# Can remove this dict when we associate challenges with programme
CODING_CHALLENGES = {
    "lesson_1_challenge_1"
    "lesson_1_challenge_1"
    "lesson_2_challenge_1"
    "lesson_2_challenge_2"
    "lesson_2_challenge_3"
    "lesson_2_challenge_4"
    "lesson_3_challenge_1"
    "lesson_3_challenge_2"
    "lesson_3_challenge_3"
    "lesson_4_challenge_1"
    "lesson_4_challenge_2"
    "lesson_4_challenge_3"
    "lesson_5_challenge_1"
    "lesson_5_challenge_2"
    "lesson_5_challenge_3"
}

def connect_to_mongo():
    mongo_client = pymongo.MongoClient(HOST, int(PORT))
    return mongo_client["challenges"]

def get_challenges(db):
    challenges_query = db.challenges.find({"name": {"$in": CODING_CHALLENGES_OLD.keys()}})
    challenges = {challenge.get("_id"):challenge.get("name") for challenge in challenges_query}
    return challenges

def get_students(program_code):
    program = get_program_by_program_code(program_code)
    enrolled_students = program.enrolled_students.all()
    return {student.id: student.email for student in enrolled_students}

def get_submissions(db, challenges, students, submitted_since):
    submissions_since_yday = db.submissions.find({
        "submitted": {"$gte": submitted_since},
        "challenge_id": {"$in": challenges.keys()},
        "user_id": {"$in": students.keys()}
        }).sort("submitted",pymongo.DESCENDING)
    return submissions_since_yday    

def get_results_for_all_students(program_code):
    # Get all students enrolled in program
    students = get_students(program_code)

    db = connect_to_mongo()
    # Get ids for all challenges in coding challenge program
    challenges = get_challenges(db)

    # Get all submissions for coding challenges, submitted by an enrolled student in the last 25 hours
    # Allowing an additional hour to account for any submissions that occur while script is running
    # Submissions are sorted by submission date, latest submission first
    one_day_ago = datetime.today() - timedelta(days=1)
    submissions_since_yday = get_submissions(db, challenges, students, one_day_ago)
    
    results = {}
    for submission in submissions_since_yday:
        email = students[submission.get("user_id")]
        if email not in results:
            results[email] = {}
        
        challenge = challenges[submission.get("challenge_id")]
        result = 'Pass' if submission.get("passed") else 'Fail'

        # We only require the result of the latest submission of a particular challenge
        # i.e. first submission found in results (which is sorted by latest submission first)
        # Previous submissions are skipped
        if challenge not in results[email]:
            results[email][challenge] = result

    return results

def post_to_hubspot(endpoint, student, properties):
    url = "%s/email/%s/profile?hapikey=%s" % (
        endpoint, student, HUBSPOT_CONTACTS_ENDPOINT)
    headers = {
        "Content-Type": "application/json"
    }
    data=json.dumps({
    "properties": properties
    })
    response = requests.post(
        data=data, url=url, headers=headers)
    if response.status_code != 200:
        print(response.json)
    print("Challenge results recorded for: %s" % (student))

def export_challenges_submitted(program_code):
    results_for_all_students = get_results_for_all_students(program_code)
    for student, results in results_for_all_students.items():
        # Create list of properties (i.e. fields) to be updated in HubSpot profile
        properties = [{
            "property": "email",
            "value": student
        }]
        for challenge_name, result in results.items():
            properties.append({
                "property": CODING_CHALLENGES_OLD[challenge_name],
                "value": result
            })
        post_to_hubspot(HUBSPOT_CONTACTS_ENDPOINT, student, properties)

class Command(BaseCommand):
    help = 'Post the results of challenge submissions submitted in the last 24 hours for a given coding challenge program'

    def add_arguments(self, parser):
        parser.add_argument('program_code', type=str)

    def handle(self, program_code):
        export_challenges_submitted(program_code)