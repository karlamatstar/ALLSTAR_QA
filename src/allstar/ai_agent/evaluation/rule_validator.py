from allstar.shared.language import language_mismatch_reason, response_language_matches


def validate_by_rules(
    user_question: str,
    ai_answer: str,
    expected_keyword: str,
) -> dict:
    keywords = [k.strip().lower() for k in expected_keyword.split('|')]
    keyword_found = any(k in ai_answer.lower() for k in keywords)
    language_match = response_language_matches(user_question, ai_answer)
    passed = keyword_found and language_match

    reasons = []
    if keyword_found:
        reasons.append(f"예상 핵심 키워드('{expected_keyword}') 중 하나가 답변에 포함되어 있습니다.")
    else:
        reasons.append(f"예상 핵심 키워드('{expected_keyword}')가 답변에 포함되지 않았습니다.")
    if not language_match:
        reasons.append(language_mismatch_reason(user_question))

    return {
        "keyword_found": keyword_found,
        "language_match": language_match,
        "critical_failure": not language_match,
        "rule_status": "PASS" if passed else "FAIL",
        "rule_reason": " ".join(reasons),
    }
