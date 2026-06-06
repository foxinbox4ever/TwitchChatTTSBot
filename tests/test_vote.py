import re
import unittest


# ---------------------------------------------------------------------------
# Logic copied inline from the relevant modules so tests run without loading
# heavy optional dependencies.
# ---------------------------------------------------------------------------

# core/Commands.py — VoteCommand option parsing (lines 408-410)
def _parse_vote(message_after_vote: str):
    """Split 'Question? 1.OptionA 2.OptionB' into (question, [options]).
    Returns (None, None) if no '?' found."""
    if '?' not in message_after_vote:
        return None, None
    question, options_str = message_after_vote.split('?', 1)
    options = re.findall(r'\d+\.(.*?)(?=\s*\d+\.|$)', options_str.strip())
    options = [opt.strip() for opt in options if opt.strip()]
    return question.strip(), options


# core/Commands.py — vote aggregation used in handle_vote_response (lines 494-498)
def _aggregate_votes(vote_responses: dict, num_options: int) -> list:
    """Count votes per option. Returns a list where index i = votes for option i+1."""
    results = {}
    for vote in vote_responses.values():
        results[vote] = results.get(vote, 0) + 1
    return [results.get(i + 1, 0) for i in range(num_options)]


# core/Commands.py — result formatting used in handle_end_of_vote (lines 525-531)
def _format_vote_results(question: str, options: list, vote_responses: dict) -> str:
    results = {}
    for vote in vote_responses.values():
        results[vote] = results.get(vote, 0) + 1
    lines = [f"{i + 1}. {opt}: {results.get(i + 1, 0)} votes" for i, opt in enumerate(options)]
    return f"🗳️ Final vote results for '{question}': " + " | ".join(lines)


# core/Commands.py — Twitch poll payload construction (lines 545-550)
def _build_poll_payload(broadcaster_id: str, question: str, options: list, duration: int = 60) -> dict:
    return {
        "broadcaster_id": broadcaster_id,
        "title": question.strip()[:60],
        "choices": [{"title": opt[:25]} for opt in options[:5]],
        "duration": duration,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVoteOptionParsing(unittest.TestCase):

    def test_two_options(self):
        q, opts = _parse_vote("Who wins? 1.Alice 2.Bob")
        self.assertEqual(q, "Who wins")
        self.assertEqual(opts, ["Alice", "Bob"])

    def test_three_options(self):
        _, opts = _parse_vote("Pick a colour? 1.Red 2.Green 3.Blue")
        self.assertEqual(opts, ["Red", "Green", "Blue"])

    def test_question_text_preserved(self):
        q, _ = _parse_vote("What should I play next? 1.DBD 2.Minecraft")
        self.assertEqual(q, "What should I play next")

    def test_options_with_spaces_in_name(self):
        _, opts = _parse_vote("Favourite game? 1.Dead by Daylight 2.Among Us")
        self.assertEqual(opts, ["Dead by Daylight", "Among Us"])

    def test_extra_whitespace_stripped(self):
        _, opts = _parse_vote("Who?  1.Alice   2.Bob  ")
        self.assertEqual(opts, ["Alice", "Bob"])

    def test_no_question_mark_returns_none(self):
        q, opts = _parse_vote("Who wins 1.Alice 2.Bob")
        self.assertIsNone(q)
        self.assertIsNone(opts)

    def test_only_one_option_parsed(self):
        _, opts = _parse_vote("Solo? 1.Only")
        self.assertEqual(opts, ["Only"])
        self.assertLess(len(opts), 2)  # would be rejected by the command

    def test_five_options(self):
        _, opts = _parse_vote("Pick? 1.A 2.B 3.C 4.D 5.E")
        self.assertEqual(len(opts), 5)
        self.assertEqual(opts[4], "E")

    def test_question_mark_in_question_splits_on_first(self):
        # "Really?? 1.Yes 2.No" — splits on first '?', options come after
        q, opts = _parse_vote("Really?? 1.Yes 2.No")
        self.assertEqual(q, "Really")
        self.assertEqual(opts, ["Yes", "No"])


class TestVoteAggregation(unittest.TestCase):

    def test_unanimous_vote(self):
        responses = {"alice": 1, "bob": 1, "carol": 1}
        counts = _aggregate_votes(responses, num_options=2)
        self.assertEqual(counts, [3, 0])

    def test_split_vote(self):
        responses = {"alice": 1, "bob": 2}
        counts = _aggregate_votes(responses, num_options=2)
        self.assertEqual(counts, [1, 1])

    def test_no_votes_all_zeros(self):
        counts = _aggregate_votes({}, num_options=3)
        self.assertEqual(counts, [0, 0, 0])

    def test_later_vote_overrides_earlier(self):
        # dict only keeps last value — same user voting twice keeps their latest choice
        responses = {"alice": 2}  # alice changed from 1 to 2
        counts = _aggregate_votes(responses, num_options=2)
        self.assertEqual(counts, [0, 1])

    def test_count_length_matches_num_options(self):
        responses = {"alice": 1}
        counts = _aggregate_votes(responses, num_options=4)
        self.assertEqual(len(counts), 4)

    def test_three_way_vote(self):
        responses = {"alice": 1, "bob": 2, "carol": 3, "dave": 2}
        counts = _aggregate_votes(responses, num_options=3)
        self.assertEqual(counts, [1, 2, 1])


class TestVoteResultFormatting(unittest.TestCase):

    def test_basic_result(self):
        result = _format_vote_results(
            "Who wins?",
            ["Alice", "Bob"],
            {"alice": 1, "bob": 2, "carol": 1}
        )
        self.assertIn("Alice: 2 votes", result)
        self.assertIn("Bob: 1 votes", result)

    def test_question_included_in_output(self):
        result = _format_vote_results("Best game?", ["DBD", "Minecraft"], {})
        self.assertIn("Best game?", result)

    def test_option_with_zero_votes(self):
        result = _format_vote_results("Pick?", ["A", "B"], {"alice": 1})
        self.assertIn("B: 0 votes", result)

    def test_options_separated_by_pipe(self):
        result = _format_vote_results("Pick?", ["A", "B"], {})
        self.assertIn(" | ", result)

    def test_numbering_starts_at_one(self):
        result = _format_vote_results("Pick?", ["Alpha", "Beta"], {})
        self.assertIn("1. Alpha", result)
        self.assertIn("2. Beta", result)

    def test_no_votes_still_formats(self):
        result = _format_vote_results("Pick?", ["Yes", "No"], {})
        self.assertIn("Yes: 0 votes", result)
        self.assertIn("No: 0 votes", result)


class TestTwitchPollPayload(unittest.TestCase):

    def test_basic_payload(self):
        payload = _build_poll_payload("123", "Best game?", ["DBD", "Minecraft"])
        self.assertEqual(payload["broadcaster_id"], "123")
        self.assertEqual(payload["title"], "Best game?")
        self.assertEqual(payload["duration"], 60)

    def test_question_truncated_to_60_chars(self):
        long_question = "A" * 70
        payload = _build_poll_payload("123", long_question, ["A", "B"])
        self.assertEqual(len(payload["title"]), 60)

    def test_question_within_60_chars_not_truncated(self):
        question = "Short question?"
        payload = _build_poll_payload("123", question, ["A", "B"])
        self.assertEqual(payload["title"], question)

    def test_option_truncated_to_25_chars(self):
        long_option = "X" * 30
        payload = _build_poll_payload("123", "Q?", [long_option, "B"])
        self.assertEqual(len(payload["choices"][0]["title"]), 25)

    def test_options_capped_at_five(self):
        options = ["A", "B", "C", "D", "E", "F", "G"]
        payload = _build_poll_payload("123", "Q?", options)
        self.assertEqual(len(payload["choices"]), 5)

    def test_fewer_than_five_options_all_included(self):
        options = ["A", "B", "C"]
        payload = _build_poll_payload("123", "Q?", options)
        self.assertEqual(len(payload["choices"]), 3)

    def test_choices_format(self):
        payload = _build_poll_payload("123", "Q?", ["Yes", "No"])
        self.assertEqual(payload["choices"], [{"title": "Yes"}, {"title": "No"}])

    def test_question_whitespace_stripped(self):
        payload = _build_poll_payload("123", "  Padded?  ", ["A", "B"])
        self.assertFalse(payload["title"].startswith(" "))
        self.assertFalse(payload["title"].endswith(" "))


if __name__ == "__main__":
    unittest.main()
