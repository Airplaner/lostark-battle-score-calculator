import json
import re
from typing import Any, Literal

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

    def arkpassive_points(
        self,
        arkpassive_type: Literal["진화", "깨달음", "도약"],
    ) -> int:
        """아크패시브에 소요한 포인트의 수"""
        result = 0
        effects = jmespath.search("ArkPassive.Effects", self._data)
        for effect in effects:
            if effect["Name"] != arkpassive_type:
                continue

            desc = effect["Description"]
            tier, name, level = self.parse_arkpassive_effect_description(desc)

            coeff = 0  # level당 포인트

            # TODO name에 기반하여 레벨당 사용하는 포인트 계산
            if arkpassive_type == "진화":
                if tier == 1:
                    coeff = 1
                if tier == 2 or tier == 3:
                    coeff = 10
                elif tier == 4:
                    coeff = 15

            result += level * coeff

        return result

    @property
    def arkpassive_evolution(self) -> int:
        return self.arkpassive_points("진화")

    @property
    def arkpassive_enlightment(self) -> int:
        return self.arkpassive_points("깨달음")

    @property
    def arkpassive_leap(self) -> int:
        return self.arkpassive_points("도약")

    def parse_arkpassive_points_description(self, str_in: str) -> tuple[int, int]:
        """
        ArkPassive.Points.Description인 "6랭크 25레벨" 문자열에서
        랭크와 레벨을 파싱하여 반환합니다.
        """
        matches = re.match(r"(\d+)랭크\s(\d+)레벨", str_in)
        if matches:
            return int(matches.group(1)), int(matches.group(2))

    @property
    def karma_evolutionrank(self) -> int:
        points = jmespath.search("ArkPassive.Points", self._data)
        for point in points:
            if point["Name"] == "진화":
                rank, level = self.parse_arkpassive_points_description(
                    point["Description"]
                )
                return rank

        raise RuntimeError("진화 카르마 랭크를 찾을 수 없습니다.")

    @property
    def karma_leaplevel(self) -> int:
        points = jmespath.search("ArkPassive.Points", self._data)
        for point in points:
            if point["Name"] == "도약":
                rank, level = self.parse_arkpassive_points_description(
                    point["Description"]
                )
                return level

        raise RuntimeError("도약 카르마 레벨을 찾을 수 없습니다.")

    @property
    def engravings(self) -> list[tuple[str, int]]:
        """
        플레이어의 모든 각인을 (이름, 종합 레벨) tuple의 list로 반환합니다.
        """
        items = jmespath.search("ArmoryEngraving.ArkPassiveEffects", self._data)
        result = list()

        for item in items:
            # 종합 레벨은 어빌리티 스톤 레벨x20 + 각인 활성화 수 + 1
            # ex)전설 10권을 읽어서 2단계 활성화했으면 영웅4 + 전설2 = 6
            total_level = 1

            ability_stone_level = item["AbilityStoneLevel"]
            if ability_stone_level is None:
                ability_stone_level = 0
            else:
                ability_stone_level = int(ability_stone_level)
            total_level += 20 * ability_stone_level

            grade = str(item["Grade"])
            level = int(item["Level"])
            name = str(item["Name"])

            total_level += level
            if grade == "전설":
                total_level += 4
            elif grade == "유물":
                total_level += 8

            result.append((name, total_level))

        return result
