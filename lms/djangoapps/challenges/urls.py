from rest_framework import routers

from challenges.views import ChallengeSubmissionViewset

router = routers.DefaultRouter()
router.register(r'', ChallengeSubmissionViewset, 'api')

print(router.urls)