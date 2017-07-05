"""
Tests for the course home page.
"""
import ddt

from courseware.tests.factories import StaffFactory
from ccx_keys.locator import CCXLocator
from django.core.urlresolvers import reverse
from django.utils.http import urlquote_plus
from lms.djangoapps.ccx.tests.factories import CcxFactory
from openedx.core.djangoapps.waffle_utils.testutils import WAFFLE_TABLES, override_waffle_flag
from openedx.features.course_experience import SHOW_REVIEWS_TOOL_FLAG, UNIFIED_COURSE_TAB_FLAG
from student.models import CourseEnrollment
from student.tests.factories import AdminFactory, UserFactory
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import (
    TEST_DATA_SPLIT_MODULESTORE,
    SharedModuleStoreTestCase
)
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory, check_mongo_calls

from .helpers import add_course_mode
from .test_course_updates import create_course_update

TEST_PASSWORD = 'test'
TEST_CHAPTER_NAME = 'Test Chapter'
TEST_WELCOME_MESSAGE = '<h2>Welcome!</h2>'
TEST_UPDATE_MESSAGE = '<h2>Test Update!</h2>'
TEST_COURSE_UPDATES_TOOL = '/course/updates">'

QUERY_COUNT_TABLE_BLACKLIST = WAFFLE_TABLES


def course_home_url(course, course_key=None):
    """
    Returns the URL for the course's home page
    """
    return reverse(
        'openedx.course_experience.course_home',
        kwargs={
            'course_id': course_key if course_key else unicode(course.id),
        }
    )


class CourseHomePageTestCase(SharedModuleStoreTestCase):
    """
    Base class for testing the course home page.
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up a course to be used for testing.
        """
        # setUpClassAndTestData() already calls setUpClass on SharedModuleStoreTestCase
        # pylint: disable=super-method-not-called
        with super(CourseHomePageTestCase, cls).setUpClassAndTestData():
            with cls.store.default_store(ModuleStoreEnum.Type.split):
                cls.course = CourseFactory.create(org='edX', number='test', display_name='Test Course')
                with cls.store.bulk_operations(cls.course.id):
                    chapter = ItemFactory.create(
                        category='chapter',
                        parent_location=cls.course.location,
                        display_name=TEST_CHAPTER_NAME,
                    )
                    section = ItemFactory.create(category='sequential', parent_location=chapter.location)
                    section2 = ItemFactory.create(category='sequential', parent_location=chapter.location)
                    ItemFactory.create(category='vertical', parent_location=section.location)
                    ItemFactory.create(category='vertical', parent_location=section2.location)

    @classmethod
    def setUpTestData(cls):
        """Set up and enroll our fake user in the course."""
        cls.staff_user = StaffFactory(course_key=cls.course.id, password=TEST_PASSWORD)
        cls.user = UserFactory(password=TEST_PASSWORD)
        CourseEnrollment.enroll(cls.user, cls.course.id)


class TestCourseHomePage(CourseHomePageTestCase):
    def setUp(self):
        """
        Set up for the tests.
        """
        super(TestCourseHomePage, self).setUp()
        self.client.login(username=self.user.username, password=TEST_PASSWORD)

    @override_waffle_flag(UNIFIED_COURSE_TAB_FLAG, active=True)
    def test_welcome_message_when_unified(self):
        # Create a welcome message
        create_course_update(self.course, self.user, TEST_WELCOME_MESSAGE)

        url = course_home_url(self.course)
        response = self.client.get(url)
        self.assertContains(response, TEST_WELCOME_MESSAGE, status_code=200)

    @override_waffle_flag(UNIFIED_COURSE_TAB_FLAG, active=False)
    def test_welcome_message_when_not_unified(self):
        # Create a welcome message
        create_course_update(self.course, self.user, TEST_WELCOME_MESSAGE)

        url = course_home_url(self.course)
        response = self.client.get(url)
        self.assertNotContains(response, TEST_WELCOME_MESSAGE, status_code=200)

    @override_waffle_flag(UNIFIED_COURSE_TAB_FLAG, active=True)
    def test_updates_tool_visibility(self):
        """
        Verify that the updates course tool is visible only when the course
        has one or more updates.
        """
        url = course_home_url(self.course)
        response = self.client.get(url)
        self.assertNotContains(response, TEST_COURSE_UPDATES_TOOL, status_code=200)

        create_course_update(self.course, self.user, TEST_UPDATE_MESSAGE)
        url = course_home_url(self.course)
        response = self.client.get(url)
        self.assertContains(response, TEST_COURSE_UPDATES_TOOL, status_code=200)

    def test_queries(self):
        """
        Verify that the view's query count doesn't regress.
        """
        # Pre-fetch the view to populate any caches
        course_home_url(self.course)

        # Fetch the view and verify the query counts
        with self.assertNumQueries(39, table_blacklist=QUERY_COUNT_TABLE_BLACKLIST):
            with check_mongo_calls(4):
                url = course_home_url(self.course)
                self.client.get(url)


@ddt.ddt
class TestCourseHomePageAccess(CourseHomePageTestCase):
    """
    Test access to the course home page.
    """

    def setUp(self):
        super(TestCourseHomePageAccess, self).setUp()

        # Make this a verified course so that an upgrade message might be shown
        add_course_mode(self.course, upgrade_deadline_expired=False)

        # Add a welcome message
        create_course_update(self.course, self.staff_user, TEST_WELCOME_MESSAGE)

    def _create_test_user(self, user_type):
        """
        Create a test user of the specified type.

        Valid values for user type:
          anonymous - an anonymous user
          enrolled - a user enrolled in the test course
          unenrolled - a logged in user but not enrolled
          unenrolled_staff - an unenrolled staff user
        """
        is_enrolled = user_type is 'enrolled'
        is_unenrolled_staff = user_type is 'unenrolled_staff'

        # Set up the test user
        if user_type is not 'anonymous':
            if is_unenrolled_staff:
                self.user = self.staff_user
            else:
                self.user = UserFactory(password=TEST_PASSWORD)
            self.client.login(username=self.user.username, password=TEST_PASSWORD)
            if is_enrolled:
                CourseEnrollment.enroll(self.user, self.course.id)

    @override_waffle_flag(UNIFIED_COURSE_TAB_FLAG, active=True)
    @override_waffle_flag(SHOW_REVIEWS_TOOL_FLAG, active=True)
    @ddt.data(
        'anonymous',
        'enrolled',
        'unenrolled',
        'unenrolled_staff',
    )
    def test_home_page(self, user_type):
        self._create_test_user(user_type)

        # Render the course home page
        url = course_home_url(self.course)
        response = self.client.get(url)

        # Verify that the course tools and dates are always shown
        self.assertContains(response, 'Course Tools')
        self.assertContains(response, 'Today is')

        # Verify that the outline, start button, course sock, and welcome message
        # are only shown to enrolled users.
        is_enrolled = user_type is 'enrolled'
        is_unenrolled_staff = user_type is 'unenrolled_staff'
        expected_count = 1 if (is_enrolled or is_unenrolled_staff) else 0
        self.assertContains(response, TEST_CHAPTER_NAME, count=expected_count)
        self.assertContains(response, 'Start Course', count=expected_count)
        self.assertContains(response, 'Learn About Verified Certificate', count=expected_count)
        self.assertContains(response, TEST_WELCOME_MESSAGE, count=expected_count)


    @override_waffle_flag(UNIFIED_COURSE_TAB_FLAG, active=False)
    @override_waffle_flag(SHOW_REVIEWS_TOOL_FLAG, active=True)
    @ddt.data(
        'anonymous',
        'enrolled',
        'unenrolled',
        'unenrolled_staff',
    )
    def test_home_page_not_unified(self, user_type):
        """
        Verifies the course home tab when not unified.
        """
        self._create_test_user(user_type)

        # Render the course home page
        url = course_home_url(self.course)
        response = self.client.get(url)

        # Verify that the course tools and dates are always shown
        self.assertContains(response, 'Course Tools')
        self.assertContains(response, 'Today is')

        # Verify that welcome messages are never shown
        self.assertNotContains(response, TEST_WELCOME_MESSAGE)

        # Verify that the outline, start button, course sock, and welcome message
        # are only shown to enrolled users.
        is_enrolled = user_type is 'enrolled'
        is_unenrolled_staff = user_type is 'unenrolled_staff'
        expected_count = 1 if (is_enrolled or is_unenrolled_staff) else 0
        self.assertContains(response, TEST_CHAPTER_NAME, count=expected_count)
        self.assertContains(response, 'Start Course', count=expected_count)
        self.assertContains(response, 'Learn About Verified Certificate', count=expected_count)

    def test_sign_in_button(self):
        """
        Verify that the sign in button will return to this page.
        """
        url = course_home_url(self.course)
        response = self.client.get(url)
        self.assertContains(response, '/login?next={url}'.format(url=urlquote_plus(url)))


class TestCcxCourseHomePage(CourseHomePageTestCase):
    """
    Test for unenrolled student tries to access ccx.
    Note: Only CCX coach can enroll a student in CCX. In sum self-registration not allowed.
    """
    MODULESTORE = TEST_DATA_SPLIT_MODULESTORE

    @classmethod
    def setUpClass(cls):
        super(TestCcxCourseHomePage, cls).setUpClass()
        cls.course = CourseFactory.create()

    def setUp(self):
        super(TestCcxCourseHomePage, self).setUp()

        # Create a CCX coach account
        self.coach = coach = AdminFactory.create(password="test")
        self.client.login(username=coach.username, password="test")

    @override_waffle_flag(UNIFIED_COURSE_TAB_FLAG, active=True)
    def test_ccx_redirect(self):
        """
        Verify that an unenrolled user cannot hit the course home page
        but is instead redirected to the dashboard.
        """

        # Create a CCX course
        ccx_course = CcxFactory(course_id=self.course.id, coach=self.coach)
        ccx_locator = CCXLocator.from_course_locator(self.course.id, unicode(ccx_course.id))

        # Log in a test user
        user = UserFactory(password=TEST_PASSWORD)
        self.client.login(username=user.username, password=TEST_PASSWORD)

        # Request the course home page
        url = course_home_url(ccx_course, course_key=ccx_locator)
        response = self.client.get(url)

        # Verify that it returns a redirect to the dashboard
        expected_redirect_url = reverse('dashboard')
        self.assertRedirects(response, expected_redirect_url, status_code=302, target_status_code=200)
