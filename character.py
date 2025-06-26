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
                matches = re.search(r"<font[^>]*>(\d+)</font>", tooltip)
                if matches is not None:
                    return int(matches.group(1))
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

    def parse_arkpassive_effect_description(self, str_in: str) -> tuple[int, str, int]:
        """
        `<FONT color='#F1D594'>진화</FONT> 1티어 <FONT color='#F1D594'>특화 Lv.30</FONT>`
        위 문자열에서 아크패시브 티어, 이름, 레벨을 가져옵니다.
        """
        matches = re.search(r"(\d+)티어.*?>([\uAC00-\uD7A3\s]+)\sLv\.(\d+)<", str_in)
        # (\d+)는 숫자 가져오기
        # .*? 는 lazy하게 매칭해서 태그 무시용 >는 태그 닫기까지
        # 이름을 가져오기 위해 한글 (AC00-D7A3)과 공백을 포함하여 매치
        # 하나의 공백 (\s) 이후 Lv 데이터 가져오기
        if matches is not None:
            tier, name, level = (
                int(matches.group(1)),
                str(matches.group(2)),
                int(matches.group(3)),
            )
        else:
            raise ValueError("주어진 문자열이 올바른 포맷이 아닙니다.")
        return tier, name, level

    @property
    def arkpassive_evolution(self) -> int:
        """아크패시브에 소요한 포인트의 수"""
        result = 0
        effects = jmespath.search("ArkPassive.Effects", self._data)
        for effect in effects:
            if effect["Name"] != "진화":
                continue

            desc = effect["Description"]
            tier, name, level = self.parse_arkpassive_effect_description(desc)

            # TODO name에 기반하여 레벨당 사용하는 포인트 계산

            coeff = 0  # level당 포인트
            if tier == 1:
                coeff = 1
            if tier == 2 or tier == 3:
                coeff = 10
            elif tier == 4:
                coeff = 15

            result += level * coeff

        return result
