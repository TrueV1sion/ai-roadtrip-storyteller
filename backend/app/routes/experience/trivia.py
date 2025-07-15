from fastapi import APIRouter, HTTPException
import random


router = APIRouter()


TRIVIA_QUESTIONS = [
    {
        "question": "What is the tallest mountain in the world?",
        "answer": "Mount Everest"
    },
    {
        "question": "What is the capital of France?",
        "answer": "Paris"
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "answer": "Mars"
    }
]


@router.get("/trivia", tags=["Experience"])
async def get_trivia():
    """Return a random trivia question."""
    try:
        trivia = random.choice(TRIVIA_QUESTIONS)
        return {"question": trivia["question"]}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch trivia"
        ) from e


@router.post("/trivia/answer", tags=["Experience"])
async def answer_trivia(answer: dict):
    """
    Submit an answer for a trivia question.
    Expects a JSON payload with 'question' and 'answer' keys.
    """
    try:
        question_text = answer.get("question")
        user_answer = answer.get("answer")
        if not question_text or not user_answer:
            raise HTTPException(
                status_code=400,
                detail="Both 'question' and 'answer' are required"
            )
        correct_entry = next(
            (item for item in TRIVIA_QUESTIONS
             if item["question"] == question_text),
            None
        )
        if correct_entry is None:
            raise HTTPException(
                status_code=404,
                detail="Trivia question not found"
            )
        is_correct = (
            user_answer.strip().lower() ==
            correct_entry["answer"].strip().lower()
        )
        return {"correct": is_correct}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error processing trivia answer"
        ) from e 