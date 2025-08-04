from app.routes.experience.reservations import RESERVATIONS
from app.routes.experience.pitstops import PITSTOPS


def generate_itinerary() -> dict:
    """
    Generate a consolidated itinerary by aggregating
    reservations and pit stops.

    Returns:
        dict: A dictionary containing lists of reservations and pit stops.
    """
    itinerary = {
        "reservations": list(RESERVATIONS.values()),
        "pitstops": list(PITSTOPS.values())
    }
    return itinerary 