import json
import re
from dataclasses import dataclass, field
from enum import Enum, StrEnum
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

# 연성 추가 효과 칼날 방패 (2단계)
REGEX_ELIXIR_SET = re.compile("연성 추가 효과 ([가-힣 ]+) \((1|2)단계\)")

# 8레벨 광휘의 보석
REGEX_GEM = re.compile(r"^(\d+)레벨 (멸화|홍염|겁화|작열|광휘)의 보석")

REGEX_BASE_ATTACK_POINT = re.compile(
    r"힘, 민첩, 지능과 무기 공격력을 기반으로 증가한 기본 공격력은 (\d+) 입니다."
)

REGEX_KARMA = re.compile(r"^(\d)랭크 (\d+)레벨$")
KARMA_NOT_OPEN = "미개방"

# 진화 1티어 특화 Lv.30
REGEX_ARKPASSIVE_NODE = re.compile(r"(\d)티어 ([가-힣A-Z \.\?\!]+) Lv\.(\d+)$")


@dataclass
class ArkPassiveNode:
    name: str  # 이름
    level: int  # 레벨 (1-5)
    tier: int  # 티어 (1-4)
    desc: str  # 설명


class EquipmentType(StrEnum):
    NA = ("NA", "NA")
    무기 = ("무기", "무기")
    투구 = ("투구", "방어구")
    상의 = ("상의", "방어구")
    하의 = ("하의", "방어구")
    장갑 = ("장갑", "방어구")
    어깨 = ("어깨", "방어구")
    목걸이 = ("목걸이", "장신구")
    귀걸이 = ("귀걸이", "장신구")
    반지 = ("반지", "장신구")
    팔찌 = ("팔찌", "팔찌")

    def __new__(cls, value: str, category: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.category = category
        return obj


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
        total_level = self.ability_stone_level * 20 + 1
        if self.grade == Grade.유물:
            total_level += 8
        else:
            total_level += 4
        total_level += self.level

        return total_level


BattleStatType: TypeAlias = Literal["치명", "특화", "제압", "신속", "인내", "숙련"]
VALID_BATTLE_STAT_TYPE = {"치명", "특화", "제압", "신속", "인내", "숙련"}


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
    raw_data: dict | None = field(default=None, repr=False)
    name: str = ""
    equipment_type: EquipmentType = field(default=EquipmentType.NA)
    quality: int = -1  # 품질이 없는 어빌스톤, 팔찌 등
    base_effects: list[str] = field(default_factory=list)  # 기본 효과
    additional_effects: list[str] = field(default_factory=list)  # 추가 효과
    grinding_effects: list[str] = field(default_factory=list)  # 연마 효과
    bracelet_effects: list[str] = field(default_factory=list)  # 팔찌 효과
    transcendence_level: int | None = None  # 초월 단계 (7)
    transcendence_grade: int | None = None  # 초월 등급 (21)
    elixir_effects: list[str] = field(default_factory=list)  # 엘릭서 효과
    elixir_set: tuple[str, int] | None = None

    def __post_init__(self):
        if self.raw_data:
            self.name = self.raw_data["Name"]
            self.equipment_type = self.raw_data["Type"]
            self._parse_tooltip(self.raw_data["Tooltip"])

    def _parse_tooltip(self, str_tooltip: str):
        tooltip: dict = json.loads(str_tooltip)

        for e in tooltip.values():
            if not e:  # null 제외
                continue

            t, v = e["type"], e["value"]

            if not v:  # null 제외
                continue

            if t == "ItemTitle":
                self.quality = int(v["qualityValue"])

            elif t == "ItemPartBox":
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
                    case "추가 효과":
                        self.additional_effects = split_equipment_effects(effect_desc)
                    case _:
                        ...
                        # print("이게멀까요?", effect_type)

            elif t == "IndentStringGroup":
                top_str = clean(v["Element_000"]["topStr"])
                if top_str.startswith("슬롯 효과"):
                    top_str = top_str.replace("슬롯 효과", "", 1).strip()

                if top_str.startswith("[초월]"):
                    if matches := REGEX_TRANSCENDENCE.match(top_str):
                        self.transcendence_level = int(matches.group(1))
                        self.transcendence_grade = int(matches.group(2))
                    else:
                        raise RuntimeError("초월 추출 실패", top_str)

                elif top_str.startswith("[엘릭서] 지혜의 엘릭서"):
                    for e2 in v["Element_000"]["contentStr"].values():
                        desc = clean(e2["contentStr"])
                        if matches := REGEX_ELIXIR_OPTION.match(desc):
                            self.elixir_effects.append(matches.group(1))
                        else:
                            raise RuntimeError("엘릭서 연성 효과 추출 실패", desc)

                elif top_str.startswith("연성 추가 효과"):
                    if matches := REGEX_ELIXIR_SET.match(top_str):
                        self.elixir_set = matches.group(1), int(matches.group(2))
                    else:
                        raise RuntimeError("엘릭서 연성 추가 효과 파싱 실패", top_str)


@dataclass
class Gem:
    name: str
    tier: int
    level: int


class CharacterInformation:
    base_attack_point: int  # 기본 공격력
    base_health_point: int  # 최대 생명력
    character_level: int  # 전투 레벨
    character_class_name: str
    engravings: list[Engraving]
    card_sets: list[str]
    gems: list[Gem]
    arkpassive_nodes: dict[Literal["진화", "깨달음", "도약"], list[ArkPassiveNode]]
    karma: dict[Literal["진화", "깨달음", "도약"], tuple[int, int]]  # 랭크, 레벨
    battle_stat: dict[BattleStatType, int]
    equipments: list[Equipment]

    def __init__(self, data: dict):
        self._data = data

        #################
        # ArmoryProfile #
        #################
        """
        캐릭터의 기본 공격력, 최대 생명력, 스탯
        다만 만찬과 같은 버프로 인해 부정확한 정보가 설정될 수 있다.
        """
        # 기본 공격력, 최대 생명력
        self.battle_stat = {}
        for stat in data["ArmoryProfile"]["Stats"]:
            stat_type = stat["Type"]
            if stat_type == "공격력":
                for tooltip in stat["Tooltip"]:
                    if matches := REGEX_BASE_ATTACK_POINT.match(clean(tooltip)):
                        self.base_attack_point = int(matches.group(1))
                        break

            elif stat_type == "최대 생명력":
                self.base_health_point = int(stat["Value"])

            elif stat_type in VALID_BATTLE_STAT_TYPE:
                self.battle_stat[stat_type] = int(stat["Value"])

        """
        캐릭터의 전투 레벨
        """
        self.character_level = data["ArmoryProfile"]["CharacterLevel"]

        """
        캐릭터의 직업
        """
        self.character_class_name = data["ArmoryProfile"]["CharacterClassName"]

        ###################
        # ArmoryEquipment #
        ###################
        """
        캐릭터의 모든 장비
        """
        self.equipments: list[Equipment] = []

        for equipment in data["ArmoryEquipment"]:
            obj_equipment = Equipment(raw_data=equipment)
            self.equipments.append(obj_equipment)

        ###################
        # ArmoryEngraving #
        ###################
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

        ##############
        # ArmoryCard #
        ##############
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

        #############
        # ArmoryGem #
        #############
        """
        캐릭터가 장착 중인 보석
        """
        self.gems: list[Gem] = []
        gem_list = data["ArmoryGem"]["Gems"]
        if gem_list:
            for gem in gem_list:
                fullname = clean(gem["Name"])
                if matches := REGEX_GEM.match(fullname):
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

        ##############
        # ArkPassive #
        ##############
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
            desc = clean(effect["Description"])
            if matches := REGEX_ARKPASSIVE_NODE.search(desc):
                tier, name, level = (
                    int(matches.group(1)),
                    str(matches.group(2)),
                    int(matches.group(3)),
                )
            else:
                raise RuntimeError(f"아크 패시브 노드 파싱 실패: {desc}")

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
            if not desc or desc == KARMA_NOT_OPEN:
                continue

            if matches := REGEX_KARMA.match(desc):
                rank, level = int(matches.group(1)), int(matches.group(2))
            else:
                raise RuntimeError("카르마 파싱 실패")
            self.karma[karma_type] = rank, level

    @property
    def weapon_quality(self) -> int | None:
        """무기 품질"""
        for equipment in self.equipments:
            if equipment.equipment_type == EquipmentType.무기:
                return equipment.quality

    @property
    def elixir_set(self) -> str | None:
        """
        플레이어의 엘릭서 세트 이름과 단계를 하나의 문자열로 반환합니다.
        ex) 회심 2단계
        """
        for equipment in self.equipments:
            if equipment.equipment_type == EquipmentType.투구:
                es = equipment.elixir_set
                if es is None:
                    return
                return f"{es[0]} {es[1]}단계"
        return

    @property
    def arkpassive_available_points(
        self,
    ) -> dict[Literal["진화", "깨달음", "도약"], int]:
        result = {}
        if obj_arkpassive := self._data["ArkPassive"]:
            for obj_point in obj_arkpassive["Points"]:
                result[obj_point["Name"]] = obj_point["Value"]

        return result
