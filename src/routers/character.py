from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.controllers.character import CharacterController
from src.database import session_local
from src.models.character import CharacterActionEnum

router = APIRouter(prefix="/character")


@router.patch("/{id}/action")
def patch_character_action(
    id: int,
    action: CharacterActionEnum | None,
    session: Session = Depends(session_local),
):
    return CharacterController.update_action(session, id, action)


@router.get("/mule_accept_bank_ids", response_model=list[int])
def get_mule_accept_bank_ids(session: Session = Depends(session_local)):
    return CharacterController.get_mule_accept_bank_ids(session)
