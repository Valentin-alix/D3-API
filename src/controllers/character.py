from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.models.character import Character, CharacterActionEnum


class CharacterController:
    @staticmethod
    def update_action(session: Session, id: int, action: CharacterActionEnum | None):
        session.execute(
            update(Character).where(Character.id == id).values(action=action)
        )
        session.commit()

    @staticmethod
    def get_mule_accept_bank_ids(session: Session):
        return session.scalars(
            select(Character.id).where(
                Character.action == CharacterActionEnum.MULE_ACCEPT_BANK
            )
        )
