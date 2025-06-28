from decimal import Decimal
import json
from enum import Enum
import re
from typing import Literal

from character import CharacterInformation


def init_recursive_battle_point_dict(json_file_path: str = "BattlePoint.json"):
    """
    BattlePoint.json을 읽습니다.
    """
    with open(json_file_path, "r", encoding="utf-8") as fp:
        result = json.load(fp)

    return result


class BattlePointType(str, Enum):
    BASE_ATTACK_POINT = "base_attack_point"
    BASE_HEALTH_POINT = "base_health_point"
    LEVEL = "level"
    WEAPON_QUALITY = "weapon_quality"
    ARKPASSIVE_EVOLUTION = "arkpassive_evolution"
    ARKPASSIVE_ENLIGHTMENT = "arkpassive_enlightment"
    ARKPASSIVE_LEAP = "arkpassive_leap"
    KARMA_EVOLUTIONRANK = "karma_evolutionrank"
    KARMA_LEAPLEVEL = "karma_leaplevel"
    ABILITY_ATTACK = "ability_attack"
    ABILITY_DEFENSE = "ability_defense"
    ELIXIR_SET = "elixir_set"
    ELIXIR_GRADE_ATTACK = "elixir_grade_attack"
    ELIXIR_GRADE_DEFENSE = "elixir_grade_defense"
    ACCESSORY_GRINDING_ATTACK = "accessory_grinding_attack"
    ACCESSORY_GRINDING_DEFENSE = "accessory_grinding_defense"
    ACCESSORY_GRINDING_ADDONTYPE_ATTACK = "accessory_grinding_addontype_attack"
    ACCESSORY_GRINDING_ADDONTYPE_DEFENSE = "accessory_grinding_addontype_defense"
    BRACELET_STATTYPE = "bracelet_stattype"
    BRACELET_ADDONTYPE_ATTACK = "bracelet_addontype_attack"
    BRACELET_ADDONTYPE_DEFENSE = "bracelet_addontype_defense"
    GEM = "gem"
    ESTHER_WEAPON = "esther_weapon"
    TRANSCENDENCE_ARMOR = "transcendence_armor"
    TRANSCENDENCE_ADDITIONAL = "transcendence_additional"
    BATTLESTAT = "battlestat"
    CARD_SET = "card_set"
    PET_SPECIALTY = "pet_specialty"


class BattlePointCalculator:
    def __init__(self):
        self.dict_battle_point = init_recursive_battle_point_dict()
        with open("ArkPassive.json", "r", encoding="utf-8") as fp:
            self.dict_arkpassive_point = json.load(fp)
        self.verbose = False  # not thread-safe

    def logging(
        self,
        battle_point_type: BattlePointType,
        coeff: int | None,
        additional_message: str = "",
    ):
        if self.verbose:
            if coeff is None:
                coeff = 0
            base = Decimal(10000)
            coeff = Decimal(coeff)
            increase = ((coeff + base) / base - 1) * 100
            print(f"{battle_point_type} {additional_message} +{increase:.2f}%")

    def calc(
        self,
        char: CharacterInformation,
        score_type: Literal["attack", "defense"] = "attack",
        *,
        verbose: bool = False,
    ) -> int:
        result: int = (
            self.dict_battle_point[score_type][BattlePointType.BASE_ATTACK_POINT]
            * char.base_attack_point
        )

        for battle_point_type in BattlePointType:
            coeff = 0
            # 현재 battle point type에 맞는 계수를 가져옴
            dict_battle_point: dict | None = self.dict_battle_point[score_type].get(
                battle_point_type
            )
            if dict_battle_point is None:
                continue

            match battle_point_type:
                case BattlePointType.LEVEL:
                    char_level = char.character_level
                    coeff = dict_battle_point.get(str(char_level))
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.WEAPON_QUALITY:
                    coeff = dict_battle_point.get(str(char.weapon_quality))
                    if coeff:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ARKPASSIVE_EVOLUTION:
                    total_points = 0
                    for node in char.arkpassive_nodes["진화"]:
                        if node.tier == 1:  # 스탯에 투자한 포인트는 제외
                            continue

                        total_points += (
                            self.dict_arkpassive_point["진화"][node.name] * node.level
                        )

                    coeff = dict_battle_point * total_points
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ARKPASSIVE_ENLIGHTMENT:
                    total_points = 0
                    for node in char.arkpassive_nodes["깨달음"]:
                        total_points += (
                            self.dict_arkpassive_point["깨달음"][
                                char.character_class_name
                            ][node.name]
                            * node.level
                        )

                    coeff = dict_battle_point * total_points
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ARKPASSIVE_LEAP:
                    total_points = 0
                    for node in char.arkpassive_nodes["도약"]:
                        total_points += (
                            self.dict_arkpassive_point["도약"][
                                char.character_class_name
                            ][node.name]
                            * node.level
                        )

                    coeff = dict_battle_point * total_points
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.KARMA_EVOLUTIONRANK:
                    coeff = dict_battle_point * char.karma_evolutionrank
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.KARMA_LEAPLEVEL:
                    coeff = dict_battle_point * char.karma_leaplevel
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ABILITY_ATTACK:
                    for engraving in char.engravings:
                        name, level = engraving
                        try:
                            coeff = dict_battle_point[name][str(level)]
                        except KeyError:
                            coeff = 0

                        result = result * (coeff + 10000) // 10000
                        self.logging(battle_point_type, coeff, name)

                case BattlePointType.ELIXIR_SET:
                    try:
                        coeff = dict_battle_point[char.elixir_set]
                    except KeyError:
                        coeff = 0

                    result = result * (coeff + 10000) // 10000
                    self.logging(
                        battle_point_type,
                        coeff,
                        char.elixir_set,
                    )
                case (
                    BattlePointType.ACCESSORY_GRINDING_ATTACK
                    | BattlePointType.ACCESSORY_GRINDING_DEFENSE
                ):
                    for equipment in char.equipments:
                        for grinding_effect in equipment.grinding_effects:
                            coeff = self.find_by_regex(
                                grinding_effect, dict_battle_point
                            )

                            if coeff:
                                result = result * (coeff + 10000) // 10000
                                self.logging(
                                    battle_point_type,
                                    coeff,
                                    f"{equipment.name} - {grinding_effect}",
                                )

                case (
                    BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_ATTACK
                    | BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_ATTACK
                ):
                    for equipment in char.equipments:
                        for grinding_effect in equipment.grinding_effects:
                            coeff = self.find_by_str(grinding_effect, dict_battle_point)

                            if coeff:
                                result = result * (coeff + 10000) // 10000
                                self.logging(
                                    battle_point_type,
                                    coeff,
                                    f"{equipment.name} - {grinding_effect}",
                                )

        return result

    def find_by_regex(self, str_in: str, dict_in: dict) -> int:
        coeff = 0
        for regex in dict_in:
            matches = re.match(regex, str_in)
            if not matches:
                continue
            value = Decimal(matches.group(1)) * 100
            coeff = dict_in[regex] * value // 10000

        return coeff

    def find_by_str(self, str_in: str, dict_in: dict) -> int:
        return dict_in.get(str_in, 0)


# GET /armories/characters/{characterName} 응답을 json으로 저장하여 사용
character_info = CharacterInformation(json.load(open("character.json", "rb")))
calculator = BattlePointCalculator()
calculator.verbose = True
print(calculator.calc(character_info) / 10000 / 100)
