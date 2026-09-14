import io
import time
from fpdf import FPDF
from app.models.quiz import Quiz, QuizQuestion, QuizAnswer, QuizStatus
from app.models.activity_event import ActivityEvent, ActivityEventType

def make_sample_pdf(pages_text):
    pdf = FPDF()
    for text in pages_text:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(w=0, h=10, text=text)
    return bytes(pdf.output())

def poll_for_ready(client, headers, mat_id, max_wait_sec=10):
    start = time.time()
    while time.time() - start < max_wait_sec:
        res = client.get(f"/materials/{mat_id}", headers=headers)
        if res.status_code == 200 and res.json()["status"] == "ready":
            return res.json()
        time.sleep(0.3)
    res = client.get(f"/materials/{mat_id}", headers=headers)
    return res.json()

def test_start_quiz_without_materials_fails(client, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Empty Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Empty Project"}).json()

    res = client.post(f"/projects/{proj['id']}/quiz/start", headers=user_a_headers, json={"total_questions": 3})
    assert res.status_code == 400
    assert "no processed materials" in res.json()["detail"].lower()

def test_adaptive_quiz_lifecycle(client, db_session, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Computer Science"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Algorithms"}).json()

    # Upload material with distinct concepts
    pdf_bytes = make_sample_pdf([
        "Recursion is a programming technique where a function calls itself directly or indirectly to solve a problem.",
        "Binary search is an efficient algorithm for finding an item from a sorted list of items with logarithmic time complexity.",
        "Dynamic programming solves problems by combining the solutions to subproblems through memoization or tabulation."
    ])
    files = {"file": ("algorithms_intro.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=files)
    mat_id = upload_res.json()["id"]
    poll_for_ready(client, user_a_headers, mat_id)

    # 1. Start Quiz
    start_res = client.post(f"/projects/{proj['id']}/quiz/start", headers=user_a_headers, json={"total_questions": 3})
    assert start_res.status_code == 201
    quiz_data = start_res.json()
    quiz_id = quiz_data["id"]
    assert quiz_data["status"] == "in_progress"
    assert quiz_data["total_questions"] == 3
    assert quiz_data["score"] == 0

    first_q = quiz_data["current_question"]
    assert first_q is not None
    assert "correct_answer" not in first_q  # Security: correct answer is not leaked to client!
    assert len(first_q["options"]) == 4

    # Verify QUIZ_STARTED activity event
    start_event = (
        db_session.query(ActivityEvent)
        .filter(ActivityEvent.event_type == ActivityEventType.QUIZ_STARTED.value)
        .order_by(ActivityEvent.created_at.desc())
        .first()
    )
    assert start_event is not None
    assert start_event.metadata_json["quiz_id"] == quiz_id

    # 2. Answer Question 1 Incorrectly
    db_q1 = db_session.query(QuizQuestion).filter(QuizQuestion.id == first_q["id"]).first()
    wrong_answer = "This is a completely intentionally wrong option."
    ans1_res = client.post(
        f"/projects/{proj['id']}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": first_q["id"], "answer_text": wrong_answer}
    )
    assert ans1_res.status_code == 200
    ans1_data = ans1_res.json()
    assert ans1_data["is_correct"] is False
    assert ans1_data["correct_answer"] == db_q1.correct_answer
    assert "Incorrect" in ans1_data["feedback"]
    assert ans1_data["current_score"] == 0
    assert ans1_data["total_answered"] == 1
    assert ans1_data["is_completed"] is False
    assert ans1_data["next_question"] is not None

    # Duplicate answer attempt rejected
    dup_res = client.post(
        f"/projects/{proj['id']}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": first_q["id"], "answer_text": wrong_answer}
    )
    assert dup_res.status_code == 400
    assert "already been answered" in dup_res.json()["detail"]

    # 3. Answer Question 2 Correctly
    q2 = ans1_data["next_question"]
    db_q2 = db_session.query(QuizQuestion).filter(QuizQuestion.id == q2["id"]).first()
    ans2_res = client.post(
        f"/projects/{proj['id']}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": q2["id"], "answer_text": db_q2.correct_answer}
    )
    assert ans2_res.status_code == 200
    ans2_data = ans2_res.json()
    assert ans2_data["is_correct"] is True
    assert ans2_data["current_score"] == 1
    assert ans2_data["total_answered"] == 2
    assert ans2_data["is_completed"] is False
    assert ans2_data["next_question"] is not None

    # 4. Answer Question 3 Correctly (Final Question)
    q3 = ans2_data["next_question"]
    db_q3 = db_session.query(QuizQuestion).filter(QuizQuestion.id == q3["id"]).first()
    ans3_res = client.post(
        f"/projects/{proj['id']}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": q3["id"], "answer_text": db_q3.correct_answer}
    )
    assert ans3_res.status_code == 200
    ans3_data = ans3_res.json()
    assert ans3_data["is_correct"] is True
    assert ans3_data["current_score"] == 2
    assert ans3_data["total_answered"] == 3
    assert ans3_data["is_completed"] is True
    assert ans3_data["next_question"] is None
    assert ans3_data["summary"] is not None
    assert ans3_data["summary"]["score"] == 2
    assert ans3_data["summary"]["total_questions"] == 3
    assert ans3_data["summary"]["percentage"] == 66.7
    # Question 1 was missed, so its concept must be listed in weak_concepts
    assert db_q1.concept in ans3_data["summary"]["weak_concepts"]

    # Verify QUIZ_COMPLETED activity event
    comp_event = (
        db_session.query(ActivityEvent)
        .filter(ActivityEvent.event_type == ActivityEventType.QUIZ_COMPLETED.value)
        .order_by(ActivityEvent.created_at.desc())
        .first()
    )
    assert comp_event is not None
    assert comp_event.metadata_json["quiz_id"] == quiz_id

    # Answering after completion is rejected
    post_res = client.post(
        f"/projects/{proj['id']}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": q3["id"], "answer_text": "foo"}
    )
    assert post_res.status_code == 400

    # 5. Get Quiz Details
    get_res = client.get(f"/projects/{proj['id']}/quiz/{quiz_id}", headers=user_a_headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["status"] == "completed"
    assert len(detail["answers"]) == 3
    assert detail["summary"]["score"] == 2

    # 6. List Quizzes
    list_res = client.get(f"/projects/{proj['id']}/quiz", headers=user_a_headers)
    assert list_res.status_code == 200
    quizzes = list_res.json()
    assert len(quizzes) >= 1
    assert any(q["id"] == quiz_id for q in quizzes)

def test_quiz_isolation(client, user_a_headers, user_b_headers):
    space_a = client.post("/spaces", headers=user_a_headers, json={"name": "Space A"}).json()
    proj_a = client.post(f"/spaces/{space_a['id']}/projects", headers=user_a_headers, json={"name": "Proj A"}).json()

    pdf_bytes = make_sample_pdf(["Machine learning explores the study and construction of algorithms that can learn from data."])
    files = {"file": ("ml.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj_a['id']}/materials", headers=user_a_headers, files=files)
    poll_for_ready(client, user_a_headers, upload_res.json()["id"])

    # User A starts quiz
    start_res = client.post(f"/projects/{proj_a['id']}/quiz/start", headers=user_a_headers, json={"total_questions": 1})
    quiz_id = start_res.json()["id"]

    # User B cannot view User A's quiz
    assert client.get(f"/projects/{proj_a['id']}/quiz/{quiz_id}", headers=user_b_headers).status_code == 404

    # User B cannot list User A's quizzes
    assert client.get(f"/projects/{proj_a['id']}/quiz", headers=user_b_headers).status_code == 404

    # User B cannot answer User A's quiz
    ans_res = client.post(
        f"/projects/{proj_a['id']}/quiz/{quiz_id}/answer",
        headers=user_b_headers,
        json={"question_id": 1, "answer_text": "test"}
    )
    assert ans_res.status_code == 404

def test_quiz_question_quality_and_no_heading_bias(client, db_session, user_a_headers):
    """
    Verify questions generated from rich material:
    1. Are conceptual and not heading-based (e.g. 'According to the study material on Complete...').
    2. Have exactly 4 distinct options.
    3. Correct answers are placed in random positions (not all at index 0).
    4. Options do not mirror table of contents / chapter titles.
    """
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Python Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Python Core"}).json()

    # Create multi-concept Python material including potential TOC text to test filtering
    content = [
        "Table of Contents\n1. Python Basics Complete Beginner-Friendly Notes\n2. Variables and Types\n3. Loops and Conditionals",
        "Python is an interpreted, high-level, general-purpose programming language commonly used for web development, data science, and automation.",
        "In Python, list indexing is zero-based, meaning the first element is accessed using index 0, and the second element is accessed with index 1.",
        "The range() function in Python, such as range(5), generates a sequence of integers starting from 0 up to 4 (5 is excluded).",
        "A dictionary in Python stores key-value pairs where keys must be immutable objects like strings or numbers.",
        "Functions in Python are defined using the def keyword followed by the function name and parentheses.",
        "In Python, integer division is performed using the // operator, which returns the floor of the division.",
        "The len() function returns the number of items in an object such as a string, list, tuple, or dictionary.",
        "A for loop is used for iterating over a sequence such as a list, tuple, dictionary, set, or string.",
        "Python booleans have two constant values: True and False.",
        "The if-elif-else statement is used in Python for conditional branching and decision making."
    ]
    pdf_bytes = make_sample_pdf(content)
    files = {"file": ("python_comprehensive.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=files)
    poll_for_ready(client, user_a_headers, upload_res.json()["id"])

    # Start 10-question quiz
    start_res = client.post(f"/projects/{proj['id']}/quiz/start", headers=user_a_headers, json={"total_questions": 10})
    assert start_res.status_code == 201
    quiz_data = start_res.json()
    quiz_id = quiz_data["id"]

    # Query all generated questions for this quiz from DB
    questions = db_session.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.order).all()
    assert len(questions) == 10

    positions = []
    forbidden_phrases = [
        "according to the study material on complete",
        "table of contents",
        "which of the following matches the title",
        "which section of the notes",
        "true about chapter",
    ]

    for q in questions:
        q_text = q.question_text.lower()
        # Verify no heading-based patterns
        for phrase in forbidden_phrases:
            assert phrase not in q_text, f"Forbidden phrase '{phrase}' found in question: {q.question_text}"

        # Verify 4 distinct options
        assert len(q.options) == 4
        assert len(set(q.options)) == 4, f"Options not distinct in question: {q.question_text}"

        # Verify correct_answer is in options
        assert q.correct_answer in q.options, f"Correct answer '{q.correct_answer}' not in options {q.options}"

        idx = q.options.index(q.correct_answer)
        positions.append(idx)

    # Verify positions are not all 0 (position bias bug fixed)
    distinct_positions = set(positions)
    assert len(distinct_positions) > 1, f"All correct answers were at index {positions[0]}! Positions: {positions}"
    assert len(distinct_positions) >= 2, f"Expected varied distribution across 0-3, got positions: {positions}"

def test_quiz_answer_evaluation_variants(client, db_session, user_a_headers):
    """
    Test answering questions with text, letter ('A', 'b'), and index ('0', '1').
    """
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Eval Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Eval Proj"}).json()

    pdf_bytes = make_sample_pdf([
        "In Python, list indexing is zero-based, meaning the first element is accessed using index 0.",
        "The len() function returns the number of items in a list or collection.",
        "Functions are defined using the def keyword in Python."
    ])
    files = {"file": ("eval_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj['id']}/materials", headers=user_a_headers, files=files)
    poll_for_ready(client, user_a_headers, upload_res.json()["id"])

    start_res = client.post(f"/projects/{proj['id']}/quiz/start", headers=user_a_headers, json={"total_questions": 3})
    quiz_data = start_res.json()
    quiz_id = quiz_data["id"]

    questions = db_session.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.order).all()

    # Question 1: Answer using letter (e.g. 'A', 'B', 'C', or 'D') corresponding to correct answer
    q1 = questions[0]
    q1_correct_idx = q1.options.index(q1.correct_answer)
    letter = chr(ord('A') + q1_correct_idx)

    ans1_res = client.post(
        f"/projects/{proj['id']}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": q1.id, "answer_text": letter}
    )
    assert ans1_res.status_code == 200
    assert ans1_res.json()["is_correct"] is True

    # Question 2: Answer using exact string
    q2 = questions[1]
    ans2_res = client.post(
        f"/projects/{proj['id']}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": q2.id, "answer_text": q2.correct_answer}
    )
    assert ans2_res.status_code == 200
    assert ans2_res.json()["is_correct"] is True

    # Question 3: Wrong answer returns correct feedback and correct_answer field
    q3 = questions[2]
    wrong_opt = next(opt for opt in q3.options if opt != q3.correct_answer)
    ans3_res = client.post(
        f"/projects/{proj['id']}/quiz/{quiz_id}/answer",
        headers=user_a_headers,
        json={"question_id": q3.id, "answer_text": wrong_opt}
    )
    assert ans3_res.status_code == 200
    assert ans3_res.json()["is_correct"] is False
    assert ans3_res.json()["correct_answer"] == q3.correct_answer
    assert "Incorrect" in ans3_res.json()["feedback"]

def test_quiz_resumption_and_retake_exhaustion(client, db_session, user_a_headers):
    space = client.post("/spaces", headers=user_a_headers, json={"name": "Resumption Space"}).json()
    proj = client.post(f"/spaces/{space['id']}/projects", headers=user_a_headers, json={"name": "Resumption Proj"}).json()
    proj_id = proj["id"]

    pdf_bytes = make_sample_pdf([
        "Functions in Python are defined using the def keyword to encapsulate reusable logic.",
        "A variable is a named container that stores a value in memory so you can use and reuse it later.",
        "The range(1, 4) produces 1, 2, and 3 because the stop value 4 is not included."
    ])
    files = {"file": ("notes.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(f"/projects/{proj_id}/materials", headers=user_a_headers, files=files)
    poll_for_ready(client, user_a_headers, upload_res.json()["id"])

    # 1. Start a quiz with 3 questions
    start1 = client.post(f"/projects/{proj_id}/quiz/start", headers=user_a_headers, json={"total_questions": 3}).json()
    quiz_id1 = start1["id"]
    q1 = start1["current_question"]
    assert q1 is not None

    # Answer Question 1
    db_q1 = db_session.query(QuizQuestion).filter(QuizQuestion.id == q1["id"]).first()
    client.post(f"/projects/{proj_id}/quiz/{quiz_id1}/answer", headers=user_a_headers, json={
        "question_id": q1["id"],
        "answer_text": db_q1.correct_answer
    })

    # 2. Call start_quiz again -> should resume Quiz 1 and return Question 2 (not crash or restart from Q1)
    resume_res = client.post(f"/projects/{proj_id}/quiz/start", headers=user_a_headers, json={"total_questions": 3})
    assert resume_res.status_code == 201
    resumed_data = resume_res.json()
    assert resumed_data["id"] == quiz_id1
    assert resumed_data["current_question"]["id"] != q1["id"]
    assert resumed_data["score"] == 1

    # 3. Answer remaining questions to complete Quiz 1
    q2 = resumed_data["current_question"]
    db_q2 = db_session.query(QuizQuestion).filter(QuizQuestion.id == q2["id"]).first()
    ans2 = client.post(f"/projects/{proj_id}/quiz/{quiz_id1}/answer", headers=user_a_headers, json={
        "question_id": q2["id"],
        "answer_text": db_q2.correct_answer
    }).json()

    q3 = ans2["next_question"]
    db_q3 = db_session.query(QuizQuestion).filter(QuizQuestion.id == q3["id"]).first()
    ans3 = client.post(f"/projects/{proj_id}/quiz/{quiz_id1}/answer", headers=user_a_headers, json={
        "question_id": q3["id"],
        "answer_text": db_q3.correct_answer
    }).json()
    assert ans3["is_completed"] is True

    # 4. Retake quiz on same project (should NOT fail with 400 even though questions already exist)
    retake_res = client.post(f"/projects/{proj_id}/quiz/start", headers=user_a_headers, json={"total_questions": 3})
    assert retake_res.status_code == 201
    retake_data = retake_res.json()
    assert retake_data["id"] != quiz_id1
    assert retake_data["total_questions"] == 3
    assert retake_data["current_question"] is not None

