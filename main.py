from decimal import Decimal
import json
from enum import Enum
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
    LEVEL = "level"
    WEAPON_QUALITY = "weapon_quality"
    ARKPASSIVE_EVOLUTION = "arkpassive_evolution"
    ARKPASSIVE_ENLIGHTMENT = "arkpassive_enlightment"
    ARKPASSIVE_LEAP = "arkpassive_leap"
    KARMA_EVOLUTIONRANK = "karma_evolutionrank"
    KARMA_LEAPLEVEL = "karma_leaplevel"
    ABILITY_ATTACK = "ability_attack"
    ELIXIR_SET = "elixir_set"
    ...


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
            dict_battle_point: dict = self.dict_battle_point[score_type][
                battle_point_type
            ]
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

        return result


# GET /armories/characters/{characterName} 응답을 json으로 저장하여 사용
character_info = CharacterInformation(json.load(open("character.json", "rb")))
calculator = BattlePointCalculator()
calculator.verbose = True
print(calculator.calc(character_info))
