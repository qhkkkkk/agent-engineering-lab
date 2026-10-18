import json
import unittest

from agent.common.preferences import append_reservation, merge_budget_envelope, preference_namespace
from agent.common.store import ReservedInfo


class PreferencesTests(unittest.TestCase):
    def test_zero_budget_and_missing_history(self):
        self.assertEqual(merge_budget_envelope({}, 0, 1500), {"budget_min": 0, "budget_max": 1500})

    def test_envelope_does_not_shrink_or_destroy_reservations(self):
        original = {"budget_min": 500, "budget_max": 5000, "reserved_info": [{"order_id": "old"}]}
        actual = merge_budget_envelope(original, 1000, 2000)
        self.assertEqual(actual, original)
        actual["reserved_info"].append({"order_id": "new"})
        self.assertEqual(len(original["reserved_info"]), 1)
        wide = merge_budget_envelope(original, 0, 6000)
        self.assertEqual((wide["budget_min"], wide["budget_max"]), (0, 6000))

    def test_booking_only_record_can_gain_budget(self):
        self.assertEqual(merge_budget_envelope({"reserved_info": []}, 0, 1000)["budget_min"], 0)

    def test_append_is_json_serializable_in_both_branches(self):
        booking = ReservedInfo(order_id="demo-order", title="虚构房源", phone_number="demo-phone")
        for old in (None, {}, {"reserved_info": None}, {"budget_min": 0, "reserved_info": []}):
            with self.subTest(old=old):
                new = append_reservation(old, booking)
                self.assertEqual(json.loads(json.dumps(new))["reserved_info"][0]["order_id"], "demo-order")
        old = {"budget_min": 0, "reserved_info": [{"order_id": "first"}]}
        new = append_reservation(old, booking)
        self.assertEqual(len(new["reserved_info"]), 2)
        self.assertEqual(len(old["reserved_info"]), 1)
        self.assertEqual(new["budget_min"], 0)

    def test_namespace_rejects_missing_user(self):
        for context in (None, {}, {"user_id": " "}, {"user_id": None}):
            with self.assertRaises(ValueError):
                preference_namespace(context)
        self.assertEqual(preference_namespace({"user_id": " demo "}), ("demo", "preferences"))


if __name__ == "__main__":
    unittest.main()
