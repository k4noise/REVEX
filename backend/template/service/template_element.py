import uuid
from typing import Sequence, Any

from template.models.template_element import TemplateElement
from template.repository.template_element import TemplateElementRepository
from template.schemas.template_element import AnyPatch, PatchAction, CreateElementPatch, TemplateElementResponse


class TemplateElementService:
    def __init__(self, repository: TemplateElementRepository):
        self.repository = repository

    async def apply_patches(self, template_id: uuid.UUID, patches: Sequence[AnyPatch]):
        if not patches:
            return

        CORE_COLUMNS = {'id', 'parent_element_id', 'type', 'order', 'data', 'display_mode'}

        ids_to_delete: list[uuid.UUID] = []
        updates_map: dict[uuid.UUID | str, dict[str, Any]] = {}

        temp_id_map: dict[str | uuid.UUID, uuid.UUID] = {}
        create_patches: list[CreateElementPatch] = []

        for patch in patches:
            if patch.action == PatchAction.DELETE:
                ids_to_delete.append(patch.payload.id)

            elif patch.action == PatchAction.UPDATE:
                updates_map[patch.payload.id] = patch.payload.model_dump(exclude_unset=True, exclude={'id'})

            elif patch.action == PatchAction.CREATE:
                real_id = uuid.uuid4() if isinstance(patch.payload.id, str) else patch.payload.id
                temp_id_map[patch.payload.id] = real_id
                create_patches.append(patch)

        elements_to_create = []

        for patch in create_patches:
            payload = patch.payload
            real_id = temp_id_map[payload.id]
            raw_parent_id = payload.parent_element_id
            parent_id = temp_id_map.get(raw_parent_id, raw_parent_id) if raw_parent_id else None
            full_data = payload.model_dump(by_alias=False)

            data_value = full_data.get('data')
            properties = {
                k: v for k, v in full_data.items()
                if k not in CORE_COLUMNS and k != 'parentElementId'
            }

            elements_to_create.append({
                "id": real_id,
                "template_id": template_id,
                "parent_element_id": parent_id,
                "type": payload.type.value,
                "order": payload.order,
                "data": data_value,
                "display_mode": payload.display_mode.value if payload.display_mode else None,
                "properties": properties
            })

        if ids_to_delete:
            await self.repository.bulk_delete(template_id, ids_to_delete)

        if elements_to_create:
            await self.repository.bulk_create_raw(elements_to_create)

        if updates_map:
            await self.repository.bulk_update_from_map(template_id, updates_map)

    def build_tree(self, db_elements: Sequence[TemplateElement]) -> list[TemplateElementResponse]:
        if not db_elements:
            return []

        nodes_map: dict[uuid.UUID, TemplateElementResponse] = {
            el.id: TemplateElementResponse.from_db(el)
            for el in db_elements
        }

        tree: list[TemplateElementResponse] = []

        for el in db_elements:
            current_node = nodes_map[el.id]
            if el.parent_element_id:
                parent_node = nodes_map.get(el.parent_element_id)
                if parent_node:
                    parent_node.children.append(current_node)
                else:
                    tree.append(current_node)
            else:
                tree.append(current_node)

        return tree

    async def get_media_keys(self, template_id: uuid.UUID) -> list[str]:
        elements = await self.repository.get_all_by_template(template_id)
        return [
            el.properties["media_key"]
            for el in elements
            if el.properties and "media_key" in el.properties
        ]