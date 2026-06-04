import re
import unittest

# Copied from core/BotTTS.py so tests run without heavy dependencies
SPAM_LINK_KEYWORDS = [
    ".com", "dot com", ".net", "dot net", ".xyz", "dot xyz",
    "http", "www", "discord.gg", "free viewers",
]

_TTS_SLUR_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"n[i1!|][g9q][g9q][e3a4]r",
    r"n[\s\W_]*i[\s\W_]*g[\s\W_]*g[\s\W_]*[ae][\s\W_]*r",
    r"\bnick\s*er",
    r"\bnigg[\s\-_]*h?er\b",
    r"\bf[a4][g9][g9][io0]t",
    r"\bf[\s\W_]*[a4][\s\W_]*g[\s\W_]*g[\s\W_]*[io0][\s\W_]*t",
]]


def _should_block(message):
    msg = message.lower()
    if any(kw in msg for kw in SPAM_LINK_KEYWORDS):
        return True
    if re.search(r"(.)\1{4,}", msg):
        return True
    if re.search(r"(\b\w+\b(?:\s+\b\w+\b){0,4})\s+\1\s+\1", msg):
        return True
    if any(p.search(message) for p in _TTS_SLUR_PATTERNS):
        return True
    return False


class TestSpamFilter(unittest.TestCase):
    def test_allows_normal_message(self):
        self.assertFalse(_should_block("hello how are you"))

    def test_blocks_link(self):
        self.assertTrue(_should_block("check out my stream at twitch.com"))

    def test_blocks_http(self):
        self.assertTrue(_should_block("go to http://example.com"))

    def test_blocks_discord(self):
        self.assertTrue(_should_block("join discord.gg/abc123"))

    def test_blocks_repeated_chars(self):
        self.assertTrue(_should_block("heeeeello"))

    def test_blocks_repeated_phrase(self):
        self.assertTrue(_should_block("buy now buy now buy now"))

    def test_allows_mild_repetition(self):
        self.assertFalse(_should_block("haha that was funny"))


class TestSlurFilter(unittest.TestCase):
    def test_blocks_direct_slur(self):
        self.assertTrue(_should_block("n" + "igger"))

    def test_blocks_leet_substitution(self):
        self.assertTrue(_should_block("n1" + "gg3r"))

    def test_blocks_spaced_slur(self):
        self.assertTrue(_should_block("n i g g " + "e r"))

    def test_blocks_phonetic_variant(self):
        self.assertTrue(_should_block("ni" + "gger"))

    def test_blocks_f_slur(self):
        self.assertTrue(_should_block("f" + "aggot"))

    def test_allows_similar_innocent_word(self):
        self.assertFalse(_should_block("bigger"))
        self.assertFalse(_should_block("trigger"))


if __name__ == "__main__":
    unittest.main()
