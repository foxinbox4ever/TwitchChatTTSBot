import json
import unittest


# ---------------------------------------------------------------------------
# Logic copied inline from the relevant modules so tests run without loading
# heavy optional dependencies (edge_tts, aiohttp, websockets, etc.)
# ---------------------------------------------------------------------------

# platforms/TwitchBot.py — EventSub subscription payload construction
def _build_eventsub_subscription(broadcaster_id: str, session_id: str) -> dict:
    return {
        "type": "channel.follow",
        "version": "2",
        "condition": {
            "broadcaster_user_id": broadcaster_id,
            "moderator_user_id": broadcaster_id
        },
        "transport": {
            "method": "websocket",
            "session_id": session_id
        }
    }


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


# core/TTSObsWebsocket.py — broadcast_message isSub detection
def _is_sub_message(message: str) -> bool:
    return any(
        keyword in message.lower()
        for keyword in ("thank you very much for the sub!", "thank you very much for the gifted sub")
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEventSubSubscription(unittest.TestCase):

    def test_correct_event_type(self):
        sub = _build_eventsub_subscription("123", "sess_abc")
        self.assertEqual(sub["type"], "channel.follow")

    def test_correct_version(self):
        sub = _build_eventsub_subscription("123", "sess_abc")
        self.assertEqual(sub["version"], "2")

    def test_condition_uses_broadcaster_id(self):
        sub = _build_eventsub_subscription("456", "sess_abc")
        self.assertEqual(sub["condition"]["broadcaster_user_id"], "456")
        self.assertEqual(sub["condition"]["moderator_user_id"], "456")

    def test_transport_is_websocket(self):
        sub = _build_eventsub_subscription("123", "sess_abc")
        self.assertEqual(sub["transport"]["method"], "websocket")

    def test_session_id_included(self):
        sub = _build_eventsub_subscription("123", "sess_xyz")
        self.assertEqual(sub["transport"]["session_id"], "sess_xyz")

    def test_payload_is_json_serialisable(self):
        sub = _build_eventsub_subscription("123", "sess_abc")
        self.assertIsInstance(json.dumps(sub), str)


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
