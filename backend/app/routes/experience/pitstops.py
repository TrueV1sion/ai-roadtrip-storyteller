from fastapi import APIRouter, HTTPException
from uuid import uuid4

router = APIRouter()

# In-memory storage for pit stops
PITSTOPS: dict[str, dict] = {}


@router.get("/pitstops", tags=["Experience"])
async def list_pitstops():
    """List all pit stop recommendations."""
    try:
        return {"pitstops": list(PITSTOPS.values())}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to list pit stops"
        ) from e


@router.post("/pitstops", tags=["Experience"])
async def create_pitstop(pitstop: dict):
    """
    Create a new pit stop suggestion.
    Expects JSON payload with 'name', 'location', and 'type' fields.
    """
    try:
        name = pitstop.get("name")
        location = pitstop.get("location")
        pit_type = pitstop.get("type")
        if not name or not location or not pit_type:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: name, location, type"
            )
        pitstop_id = str(uuid4())
        new_pitstop = {
            "id": pitstop_id,
            "name": name,
            "location": location,
            "type": pit_type
        }
        PITSTOPS[pitstop_id] = new_pitstop
        return new_pitstop
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to create pit stop"
        ) from e


@router.get("/pitstops/{pitstop_id}", tags=["Experience"])
async def get_pitstop(pitstop_id: str):
    """Get details of a pit stop by ID."""
    try:
        pitstop = PITSTOPS.get(pitstop_id)
        if not pitstop:
            raise HTTPException(
                status_code=404,
                detail="Pit stop not found"
            )
        return pitstop
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error fetching pit stop"
        ) from e


@router.put("/pitstops/{pitstop_id}", tags=["Experience"])
async def update_pitstop(pitstop_id: str, update: dict):
    """
    Update an existing pit stop.
    Accepts JSON payload with fields to update (name, location, type).
    """
    try:
        pitstop = PITSTOPS.get(pitstop_id)
        if not pitstop:
            raise HTTPException(
                status_code=404,
                detail="Pit stop not found"
            )
        name = update.get("name")
        location = update.get("location")
        pit_type = update.get("type")
        if name:
            pitstop["name"] = name
        if location:
            pitstop["location"] = location
        if pit_type:
            pitstop["type"] = pit_type
        PITSTOPS[pitstop_id] = pitstop
        return pitstop
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to update pit stop"
        ) from e


@router.delete("/pitstops/{pitstop_id}", tags=["Experience"])
async def delete_pitstop(pitstop_id: str):
    """Delete a pit stop by ID."""
    try:
        pitstop = PITSTOPS.pop(pitstop_id, None)
        if not pitstop:
            raise HTTPException(
                status_code=404,
                detail="Pit stop not found"
            )
        return {"detail": "Pit stop deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete pit stop"
        ) from e 