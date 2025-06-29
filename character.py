import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, TypeAlias

import jmespath

REGEX_KOREAN = r"[가-힣 ]"
REGEX_TAG = re.compile(r"<[^>]+>")
REGEX_IMAGE_TAG = re.compile(r"(?=<img[^>]*><\/img>)")
REGEX_BR = re.compile(r"<br>", flags=re.IGNORECASE)

# 슬롯 효과 [초월] 7단계 21
REGEX_TRANSCENDENCE = re.compile(r"\[초월\] (\d+)단계 (\d+)")

# [투구] 회심 (투구) Lv.2
# [상의] 공격력 Lv.5
REGEX_ELIXIR_OPTION = re.compile(r"^\[[가-힣]+\] ([가-힣 \(\)]+ Lv\.\d)")

# 8레벨 광휘의 보석
REGEX_GEM = re.compile(r"(\d+)레벨 ([가-힣]+)의 보석")


@dataclass
class ArkPassiveNode:
    name: str
    level: int
    tier: int
    desc: str


class EquipmentType(str, Enum):
    무기 = "무기"
    투구 = "투구"
    상의 = "상의"
    하의 = "하의"
    장갑 = "장갑"
    어깨 = "어깨"
    목걸이 = "목걸이"
    귀걸이 = "귀걸이"
    반지 = "반지"
    팔찌 = "팔찌"


StatType: TypeAlias = Literal["치명", "특화", "제압", "신속", "인내", "숙련"]


def clean(s: str) -> str:
    s = s.replace("<br>", " ")
    s = s.replace("<BR>", " ")
    s = re.sub(REGEX_TAG, "", s)
    return s.strip()


def split_equipment_effects(str_in: str, regex_split=REGEX_IMAGE_TAG) -> list[str]:
    """
    장비 옵션들이 HTML 태그와 함께 뭉쳐진 하나의 문자열로 왔을 때,
    깔끔한 한글로 변환한 뒤 이미지 태그를 기반으로 분리함

    팔찌 효과나 연마 효과는 <br>로 분리할 경우, 두 줄 이상으로 이루어진 옵션이 분리되는 문제가 있음
    ps. 연마 효과는 이미지가 보이진 않아도 greendot이라는 이미지로 분리 중
    """
    result = re.split(regex_split, str_in)
    result = [clean(i) for i in result if i]
    return result


@dataclass
class Equipment:
    name: str = field(init=False)
    equipment_type: EquipmentType = field(init=False)
    base_effects: list[str] = field(default_factory=list)  # 기본 효과
    grinding_effects: list[str] = field(default_factory=list)  # 연마 효과
    bracelet_effects: list[str] = field(default_factory=list)  # 팔찌 효과
    transcendence_level: int | None = None  # 7단계
    transcendence_grade: int | None = None  # 21등급
    elixir_effects: list[str] = field(default_factory=list)  # 엘릭서 효과

    def parse(self, d: dict):
        self.equipment_type = d["Type"]
        self.name = d["Name"]
        self._parse_tooltip(d["Tooltip"])

    def _parse_tooltip(self, str_tooltip: str):
        tooltip: dict = json.loads(str_tooltip)

        for e in tooltip.values():
            if not e:  # null 제외
                continue

            t = e["type"]
            v = e["value"]

            if not v:  # null 제외
                continue

            if t == "ItemPartBox":
                # Element_000에는 효과의 종류 (기본 효과, 연마 효과 등)
                # Element_001에는 효과 내용들
                effect_type = clean(e["value"]["Element_000"])
                effect_desc = e["value"]["Element_001"]
                match effect_type:
                    case "기본 효과":
                        self.base_effects = split_equipment_effects(
                            effect_desc, regex_split=REGEX_BR
                        )
                    case "연마 효과":
                        self.grinding_effects = split_equipment_effects(effect_desc)
                    case "팔찌 효과":
                        self.bracelet_effects = split_equipment_effects(effect_desc)
                    case _:
                        ...
                        # print("이게멀까요?", effect_type)

            elif t == "IndentStringGroup":
                top_str = clean(v["Element_000"]["topStr"])
                if top_str.startswith("슬롯 효과"):
                    top_str = top_str.replace("슬롯 효과", "", 1).strip()

                if top_str.startswith("[초월]"):
                    if matches := re.match(REGEX_TRANSCENDENCE, top_str):
                        self.transcendence_level = int(matches.group(1))
                        self.transcendence_grade = int(matches.group(2))
                    else:
                        raise RuntimeError("초월 추출 실패", top_str)

                elif top_str.startswith("[엘릭서] 지혜의 엘릭서"):
                    for e2 in v["Element_000"]["contentStr"].values():
                        desc = clean(e2["contentStr"])
                        if matches := re.match(REGEX_ELIXIR_OPTION, desc):
                            self.elixir_effects.append(matches.group(1))
                        else:
                            raise RuntimeError("엘릭서 연성 효과 추출 실패", desc)

                elif top_str.startswith("연성 추가 효과"):
                    # TODO
                    ...


@dataclass
class Gem:
    name: str
    tier: int
    level: int


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
        matches = re.search(r"(\d+)티어.*?>([가-힣A-Z \.]+)\sLv\.(\d+)<", str_in)
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
    def arkpassive_nodes(
        self,
    ) -> dict[Literal["진화", "깨달음", "도약"], list[ArkPassiveNode]]:
        """아크패시브 노드"""
        result: dict[str, list] = {
            "진화": [],
            "깨달음": [],
            "도약": [],
        }
        effects = jmespath.search("ArkPassive.Effects", self._data)
        for effect in effects:
            group = effect["Name"]
            desc = effect["Description"]
            tier, name, level = self.parse_arkpassive_effect_description(desc)

            result[group].append(
                ArkPassiveNode(
                    tier=tier,
                    level=level,
                    name=name,
                    desc=desc,
                )
            )

        return result

    def parse_arkpassive_points_description(self, str_in: str) -> tuple[int, int]:
        """
        ArkPassive.Points.Description인 "6랭크 25레벨" 문자열에서
        랭크와 레벨을 파싱하여 반환합니다.
        """
        matches = re.match(r"(\d+)랭크\s(\d+)레벨", str_in)
        if matches:
            return int(matches.group(1)), int(matches.group(2))
        return 0, 0

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
        if not items:
            return []
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

    @property
    def elixir_set(self) -> str | None:
        """
        플레이어의 엘릭서 세트 이름과 단계를 하나의 문자열로 반환합니다.
        ex) 회심 2단계
        """
        elixir_set_name: str | None = None
        elixir_set_level: int | None = None

        equipments = jmespath.search("ArmoryEquipment", self._data)
        for equipment in equipments:
            if equipment["Type"] == "투구" or equipment["Type"] == "장갑":
                matches = re.search(
                    rf"({REGEX_KOREAN}+) \(([12])단계\)", equipment["Tooltip"]
                )
                if matches:
                    elixir_set_name = matches.group(1)
                    elixir_set_level = int(matches.group(2))
                    break

        if elixir_set_name and elixir_set_level:
            return f"{elixir_set_name} {elixir_set_level}단계"
        return

    @property
    def character_class_name(self) -> str:
        """클래스명"""
        return jmespath.search("ArmoryProfile.CharacterClassName", self._data)

    @property
    def equipments(self) -> list[Equipment]:
        result = []

        equipments = jmespath.search("ArmoryEquipment", self._data)
        for equipment in equipments:
            obj_equipment = Equipment()
            obj_equipment.parse(equipment)
            result.append(obj_equipment)

        return result

    @property
    def gems(self) -> list[Gem]:
        gem_list = jmespath.search("ArmoryGem.Gems", self._data)
        if not gem_list:
            return []

        result = []
        for gem in gem_list:
            fullname = clean(gem["Name"])
            if matches := re.match(REGEX_GEM, fullname):
                level = matches.group(1)
                name = matches.group(2)

            result.append(
                Gem(
                    name=name,
                    level=level,
                    tier=4 if name in ["겁화", "작열", "광휘"] else 3,
                )
            )
        return result

    @property
    def battle_stat(self) -> dict[StatType, int]:
        stats = jmespath.search("ArmoryProfile.Stats", self._data)
        result = {}
        for stat in stats:
            result[stat["Type"]] = int(stat["Value"])
        return result

    @property
    def card_sets(self) -> list[str]:
        """
        플레이어에게 적용 중인 카드 세트들의 목록을 가져옵니다.
        하나의 카트 세트에 여러 효과가 적용 중인 경우에는 가장 마지막 효과 가져옵니다.

        세우라제 같은 경우 카드 세트는 두 개입니다.
        """
        armory_card = self._data["ArmoryCard"]
        if armory_card is None:
            return []

        result = []
        for effect in armory_card["Effects"]:
            result.append(effect["Items"][-1]["Name"])

        return result

    @property
    def arkpassive_available_points(
        self,
    ) -> dict[Literal["진화", "깨달음", "도약"], int]:
        result = {}
        if obj_arkpassive := self._data["ArkPassive"]:
            for obj_point in obj_arkpassive["Points"]:
                result[obj_point["Name"]] = obj_point["Value"]

        return result
