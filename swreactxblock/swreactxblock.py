"""
StepWise xblock questions can contain up to 10 variants.  The xblock remembers which variants the student has attempted and if the student
requests a new variant, we will try to assign one that has not yet been attempted. Once the student has attempted all available variants,
if they request another variant, we will clear the list of attempted variants and start assigning variants over again.

We count question attempts made by the student.  We don't consider an attempt to have begun until the student submits their first step
in the attempt, or requests a hint, or requests to see the worked-out solution ('ShowMe').
We use a callback from the StepWise UI client code to know that the student has begun their attempt.

An attempt isn't counted until the student submits their first step since the student can visit the question, then leave the question
without doing any work, and come back later.  We don't want to wait until after the student submits their final answer to count the attempt
to prevent the student from (1) visiting the problem, (2) clicking show solution, (3) writing down the steps, and (4) reloading the browser
web page.  In this scenario the student has seen the steps to the solution, but is not charged for an attempt.

When the student completes work on the StepWise problem ('victory'), we use a callback from the StepWise UI client code to record
the student's score on that attempt.

The Javascript code in this xblock displays the score and steps on the student's most recent attempt (only).

Note that the xblock Python code's logic for computing the score is somewhat duplicated in the xblock's Javascript code since the Javascript is
responsible for updating the information displayed to the student on their results, and the Python code does not currently provide
this detailed scoring data down to the Javascript code.  It may be possible for the results of the scoring callback POST to return
the scoring details to the Javascript code for display, but this is not currently done.  Thus, if you need to update the scoring logic
here in Python, you need to check the Javascript source in js/src/swreactxstudent.js to make sure you don't also have to change the score display
logic there.
"""

# Python stuff
import pkg_resources
import random
import json
from logging import getLogger
import urllib.parse
import requests

# Django Stuff
from django.conf import settings

# Open edX stuff
from xblock.core import XBlock
from xblock.fields import Integer, String, Scope, Dict, Float, Boolean
from web_fragments.fragment import Fragment
# McDaniel apr-2019: this is deprecated.
#from xblock.fragment import Fragment
from xblock.scorable import ScorableXBlockMixin, Score
from xblockutils.studio_editable import StudioEditableXBlockMixin
from lms.djangoapps.courseware.courses import get_course_by_id
from xblock.mixins import ScopedStorageMixin


UNSET = object()

logger = getLogger(__name__)

#DEBUG=settings.ROVER_DEBUG
DEBUG=False

"""
The general idea is that we'll determine which question parameters to pass to the StepWise client before invoking it,
making use of course-wide StepWise defaults if set.
If the student has exceeded the max mumber of attempts (course-wide setting or per-question setting), we won't let them
start another attempt.
We'll then get two call-backs:
1. When the student begins work on the question (e.g. submits a first step, clicks 'Hint', or clicks 'Show Solution',
the callback code here will increment the attempts counter.
2. When the student completes the problem ('victory'), we'll compute their grade and save their grade for this attempt.
Note that the student can start an attempt, but never finish (abandoned attempt), but we will still want to count that attempt.
"""

@XBlock.wants('user')
class SWREACTXBlock(StudioEditableXBlockMixin, ScorableXBlockMixin, XBlock):
    """
    This xblock provides up to 10 variants of a question for delivery using the StepWise UI.
    """

    has_author_view = True # tells the xblock to not ignore the AuthorView
    has_score = True       # tells the xblock to not ignore the grade event
    show_in_read_only_mode = True # tells the xblock to let the instructor view the student's work (lms/djangoapps/courseware/masquerade.py)

    MAX_VARIANTS = 10	   # This code handles 10 or fewer variants

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    # Place to store the UUID for this xblock instance.  Not currently displayed in any view.
    url_name = String(display_name="URL name", default='NONE', scope=Scope.content)

    # PER-QUESTION GRADING OPTIONS (SEPARATE SET FOR COURSE DEFAULTS)
    q_weight = Float(
        display_name="Problem Weight",
        help="Defines the number of points the problem is worth.",
        scope=Scope.content,
        default=1.0,
        enforce_type=True
    )

    q_grade_showme_ded = Float(display_name="Point deduction for using Show Solution",help="Raw points deducted from 3.0 (Default: 3.0)", default=3.0, scope=Scope.content)
    q_grade_hints_count = Integer(help="Number of Hints before deduction", default=2, scope=Scope.content)
    q_grade_hints_ded = Float(help="Point deduction for using excessive Hints", default=1.0, scope=Scope.content)
    q_grade_errors_count = Integer(help="Number of Errors before deduction", default=2, scope=Scope.content)
    q_grade_errors_ded = Float(help="Point deduction for excessive Errors", default=1.0, scope=Scope.content)
    q_grade_min_steps_count = Integer(help="Minimum valid steps in solution for full credit", default=3, scope=Scope.content)
    q_grade_min_steps_ded = Float(help="Point deduction for fewer than minimum valid steps", default=0.25, scope=Scope.content)

    # PER-QUESTION HINTS/SHOW SOLUTION OPTIONS
    q_option_hint = Boolean(help='Display Hint button if "True"', default=True, scope=Scope.content)
    q_option_showme = Boolean(help='Display ShowSolution button if "True"', default=True, scope=Scope.content)

    # MAX ATTEMPTS PER-QUESTION OVERRIDE OF COURSE DEFAULT
    q_max_attempts = Integer(help="Max question attempts (-1 = Use Course Default)", default=-1, scope=Scope.content)

    # STEP-WISE QUESTION DEFINITION FIELDS FOR TEN VARIANTS
    display_name = String(display_name="Display name", default='StepWise', scope=Scope.content)

    q_id = String(help="Question ID", default="", scope=Scope.content)
    q_label = String(help="Question label", default="", scope=Scope.content)
    q_stimulus = String(help="Stimulus", default='Solve for \\(a\\).', scope=Scope.content)
    q_definition = String(help="Definition", default='SolveFor[5a+4=2a-5,a]', scope=Scope.content)
    q_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q1_id = String(help="Question ID", default="", scope=Scope.content)
    q1_label = String(help="Question Alternate 1", default="", scope=Scope.content)
    q1_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q1_definition = String(help="Definition", default='', scope=Scope.content)
    q1_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q1_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q_grade_hints_ded = Integer(help="Deduction for using extra Hints", default=-1, scope=Scope.content)
    q1_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q1_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q1_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q2_id = String(help="Question ID", default="", scope=Scope.content)
    q2_label = String(help="Question Alternate 2", default="", scope=Scope.content)
    q2_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q2_definition = String(help="Definition", default='', scope=Scope.content)
    q2_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q2_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q2_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q2_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q2_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q3_id = String(help="Question ID", default="", scope=Scope.content)
    q3_label = String(help="Question Alternate 3", default="", scope=Scope.content)
    q3_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q3_definition = String(help="Definition", default='', scope=Scope.content)
    q3_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q3_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q3_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q3_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q3_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q4_id = String(help="Question ID", default="", scope=Scope.content)
    q4_label = String(help="Question Alternate 4", default="", scope=Scope.content)
    q4_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q4_definition = String(help="Definition", default='', scope=Scope.content)
    q4_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q4_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q4_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q4_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q4_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q5_id = String(help="Question ID", default="", scope=Scope.content)
    q5_label = String(help="Question Alternate 5", default="", scope=Scope.content)
    q5_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q5_definition = String(help="Definition", default='', scope=Scope.content)
    q5_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q5_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q5_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q5_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q5_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q6_id = String(help="Question ID", default="", scope=Scope.content)
    q6_label = String(help="Question Alternate 6", default="", scope=Scope.content)
    q6_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q6_definition = String(help="Definition", default='', scope=Scope.content)
    q6_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q6_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q6_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q6_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q6_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q7_id = String(help="Question ID", default="", scope=Scope.content)
    q7_label = String(help="Question Alternate 7", default="", scope=Scope.content)
    q7_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q7_definition = String(help="Definition", default='', scope=Scope.content)
    q7_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q7_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q7_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q7_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q7_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q8_id = String(help="Question ID", default="", scope=Scope.content)
    q8_label = String(help="Question Alternate 8", default="", scope=Scope.content)
    q8_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q8_definition = String(help="Definition", default='', scope=Scope.content)
    q8_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q8_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q8_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q8_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q8_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    q9_id = String(help="Question ID", default="", scope=Scope.content)
    q9_label = String(help="Question Alternate 9", default="", scope=Scope.content)
    q9_stimulus = String(help="Stimulus", default='', scope=Scope.content)
    q9_definition = String(help="Definition", default='', scope=Scope.content)
    q9_type = String(help="Type", default='gradeBasicAlgebra', scope=Scope.content)
    q9_display_math = String(help="Display Math", default='\\(\\)', scope=Scope.content)
    q9_hint1 = String(help="First Hint", default='', scope=Scope.content)
    q9_hint2 = String(help="Second Hint", default='', scope=Scope.content)
    q9_hint3 = String(help="Third Hint", default='', scope=Scope.content)

    # STUDENT'S QUESTION PERFORMANCE FIELDS
    xb_user_email = String(help="The user's email addr", default="", scope=Scope.user_state)
    grade = Float(help="The student's grade", default=-1, scope=Scope.user_state)
    solution = Dict(help="The student's last solution", default={}, scope=Scope.user_state)
    question = Dict(help="The student's current question", default={}, scope=Scope.user_state)
    # count_attempts keeps track of the number of attempts of this question by this student so we can
    # compare to course.max_attempts which is inherited as an per-question setting or a course-wide setting.
    count_attempts = Integer(help="Counted number of questions attempts", default=0, scope=Scope.user_state)
    raw_possible = Float(help="Number of possible points", default=3,scope=Scope.user_state)
    # The following 'weight' is examined by the standard scoring code, so needs to be set once we determine which weight value to use
    # (per-Q or per-course). Also used in rescoring by override_score_module_state.
    weight = Float(help="Defines the number of points the problem is worth.", default=1, scope=Scope.user_state)

    my_weight  = Integer(help="Remember weight course setting vs question setting", default=-1, scope=Scope.user_state)
    my_max_attempts  = Integer(help="Remember max_attempts course setting vs question setting", default=-1, scope=Scope.user_state)
    my_option_showme  = Integer(help="Remember option_showme course setting vs question setting", default=-1, scope=Scope.user_state)
    my_option_hint  = Integer(help="Remember option_hint course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_showme_ded  = Integer(help="Remember grade_showme_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_hints_count  = Integer(help="Remember grade_hints_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_hints_ded  = Integer(help="Remember grade_hints_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_errors_count  = Integer(help="Remember grade_errors_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_errors_ded  = Integer(help="Remember grade_errors_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_min_steps_count  = Integer(help="Remember grade_min_steps_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_min_steps_ded  = Integer(help="Remember grade_min_steps_ded course setting vs question setting", default=-1, scope=Scope.user_state)

    # variant_attempted: Remembers the set of variant q_index values the student has already attempted.
    # We can't add a Set to Scope.user_state, or we get get runtime errors whenever we update this field:
    #      variants_attempted = Set(scope=Scope.user_state)
    #      TypeError: Object of type set is not JSON serializable
    # See e.g. this:  https://stackoverflow.com/questions/8230315/how-to-json-serialize-sets
    # So we'll leave the variants in an Integer field and fiddle the bits ourselves :-(
    # We define our own bitwise utility functions below: bit_count_ones() bit_is_set() bit_is_set()

    variants_attempted = Integer(help="Bitmap of attempted variants", default=0,scope=Scope.user_state)
    variants_count = Integer(help="Count of available variants", default=0,scope=Scope.user_state)
    previous_variant = Integer(help="Index (q_index) of the last variant used", default=-1,scope=Scope.user_state)

    # FIELDS FOR THE ScorableXBlockMixin

    is_answered = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if successfully answered'
    )

    correct = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if correctly answered'
    )

    raw_earned = Float(
        help="Keeps maximum score achieved by student as a raw value between 0 and 1.",
        scope=Scope.user_state,
        default=0,
        enforce_type=True,
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # STUDENT_VIEW
    def student_view(self, context=None):
        """
        The STUDENT view of the SWREACTXBlock, shown to students
        when viewing courses.  We set up the question parameters (referring to course-wide settings), then launch
        the javascript StepWise client.
        """
        if DEBUG: logger.info('SWREACTXBlock student_view() entered. context={context}'.format(context=context))

        if DEBUG: logger.info("SWREACTXBlock student_view() self={a}".format(a=self))
        if DEBUG: logger.info("SWREACTXBlock student_view() self.runtime={a}".format(a=self.runtime))
        if DEBUG: logger.info("SWREACTXBlock student_view() self.runtime.course_id={a}".format(a=self.runtime.course_id))
        if DEBUG: logger.info("SWREACTXBlock student_view() self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWREACTXBlock student_view() self.previous_variant={v}".format(v=self.previous_variant))

        course = get_course_by_id(self.runtime.course_id)
        if DEBUG: logger.info("SWREACTXBlock student_view() course={c}".format(c=course))

        if DEBUG: logger.info("SWREACTXBlock student_view() max_attempts={a} q_max_attempts={b}".format(a=self.max_attempts,b=self.q_max_attempts))

        # NOTE: Can't set a self.q_* field here if an older imported swreactxblock doesn't define this field, since it defaults to None
        # (read only?) so we'll use instance vars my_* to remember whether to use the course-wide setting or the per-question setting.
        # Similarly, some old courses may not define the stepwise advanced settings we want, so we create local variables for them.

        # For per-xblock settings
        temp_weight = -1
        temp_max_attempts = -1
        temp_option_hint = -1
        temp_option_showme = -1
        temp_grade_shome_ded = -1
        temp_grade_hints_count = -1
        temp_grade_hints_ded = -1
        temp_grade_errors_count = -1
        temp_grade_errors_ded = -1
        temp_grade_min_steps_count = -1
        temp_grade_min_steps_ded = -1

        # For course-wide settings
        temp_course_stepwise_weight = -1
        temp_course_stepwise_max_attempts = -1
        temp_course_stepwise_option_hint = -1
        temp_course_stepwise_option_showme = -1
        temp_course_stepwise_grade_showme_ded = -1
        temp_course_stepwise_grade_hints_count = -1
        temp_course_stepwise_grade_hints_ded = -1
        temp_course_stepwise_grade_errors_count = -1
        temp_course_stepwise_grade_errors_ded = -1
        temp_course_stepwise_grade_min_steps_count = -1
        temp_course_stepwise_grade_min_steps_ded = -1

        # Defaults For course-wide settings if they aren't defined for this course
        def_course_stepwise_weight = 1.0
        def_course_stepwise_max_attempts = None
        def_course_stepwise_option_hint = True
        def_course_stepwise_option_showme = True
        def_course_stepwise_grade_showme_ded = 3.0
        def_course_stepwise_grade_hints_count = 2
        def_course_stepwise_grade_hints_ded = 1.0
        def_course_stepwise_grade_errors_count = 2
        def_course_stepwise_grade_errors_ded = 1.0
        def_course_stepwise_grade_min_steps_count = 3
        def_course_stepwise_grade_min_steps_ded = 0.25

        # after application of course-wide settings
        self.my_weight = -1
        self.my_max_attempts = -1
        self.my_option_showme = -1
        self.my_option_hint = -1
        self.my_grade_showme_ded = -1
        self.my_grade_hints_count = -1
        self.my_grade_hints_ded = -1
        self.my_grade_errors_count = -1
        self.my_grade_errors_ded = -1
        self.my_grade_min_steps_count = -1
        self.my_grade_min_steps_ded = -1

        # Fetch the xblock-specific settings if they exist, otherwise create a default
        try:
            temp_weight = self.q_weight
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_weight was not defined in this instance: {e}'.format(e=e))
            temp_weight = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_weight: {t}'.format(t=temp_weight))

        try:
            temp_max_attempts = self.q_max_attempts
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_max_attempts was not defined in this instance: {e}'.format(e=e))
            temp_max_attempts = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_max_attempts: {t}'.format(t=temp_max_attempts))

        try:
            temp_option_hint = self.q_option_hint
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.option_hint was not defined in this instance: {e}'.format(e=e))
            temp_option_hint = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_option_hint: {t}'.format(t=temp_option_hint))

        try:
            temp_option_showme = self.q_option_showme
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.option_showme was not defined in this instance: {e}'.format(e=e))
            temp_option_showme = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_option_showme: {t}'.format(t=temp_option_showme))

        try:
            temp_grade_showme_ded = self.q_grade_showme_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_grade_showme_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_showme_ded = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_grade_showme_ded: {t}'.format(t=temp_grade_showme_ded))

        try:
            temp_grade_hints_count = self.q_grade_hints_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_grade_hints_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_hints_count = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_grade_hints_count: {t}'.format(t=temp_grade_hints_count))

        try:
            temp_grade_hints_ded = self.q_grade_hints_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_grade_hints_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_hints_ded = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_grade_hints_ded: {t}'.format(t=temp_grade_hints_ded))

        try:
            temp_grade_errors_count = self.q_grade_errors_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_grade_errors_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_errors_count = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_grade_errors_count: {t}'.format(t=temp_grade_errors_count))

        try:
            temp_grade_errors_ded = self.q_grade_errors_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_grade_errors_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_errors_ded = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_grade_errors_ded: {t}'.format(t=temp_grade_errors_ded))

        try:
            temp_grade_min_steps_count = self.q_grade_min_steps_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_grade_min_steps_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_min_steps_count = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_grade_min_steps_count: {t}'.format(t=temp_grade_min_steps_count))

        try:
            temp_grade_min_steps_ded = self.q_grade_min_steps_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() self.q_grade_min_steps_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_min_steps_ded = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_grade_min_steps_ded: {t}'.format(t=temp_grade_min_steps_ded))

        # Fetch the course-wide settings if they exist, otherwise create a default

        try:
            temp_course_stepwise_weight = course.stepwise_weight
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_weight was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_stepwise_weight = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_weight: {s}'.format(s=temp_course_stepwise_weight))

        try:
            temp_course_stepwise_max_attempts = course.stepwise_max_attempts
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_max_attempts was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_stepwise_max_attempts = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_max_attempts: {s}'.format(s=temp_course_stepwise_max_attempts))

        try:
            temp_course_stepwise_option_showme = course.stepwise_option_showme
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_option_showme was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_option_showme = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_option_showme: {s}'.format(s=temp_course_stepwise_option_showme))

        try:
            temp_course_stepwise_option_hint = course.stepwise_option_hint
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_option_hint was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_option_hint = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_option_hint: {s}'.format(s=temp_course_stepwise_option_hint))

        try:
            temp_course_stepwise_grade_hints_count = course.stepwise_grade_hints_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_settings_grade_hints_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_hints_count = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_grade_hints_count: {s}'.format(s=temp_course_stepwise_grade_hints_count))

        try:
            temp_course_stepwise_grade_showme_ded = course.stepwise_grade_showme_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_grade_showme_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_showme_ded = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_grade_showme_ded: {s}'.format(s=temp_course_stepwise_grade_showme_ded))

        try:
            temp_course_stepwise_grade_hints_ded = course.stepwise_grade_hints_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_grade_hints_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_hints_ded = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_grade_hints_ded: {s}'.format(s=temp_course_stepwise_grade_hints_ded))

        try:
            temp_course_stepwise_grade_errors_count = course.stepwise_grade_errors_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_grade_errors_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_errors_count = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_grade_errors_count: {s}'.format(s=temp_course_stepwise_grade_errors_count))

        try:
            temp_course_stepwise_grade_errors_ded = course.stepwise_grade_errors_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_grade_errors_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_errors_ded = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_grade_errors_ded: {s}'.format(s=temp_course_stepwise_grade_errors_ded))

        try:
            temp_course_stepwise_grade_min_steps_count = course.stepwise_grade_min_steps_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_grade_min_steps_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_min_steps_count = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_grade_min_steps_count: {s}'.format(s=temp_course_stepwise_grade_min_steps_count))

        try:
            temp_course_stepwise_grade_min_steps_ded = course.stepwise_grade_min_steps_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWREACTXBlock student_view() course.stepwise_grade_min_steps_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_min_steps_ded = -1
        if DEBUG: logger.info('SWREACTXBlock student_view() temp_course_stepwise_grade_min_steps_ded: {s}'.format(s=temp_course_stepwise_grade_min_steps_ded))

        # Enforce course-wide grading options here.
        # We prefer the per-question setting to the course setting.
        # If neither the question setting nor the course setting exist, use the course default.

        if (temp_weight != -1):
            self.my_weight = temp_weight
        elif (temp_course_stepwise_weight != -1):
            self.my_weight = temp_course_stepwise_weight
        else:
            self.my_weight = def_course_stepwise_weight
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_weight={m}'.format(m=self.my_weight))

        # Set the real object weight here how that we know all of the weight settings (per-Q vs. per-course).
        # weight is used by the real grading code e.g. for overriding student scores.
        self.weight = self.my_weight
        if DEBUG: logger.info('SWREACTXBlock student_view() self.weight={m}'.format(m=self.weight))

        # For max_attempts: If there is a per-question max_attempts setting, use that.
        # Otherwise, if there is a course-wide stepwise_max_attempts setting, use that.
        # Otherwise, use the course-wide max_attempts setting that is used for CAPA (non-StepWise) problems.

        if temp_max_attempts is None:
            temp_max_attempts = -1

        if (temp_max_attempts != -1):
            self.my_max_attempts = temp_max_attempts
            if DEBUG: logger.info('SWREACTXBlock student_view() my_max_attempts={a} temp_max_attempts={m}'.format(a=self.my_max_attempts,m=temp_max_attempts))
        elif (temp_course_stepwise_max_attempts != -1):
            self.my_max_attempts = temp_course_stepwise_max_attempts
            if DEBUG: logger.info('SWREACTXBlock student_view() my_max_attempts={a} temp_course_stepwise_max_attempts={m}'.format(a=self.my_max_attempts,m=temp_course_stepwise_max_attempts))
        else:
            self.my_max_attempts = course.max_attempts
            if DEBUG: logger.info('SWREACTXBlock student_view() my_max_attempts={a} course.max_attempts={m}'.format(a=self.my_max_attempts,m=course.max_attempts))

        if (temp_option_hint != -1):
            self.my_option_hint = temp_option_hint
        elif (temp_course_stepwise_option_hint != -1):
            self.my_option_hint = temp_course_stepwise_option_hint
        else:
            self.my_option_hint = def_course_stepwise_option_hint
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_option_hint={m}'.format(m=self.my_option_hint))

        if (temp_option_showme != -1):
            self.my_option_showme = temp_option_showme
        elif (temp_course_stepwise_option_showme != -1):
            self.my_option_showme = temp_course_stepwise_option_showme
        else:
            self.my_option_showme = def_course_stepwise_option_showme
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_option_showme={m}'.format(m=self.my_option_showme))

        if (temp_grade_showme_ded != -1):
            self.my_grade_showme_ded = temp_grade_showme_ded
        elif (temp_course_stepwise_grade_showme_ded != -1):
            self.my_grade_showme_ded = temp_course_stepwise_grade_showme_ded
        else:
            self.my_grade_showme_ded = def_course_stepwise_grade_showme_ded
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_grade_showme_ded={m}'.format(m=self.my_grade_showme_ded))

        if (temp_grade_hints_count != -1):
            self.my_grade_hints_count = temp_grade_hints_count
        elif (temp_course_stepwise_grade_hints_count != -1):
            self.my_grade_hints_count = temp_course_stepwise_grade_hints_count
        else:
            self.my_grade_hints_count = def_course_stepwise_grade_hints_count
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_grade_hints_count={m}'.format(m=self.my_grade_hints_count))

        if (temp_grade_hints_ded != -1):
            self.my_grade_hints_ded = temp_grade_hints_ded
        elif (temp_course_stepwise_grade_hints_ded != -1):
            self.my_grade_hints_ded = temp_course_stepwise_grade_hints_ded
        else:
            self.my_grade_hints_ded = def_course_stepwise_grade_hints_ded
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_grade_hints_ded={m}'.format(m=self.my_grade_hints_ded))

        if (temp_grade_errors_count != -1):
            self.my_grade_errors_count = temp_grade_errors_count
        elif (temp_course_stepwise_grade_errors_count != -1):
            self.my_grade_errors_count = temp_course_stepwise_grade_errors_count
        else:
            self.my_grade_errors_count = def_course_stepwise_grade_errors_count
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_grade_errors_count={m}'.format(m=self.my_grade_errors_count))

        if (temp_grade_errors_ded != -1):
            self.my_grade_errors_ded = temp_grade_errors_ded
        elif (temp_course_stepwise_grade_errors_ded != -1):
            self.my_grade_errors_ded = temp_course_stepwise_grade_errors_ded
        else:
            self.my_grade_errors_ded = def_course_stepwise_grade_errors_ded
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_grade_errors_ded={m}'.format(m=self.my_grade_errors_ded))

        if (temp_grade_min_steps_count != -1):
            self.my_grade_min_steps_count = temp_grade_min_steps_count
        elif (temp_course_stepwise_grade_min_steps_count != -1):
            self.my_grade_min_steps_count = temp_course_stepwise_grade_min_steps_count
        else:
            self.my_grade_min_steps_count = def_course_stepwise_grade_min_steps_count
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_grade_min_steps_count={m}'.format(m=self.my_grade_min_steps_count))

        if (temp_grade_min_steps_ded != -1):
            self.my_grade_min_steps_ded = temp_grade_min_steps_ded
        elif (temp_course_stepwise_grade_min_steps_ded != -1):
            self.my_grade_min_steps_ded = temp_course_stepwise_grade_min_steps_ded
        else:
            self.my_grade_min_steps_ded = def_course_stepwise_grade_min_steps_ded
        if DEBUG: logger.info('SWREACTXBlock student_view() self.my_grade_min_steps_ded={m}'.format(m=self.my_grade_min_steps_ded))


        # Save an identifier for the user

        user_service = self.runtime.service( self, 'user')
        xb_user = user_service.get_current_user()
        self.xb_user_email = xb_user.emails[0]

        # Determine which stepwise variant to use

        self.variants_count = 0

        if len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0 and len(self.q8_definition)>0  and len(self.q9_definition)>0:
            self.variants_count = 10
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0 and len(self.q8_definition)>0:
            self.variants_count = 9
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0:
            self.variants_count = 8
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0:
            self.variants_count = 7
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0:
            self.variants_count = 6
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0:
            self.variants_count = 5
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0:
            self.variants_count = 4
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0:
            self.variants_count = 3
        elif len(self.q_definition)>0 and len(self.q1_definition)>0:
            self.variants_count = 2
        else:
            self.variants_count = 1

        if DEBUG: logger.info("SWREACTXBlock student_view() self.variants_count={c}".format(c=self.variants_count))
        # Pick a variant at random, and make sure that it is one we haven't attempted before.

        random.seed()				# Use the clock to seed the random number generator for picking variants
        self.question = self.pick_variant()

        # question = self.question		# Don't need local var
        q_index = self.question['q_index']

        if DEBUG: logger.info("SWREACTXBlock student_view() pick_variant selected q_index={i} question={q}".format(i=q_index,q=self.question))
        html = self.resource_string("static/html/swreactxstudent.html")
        frag = Fragment(html.format(self=self))

        try:
            url = f"https://cdn.{settings.LMS_BASE}/swreactxblock/static/css/swreactxstudent.css"
            response = requests.get(url)
            if response.status_code == 200:
                frag.add_css_url(f"//cdn.{settings.LMS_BASE}/swreactxblock/static/css/swreactxstudent.css")
            else:
                logger.warning(f"SWREACTXBlock student_view() failed to load css: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"SWREACTXBlock student_view() failed to load css: {e}")

        frag.add_css_url("//stepwise.querium.com/libs/mathquill/mathquill.css")
        frag.add_css_url("//code.ionicframework.com/ionicons/2.0.1/css/ionicons.min.css")
        frag.add_css_url("//stepwiseai.querium.com/client/querium-stepwise-1.6.9.css")

        frag.add_javascript_url("//cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=TeX-MML-AM_HTMLorMML")
        frag.add_javascript_url("//stepwise.querium.com/libs/mathquill/mathquill.js")
        frag.add_javascript_url("//ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular.min.js")
        frag.add_javascript_url("//ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-sanitize.min.js")
        frag.add_javascript_url("//ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-animate.min.js")
        frag.add_javascript_url("//www.gstatic.com/firebasejs/4.4.0/firebase.js")               # For qEval client-side logging
        frag.add_javascript_url("//stepwiseai.querium.com/client/querium-stepwise-1.6.9.js")    # 1.6.9.1 corrects a bug in hints looping


        frag.add_javascript(self.resource_string("static/js/src/swreactxstudent.js"))
        if DEBUG: logger.info("SWREACTXBlock student_view() calling frag.initialize_js")
        frag.initialize_js('SWREACTXStudent', {})
        return frag


    # PUBLISH_GRADE
    # For rescoring events
    def publish_grade(self):
        if DEBUG: logger.info("SWREACTXBlock publish_grade() self.raw_earned={e} self.weight={w}".format(e=self.raw_earned,w=self.weight))
        if self.raw_earned < 0.0:
           self.raw_earned = 0.0
        if self.raw_earned > self.weight:
           self.raw_earned = self.weight
        self.runtime.publish(self, 'grade',
             {   'value': self.raw_earned,
                 'max_value': self.weight
             })



    # SAVE
    # For rescoring events.  Should be a no-op.
    def save(self):
        # if DEBUG: logger.info("SWREACTXBlock save() self.raw_earned={g} self.weight={w} self.solution={s}".format(g=self.raw_earned,w=self.weight,s=self.solution))
        XBlock.save(self)       # Call parent class save()
        # if DEBUG: logger.info("SWREACTXBlock save() back from parent save. self.solution={s}".format(s=self.solution))


    # GET_DATA: RETURN DATA FOR THIS QUESTION
    @XBlock.json_handler
    def get_data(self, msg, suffix=''):
        if DEBUG: logger.info("SWREACTXBlock get_data() entered. msg={msg}".format(msg=msg))

        if self.my_max_attempts is None:
            self.my_max_attempts = -1

        data = {
            "question" : self.question,
            "grade" : self.grade,
            "solution" : self.solution,
            "count_attempts" : self.count_attempts,
            "variants_count" : self.variants_count,
            "max_attempts" : self.my_max_attempts
        }
        if DEBUG: logger.info("SWREACTXBlock get_data() data={d}".format(d=data))
        json_data = json.dumps(data)
        return json_data

    # SAVE GRADE
    @XBlock.json_handler
    def save_grade(self, data, suffix=''):
        if DEBUG: logger.info('SWREACTXBlock save_grade() entered')
        if DEBUG: logger.info("SWREACTXBlock save_grade() self.max_attempts={a}".format(a=self.max_attempts))

        # Check for missing grading attributes

        if DEBUG: logger.info("SWREACTXBlock save_grade() initial self={a}".format(a=self))
        if DEBUG: logger.info("SWREACTXBlock save_grade() initial data={a}".format(a=data))

        try: q_weight = self.q_weight
        except (NameError,AttributeError) as e:
             if DEBUG: logger.info('SWREACTXBlock save_grade() self.q_weight was not defined: {e}'.format(e=e))
             q_weight = 1.0

        try: q_grade_showme_ded = self.q_grade_showme_ded
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWREACTXBlock save_grade() self.q_grade_showme_dev was not defined: {e}'.format(e=e))
             q_grade_showme_ded = -1

        try: q_grade_hints_count = self.q_grade_hints_count
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWREACTXBlock save_grade() self.q_grade_hints_count was not defined: {e}',format(e=e))
             q_grade_hints_count = -1

        try: q_grade_hints_ded = self.q_grade_hints_ded
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWREACTXBlock save_grade() self.q_grade_hints_ded was not defined: {e}'.format(e=e))
             q_grade_hints_ded = -1

        try: q_grade_errors_count = self.q_grade_errors_count
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWREACTXBlock save_grade() self.q_grade_errors_count was not defined: {e}'.format(e=e))
             q_grade_errors_count = -1

        try: q_grade_errors_ded = self.q_grade_errors_ded
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWREACTXBlock save_grade() self.q_grade_errors_ded was not defined: {e}'.format(e=e))
             q_grade_errors_ded = -1

        try: q_grade_min_steps_count = self.q_grade_min_steps_count
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWREACTXBlock save_grade() self.q_grade_min_steps_count was not defined: {e}'.format(e=e))
             q_grade_min_steps_count = -1

        try: q_grade_min_steps_ded = self.q_grade_min_steps_ded
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWREACTXBlock save_grade() self.q_grade_min_steps_ded was not defined: {e}'.format(e=e))
             q_grade_min_steps_ded = -1

        # Apply grading defaults

        if q_weight == -1:
            if DEBUG: logger.info('SWREACTXBlock save_grade() weight set to 1.0')
            q_weight = 1.0
        if q_grade_showme_ded == -1:
            if DEBUG: logger.info('SWREACTXBlock save_grade() showme default set to 3.0')
            q_grade_showme_ded = 3.0
        if q_grade_hints_count == -1:
            if DEBUG: logger.info('SWREACTXBlock save_grade() hints_count default set to 2')
            q_grade_hints_count = 2
        if q_grade_hints_ded == -1:
            if DEBUG: logger.info('SWREACTXBlock save_grade() hints_ded default set to 1.0')
            q_grade_hints_ded = 1.0
        if q_grade_errors_count == -1:
            if DEBUG: logger.info('SWREACTXBlock save_grade() errors_count default set to 3')
            q_grade_errors_count = 3
        if q_grade_errors_ded == -1:
            if DEBUG: logger.info('SWREACTXBlock save_grade() errors_ded default set to 1.0')
            q_grade_errors_ded = 1.0
        if q_grade_min_steps_ded == -1:
            if DEBUG: logger.info('SWREACTXBlock save_grade() min_steps_ded default set to 0.25')
            q_grade_min_steps_ded = 0.25

        """
        Count the total number of VALID steps the student input.
        Used to determine if they get full credit for entering at least a min number of good steps.
        """
        valid_steps = 0;

        if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps data={d}".format(d=data))
        step_details = data['stepDetails']
        if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps step_details={d}".format(d=step_details))
        if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps len(step_details)={l}".format(l=len(step_details)))
        for c in range(len(step_details)):
            if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps begin examine step c={c} step_details[c]={d}".format(c=c,d=step_details[c]))
            for i in range (len(step_details[c]['info'])):
                if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps examine step c={c} i={i} step_details[c]['info']={s}".format(c=c,i=i,s=step_details[c]['info']))
                if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps examine step c={c} i={i} step_details[c]['info'][i]={s}".format(c=c,i=i,s=step_details[c]['info'][i]))
                step_status = step_details[c]['info'][i]['status']
                if (step_status == 0):       # victory valid_steps += 1
                    valid_steps += 1
                    if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps c={c} i={i} victory step found".format(c=c,i=i))
                elif (step_status == 1):     # valid step
                    valid_steps += 1
                    if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps c={c} i={i} valid step found".format(c=c,i=i))
                elif (step_status == 3):     # invalid step
                    valid_steps += 0         # don't count invalid steps
                else:
                    if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps c={c} i={i} ignoring step_status={s}".format(c=c,i=i,s=step_status))
                if DEBUG: logger.info("SWREACTXBlock save_grade() count valid_steps examine step c={c} i={i} step_status={s} valid_steps={v}".format(c=c,i=i,s=step_status,v=valid_steps))
        if DEBUG: logger.info("SWREACTXBlock save_grade() final valid_steps={v}".format(v=valid_steps))

        grade=3.0
        max_grade=grade

        if DEBUG: logger.info('SWREACTXBlock save_grade() initial grade={a} errors={b} errors_count={c} hints={d} hints_count={e} showme={f} min_steps={g} valid_steps={h}'.format(a=grade,b=data['errors'],c=q_grade_errors_count,d=data['hints'],e=q_grade_hints_count,f=data['usedShowMe'],g=q_grade_min_steps_count,h=valid_steps))
        if data['errors']>q_grade_errors_count:
            grade=grade-q_grade_errors_ded
            if DEBUG: logger.info('SWREACTXBlock save_grade() errors test errors_ded={a} grade={b}'.format(a=q_grade_errors_ded,b=grade))
        if data['hints']>q_grade_hints_count:
            grade=grade-q_grade_hints_ded
            if DEBUG: logger.info('SWREACTXBlock save_grade() hints test hints_ded={a} grade={b}'.format(a=q_grade_hints_ded,b=grade))
        if data['usedShowMe']:
            grade=grade-q_grade_showme_ded
            if DEBUG: logger.info('SWREACTXBlock save_grade() showme test showme_ded={a} grade={b}'.format(a=q_grade_showme_ded,b=grade))
        
        # Don't subtract min_steps points on a MatchSpec problem or DomainOf
        self.my_q_definition = data['answered_question']['q_definition']
        if DEBUG: logger.info('SWREACTXBlock save_grade() check on min_steps deduction grade={g} max_grade={m} q_grade_min_steps_count={c} q_grade_min_steps_ded={d} self.my_q_definition={q}'.format(g=grade,m=max_grade,c=q_grade_min_steps_count,d=q_grade_min_steps_ded,q=self.my_q_definition))
        if (grade >= max_grade and valid_steps < q_grade_min_steps_count and self.my_q_definition.count('MatchSpec') == 0 and self.my_q_definition.count('DomainOf') == 0 ):
            grade=grade-q_grade_min_steps_ded
            if DEBUG: logger.info('SWREACTXBlock save_grade() took min_steps deduction after grade={g}'.format(g=grade))
        else:
            if DEBUG: logger.info('SWREACTXBlock save_grade() did not take min_steps deduction after grade={g}'.format(g=grade))

        if grade<0.0:
            logger.info('SWREACTXBlock save_grade() zero negative grade')
            grade=0.0

        if DEBUG: logger.info("SWREACTXBlock save_grade() final grade={a} q_weight={b}".format(a=grade,b=q_weight))

        self.runtime.publish(self, 'grade',
            {   'value': (grade/3.0)*q_weight,
                'max_value': 1.0*q_weight
            })

        if DEBUG: logger.info("SWREACTXBlock save_grade() final data={a}".format(a=data))
        self.solution = data
        self.grade = grade
        if DEBUG: logger.info("SWREACTXBlock save_grade() final self.solution={a}".format(a=self.solution))

        # Don't increment attempts on save grade.  We want to increment them when the student starts
        # a question, not when they finish.  Otherwise people can start the question as many times
        # as they want as long as they don't finish it, then reload the page.
        # self.count_attempts += 1
        # make sure we've recorded this atttempt, but it should have been done in start_attempt():
        try:
            if self.q_index != -1:
                self.variants_attempted = set.bit_set_one(self.variants_attempted,self.q_index)
                if DEBUG: logger.info("SWREACTXBlock save_grade() record variants_attempted for variant {a}".format(v=self.q_index))
                self.previous_variant = q_index
                if DEBUG: logger.info("SWREACTXBlock save_grade() record previous_variant for variant {a}".format(v=self.previous_variant))
            else:
                if DEBUG: logger.error("SWREACTXBlock save_grade record variants_attempted for variant -1")
        except (NameError,AttributeError) as e:
            if DEBUG: logger.warning('SWREACTXBlock save_grade() self.q_index was not defined: {e}'.format(e=e))

        self.save()     # Time to persist our state!!!

        # if DEBUG: logger.info("SWREACTXBlock save_grade() final self={a}".format(a=self))
        if DEBUG: logger.info("SWREACTXBlock save_grade() final self.count_attempts={a}".format(a=self.count_attempts))
        if DEBUG: logger.info("SWREACTXBlock save_grade() final self.solution={a}".format(a=self.solution))
        if DEBUG: logger.info("SWREACTXBlock save_grade() final self.grade={a}".format(a=self.grade))
        if DEBUG: logger.info("SWREACTXBlock save_grade() final self.weight={a}".format(a=self.weight))
        if DEBUG: logger.info("SWREACTXBlock save_grade() final self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWREACTXBlock save_grade() final self.previous_variant={v}".format(v=self.previous_variant))



    # START ATTEMPT
    @XBlock.json_handler
    def start_attempt(self, data, suffix=''):
        if DEBUG: logger.info("SWREACTXBlock start_attempt() entered")
        if DEBUG: logger.info("SWREACTXBlock start_attempt() data={d}".format(d=data))
        if DEBUG: logger.info("SWREACTXBlock start_attempt() self.count_attempts={c} max_attempts={m}".format(c=self.count_attempts,m=self.max_attempts))
        if DEBUG: logger.info("SWREACTXBlock start_attempt() self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWREACTXBlock start_attempt() self.previous_variant={v}".format(v=self.previous_variant))
        # logger.info("SWREACTXBlock start_attempt() action={d} sessionId={s} timeMark={t}".format(d=data['status']['action'],s=data['status']['sessionId'],t=data['status']['timeMark']))
        if DEBUG: logger.info("SWREACTXBlock start_attempt() passed q_index={q}".format(q=data['q_index']))
        self.count_attempts += 1
        if DEBUG: logger.info("SWREACTXBlock start_attempt() updated self.count_attempts={c}".format(c=self.count_attempts))
        variant = data['q_index']
        if DEBUG: logger.info("variant is {v}".format(v=variant))
        if self.bit_is_set(self.variants_attempted,variant):
            if DEBUG: logger.info("variant {v} has already been attempted!".format(v=variant))
        else:
            if DEBUG: logger.info("adding variant {v} to self.variants_attempted={s}".format(v=variant,s=self.variants_attempted))
            self.variants_attempted = self.bit_set_one(self.variants_attempted,variant)
            if DEBUG: logger.info("checking bit_is_set {v}={b}".format(v=variant,b=self.bit_is_set(self.variants_attempted,variant)))
            self.previous_variant = variant
            if DEBUG: logger.info("setting previous_variant to {v}".format(v=variant))
            
        return_data = {
            "count_attempts" : self.count_attempts,
        }
        if DEBUG: logger.info("SWREACTXBlock start_attempt() done return_data={return_data}".format(return_data=return_data))
        json_data = json.dumps(return_data)
        return json_data


    # RESET: PICK A NEW VARIANT
    @XBlock.json_handler
    def retry(self, data, suffix=''):
        if DEBUG: logger.info("SWREACTXBlock retry() entered")
        if DEBUG: logger.info("SWREACTXBlock retry() data={d}".format(d=data))
        if DEBUG: logger.info("SWREACTXBlock retry() self.count_attempts={c} max_attempts={m}".format(c=self.count_attempts,m=self.max_attempts))
        if DEBUG: logger.info("SWREACTXBlock retry() self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWREACTXBlock retry() pre-pick_question q_index={i}".format(v=self.question['q_index']))
        self.question = self.pick_variant()

        return_data = {
            "question" : self.question,
        }

        if DEBUG: logger.info("SWREACTXBlock retry() post-pick returning self.question={q} return_data={r}".format(q=self.question,r=return_data))
        json_data = json.dumps(return_data)
        return json_data


    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        if DEBUG: logger.info('SWREACTXBlock workbench_scenarios() entered')
        """A canned scenario for display in the workbench."""
        return [
            ("SWREACTXBlock",
             """<swreactxblock/>
             """),
            ("Multiple SWREACTXBlock",
             """<vertical_demo>
                <swreactxblock/>
                <swreactxblock/>
                <swreactxblock/>
                </vertical_demo>
             """),
        ]


    def studio_view(self, context=None):
        if DEBUG: logger.info('SWREACTXBlock studio_view() entered')
        """
        The STUDIO view of the SWREACTXBlock, shown to instructors
        when authoring courses.
        """
        html = self.resource_string("static/html/swreactxstudio.html")
        frag = Fragment(html.format(self=self))
        frag.add_css_url("//cdn.web.stepwisemath.ai/swreactxblock/static/css/swreactxstudio.css")
        frag.add_javascript(self.resource_string("static/js/src/swreactxstudio.js"))

        frag.initialize_js('SWREACTXStudio')
        return frag


    def author_view(self, context=None):
        if DEBUG: logger.info('SWREACTXBlock author_view() entered')
        """
        The AUTHOR view of the SWREACTXBlock, shown to instructors
        when previewing courses.
        """
        html = self.resource_string("static/html/swreactxauthor.html")
        frag = Fragment(html.format(self=self))
        frag.add_css_url("//cdn.web.stepwisemath.ai/swreactxblock/static/css/swreactxauthor.css")
        frag.add_javascript_url("//cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=TeX-MML-AM_HTMLorMML")
        frag.add_javascript(self.resource_string("static/js/src/swreactxauthor.js"))

        if DEBUG: logger.info("SWREACTXBlock SWREACTXAuthor author_view v={a}".format(a=self.q_definition))
        if DEBUG: logger.info("SWREACTXBlock SWREACTXAuthor author_view v1={a} v2={b} v3={c}".format(a=self.q1_definition,b=self.q2_definition,c=self.q3_definition))
        if DEBUG: logger.info("SWREACTXBlock SWREACTXAuthor author_view v4={a} v5={b} v6={c}".format(a=self.q4_definition,b=self.q5_definition,c=self.q6_definition))
        if DEBUG: logger.info("SWREACTXBlock SWREACTXAuthor author_view v7={a} v8={b} v9={c}".format(a=self.q7_definition,b=self.q8_definition,c=self.q9_definition))

        # tell author_view how many variants are defined
        if len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0 and len(self.q8_definition)>0 and len(self.q9_definition)>0:
            variants = 10
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0 and len(self.q8_definition)>0:
            variants = 9
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0:
            variants = 8
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0:
            variants = 7
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0:
            variants = 6
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0:
            variants = 5
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0:
            variants = 4
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0:
            variants = 3
        elif len(self.q_definition)>0 and len(self.q1_definition)>0:
            variants = 2
        else:
            variants = 1

        if DEBUG: logger.info("SWREACTXBlock SWREACTXAuthor author_view variants={a}".format(a=variants))

        frag.initialize_js('SWREACTXAuthor', variants)
        return frag


    # SAVE QUESTION
    @XBlock.json_handler
    def save_question(self, data, suffix=''):
        if DEBUG: logger.info('SWREACTXBlock save_question() entered')
        self.q_max_attempts = int(data['q_max_attempts'])
        self.q_weight = float(data['q_weight'])
        if data['q_option_showme'].lower() == u'true':
            self.q_option_showme = True
        else:
            self.q_option_showme = False
        if data['q_option_hint'].lower() == u'true':
            self.q_option_hint = True
        else:
            self.q_option_hint = False
        self.q_grade_showme_ded = float(data['q_grade_showme_ded'])
        self.q_grade_hints_count = int(data['q_grade_hints_count'])
        self.q_grade_hints_ded = float(data['q_grade_hints_ded'])
        self.q_grade_errors_count = int(data['q_grade_errors_count'])
        self.q_grade_errors_ded = float(data['q_grade_errors_ded'])
        self.q_grade_min_steps_count = int(data['q_grade_min_steps_count'])
        self.q_grade_min_steps_ded = float(data['q_grade_min_steps_ded'])

        self.q_id = data['id']
        self.q_label = data['label']
        self.q_stimulus = data['stimulus']
        self.q_definition = data['definition']
        self.q_type = data['qtype']
        self.q_display_math = data['display_math']
        self.q_hint1 = data['hint1']
        self.q_hint2 = data['hint2']
        self.q_hint3 = data['hint3']

        self.q1_id = data['q1_id']
        self.q1_label = data['q1_label']
        self.q1_stimulus = data['q1_stimulus']
        self.q1_definition = data['q1_definition']
        self.q1_type = data['q1_qtype']
        self.q1_display_math = data['q1_display_math']
        self.q1_hint1 = data['q1_hint1']
        self.q1_hint2 = data['q1_hint2']
        self.q_id = data['id']
        self.q_label = data['label']
        self.q_stimulus = data['stimulus']
        self.q_definition = data['definition']
        self.q_type = data['qtype']
        self.q_display_math = data['display_math']
        self.q_hint1 = data['hint1']
        self.q_hint2 = data['hint2']
        self.q_hint3 = data['hint3']

        self.q1_id = data['q1_id']
        self.q1_label = data['q1_label']
        self.q1_stimulus = data['q1_stimulus']
        self.q1_definition = data['q1_definition']
        self.q1_type = data['q1_qtype']
        self.q1_display_math = data['q1_display_math']
        self.q1_hint1 = data['q1_hint1']
        self.q1_hint2 = data['q1_hint2']
        self.q1_hint3 = data['q1_hint3']

        self.q2_id = data['q2_id']
        self.q2_label = data['q2_label']
        self.q2_stimulus = data['q2_stimulus']
        self.q2_definition = data['q2_definition']
        self.q2_type = data['q2_qtype']
        self.q2_display_math = data['q2_display_math']
        self.q2_hint1 = data['q2_hint1']
        self.q2_hint2 = data['q2_hint2']
        self.q2_hint3 = data['q2_hint3']

        self.q3_id = data['q3_id']
        self.q3_label = data['q3_label']
        self.q3_stimulus = data['q3_stimulus']
        self.q3_definition = data['q3_definition']
        self.q3_type = data['q3_qtype']
        self.q3_display_math = data['q3_display_math']
        self.q3_hint1 = data['q3_hint1']
        self.q3_hint2 = data['q3_hint2']
        self.q3_hint3 = data['q3_hint3']

        self.q4_id = data['q4_id']
        self.q4_label = data['q4_label']
        self.q4_stimulus = data['q4_stimulus']
        self.q4_definition = data['q4_definition']
        self.q4_type = data['q4_qtype']
        self.q4_display_math = data['q4_display_math']
        self.q4_hint1 = data['q4_hint1']
        self.q4_hint2 = data['q4_hint2']
        self.q4_hint3 = data['q4_hint3']

        self.q5_id = data['q5_id']
        self.q5_label = data['q5_label']
        self.q5_stimulus = data['q5_stimulus']
        self.q5_definition = data['q5_definition']
        self.q5_type = data['q5_qtype']
        self.q5_display_math = data['q5_display_math']
        self.q5_hint1 = data['q5_hint1']
        self.q5_hint2 = data['q5_hint2']
        self.q5_hint3 = data['q5_hint3']

        self.q6_id = data['q6_id']
        self.q6_label = data['q6_label']
        self.q6_stimulus = data['q6_stimulus']
        self.q6_definition = data['q6_definition']
        self.q6_type = data['q6_qtype']
        self.q6_display_math = data['q6_display_math']
        self.q6_hint1 = data['q6_hint1']
        self.q6_hint2 = data['q6_hint2']
        self.q6_hint3 = data['q6_hint3']

        self.q7_id = data['q7_id']
        self.q7_label = data['q7_label']
        self.q7_stimulus = data['q7_stimulus']
        self.q7_definition = data['q7_definition']
        self.q7_type = data['q7_qtype']
        self.q7_display_math = data['q7_display_math']
        self.q7_hint1 = data['q7_hint1']
        self.q7_hint2 = data['q7_hint2']
        self.q7_hint3 = data['q7_hint3']

        self.q8_id = data['q8_id']
        self.q8_label = data['q8_label']
        self.q8_stimulus = data['q8_stimulus']
        self.q8_definition = data['q8_definition']
        self.q8_type = data['q8_qtype']
        self.q8_display_math = data['q8_display_math']
        self.q8_hint1 = data['q8_hint1']
        self.q8_hint2 = data['q8_hint2']
        self.q8_hint3 = data['q8_hint3']

        self.q9_id = data['q9_id']
        self.q9_label = data['q9_label']
        self.q9_stimulus = data['q9_stimulus']
        self.q9_definition = data['q9_definition']
        self.q9_type = data['q9_qtype']
        self.q9_display_math = data['q9_display_math']
        self.q9_hint1 = data['q9_hint1']
        self.q9_hint2 = data['q9_hint2']
        self.q9_hint3 = data['q9_hint3']

        if len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0 and len(self.q8_definition)>0 and len(self.q9_definition)>0:
            self.display_name = "Step-by-Step Dynamic [10]"
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0 and len(self.q8_definition)>0:
            self.display_name = "Step-by-Step Dynamic [9]"
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0 and len(self.q7_definition)>0:
            self.display_name = "Step-by-Step Dynamic [8]"
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0 and len(self.q6_definition)>0:
            self.display_name = "Step-by-Step Dynamic [7]"
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0 and len(self.q5_definition)>0:
            self.display_name = "Step-by-Step Dynamic [6]"
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0 and len(self.q4_definition)>0:
            self.display_name = "Step-by-Step Dynamic [5]"
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0 and len(self.q3_definition)>0:
            self.display_name = "Step-by-Step Dynamic [4]"
        elif len(self.q_definition)>0 and len(self.q1_definition)>0 and len(self.q2_definition)>0:
            self.display_name = "Step-by-Step Dynamic [3]"
        elif len(self.q_definition)>0 and len(self.q1_definition)>0:
            self.display_name = "Step-by-Step Dynamic [2]"
        else:
            self.display_name = "Step-by-Step"

        # mcdaniel jul-2020: fix syntax error in print statement
        print(self.display_name)
        return {'result': 'success'}


    # Do necessary overrides from ScorableXBlockMixin
    def has_submitted_answer(self):
        if DEBUG: logger.info('SWREACTXBlock has_submitted_answer() entered')
        """
        Returns True if the problem has been answered by the runtime user.
        """
        if DEBUG: logger.info("SWREACTXBlock has_submitted_answer() {a}".format(a=self.is_answered))
        return self.is_answered


    def get_score(self):
        if DEBUG: logger.info('SWREACTXBlock get_score() entered')
        """
        Return a raw score already persisted on the XBlock.  Should not
        perform new calculations.
        Returns:
            Score(raw_earned=float, raw_possible=float)
        """
        if DEBUG: logger.info("SWREACTXBlock get_score() earned {e}".format(e=self.raw_earned))
        if DEBUG: logger.info("SWREACTXBlock get_score() max {m}".format(m=self.max_score()))
        return Score(float(self.raw_earned), float(self.max_score()))


    def set_score(self, score):
        """
        Persist a score to the XBlock.
        The score is a named tuple with a raw_earned attribute and a
        raw_possible attribute, reflecting the raw earned score and the maximum
        raw score the student could have earned respectively.
        Arguments:
            score: Score(raw_earned=float, raw_possible=float)
        Returns:
            None
        """
        if DEBUG: logger.info("SWREACTXBlock set_score() earned {e}".format(e=score.raw_earned))
        self.raw_earned = score.raw_earned


    def calculate_score(self):
        """
        Calculate a new raw score based on the state of the problem.
        This method should not modify the state of the XBlock.
        Returns:
            Score(raw_earned=float, raw_possible=float)
        """
        if DEBUG: logger.info("SWREACTXBlock calculate_score() grade {g}".format(g=self.grade))
        if DEBUG: logger.info("SWREACTXBlock calculate_score() max {m}".format(m=self.max_score))
        return Score(float(self.grade), float(self.max_score()))


    def allows_rescore(self):
        """
        Boolean value: Can this problem be rescored?
        Subtypes may wish to override this if they need conditional support for
        rescoring.
        """
        if DEBUG: logger.info("SWREACTXBlock allows_rescore() False")
        return False


    def max_score(self):
        """
        Function which returns the max score for an xBlock which emits a score
        https://openedx.atlassian.net/wiki/spaces/AC/pages/161400730/Open+edX+Runtime+XBlock+API#OpenedXRuntimeXBlockAPI-max_score(self):
        :return: Max Score for this problem
        """
        # Want the normalized, unweighted score here (1), not the points possible (3)
        return 1


    def weighted_grade(self):
        """
        Returns the block's current saved grade multiplied by the block's
        weight- the number of points earned by the learner.
        """
        if DEBUG: logger.info("SWREACTXBlock weighted_grade() earned {e}".format(e=self.raw_earned))
        if DEBUG: logger.info("SWREACTXBlock weighted_grade() weight {w}".format(w=self.q_weight))
        return self.raw_earned * self.q_weight


    def bit_count_ones(self,var):
        """
        Returns the count of one bits in an integer variable
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWREACTXBlock bit_count_ones var={v}".format(v=var))
        count=0
        bits = var
        for b in range(32):
            lsb = (bits >> b) & 1;
            count = count + lsb;
        if DEBUG: logger.info("SWREACTXBlock bit_count_ones result={c}".format(c=count))
        return count


    def bit_set_one(self,var,bitnum):
        """
        return var = var with bit 'bitnum' set
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWREACTXBlock bit_set_one var={v} bitnum={b}".format(v=var,b=bitnum))
        var = var | (1 << bitnum)
        if DEBUG: logger.info("SWREACTXBlock bit_set_one result={v}".format(v=var))
        return var


    def bit_is_set(self,var,bitnum):
        """
        return True if bit bitnum is set in var
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWREACTXBlock bit_is_set var={v} bitnum={b}".format(v=var,b=bitnum))
        result = var & (1 << bitnum)
        if DEBUG: logger.info("SWREACTXBlock bit_is_set result={v} b={b}".format(v=result,b=bool(result)))
        return bool(result)


    def pick_variant(self):
       # pick_variant() selects one of the available question variants that we have not yet attempted.
       # If there is only one variant left, we have to return that one.
       # If there are 2+ variants left, do not return the same one we started with.
       # If we've attempted all variants, we clear the list of attempted variants and pick again.
       #  Returns the question structure for the one we will use this time.

        try:
            prev_index = self.q_index
        except (NameError,AttributeError) as e:
            prev_index = -1

        if DEBUG: logger.info("SWREACTXBlock pick_variant() started replacing prev_index={p}".format(p=prev_index))

        # If there's no self.q_index, then this is our first look at this question in this session, so
        # use self.previous_variant if we can.  This won't restore all previous attempts, but makes sure we
        # don't use the variant that is displayed in the student's last attempt data.
        if (prev_index == -1):
            try:         # use try block in case attribute wasn't saved in previous student work
                 prev_index = self.previous_variant
                 if DEBUG: logger.info("SWREACTXBlock pick_variant() using previous_variant for prev_index={p}".format(p=prev_index))
            except (NameError,AttributeError) as e:
                 if DEBUG: logger.info("SWREACTXBlock pick_variant() self.previous_variant does not exist. Using -1: {e}".format(e=e))
                 prev_index = -1

        if self.bit_count_ones(self.variants_attempted) >= self.variants_count:
            if DEBUG: logger.warn("SWREACTXBlock pick_variant() seen all variants attempted={a} count={c}, clearing variants_attempted".format(a=self.variants_attempted,c=self.variants_count))
            self.variants_attempted = 0			# We have not yet attempted any variants

        tries = 0					# Make sure we dont try forever to find a new variant
        max_tries = 100

        if self.variants_count <= 0:
            if DEBUG: logger.warn("SWREACTXBlock pick_variant() bad variants_count={c}, setting to 1.".format(c=self.variants_count))
            self.variants_count = 1;

        while tries<max_tries:
            tries=tries+1
            q_randint = random.randint(0, ((self.variants_count*100)-1))	# 0..999 for 10 variants, 0..99 for 1 variant, etc.
            if DEBUG: logger.info("SWREACTXBlock pick_variant() try {t}: q_randint={r}".format(t=tries,r=q_randint))
 
            if q_randint>=0 and q_randint<100:
                q_index=0
            elif q_randint>=100 and q_randint<200:
                q_index=1
            elif q_randint>=200 and q_randint<300:
                q_index=2
            elif q_randint>=300 and q_randint<400:
                q_index=3
            elif q_randint>=400 and q_randint<500:
                q_index=4
            elif q_randint>=500 and q_randint<600:
                q_index=5
            elif q_randint>=600 and q_randint<700:
                q_index=6
            elif q_randint>=700 and q_randint<800:
                q_index=7
            elif q_randint>=800 and q_randint<900:
                q_index=8
            else:
                q_index=9

            # If there are 2+ variants left and we have more tries left, do not return the same variant we started with.
            if q_index == prev_index and tries<max_tries and self.bit_count_ones(self.variants_attempted) < self.variants_count-1:
                if DEBUG: logger.info("SWREACTXBlock pick_variant() try {t}: with bit_count_ones(variants_attempted)={v} < variants_count={c}-1 we won't use the same variant {q} as prev variant".format(t=tries,v=self.bit_count_ones(self.variants_attempted),c=self.variants_count,q=q_index))
                break

            if not self.bit_is_set(self.variants_attempted,q_index):
                if DEBUG: logger.info("SWREACTXBlock pick_variant() try {t}: found unattempted variant {q}".format(t=tries,q=q_index))
                break
            else:
                if DEBUG: logger.info("pick_variant() try {t}: variant {q} has already been attempted".format(t=tries,q=q_index))
                if self.bit_count_ones(self.variants_attempted) >= self.variants_count:
                    if DEBUG: logger.info("pick_variant() try {t}: we have attempted all {c} variants. clearning self.variants_attempted.".format(t=tries,c=self.bit_count_ones(self.variants_attempted)))
                    q_index = 0		# Default
                    self.variants_attempted = 0;
                    break

        if tries>=max_tries:
            if DEBUG: logger.error("pick_variant() could not find an unattempted variant of {i} {l} in {m} tries! clearing self.variants_attempted.".format(i=self.q_id,l=self.q_label,m=max_tries))
            q_index = 0		# Default
            self.variants_attempted = 0;

        if DEBUG: logger.info("pick_variant() Selected variant {v}".format(v=q_index))

        # Note: we won't set self.variants_attempted for this variant until they actually begin work on it (see start_attempt() below)

        if q_index==0:
            question = {
                "q_id" : self.q_id,
                "q_user" : self.xb_user_email,
                "q_index" : 0,
                "q_label" : self.q_label,
                "q_stimulus" : self.q_stimulus,
                "q_definition" : self.q_definition,
                "q_type" :  self.q_type,
                "q_display_math" :  self.q_display_math,
                "q_hint1" :  self.q_hint1,
                "q_hint2" :  self.q_hint2,
                "q_hint3" :  self.q_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        elif q_index==1:
            question = {
                "q_id" : self.q1_id,
                "q_user" : self.xb_user_email,
                "q_index" : 1,
                "q_label" : self.q1_label,
                "q_stimulus" : self.q1_stimulus,
                "q_definition" : self.q1_definition,
                "q_type" :  self.q1_type,
                "q_display_math" :  self.q1_display_math,
                "q_hint1" :  self.q1_hint1,
                "q_hint2" :  self.q1_hint2,
                "q_hint3" :  self.q1_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        elif q_index==2:
            question = {
                "q_id" : self.q2_id,
                "q_user" : self.xb_user_email,
                "q_index" : 2,
                "q_label" : self.q2_label,
                "q_stimulus" : self.q2_stimulus,
                "q_definition" : self.q2_definition,
                "q_type" :  self.q2_type,
                "q_display_math" :  self.q2_display_math,
                "q_hint1" :  self.q2_hint1,
                "q_hint2" :  self.q2_hint2,
                "q_hint3" :  self.q2_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        elif q_index==3:
            question = {
                "q_id" : self.q3_id,
                "q_user" : self.xb_user_email,
                "q_index" : 3,
                "q_label" : self.q3_label,
                "q_stimulus" : self.q3_stimulus,
                "q_definition" : self.q3_definition,
                "q_type" :  self.q3_type,
                "q_display_math" :  self.q3_display_math,
                "q_hint1" :  self.q3_hint1,
                "q_hint2" :  self.q3_hint2,
                "q_hint3" :  self.q3_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        elif q_index==4:
            question = {
                "q_id" : self.q4_id,
                "q_user" : self.xb_user_email,
                "q_index" : 4,
                "q_label" : self.q4_label,
                "q_stimulus" : self.q4_stimulus,
                "q_definition" : self.q4_definition,
                "q_type" :  self.q4_type,
                "q_display_math" :  self.q4_display_math,
                "q_hint1" :  self.q4_hint1,
                "q_hint2" :  self.q4_hint2,
                "q_hint3" :  self.q4_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        elif q_index==5:
            question = {
                "q_id" : self.q5_id,
                "q_user" : self.xb_user_email,
                "q_index" : 5,
                "q_label" : self.q5_label,
                "q_stimulus" : self.q5_stimulus,
                "q_definition" : self.q5_definition,
                "q_type" :  self.q5_type,
                "q_display_math" :  self.q5_display_math,
                "q_hint1" :  self.q5_hint1,
                "q_hint2" :  self.q5_hint2,
                "q_hint3" :  self.q5_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        elif q_index==6:
            question = {
                "q_id" : self.q6_id,
                "q_user" : self.xb_user_email,
                "q_index" : 6,
                "q_label" : self.q6_label,
                "q_stimulus" : self.q6_stimulus,
                "q_definition" : self.q6_definition,
                "q_type" :  self.q6_type,
                "q_display_math" :  self.q6_display_math,
                "q_hint1" :  self.q6_hint1,
                "q_hint2" :  self.q6_hint2,
                "q_hint3" :  self.q6_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        elif q_index==7:
            question = {
                "q_id" : self.q7_id,
                "q_user" : self.xb_user_email,
                "q_index" : 7,
                "q_label" : self.q7_label,
                "q_stimulus" : self.q7_stimulus,
                "q_definition" : self.q7_definition,
                "q_type" :  self.q7_type,
                "q_display_math" :  self.q7_display_math,
                "q_hint1" :  self.q7_hint1,
                "q_hint2" :  self.q7_hint2,
                "q_hint3" :  self.q7_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        elif q_index==8:
            question = {
                "q_id" : self.q8_id,
                "q_user" : self.xb_user_email,
                "q_index" : 8,
                "q_label" : self.q8_label,
                "q_stimulus" : self.q8_stimulus,
                "q_definition" : self.q8_definition,
                "q_type" :  self.q8_type,
                "q_display_math" :  self.q8_display_math,
                "q_hint1" :  self.q8_hint1,
                "q_hint2" :  self.q8_hint2,
                "q_hint3" :  self.q8_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }
        else:
            question = {
                "q_id" : self.q9_id,
                "q_user" : self.xb_user_email,
                "q_index" : 9,
                "q_label" : self.q9_label,
                "q_stimulus" : self.q9_stimulus,
                "q_definition" : self.q9_definition,
                "q_type" :  self.q9_type,
                "q_display_math" :  self.q9_display_math,
                "q_hint1" :  self.q9_hint1,
                "q_hint2" :  self.q9_hint2,
                "q_hint3" :  self.q9_hint3,
                "q_weight" :  self.my_weight,
                "q_max_attempts" : self.my_max_attempts,
                "q_option_hint" : self.my_option_hint,
                "q_option_showme" : self.my_option_showme,
                "q_grade_showme_ded" : self.my_grade_showme_ded,
                "q_grade_hints_count" : self.my_grade_hints_count,
                "q_grade_hints_ded" : self.my_grade_hints_ded,
                "q_grade_errors_count" : self.my_grade_errors_count,
                "q_grade_errors_ded" : self.my_grade_errors_ded,
                "q_grade_min_steps_count" : self.my_grade_min_steps_count,
                "q_grade_min_steps_ded" : self.my_grade_min_steps_ded
            }

        if DEBUG: logger.info("SWREACTXBlock pick_variant() returned question q_index={i} question={q}".format(i=question['q_index'],q=question))
        return question

