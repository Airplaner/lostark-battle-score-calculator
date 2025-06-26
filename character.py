import json
import re
from typing import Any

import jmespath


class CharacterInformation:
    def __init__(self, data: dict):
        self._data = data
        return

    @property
    def base_attack_point(self) -> int:
        """기본 공격력"""
        tooltips: list[str] | None = jmespath.search(
            "ArmoryProfile.Stats[?Type=='공격력'].Tooltip | [0]",
            self._data,
        )
        if tooltips is None:
            raise RuntimeError("기본 공격력 찾기 실패")

        for tooltip in tooltips:
            if (
                "힘, 민첩, 지능과 무기 공격력을 기반으로 증가한 기본 공격력은"
                in tooltip
            ):
                find = re.search(r"<font[^>]*>(\d+)</font>", tooltip)
                if find is not None:
                    return int(find.group(1))
                raise RuntimeError("기본 공격력 찾기 실패")

    @property
    def character_level(self) -> int:
        """전투 레벨"""
        return int(jmespath.search("ArmoryProfile.CharacterLevel", self._data))

    @property
    def weapon_quality(self) -> int | None:
        """무기 품질"""
        # TODO
        # 군단장 무기 부터 품질 100이 추가 피해 30%이라 이 부분 검사 필요
        tooltips = jmespath.search("ArmoryEquipment[?Type=='무기'].Tooltip", self._data)
        if not tooltips:
            return None
            raise ValueError("무기를 장착하지 않았습니다.")

        # 장비 툴팁은 json string이므로 load
        dict_tooltip: dict[str, Any] = json.loads(tooltips[0])
        for element in dict_tooltip:
            if result := jmespath.search("value.qualityValue", dict_tooltip[element]):
                return result

        return None
        raise RuntimeError("무기 품질 찾기 실패")
