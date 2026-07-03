PEN_UNPLACED = 1_000_000_000

PEN_LATE_LAST = 1 # Base penalty for scheduling an activity in the last time slot of the day.
PEN_LATE_COURSE_MASTER = 1 # Master's courses may still be placed late, but earlier is preferred.

PEN_LATE_LAB_SEM_MASTER = 2 # Master's lab/sem late placement is mildly discouraged.
PEN_PAIR_GROUP_DIFFERENT_ROOM = 2 # Penalty applied when paired 1h odd/even activities use different rooms.

PEN_LATE_LAB_SEM_BACHELOR = 3 # Bachelor lab/sem in the last interval is undesirable, but less important than courses.
PEN_MIXED_PARITY_PAIR_SY = 5 # Penalty applied when a study year has mixed activity types  across odd and even weeks in the same time slot.
PEN_LATE_COURSE_BACHELOR = 6 # Bachelor courses in the last interval are clearly undesirable.

PEN_ROOM_SINGLE_PARITY_ONE_HOUR = 10 # Penalty when a room-time cell hosts only one parity of 1-hour activities instead of using the free parity too.

PEN_TEACHER_COURSE_OVERLOAD_PER_DAY = 30 # Penalty applied for each hour exceeding the maximum allowed COURSE hours per day for a teacher.
PEN_STUDENT_COURSE_OVERLOAD_PER_DAY = 35 # Penalty applied for each hour exceeding the maximum allowed COURSE hours per day for a study year.
PEN_STUDENT_TOTAL_OVERLOAD_PER_DAY  = 40 # Penalty applied for each hour exceeding the maximum allowed TOTAL hours per day for a study year.
PEN_TEACHER_TOTAL_OVERLOAD_PER_DAY  = 45 # Penalty applied for each hour exceeding the maximum allowed TOTAL teaching hours per day for a teacher.

PEN_GROUP_WEEK_PARITY_IMBALANCE = 50 # Penalty for imbalance between odd/even 1h group activities inside the same study-year group.
PEN_MIXED_PARITY_PAIR_GROUP = 60 # Penalty applied when a student group has mixed activity types (course and lab/ sem) across odd and even weeks in the same time slot.

PEN_STUDENT_EXTRA_GAP = 100 # Penalty applied for each idle gap beyond the first acceptable one inside a student's day.
PEN_TEACHER_EXTRA_GAP = 100 # Penalty applied for each idle gap beyond the first acceptable one inside a teacher's day.
PEN_PREFERRED_ROW_MISSED = 100

PEN_STUDENT_WIDE_SPAN = 250 # Penalty applied when a student's teaching day becomes too fragmented.
PEN_TEACHER_WIDE_SPAN = 250 # Penalty applied when a teacher's teaching day becomes too fragmented.
PEN_TEACHER_TOO_MANY_DAYS = 250 # Penalty applied when a teacher teaches on more days than necessary.
PEN_ONSITE_ONLINE_NO_PAUSE = 250 # Penalty when onsite and online activities are adjacent with no module pause between them.
PEN_MANDATORY_ROW_MISSED = 250

PEN_BACHELOR_THIRD_YEAR_MODULES_DAY_OVER_LIMIT = 400 # Strong penalty when bachelor 3rd-year modules are spread across more than 4 days.
PEN_ILLEGAL_PACK_OVERLAP = 500 # Very strong penalty when overlapping student-visible modules are not from the same optional pack.
PEN_BACHELOR_THIRD_YEAR_COURSE_DAY_OVER_LIMIT = 500 # Strong penalty when bachelor 3rd-year courses are spread across more than 4 days.
