from datetime import datetime, timedelta
import pymongo

from ci_program.api import get_program_by_program_code

HOST = "127.0.0.1"
PORT = "27017"

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

# Agreed list of names for coding challenges
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

def get_results(program_code):
    students = get_students(program_code)
    one_day_ago = datetime.today() - timedelta(days=1)

    db = connect_to_mongo()
    challenges = get_challenges(db)
    submissions_since_yday = get_submissions(db, challenges, students, one_day_ago)
    
    results = {}

    for submission in submissions_since_yday:
        email = students[submission.get("user_id")]
        if email not in results:
            results[email] = {}
        
        challenge = challenges[submission.get("challenge_id")]
        result = 'Pass' if submission.get("passed") else 'Fail'
        if challenge not in results[email]:
            results[email][challenge] = result

    return results

get_results("CODEITFDCC")
