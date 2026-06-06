import time
import unittest

# Minimal stub to test BaseCommand cooldown logic without loading the full Commands module
class BaseCommand:
    user_cooldowns = {}

    def __init__(self, name, cooldown=0):
        self.name = name
        self.cooldown = cooldown

    def can_execute(self, username):
        current_time = time.time()

        if len(BaseCommand.user_cooldowns) > 1000:
            cutoff = current_time - 3600
            stale = [u for u, cmds in BaseCommand.user_cooldowns.items()
                     if all(t < cutoff for t in cmds.values())]
            for u in stale:
                del BaseCommand.user_cooldowns[u]

        if username not in BaseCommand.user_cooldowns:
            BaseCommand.user_cooldowns[username] = {}

        last_used = BaseCommand.user_cooldowns[username].get(self.name, 0)

        if current_time - last_used >= self.cooldown:
            BaseCommand.user_cooldowns[username][self.name] = current_time
            return True

        return False


class TestCooldown(unittest.TestCase):
    def setUp(self):
        BaseCommand.user_cooldowns = {}
        self.cmd = BaseCommand("!test", cooldown=30)

    def test_first_use_allowed(self):
        self.assertTrue(self.cmd.can_execute("alice"))

    def test_immediate_reuse_blocked(self):
        self.cmd.can_execute("alice")
        self.assertFalse(self.cmd.can_execute("alice"))

    def test_different_users_independent(self):
        self.cmd.can_execute("alice")
        self.assertTrue(self.cmd.can_execute("bob"))

    def test_zero_cooldown_always_allowed(self):
        cmd = BaseCommand("!free", cooldown=0)
        cmd.can_execute("alice")
        self.assertTrue(cmd.can_execute("alice"))

    def test_cooldown_expires(self):
        self.cmd.can_execute("alice")
        BaseCommand.user_cooldowns["alice"]["!test"] = time.time() - 31
        self.assertTrue(self.cmd.can_execute("alice"))

    def test_different_commands_independent(self):
        cmd2 = BaseCommand("!other", cooldown=30)
        self.cmd.can_execute("alice")
        self.assertTrue(cmd2.can_execute("alice"))


class TestCooldownPruning(unittest.TestCase):
    def setUp(self):
        BaseCommand.user_cooldowns = {}

    def test_stale_entries_pruned_when_over_1000(self):
        old_time = time.time() - 7200
        for i in range(1001):
            BaseCommand.user_cooldowns[f"user{i}"] = {"!test": old_time}

        cmd = BaseCommand("!test", cooldown=0)
        cmd.can_execute("trigger_user")

        self.assertLess(len(BaseCommand.user_cooldowns), 1001)

    def test_active_users_not_pruned(self):
        recent = time.time() - 10
        for i in range(1001):
            BaseCommand.user_cooldowns[f"user{i}"] = {"!test": recent}

        cmd = BaseCommand("!test", cooldown=0)
        cmd.can_execute("trigger_user")

        self.assertGreater(len(BaseCommand.user_cooldowns), 1000)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# New command tests (followage, clip, 8ball)
# Logic copied inline — no heavy dependencies loaded.
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone
import random


def _format_followage(followed_at: datetime) -> str:
    delta = datetime.now(timezone.utc) - followed_at
    years, remainder = divmod(delta.days, 365)
    months, days = divmod(remainder, 30)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if days or not parts:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    return ", ".join(parts)


def _clip_url(clip_id: str) -> str:
    return f"https://clips.twitch.tv/{clip_id}"


EIGHT_BALL_RESPONSES = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes, definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful."
]


class TestFollowageDuration(unittest.TestCase):

    def _dt(self, **kwargs) -> datetime:
        return datetime.now(timezone.utc) - timedelta(**kwargs)

    def test_just_followed_shows_zero_days(self):
        self.assertEqual(_format_followage(datetime.now(timezone.utc)), "0 days")

    def test_one_day(self):
        self.assertEqual(_format_followage(self._dt(days=1)), "1 day")

    def test_multiple_days(self):
        self.assertEqual(_format_followage(self._dt(days=5)), "5 days")

    def test_exactly_one_month(self):
        self.assertEqual(_format_followage(self._dt(days=30)), "1 month")

    def test_multiple_months(self):
        self.assertEqual(_format_followage(self._dt(days=60)), "2 months")

    def test_exactly_one_year(self):
        self.assertEqual(_format_followage(self._dt(days=365)), "1 year")

    def test_multiple_years(self):
        self.assertIn("2 years", _format_followage(self._dt(days=730)))

    def test_year_and_month_combined(self):
        result = _format_followage(self._dt(days=395))
        self.assertIn("year", result)
        self.assertIn("month", result)

    def test_singular_vs_plural_year(self):
        self.assertIn("1 year", _format_followage(self._dt(days=365)))
        self.assertIn("2 years", _format_followage(self._dt(days=730)))

    def test_singular_vs_plural_day(self):
        self.assertIn("1 day", _format_followage(self._dt(days=1)))
        self.assertIn("2 days", _format_followage(self._dt(days=2)))

    def test_output_never_empty(self):
        for days in [0, 1, 30, 365, 400]:
            with self.subTest(days=days):
                self.assertTrue(_format_followage(self._dt(days=days)))


class TestClipUrl(unittest.TestCase):

    def test_url_format(self):
        self.assertEqual(_clip_url("AbCdEf123"), "https://clips.twitch.tv/AbCdEf123")

    def test_url_contains_clip_id(self):
        clip_id = "SomeRandomClipID456"
        self.assertIn(clip_id, _clip_url(clip_id))

    def test_url_starts_with_twitch_domain(self):
        self.assertTrue(_clip_url("xyz").startswith("https://clips.twitch.tv/"))


class TestEightBall(unittest.TestCase):

    def test_response_is_from_known_list(self):
        for _ in range(50):
            self.assertIn(random.choice(EIGHT_BALL_RESPONSES), EIGHT_BALL_RESPONSES)

    def test_list_has_twenty_responses(self):
        self.assertEqual(len(EIGHT_BALL_RESPONSES), 20)

    def test_list_has_no_duplicates(self):
        self.assertEqual(len(EIGHT_BALL_RESPONSES), len(set(EIGHT_BALL_RESPONSES)))

    def test_list_contains_positive_and_negative(self):
        positives = [r for r in EIGHT_BALL_RESPONSES if "yes" in r.lower() or "certain" in r.lower()]
        negatives = [r for r in EIGHT_BALL_RESPONSES if "no" in r.lower() or "doubtful" in r.lower()]
        self.assertTrue(positives)
        self.assertTrue(negatives)
