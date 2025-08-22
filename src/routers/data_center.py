from fastapi import APIRouter

from D3Database.data_center.data_reader import DataReader
from D3Database.data_center.i18n import I18N
from D3Database.enums.category_item_enum import CategoryEnum
from src.schemas.data_center import ItemSchemas, ItemTypeSchemas

router = APIRouter(prefix="/data_center")


@router.get("/type_item", response_model=list[ItemTypeSchemas])
def get_type_items(category: CategoryEnum):
    return [
        ItemTypeSchemas(id=type_item.id, name=I18N().name_by_id[type_item.nameId])
        for type_item in DataReader().item_type_by_id.values()
        if type_item.categoryId == category.value
    ]


@router.get("/item", response_model=list[ItemSchemas])
def get_items(type_id: int):
    return [
        ItemSchemas(id=item.id, name=I18N().name_by_id[item.nameId])
        for item in DataReader().item_by_id.values()
        if item.id is not None and item.nameId is not None and item.typeId is type_id
    ]
