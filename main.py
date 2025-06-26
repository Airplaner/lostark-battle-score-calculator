import json
import sqlite3
import xml.etree.ElementTree as ET
from collections import defaultdict
from enum import Enum

from character import CharacterInformation


# current version: 865
def dump_battle_point_json():
    """
    XML과 DB를 읽고 공유 가능한 JSON 형태로 덤프합니다.
    """
    # read EFGameMsg_Enums.xml and build dict
    tree = ET.parse("EFGameMsg_Enums.xml")
    root = tree.getroot()

    battle_point_type: dict[str, str] = {}
    for node in root.findall("NODE"):
        node_type = node.attrib.get("Type")
        if node_type == "battlepointtype":
            battle_point_type[node.attrib["Index"]] = node.attrib["Name"]

    # read EFTable_BattlePoint.db and build dict
    con = sqlite3.connect("EFTable_BattlePoint.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # replace integer Type to `battlepointtype`
    rows = cur.execute(
        "SELECT Type, ValueA, ValueB, ValueC FROM BattlePoint WHERE PrimaryKey = 1"
    ).fetchall()
    rows = list(map(dict, rows))
    for row in rows:
        row["Type"] = battle_point_type[str(row["Type"])]

    # dump as `BattlePoint.json`
    with open("BattlePoint.json", "w") as fp:
        fp.write(json.dumps(rows))


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
    ...


class BattlePointCalculator:
    def __init__(self):
        self.dict_battle_point = init_recursive_battle_point_dict()
        self.dict_ability = init_ability_dict()
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
        dict_battle_point = self.dict_battle_point

        result = 1000  # base값 찾아야 함

        for battle_point_type in BattlePointType:
            match battle_point_type:
                case BattlePointType.BASE_ATTACK_POINT:
                    # ValueA가 288인데 뭘까 이게?
                    ...

                case BattlePointType.LEVEL:
                    char_level = char.character_level
                    coeff = dict_battle_point[BattlePointType.LEVEL].get(char_level)
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.WEAPON_QUALITY:
                    coeff = dict_battle_point[BattlePointType.WEAPON_QUALITY].get(
                        char.weapon_quality
                    )
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ARKPASSIVE_EVOLUTION:
                    coeff = (
                        dict_battle_point[BattlePointType.ARKPASSIVE_EVOLUTION]
                        * char.arkpassive_evolution
                    )
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ARKPASSIVE_ENLIGHTMENT:
                    coeff = (
                        dict_battle_point[BattlePointType.ARKPASSIVE_ENLIGHTMENT]
                        * char.arkpassive_enlightment
                    )
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ARKPASSIVE_LEAP:
                    coeff = (
                        dict_battle_point[BattlePointType.ARKPASSIVE_ENLIGHTMENT]
                        * char.arkpassive_enlightment
                    )
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.KARMA_EVOLUTIONRANK:
                    coeff = (
                        dict_battle_point[BattlePointType.KARMA_EVOLUTIONRANK]
                        * char.karma_evolutionrank
                    )
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.KARMA_LEAPLEVEL:
                    coeff = (
                        dict_battle_point[BattlePointType.KARMA_LEAPLEVEL]
                        * char.karma_leaplevel
                    )
                    if coeff is not None:
                        result = result * (coeff + 10000) // 10000
                    self.logging(battle_point_type, coeff)

                case BattlePointType.ABILITY_ATTACK:
                    for engraving in char.engravings:
                        name, level = engraving
                        engraving_id: int = self.dict_ability[name]
                        engraving_coeffs = dict_battle_point[
                            BattlePointType.ABILITY_ATTACK
                        ].get(engraving_id)

                        if engraving_coeffs:
                            coeff = engraving_coeffs[level]
                        else:  # 일부 각인은 전투력에 영향을 끼치지 않음
                            coeff = 0

                        result = result * (coeff + 10000) // 10000
                        self.logging(battle_point_type, coeff, name)

        return result


# GET /armories/characters/{characterName} 응답을 json으로 저장하여 사용
character_info = CharacterInformation(json.load(open("character.json", "rb")))
calculator = BattlePointCalculator()
calculator.verbose = True
print(calculator.calc(character_info))
