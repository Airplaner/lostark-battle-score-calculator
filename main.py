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

    def apply(
        self,
        result: int,
        coeff_in: int | None,
        battle_point_type: BattlePointType,
        additional_message: str = "",
        *,
        base: int = 4,
    ):
        if coeff_in is None or coeff_in == 0:
            return result

        coeff = Decimal(coeff_in)
        val_base = Decimal(pow(10, base))
        increase_rate = (val_base + coeff) / val_base
        result = result * increase_rate
        result = Decimal(int(result))

        if self.verbose:
            increase = ((coeff + val_base) / val_base - 1) * 100
            print(f"{battle_point_type} {additional_message} +{increase:.{base - 2}f}%")

        result = int(result)
        return result

    def calc(
        self,
        char: CharacterInformation,
        score_type: Literal["attack", "defense"] = "attack",
        *,
        verbose: bool = False,
    ) -> int:
        d: dict[BattlePointType, Any] = self.dict_battle_point[score_type]

        # BASE_ATTACK_POINT
        result = d[BattlePointType.BASE_ATTACK_POINT] * char.base_attack_point

        # LEVEL
        coeff = d[BattlePointType.LEVEL].get(str(char.character_level))
        result = self.apply(result, coeff, BattlePointType.LEVEL)

        # WEAPON_QUALITY
        coeff = d[BattlePointType.WEAPON_QUALITY].get(str(char.weapon_quality))
        result = self.apply(result, coeff, BattlePointType.WEAPON_QUALITY)

        # ARKPASSIVE_EVOLUTION
        total_points = 0
        for node in char.arkpassive_nodes["진화"]:
            if node.tier == 1:  # 스탯에 투자한 포인트는 제외
                continue

            total_points += self.dict_arkpassive_point["진화"][node.name] * node.level

        if total_points > char.arkpassive_available_points["진화"]:
            raise ValueError("가진 포인트보다 많이 찍힌 상태입니다.")

        coeff = d[BattlePointType.ARKPASSIVE_EVOLUTION] * total_points
        result = self.apply(result, coeff, BattlePointType.ARKPASSIVE_EVOLUTION)

        # ARKPASSIVE_ENLIGHTMENT
        total_points = 0
        for node in char.arkpassive_nodes["깨달음"]:
            total_points += (
                self.dict_arkpassive_point["깨달음"][char.character_class_name][
                    node.name
                ]
                * node.level
            )

        if total_points > char.arkpassive_available_points["깨달음"]:
            raise ValueError("가진 포인트보다 많이 찍힌 상태입니다.")

        coeff = d[BattlePointType.ARKPASSIVE_ENLIGHTMENT] * total_points
        result = self.apply(result, coeff, BattlePointType.ARKPASSIVE_ENLIGHTMENT)

        # ARKPASSIVE_LEAP
        total_points = 0
        for node in char.arkpassive_nodes["도약"]:
            total_points += (
                self.dict_arkpassive_point["도약"][char.character_class_name][node.name]
                * node.level
            )

        if total_points > char.arkpassive_available_points["도약"]:
            raise ValueError("가진 포인트보다 많이 찍힌 상태입니다.")

        coeff = d[BattlePointType.ARKPASSIVE_LEAP] * total_points
        result = self.apply(result, coeff, BattlePointType.ARKPASSIVE_LEAP)

        # KARMA_EVOLUTIONRANK
        coeff = d[BattlePointType.KARMA_EVOLUTIONRANK] * char.karma_evolutionrank
        result = self.apply(result, coeff, BattlePointType.KARMA_EVOLUTIONRANK)

        # KARMA_LEAPLEVEL:
        coeff = d[BattlePointType.KARMA_LEAPLEVEL] * char.karma_leaplevel
        result = self.apply(result, coeff, BattlePointType.KARMA_LEAPLEVEL)

        # ABILITY_ATTACK:
        for engraving in char.engravings:
            name, level = engraving
            try:
                coeff = d[BattlePointType.ABILITY_ATTACK][name][str(level)]
            except KeyError:
                coeff = None

            result = self.apply(result, coeff, BattlePointType.ABILITY_ATTACK, name)

        # ELIXIR_SET:
        try:
            coeff = d[BattlePointType.ELIXIR_SET][char.elixir_set]
        except KeyError:
            coeff = 0

        result = self.apply(result, coeff, BattlePointType.ELIXIR_SET, char.elixir_set)

        # ELIXIR_GRADE_ATTACK

        for equipment in char.equipments:
            if equipment.equipment_type not in [
                EquipmentType.투구,
                EquipmentType.상의,
                EquipmentType.어깨,
                EquipmentType.하의,
                EquipmentType.장갑,
            ]:
                continue
            for effect in equipment.elixir_effects:
                coeff = self.find_by_str(effect, d[BattlePointType.ELIXIR_GRADE_ATTACK])
                result = self.apply(
                    result,
                    coeff,
                    BattlePointType.ELIXIR_GRADE_ATTACK,
                    f"{equipment.name} - {effect}",
                )

        # ACCESSORY_GRINDING_ATTACK
        # ACCESSORY_GRINDING_DEFENSE

        for equipment in char.equipments:
            if equipment.equipment_type not in [
                EquipmentType.목걸이,
                EquipmentType.귀걸이,
                EquipmentType.반지,
            ]:
                continue

            for effect in equipment.grinding_effects:
                coeff = self.find_by_regex(
                    effect,
                    d[BattlePointType.ACCESSORY_GRINDING_ATTACK],
                )

                if coeff:
                    result = self.apply(
                        result,
                        coeff,
                        BattlePointType.ACCESSORY_GRINDING_ATTACK,
                        f"{equipment.name} - {effect}",
                        base=8,
                    )

        # ACCESSORY_GRINDING_ADDONTYPE_ATTACK
        # ACCESSORY_GRINDING_ADDONTYPE_DEFENSE

        for equipment in char.equipments:
            if equipment.equipment_type not in [
                EquipmentType.목걸이,
                EquipmentType.귀걸이,
                EquipmentType.반지,
            ]:
                continue

            for effect in equipment.grinding_effects:
                coeff = self.find_by_str(
                    effect,
                    d[BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_ATTACK],
                )

                if coeff:
                    result = self.apply(
                        result,
                        coeff,
                        BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_ATTACK,
                        f"{equipment.name} - {effect}",
                    )

        # BRACELET_STATTYPE

        for equipment in char.equipments:
            if equipment.equipment_type != EquipmentType.팔찌:
                continue

            for effect in equipment.bracelet_effects:
                coeff = self.find_by_regex(
                    effect,
                    d[BattlePointType.BRACELET_STATTYPE],
                )
                if coeff:
                    result = self.apply(
                        result,
                        coeff,
                        BattlePointType.BRACELET_STATTYPE,
                        f"{equipment.name} - {effect}",
                        base=8,
                    )

        # BRACELET_ADDONTYPE_ATTACK

        for equipment in char.equipments:
            if equipment.equipment_type != EquipmentType.팔찌:
                continue

            for effect in equipment.bracelet_effects:
                coeff = self.find_by_str(
                    effect,
                    d[BattlePointType.BRACELET_ADDONTYPE_ATTACK],
                )
                if coeff:
                    result = self.apply(
                        result,
                        coeff,
                        BattlePointType.BRACELET_ADDONTYPE_ATTACK,
                        f"{equipment.name} - {effect}",
                    )

        # GEM
        for gem in char.gems:
            coeff = d[BattlePointType.GEM][str(gem.tier)][str(gem.level)]
            result = self.apply(
                result, coeff, BattlePointType.GEM, f"{gem.name} {gem.level}"
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
        result = self.apply(result, coeff, BattlePointType.TRANSCENDENCE_ARMOR)

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
                    if (
                        equipment.transcendence_grade >= int(target_grade)
                        and target_coeff > coeff
                    ):
                        coeff = target_coeff

            result = self.apply(
                result,
                coeff,
                BattlePointType.TRANSCENDENCE_ADDITIONAL,
                f"{equipment.name} {equipment.transcendence_grade}",
            )

        # battle_stat
        coeff = 0
        for stat_type, value in char.battle_stat.items():
            if stat_type in d[BattlePointType.BATTLESTAT]:
                coeff += value * d[BattlePointType.BATTLESTAT][stat_type]

        result = self.apply(
            result,
            coeff,
            BattlePointType.BATTLESTAT,
        )

        # card_set
        for card_set in char.card_sets:
            try:
                coeff = d[BattlePointType.CARD_SET][card_set]
            except KeyError:
                coeff = 0

            result = self.apply(result, coeff, BattlePointType.CARD_SET, card_set)

        # pet_specialty
        coeff = d[BattlePointType.PET_SPECIALTY]["추가 피해 1% 증가"]
        result = self.apply(
            result, coeff, BattlePointType.PET_SPECIALTY, "추가 피해 1% 증가"
        )

        real_combat_power = Decimal(
            char._data["ArmoryProfile"]["CombatPower"].replace(",", "")
        )

        print("실제 전투력:", real_combat_power)
        print("계산 전투력:", result / Decimal(1000000))
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
    calculator.calc(character_info)
