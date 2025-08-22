from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.character import Character, CharacterActionEnum
from src.schemas.character import CharacterCreateSchema


class CharacterController:
    @staticmethod
    def get_or_create_character(session: Session, payload: CharacterCreateSchema):
        does_already_exist = (
            session.query(Character.id).filter(Character.id == payload.id).first()
        )
        if does_already_exist is not None:
            return
        session.add(Character(id=payload.id, server_id=payload.server_id))
        session.commit()

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
