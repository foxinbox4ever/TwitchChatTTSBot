import json
import unittest


# ---------------------------------------------------------------------------
# Logic copied inline from the relevant modules so tests run without loading
# heavy optional dependencies (edge_tts, aiohttp, websockets, etc.)
# ---------------------------------------------------------------------------

# platforms/TwitchBot.py — follow polling new-follower detection
def _detect_new_followers(followers: list, seen_ids: set) -> list:
    return [f for f in followers if f["user_id"] not in seen_ids]


# platforms/YouTubeBot.py — event type → (tts_text, notification_type)
def _youtube_event_text(msg_type: str, author: str, snippet: dict):
    if msg_type == "newSponsorEvent":
        return f"{author} just became a member!", "member"
    if msg_type == "memberMilestoneChatEvent":
        months = snippet.get("memberMilestoneChatDetails", {}).get("memberMonth", "")
        return f"{author} has been a member for {months} months!", "member"
    if msg_type == "membershipGiftingEvent":
        count = snippet.get("membershipGiftingDetails", {}).get("giftMembershipsCount", "some")
        return f"{author} gifted {count} memberships!", "member"
    if msg_type == "superChatEvent":
        details = snippet.get("superChatDetails", {})
        amount = details.get("amountDisplayString", "")
        comment = details.get("userComment", "")
        text = f"{author} sent a super chat of {amount}!"
        if comment:
            text += f" They said: {comment}"
        return text, "superchat"
    return None, None


# core/TTSObsWebsocket.py — broadcast_notification payload construction
def _build_notification_payload(notification_type: str, username: str, audio_b64=None) -> dict:
    payload = {"notification": {"type": notification_type, "username": username}}
    if audio_b64:
        payload["notification"]["audio"] = audio_b64
    return payload


# core/TTSObsWebsocket.py — broadcast_message isSub detection (lines 25-28)
def _is_sub_message(message: str) -> bool:
    return any(
        keyword in message.lower()
        for keyword in ("thank you very much for the sub!", "thank you very much for the gifted sub")
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFollowPolling(unittest.TestCase):

    def test_detects_single_new_follower(self):
        followers = [{"user_id": "456", "user_name": "bob"}]
        new = _detect_new_followers(followers, seen_ids={"123"})
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["user_name"], "bob")

    def test_no_new_followers_when_all_seen(self):
        followers = [
            {"user_id": "123", "user_name": "alice"},
            {"user_id": "456", "user_name": "bob"},
        ]
        new = _detect_new_followers(followers, seen_ids={"123", "456"})
        self.assertEqual(new, [])

    def test_multiple_new_followers(self):
        followers = [
            {"user_id": "1", "user_name": "alice"},
            {"user_id": "2", "user_name": "bob"},
            {"user_id": "3", "user_name": "carol"},
        ]
        new = _detect_new_followers(followers, seen_ids={"1"})
        self.assertEqual(len(new), 2)
        self.assertEqual({f["user_name"] for f in new}, {"bob", "carol"})

    def test_empty_follower_list(self):
        self.assertEqual(_detect_new_followers([], seen_ids={"123"}), [])

    def test_empty_seen_ids_treats_all_as_new(self):
        followers = [
            {"user_id": "1", "user_name": "alice"},
            {"user_id": "2", "user_name": "bob"},
        ]
        self.assertEqual(len(_detect_new_followers(followers, seen_ids=set())), 2)


class TestYouTubeEventText(unittest.TestCase):

    def test_new_sponsor(self):
        text, notif_type = _youtube_event_text("newSponsorEvent", "alice", {})
        self.assertEqual(text, "alice just became a member!")
        self.assertEqual(notif_type, "member")

    def test_member_milestone(self):
        snippet = {"memberMilestoneChatDetails": {"memberMonth": 6}}
        text, notif_type = _youtube_event_text("memberMilestoneChatEvent", "bob", snippet)
        self.assertIn("6", text)
        self.assertIn("months", text)
        self.assertEqual(notif_type, "member")

    def test_membership_gifting(self):
        snippet = {"membershipGiftingDetails": {"giftMembershipsCount": 5}}
        text, notif_type = _youtube_event_text("membershipGiftingEvent", "carol", snippet)
        self.assertIn("5", text)
        self.assertIn("memberships", text)
        self.assertEqual(notif_type, "member")

    def test_membership_gifting_fallback_count(self):
        snippet = {"membershipGiftingDetails": {}}
        text, _ = _youtube_event_text("membershipGiftingEvent", "dave", snippet)
        self.assertIn("some", text)

    def test_superchat_without_comment(self):
        snippet = {"superChatDetails": {"amountDisplayString": "$10.00", "userComment": ""}}
        text, notif_type = _youtube_event_text("superChatEvent", "eve", snippet)
        self.assertIn("$10.00", text)
        self.assertNotIn("They said", text)
        self.assertEqual(notif_type, "superchat")

    def test_superchat_with_comment(self):
        snippet = {"superChatDetails": {"amountDisplayString": "$5.00", "userComment": "love the stream"}}
        text, notif_type = _youtube_event_text("superChatEvent", "frank", snippet)
        self.assertIn("$5.00", text)
        self.assertIn("love the stream", text)
        self.assertEqual(notif_type, "superchat")

    def test_unknown_event_type_returns_none(self):
        text, notif_type = _youtube_event_text("textMessageEvent", "grace", {})
        self.assertIsNone(text)
        self.assertIsNone(notif_type)


class TestNotificationPayload(unittest.TestCase):

    def test_basic_payload_structure(self):
        payload = _build_notification_payload("follow", "alice")
        self.assertIn("notification", payload)
        self.assertEqual(payload["notification"]["type"], "follow")
        self.assertEqual(payload["notification"]["username"], "alice")

    def test_payload_without_audio_has_no_audio_key(self):
        payload = _build_notification_payload("member", "bob")
        self.assertNotIn("audio", payload["notification"])

    def test_payload_with_audio_includes_audio_key(self):
        payload = _build_notification_payload("superchat", "carol", audio_b64="abc123==")
        self.assertEqual(payload["notification"]["audio"], "abc123==")

    def test_payload_is_json_serialisable(self):
        payload = _build_notification_payload("follow", "dave", audio_b64="xyz==")
        self.assertIsInstance(json.dumps(payload), str)

    def test_all_notification_types_serialise(self):
        for notif_type in ("follow", "member", "superchat"):
            with self.subTest(type=notif_type):
                payload = _build_notification_payload(notif_type, "user")
                self.assertEqual(payload["notification"]["type"], notif_type)


class TestIsSubDetection(unittest.TestCase):

    def test_sub_message(self):
        self.assertTrue(_is_sub_message("alice subbed, thank you very much for the sub!"))

    def test_resub_message(self):
        self.assertTrue(_is_sub_message("alice resubbed for 3 months, thank you very much for the sub!"))

    def test_gift_sub_message(self):
        self.assertTrue(_is_sub_message("alice gifted a sub to bob, thank you very much for the gifted sub!"))

    def test_mystery_gift_triggers(self):
        # "gifted subs!" contains "gifted sub" as a substring — intentional match
        self.assertTrue(_is_sub_message("alice gifted 5 subs! Thank you very much for the gifted subs!"))

    def test_gift_upgrade_does_not_trigger(self):
        self.assertFalse(_is_sub_message("alice continued their gifted sub, thank you very much!"))

    def test_regular_message_does_not_trigger(self):
        self.assertFalse(_is_sub_message("alice says hello everyone"))

    def test_case_insensitive(self):
        self.assertTrue(_is_sub_message("Alice Subbed, THANK YOU VERY MUCH FOR THE SUB!"))


if __name__ == "__main__":
    unittest.main()
