from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.controllers.utils import get_or_create
from src.models.character import Character, CharacterActionEnum
from src.schemas.character import CharacterCreateSchema


class CharacterController:
    @staticmethod
    def get_or_create_character(
        session: Session, payload: CharacterCreateSchema
    ) -> Character:
        return get_or_create(
            session, Character, id=payload.id, server_id=payload.server_id
        )[0]

    @staticmethod
    def update_action(session: Session, id: int, action: CharacterActionEnum | None):
        character = session.scalar(select(Character).filter(Character.id == id))
        if character is None:
            raise HTTPException(404, f"did not found character {id}")
        character.action = action
        session.commit()

    @staticmethod
    def get_mule_accept_bank_ids(session: Session, server_id: int):
        return session.scalars(
            select(Character.id).where(
                Character.action == CharacterActionEnum.MULE_ACCEPT_BANK,
                Character.server_id == server_id,
            )
        )
