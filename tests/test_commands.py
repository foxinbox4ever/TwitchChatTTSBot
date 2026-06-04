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
