import json
from enum import Enum
from typing import Literal

from character import CharacterInformation


def init_recursive_battle_point_dict(json_file_path: str = "BattlePoint2.json"):
    """
    BattlePoint.json을 읽고, ValueB, ValueC 존재에 따라 다음 둘 중 하나의 형태로 초기화합니다.
    * result[Type] = ValueA
    * result[Type][ValueA] = ValueB
    * result[Type][ValueA][ValueB] = ValueC
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
            print(f"{battle_point_type} {additional_message} {(10000 + coeff) / 10000}")

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
                    coeff = dict_battle_point * char.arkpassive_evolution
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ARKPASSIVE_ENLIGHTMENT:
                    coeff = dict_battle_point * char.arkpassive_enlightment
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ARKPASSIVE_LEAP:
                    coeff = dict_battle_point * char.arkpassive_enlightment
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
