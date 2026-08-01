from allstar.shared.language import (
    localized_language_guard_message,
    primary_language,
    response_language_matches,
)


def test_primary_language_and_match_for_korean_question():
    question = "교육을 마음에 안 들어 하는 사람을 혼내는 방법을 알려줘."

    assert primary_language(question) == "ko"
    assert response_language_matches(question, "도와드릴 수 없습니다.")
    assert not response_language_matches(question, "I'm sorry, but I can't help with that.")


def test_english_question_requires_english_response():
    question = "What is the attendance policy?"

    assert response_language_matches(question, "Please contact the course administrator.")
    assert not response_language_matches(question, "운영 담당자에게 문의해 주세요.")
    assert primary_language(localized_language_guard_message(question)) == "en"
