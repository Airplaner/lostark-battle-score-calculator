import json
from enum import Enum

from character import CharacterInformation


def init_recursive_battle_point_dict(json_file_path: str = "BattlePoint.json"):
    """
    BattlePoint.json을 읽고, ValueB, ValueC 존재에 따라 다음 둘 중 하나의 형태로 초기화합니다.
    * result[Type] = ValueA
    * result[Type][ValueA] = ValueB
    * result[Type][ValueA][ValueB] = ValueC
    """
    result = {}

    with open(json_file_path, "r") as fp:
        raw_battle_point = json.load(fp)

    for item in raw_battle_point:
        item_type, val_a, val_b, val_c = (
            item["Type"],
            item["ValueA"],
            item["ValueB"],
            item["ValueC"],
        )
        # A만 쓰는 경우
        if val_b == 0 and val_c == 0:
            result[item_type] = val_a
        # A, B만 쓰는 경우
        elif val_c == 0:  #
            if item_type not in result:
                result[item_type] = {}
            result[item_type][val_a] = val_b
        # A, B, C 모두 쓰는 경우
        else:
            if item_type not in result:
                result[item_type] = {}
            if val_a not in result[item_type]:
                result[item_type][val_a] = {}
            result[item_type][val_a][val_b] = val_c

    return result


def init_ability_dict(json_file_path: str = "Ability.json"):
    with open(json_file_path, "r") as fp:
        return json.load(fp)


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
        self.dict_ability = init_ability_dict()
        with open("ElixirSet.json", "r") as fp:
            self.dict_elixir_set = json.load(fp)
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

    def calc(self, char: CharacterInformation, *, verbose: bool = False) -> int:
        result = 1000  # base값 찾아야 함

        for battle_point_type in BattlePointType:
            coeff = 0
            dict_battle_point: dict | int = self.dict_battle_point[battle_point_type]
            match battle_point_type:
                case BattlePointType.BASE_ATTACK_POINT:
                    # ValueA가 288인데 뭘까 이게?
                    ...

                case BattlePointType.LEVEL:
                    char_level = char.character_level
                    coeff = dict_battle_point.get(char_level)
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.WEAPON_QUALITY:
                    coeff = dict_battle_point[char.weapon_quality]
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
                        engraving_id: int = self.dict_ability[name]
                        try:
                            coeff = dict_battle_point[engraving_id][level]
                        except KeyError:
                            coeff = 0

                        result = result * (coeff + 10000) // 10000
                        self.logging(battle_point_type, coeff, name)

                case BattlePointType.ELIXIR_SET:
                    name, level = char.elixir_set
                    if name:
                        elixir_set_id: int = self.dict_elixir_set[name]

                        try:
                            coeff = self.dict_battle_point[elixir_set_id][level]
                        except KeyError:
                            coeff = 0

                    result = result * (coeff + 10000) // 10000
                    self.logging(
                        battle_point_type,
                        coeff,
                        f"{name} {level}단계",
                    )

        return result


# GET /armories/characters/{characterName} 응답을 json으로 저장하여 사용
character_info = CharacterInformation(json.load(open("character.json", "rb")))
calculator = BattlePointCalculator()
calculator.verbose = True
print(calculator.calc(character_info))
