from fastapi import APIRouter, HTTPException
import random


router = APIRouter()


GAMES = [
    {
        "name": "Guess the Landmark",
        "prompt": "I am thinking of a famous landmark. Guess which one it is.",
        "answer": "Eiffel Tower"
    },
    {
        "name": "20 Questions",
        "prompt": (
            "Think of an object. I will try to guess it by asking 20 "
            "questions!"
        ),
        "answer": "interactive game"
    }
]


@router.get("/", tags=["Experience"])
async def get_game():
    """Return a random game prompt."""
    try:
        game = random.choice(GAMES)
        return {
            "name": game["name"],
            "prompt": game["prompt"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch game prompt"
        ) from e


@router.post("/answer", tags=["Experience"])
async def answer_game(answer: dict):
    """
    Submit an answer for a game.
    Expects a JSON payload with 'name' and 'answer' keys.
    """
    try:
        game_name = answer.get("name")
        user_answer = answer.get("answer")
        if not game_name or not user_answer:
            raise HTTPException(
                status_code=400,
                detail="Both 'name' and 'answer' are required"
            )
        correct_game = next(
            (
                game
                for game in GAMES
                if game["name"] == game_name
            ),
            None
        )
        if correct_game is None:
            raise HTTPException(
                status_code=404,
                detail="Game not found"
            )
        is_correct = (
            user_answer.strip().lower() ==
            correct_game["answer"].strip().lower()
        )
        return {"correct": is_correct}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error processing game answer"
        ) from e 