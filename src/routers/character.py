from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.controllers.character import CharacterController
from src.database import session_local
from src.models.character import CharacterActionEnum
from src.schemas.character import CharacterCreateSchema

router = APIRouter(prefix="/character")


@router.post("")
def create_character(
    payload: CharacterCreateSchema,
    session: Session = Depends(session_local),
):
    return CharacterController.get_or_create_character(session, payload)


@router.patch("/{id}/action")
def patch_character_action(
    id: int,
    action: CharacterActionEnum | None,
    session: Session = Depends(session_local),
):
    return CharacterController.update_action(session, id, action)


@router.get("/mule_accept_bank_ids", response_model=list[int])
def get_mule_accept_bank_ids(server_id: int, session: Session = Depends(session_local)):
    return CharacterController.get_mule_accept_bank_ids(session, server_id)
