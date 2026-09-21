"""Pure answer checks to be hosted outside the agent execution environment."""

import re


def verify_aime(prediction, official_answer):
    """Accept only an integer or a plain 1-3 digit answer string, optionally surrounded by whitespace."""
    if type(official_answer) is not int or not 0 <= official_answer <= 999:
        raise ValueError("Official answer must be an integer in [0,999]")
    if type(prediction) is int:
        value = prediction
    elif isinstance(prediction, str) and re.fullmatch(r"\s*[0-9]{1,3}\s*", prediction):
        value = int(prediction)
    else:
        return False
    return value == official_answer


def verify_place(prediction, expected_place_id, valid_place_ids):
    """Require a canonical exact place ID; alternate names must be resolved before submission."""
    if expected_place_id not in valid_place_ids:
        raise ValueError("Expected place is missing from the frozen scene")
    return isinstance(prediction, str) and prediction == expected_place_id


def verify_code_test_report(report, required_test_ids):
    """Consume a TRUSTED hidden-test runner's result, never a boolean printed by submitted code."""
    if not required_test_ids or len(set(required_test_ids)) != len(required_test_ids):
        raise ValueError("Require unique nonempty hidden test IDs")
    if set(report) != {"runner_completed", "test_results"} or type(report["runner_completed"]) is not bool:
        raise ValueError("Invalid trusted test report")
    results = report["test_results"]
    if set(results) != set(required_test_ids) or any(type(v) is not bool for v in results.values()):
        raise ValueError("Hidden-test report is incomplete or malformed")
    return report["runner_completed"] and all(results.values())
