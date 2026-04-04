from typing import Self, Dict, Union, Sequence, Mapping, Any

from fastapi_hypermodel import HALHyperModel as HyperModel, FrozenDict
from fastapi_hypermodel.hal.hal_hypermodel import HALLinkType
from pydantic import model_validator, ConfigDict, Field, model_serializer


class HALHyperModel(HyperModel):
    embedded: Mapping[str, Union[Self, Sequence[Self]]] = Field(default=None, alias="_embedded")

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    @model_validator(mode="after")
    def add_hypermodels_to_embedded(self: Self) -> Self:
        embedded = getattr(self, "embedded", {}) or {}
        new_embedded = dict(embedded)

        for name, field in self:
            if isinstance(field, list):
                key = self.model_fields[name].alias or name
                new_embedded[key] = field

        if new_embedded:
            self.embedded = new_embedded
        return self

    @model_validator(mode="after")
    def build_links(self: Self) -> Self:
        raw_links = getattr(self, "links", None)
        if not raw_links:
            return self

        context = dict(self)

        validated_links: Dict[str, HALLinkType] = {}
        for link_name, link_ in raw_links.items():
            valid_links = self._validate_factory(link_, context)
            if not valid_links:
                continue

            first_link, *_ = valid_links
            validated_links[link_name] = (
                valid_links if isinstance(link_, Sequence) else first_link
            )

        if hasattr(self, "curies") and self.curies():
            validated_links["curies"] = self.curies()

        self.links = FrozenDict(validated_links)
        return self

    @model_serializer(mode='wrap')
    def remove_extra(self, handler) -> Dict[str, Any]:
        data = handler(self)

        if "links" in data:
            data["_links"] = data.pop("links")

        keys_to_remove = [k for k, v in data.items() if isinstance(v, list) and k not in ("_links", "_embedded")]
        for k in keys_to_remove:
            del data[k]

        if "_embedded" in data and not data["_embedded"]:
            del data["_embedded"]

        if "_links" in data:
            if not data["_links"]:
                del data["_links"]
            elif "self" not in data["_links"]:
                data["_links"]["self"] = {"href": "/error/link-failed-to-generate"}

        return data