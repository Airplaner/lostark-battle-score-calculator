from decimal import Decimal
import glob
import json
from enum import Enum
import re
from typing import Any, Literal

from character import CharacterInformation, EquipmentType


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
        base: int = 4,
    ):
        if self.verbose:
            if coeff is None:
                coeff = 0
            val_base = Decimal(pow(10, base))
            coeff = Decimal(coeff)
            increase = ((coeff + val_base) / val_base - 1) * 100
            print(f"{battle_point_type} {additional_message} +{increase:.{base - 2}f}%")

    def calc(
        self,
        char: CharacterInformation,
        score_type: Literal["attack", "defense"] = "attack",
        *,
        verbose: bool = False,
    ) -> int:
        d: dict[BattlePointType, Any] = self.dict_battle_point[score_type]

        # BASE_ATTACK_POINT
        result: int = d[BattlePointType.BASE_ATTACK_POINT] * char.base_attack_point

        # LEVEL
        coeff = d[BattlePointType.LEVEL].get(str(char.character_level))
        if coeff is not None:
            result = result * (coeff + 10000) // 10000
        self.logging(BattlePointType.LEVEL, coeff)

        # WEAPON_QUALITY
        coeff = d[BattlePointType.WEAPON_QUALITY].get(str(char.weapon_quality))
        if coeff:
            result = result * (coeff + 10000) // 10000
        self.logging(BattlePointType.WEAPON_QUALITY, coeff)

        # ARKPASSIVE_EVOLUTION
        total_points = 0
        for node in char.arkpassive_nodes["진화"]:
            if node.tier == 1:  # 스탯에 투자한 포인트는 제외
                continue

            total_points += self.dict_arkpassive_point["진화"][node.name] * node.level

        coeff = d[BattlePointType.ARKPASSIVE_EVOLUTION] * total_points
        if coeff is not None:
            result = result * (coeff + 10000) // 10000
        self.logging(BattlePointType.ARKPASSIVE_EVOLUTION, coeff)

        # ARKPASSIVE_ENLIGHTMENT
        total_points = 0
        for node in char.arkpassive_nodes["깨달음"]:
            total_points += (
                self.dict_arkpassive_point["깨달음"][char.character_class_name][
                    node.name
                ]
                * node.level
            )

        coeff = d[BattlePointType.ARKPASSIVE_ENLIGHTMENT] * total_points
        if coeff is not None:
            result = result * (coeff + 10000) // 10000
        self.logging(BattlePointType.ARKPASSIVE_ENLIGHTMENT, coeff)

        # ARKPASSIVE_LEAP
        total_points = 0
        for node in char.arkpassive_nodes["도약"]:
            total_points += (
                self.dict_arkpassive_point["도약"][char.character_class_name][node.name]
                * node.level
            )

        coeff = d[BattlePointType.ARKPASSIVE_LEAP] * total_points
        if coeff is not None:
            result = result * (coeff + 10000) // 10000
        self.logging(BattlePointType.ARKPASSIVE_LEAP, coeff)

        # KARMA_EVOLUTIONRANK
        coeff = d[BattlePointType.KARMA_EVOLUTIONRANK] * char.karma_evolutionrank
        if coeff is not None:
            result = result * (coeff + 10000) // 10000
        self.logging(BattlePointType.KARMA_EVOLUTIONRANK, coeff)

        # KARMA_LEAPLEVEL:
        coeff = d[BattlePointType.KARMA_LEAPLEVEL] * char.karma_leaplevel
        if coeff is not None:
            result = result * (coeff + 10000) // 10000
        self.logging(BattlePointType.KARMA_LEAPLEVEL, coeff)

        # ABILITY_ATTACK:
        for engraving in char.engravings:
            name, level = engraving
            try:
                coeff = d[BattlePointType.ABILITY_ATTACK][name][str(level)]
            except KeyError:
                coeff = 0

            result = result * (coeff + 10000) // 10000
            self.logging(BattlePointType.ABILITY_ATTACK, coeff, name)

        # ELIXIR_SET:
        try:
            coeff = d[BattlePointType.ELIXIR_SET][char.elixir_set]
        except KeyError:
            coeff = 0

        result = result * (coeff + 10000) // 10000
        self.logging(BattlePointType.ELIXIR_SET, coeff, char.elixir_set)

        # ELIXIR_GRADE_ATTACK

        # ACCESSORY_GRINDING_ATTACK
        # ACCESSORY_GRINDING_DEFENSE
        # ACCESSORY_GRINDING_ADDONTYPE_ATTACK
        # ACCESSORY_GRINDING_ADDONTYPE_DEFENSE

        for equipment in char.equipments:
            match equipment.equipment_type:
                case (
                    EquipmentType.투구
                    | EquipmentType.상의
                    | EquipmentType.어깨
                    | EquipmentType.하의
                    | EquipmentType.장갑
                ):
                    for effect in equipment.elixir_effects:
                        coeff = self.find_by_str(
                            effect, d[BattlePointType.ELIXIR_GRADE_ATTACK]
                        )
                        if coeff:
                            result = result * (coeff + 10000) // 10000
                            self.logging(
                                BattlePointType.ELIXIR_GRADE_ATTACK,
                                coeff,
                                f"{equipment.name} - {effect}",
                            )

                case EquipmentType.목걸이 | EquipmentType.귀걸이 | EquipmentType.반지:
                    for effect in equipment.grinding_effects:
                        coeff = self.find_by_regex(
                            effect,
                            d[BattlePointType.ACCESSORY_GRINDING_ATTACK],
                        )
                        # 여기는 precision이 4, 4라서 base가 1e8
                        if coeff:
                            result = result * (coeff + 100000000) // 100000000

                            self.logging(
                                BattlePointType.ACCESSORY_GRINDING_ATTACK,
                                coeff,
                                f"{equipment.name} - {effect}",
                                base=8,
                            )
                            continue

                        coeff = self.find_by_str(
                            effect,
                            d[BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_ATTACK],
                        )
                        if coeff:
                            result = result * (coeff + 10000) // 10000
                            self.logging(
                                BattlePointType.ACCESSORY_GRINDING_ATTACK,
                                coeff,
                                f"{equipment.name} - {effect}",
                            )
                            continue

                case EquipmentType.팔찌:
                    for effect in equipment.bracelet_effects:
                        coeff = self.find_by_regex(
                            effect,
                            d[BattlePointType.BRACELET_STATTYPE],
                        )
                        # 여기는 특별하게 precision이 4, 4라서 base가 1e8
                        if coeff:
                            result = result * (coeff + 100000000) // 100000000

                            self.logging(
                                BattlePointType.BRACELET_STATTYPE,
                                coeff,
                                f"{equipment.name} - {effect}",
                                base=8,
                            )
                            continue

                        coeff = self.find_by_str(
                            effect,
                            d[BattlePointType.BRACELET_ADDONTYPE_ATTACK],
                        )
                        if coeff:
                            result = result * (coeff + 10000) // 10000
                            self.logging(
                                BattlePointType.BRACELET_ADDONTYPE_ATTACK,
                                coeff,
                                f"{equipment.name} - {effect}",
                            )
                            continue

        # GEM
        for gem in char.gems:
            coeff = d[BattlePointType.GEM][str(gem.tier)][str(gem.level)]

            result = result * (coeff + 10000) // 10000
            self.logging(
                BattlePointType.GEM,
                coeff,
                f"{gem.name} {gem.level}",
            )

        # transcendence_armor
        total_transcendence_grade = 0
        for equipment in char.equipments:
            if equipment.equipment_type in [
                EquipmentType.투구,
                EquipmentType.어깨,
                EquipmentType.상의,
                EquipmentType.하의,
                EquipmentType.장갑,
                EquipmentType.무기,
            ]:
                if equipment.transcendence_level:
                    total_transcendence_grade += equipment.transcendence_grade
        coeff = d[BattlePointType.TRANSCENDENCE_ARMOR] * total_transcendence_grade
        result = result * (coeff + 10000) // 10000
        self.logging(
            BattlePointType.TRANSCENDENCE_ARMOR,
            coeff,
        )

        # transcendence_additional
        target_equipment_type = d[BattlePointType.TRANSCENDENCE_ADDITIONAL].keys()

        for equipment in char.equipments:
            coeff = 0
            if equipment.transcendence_grade is None:
                continue

            et = equipment.equipment_type
            if et in target_equipment_type:
                for target_grade, target_coeff in d[
                    BattlePointType.TRANSCENDENCE_ADDITIONAL
                ][et].items():
                    if et == EquipmentType.무기:
                        # XXX 이유 모름, 무기는 각 옵션마다 적용
                        if equipment.transcendence_grade >= int(target_grade):
                            result = result * (target_coeff + 10000) // 10000
                            self.logging(
                                BattlePointType.TRANSCENDENCE_ADDITIONAL,
                                target_coeff,
                                f"{equipment.name} {equipment.transcendence_grade} >= {target_grade}",
                            )
                    else:
                        # 그 외 부위는 최대값 하나만 적용
                        if (
                            equipment.transcendence_grade >= int(target_grade)
                            and target_coeff > coeff
                        ):
                            coeff = target_coeff

            if coeff:
                result = result * (coeff + 10000) // 10000
                self.logging(
                    BattlePointType.TRANSCENDENCE_ADDITIONAL,
                    coeff,
                    f"{equipment.name} {equipment.transcendence_grade}",
                )

        return result

    def try_get_coeff(self, str_in: str) -> int:
        coeff = self.find_by_regex(
            str_in,
            self.dict_battle_point["attack"][BattlePointType.ACCESSORY_GRINDING_ATTACK],
        )
        if coeff:
            return coeff

        coeff = self.find_by_str(
            str_in,
            self.dict_battle_point["attack"][
                BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_ATTACK
            ],
        )
        return coeff

    def find_by_regex(self, str_in: str, dict_in: dict) -> int:
        coeff = 0
        for regex in dict_in:
            matches = re.match(regex, str_in)
            if not matches:
                continue
            value = Decimal(matches.group(1))
            if str_in.endswith("%"):
                value = int(value * 100)

            coeff = dict_in[regex] * value

        return coeff

    def find_by_str(self, str_in: str, dict_in: dict) -> int:
        return dict_in.get(str_in, 0)


# GET /armories/characters/{characterName} 응답을 json으로 저장하여 사용

calculator = BattlePointCalculator()
calculator.verbose = True
for fname in glob.glob("character*.json"):
    print("=" * 100)
    print(fname)
    character_info = CharacterInformation(json.load(open(fname, "rb")))
    print(Decimal(calculator.calc(character_info)) / 10000 / 100)
