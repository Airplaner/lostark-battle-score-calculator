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
REGEX_GEM = re.compile(r"^(\d+)레벨 (멸화|홍염|겁화|작열|광휘)의 보석")

REGEX_BASE_ATTACK_POINT = re.compile(
    r"힘, 민첩, 지능과 무기 공격력을 기반으로 증가한 기본 공격력은 (\d+) 입니다."
)

REGEX_KARMA = re.compile(r"^(\d)랭크 (\d+)레벨$")


@dataclass
class ArkPassiveNode:
    name: str  # 이름
    level: int  # 레벨 (1-5)
    tier: int  # 티어 (1-4)
    desc: str  # 설명


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


class Grade(str, Enum):
    유물 = "유물"
    전설 = "전설"


@dataclass
class Engraving:
    name: str
    ability_stone_level: int
    grade: Grade
    level: int

    @property
    def total_level(self) -> int:
        # 종합 레벨은 어빌리티 스톤 레벨x20 + 각인 활성화 수 + 1
        # ex)전설 10권을 읽어서 2단계 활성화했으면 영웅4 + 전설2 = 6
        total_level = self.ability_stone_level * 20
        if self.grade == Grade.유물:
            total_level += 8
        else:
            total_level += 4
        total_level += self.level

        return total_level


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
    base_attack_point: int  # 기본 공격력
    base_health_point: int  # 최대 생명력
    character_level: int  # 전투 레벨
    engravings: list[Engraving]
    card_sets: list[str]
    gems: list[Gem]
    arkpassive_nodes: dict[Literal["진화", "깨달음", "도약"], list[ArkPassiveNode]]
    karma: dict[Literal["진화", "깨달음", "도약"], tuple[int, int]]  # 랭크, 레벨

    def __init__(self, data: dict):
        self._data = data

        # stat
        """
        캐릭터의 기본 공격력과 최대 생명력
        다만 만찬과 같은 버프로 인해 부정확한 정보가 설정될 수 있다.
        """
        # 기본 공격력, 최대 생명력
        for stat in data["ArmoryProfile"]["Stats"]:
            if stat["Type"] == "공격력":
                for tooltip in stat["Tooltip"]:
                    if matches := re.match(REGEX_BASE_ATTACK_POINT, clean(tooltip)):
                        self.base_attack_point = int(matches.group(1))
                        break

            elif stat["Type"] == "최대 생명력":
                self.base_health_point = int(stat["Value"])

        # level
        """
        캐릭터의 전투 레벨
        """
        self.character_level = data["ArmoryProfile"]["CharacterLevel"]

        # ArmoryEngraving
        """
        캐릭터의 각인
        """
        self.engravings: list[Engraving] = []
        if data["ArmoryEngraving"] is not None:
            for item in data["ArmoryEngraving"]["ArkPassiveEffects"]:
                self.engravings.append(
                    Engraving(
                        name=item["Name"],
                        ability_stone_level=item["AbilityStoneLevel"]
                        if item["AbilityStoneLevel"] is not None
                        else 0,
                        level=item["Level"],
                        grade=item["Grade"],
                    )
                )

        # ArmoryCard
        """
        캐릭터에게 적용 중인 카드 세트 목록
        하나의 카트 세트에 여러 효과가 적용 중인 경우에는 가장 마지막 효과만 가져옵니다.
        ex) 세구빛 30각인 경우 30각 효과만 가져옴
        """
        self.card_sets: list[str] = []
        armory_card = self._data["ArmoryCard"]
        if armory_card is not None:
            for effect in armory_card["Effects"]:
                self.card_sets.append(effect["Items"][-1]["Name"])

        # ArmoryGem
        """
        캐릭터가 장착 중인 보석
        """
        self.gems: list[Gem] = []
        gem_list = data["ArmoryGem"]["Gems"]
        if gem_list:
            for gem in gem_list:
                fullname = clean(gem["Name"])
                print(fullname)
                if matches := re.match(REGEX_GEM, fullname):
                    level = matches.group(1)
                    name = matches.group(2)
                else:
                    raise RuntimeError("보석 이름 파싱 실패")

                self.gems.append(
                    Gem(
                        name=name,
                        level=level,
                        tier=4 if name in ["겁화", "작열", "광휘"] else 3,
                    )
                )

        # ArkPassive
        """
        캐릭터의 모든 아크패시브 노드
        """
        self.arkpassive_nodes: dict[
            Literal["진화", "깨달음", "도약"], list[ArkPassiveNode]
        ] = {
            "진화": [],
            "깨달음": [],
            "도약": [],
        }
        for effect in data["ArkPassive"]["Effects"]:
            group = effect["Name"]
            desc = effect["Description"]
            tier, name, level = self.parse_arkpassive_effect_description(desc)

            self.arkpassive_nodes[group].append(
                ArkPassiveNode(
                    tier=tier,
                    level=level,
                    name=name,
                    desc=desc,
                )
            )

        """
        캐릭터 카르마 정보를 아래와 같은 dict으로 설정
        {
            진화: (랭크, 레벨),
        }
        """
        self.karma = {
            "진화": (0, 0),
            "깨달음": (0, 0),
            "도약": (0, 0),
        }
        for point in data["ArkPassive"]["Points"]:
            karma_type = point["Name"]
            desc = point["Description"]
            if not desc:
                continue

            if matches := re.match(REGEX_KARMA, desc):
                rank, level = int(matches.group(1)), int(matches.group(2))
            else:
                raise RuntimeError("카르마 파싱 실패")
            self.karma[karma_type] = rank, level

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
        matches = re.search(r"(\d+)티어.*?>([가-힣A-Z \.\?\!]+)\sLv\.(\d+)<", str_in)
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
    def battle_stat(self) -> dict[StatType, int]:
        stats = jmespath.search("ArmoryProfile.Stats", self._data)
        result = {}
        for stat in stats:
            result[stat["Type"]] = int(stat["Value"])
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
