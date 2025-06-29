import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from decimal import Decimal
from enum import Enum
from pathlib import Path

BASE = "F:\loadumps\868\db"

REGEX_TAG: re.Pattern[str] = re.compile(r"<[^>]+>")
DICT_BATTLE_STAT = [
    None,
    "치명",
    "특화",
    "제압",
    "신속",
    "인내",
    "숙련",
]  # 출처를 못 찾아서 하드코딩
DICT_EQUIPMENT_TYPE = {
    160: "무기",
    161: "투구",
    162: "상의",
    163: "하의",
    164: "장갑",
    165: "어깨",
}  # 출처를 못 찾아서 하드코딩, 숫자는 item 뒤에 부위별 값, 문자열은 OPENAPI의 ArmoryEquipment.Type 기준


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


def dump_enum():
    """xml에 있는 battlepoint 노드들을 BattlePointType enum을 만들기 편하게 출력"""
    tree = ET.parse(f"{BASE}/EFGameMsg_Enums.xml")
    root = tree.getroot()

    for node in root.findall("NODE"):
        node_type = node.attrib.get("Type")
        if node_type == "battlepointtype":
            name = node.attrib["Name"]
            print(f'    {name.upper()} = "{name}"')


# GameMsg를 읽고 python dict으로 만들어줌
class GameMsg:
    def __init__(self):
        with sqlite3.connect(f"{BASE}/EFTable_GameMsg.db") as conn:
            cur = conn.cursor()
            self.data: dict[str, str] = {}
            for row in cur.execute("SELECT KEY, MSG FROM GameMsg").fetchall():
                self.data[row[0].lower()] = row[1]

    def find(self, key: str) -> str:
        result = self.data[key.lower()]  # collate nocase

        result = result.replace("\n", " ")  # html의 <BR>에 대응
        result = result.replace("\t", "")
        result = re.sub(REGEX_TAG, "", result)
        return result


game_msg = GameMsg()


# current version: 865
def dump_battle_point_json():
    """
    XML과 DB를 읽고 JSON 형태로 덤프합니다.
    """
    # EFGameMsg_Enums.xml을 읽고 dict으로 만듦
    tree = ET.parse(f"{BASE}/EFGameMsg_Enums.xml")
    root = tree.getroot()

    battle_point_type: dict[int, str] = {}
    stat_type: dict[int, str] = {}
    for node in root.findall("NODE"):
        node_type = node.attrib.get("Type")
        if node_type == "battlepointtype":
            battle_point_type[int(node.attrib["Index"])] = node.attrib["Name"]

        elif node_type == "stattype":
            stat_type[int(node.attrib["Index"])] = node.attrib["Name"]

    # EFTable_BattlePoint.db을 읽기
    con = sqlite3.connect(f"{BASE}/EFTable_BattlePoint.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # BattlePoint에서 값을 읽고 dict으로 만듦
    rows = cur.execute(
        "SELECT PrimaryKey, Type, ValueA, ValueB, ValueC FROM BattlePoint"
    ).fetchall()
    rows = list(map(dict, rows))

    # 다른 필요한 db 파일도 읽기
    for db in [
        "Ability",
        "CombatEffect",
        "PetSpecialty",
        "ItemElixirOptionSet",
        "ItemElixirOption",
        "SeasonCardBook",
    ]:
        fname = f"{BASE}/EFTable_{db}.db"
        if not Path(fname).exists():
            raise ValueError(f"{fname} 파일이 없습니다.")
        cur.execute(f"ATTACH DATABASE '{BASE}/EFTable_{db}.db' AS {db}")

    # 작업 시작
    result = {"attack": {}, "defense": {}}

    for row in rows:
        pk, bp_type, val_a, val_b, val_c = (
            int(row["PrimaryKey"]),
            int(row["Type"]),
            int(row["ValueA"]),
            int(row["ValueB"]),
            int(row["ValueC"]),
        )
        pk = "attack" if pk == 1 else "defense"

        bp = battle_point_type[bp_type]

        # foreign key 처리

        # 방범대
        if bp == BattlePointType.PET_SPECIALTY:
            val_a = game_msg.find(
                cur.execute(
                    f"SELECT DESC FROM PetSpecialty WHERE PrimaryKey = {val_a}"
                ).fetchone()[0]
            )

        # 각인 이름
        if bp in [BattlePointType.ABILITY_ATTACK, BattlePointType.ABILITY_DEFENSE]:
            val_a = game_msg.find(
                cur.execute(
                    f"SELECT Name FROM Ability WHERE PrimaryKey = {val_a}"
                ).fetchone()[0]
            )

        # 엘릭서 세트
        # 회심 2단계
        if bp == BattlePointType.ELIXIR_SET:
            set_name = game_msg.find(
                cur.execute(
                    f"SELECT SetName FROM ItemElixirOptionSet WHERE PrimaryKey = {val_a}"
                ).fetchone()[0]
            )
            total_set_name = f"{set_name} {val_b}단계"

            if bp not in result[pk]:
                result[pk][bp] = {}

            result[pk][bp][total_set_name] = val_c
            continue

        # 엘릭서 효과
        if bp in [
            BattlePointType.ELIXIR_GRADE_ATTACK,
            BattlePointType.ELIXIR_GRADE_DEFENSE,
        ]:
            desc = game_msg.find(
                cur.execute(
                    f"SELECT Title FROM ItemElixirOption WHERE SecondaryKey = {val_a}"
                ).fetchone()[0]
            )
            desc += f" Lv.{val_b}"

            if bp not in result[pk]:
                result[pk][bp] = {}

            result[pk][bp][desc] = val_c
            continue

        # 연마효과
        if bp in [
            BattlePointType.ACCESSORY_GRINDING_ATTACK,
            BattlePointType.ACCESSORY_GRINDING_DEFENSE,
            BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_ATTACK,
            BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_DEFENSE,
            BattlePointType.BRACELET_STATTYPE,
            BattlePointType.BRACELET_ADDONTYPE_ATTACK,
            BattlePointType.BRACELET_ADDONTYPE_DEFENSE,
        ]:
            # ValueA가 1이면 Enum.xml의 값 참조
            if val_a == 1:
                stat_name = stat_type[val_b]
                msg = game_msg.find(f"tip.name.enum_stattype_{stat_name}")

                # 공%(49) 깡공(124) 모두 "공격력"
                # 옵션을 파싱할 수 있게 regex 형태로
                if stat_name.endswith("rate"):
                    msg += " +\+([0-9.]+)%$"
                else:
                    msg += " +\+([0-9.]+)$"

            # Value가 3이면 Ability 사용
            elif val_a == 3:
                if val_b == 0:  # 이건 모르겠음
                    msg = f"UNKNOWN {val_a} {val_b}"
                else:
                    # XXX Ability 테이블에 tip.desc.ability_11044가 담긴 Desc같은 게 없음
                    # 이렇게 조합할 리는 없을건데, 다른 테이블에 있는지 확인 필요
                    msg = game_msg.find(f"tip.desc.ability_{val_b}")

            # ValueA가 4면 CombatEffect 사용
            elif val_a == 4:
                msg = game_msg.find(
                    cur.execute(
                        f"SELECT Desc FROM CombatEffect WHERE PrimaryKey = {val_b}"
                    ).fetchone()[0]
                )
                arg = cur.execute(f"""
                    SELECT Action0ArgA
                    FROM CombatEffect
                    WHERE PrimaryKey = {val_b}
                """).fetchone()[0]

                # 악세 연마 효과용
                # 적에게 주는 피해 수치가 GameMsg에 그대로 있는 게 아니라, format해야 볼 수 있음
                if arg != 0:
                    arg = Decimal(arg) / Decimal(100)  # 부동소숫점 문제 방지
                    arg = f"+{arg:.2f}"  # 앞에 +붙이고, 2 대신 2.00
                    msg = str.format(msg, arg)
            else:
                msg = f"UNKNOWN {val_a} {val_b}"  # XXX 서폿쪽

            if bp not in result[pk]:
                result[pk][bp] = {}

            result[pk][bp][msg] = val_c
            continue

        if bp == BattlePointType.CARD_SET:
            name, card_count, awakening_level_sum = cur.execute(
                "SELECT Name, CardCount, AwakeningLevelSum FROM SeasonCardBook "
                f"WHERE PrimaryKey = {val_a} and SecondaryKey = {val_b}"
            ).fetchone()

            name = game_msg.find(name)

            if bp not in result[pk]:
                result[pk][bp] = {}

            # 아래 형태로 조립
            # 세상을 구하는 빛 6세트 (12각성합계)
            full_name = f"{name} {card_count}세트"
            if awakening_level_sum > 0:
                full_name += f" ({awakening_level_sum}각성합계)"
            result[pk][bp][full_name] = val_c
            continue

        if bp == BattlePointType.TRANSCENDENCE_ADDITIONAL:
            val_a = DICT_EQUIPMENT_TYPE[val_a]

        if bp == BattlePointType.BATTLESTAT:
            val_a = DICT_BATTLE_STAT[val_a]

        # 여기서는 위에 특수 케이스에 걸러지지 않은 애들용

        # A만 사용, 단순 계수
        if val_b == 0 and val_c == 0:
            result[pk][bp] = val_a

        # A, B사용
        elif val_c == 0:
            if bp not in result[pk]:
                result[pk][bp] = {}
            result[pk][bp][val_a] = val_b

        # A, B, C 사용
        else:
            if bp not in result[pk]:
                result[pk][bp] = {}
            if val_a not in result[pk][bp]:
                result[pk][bp][val_a] = {}
            result[pk][bp][val_a][val_b] = val_c

    # # dump as `BattlePoint.json`
    with open("BattlePoint.json", "w", encoding="utf-8") as fp:
        fp.write(json.dumps(result, ensure_ascii=False, indent=2))


def dump_ability_json():  # DEPRECATED
    """
    각인을 {이름: id} 객체로 저장합니다.
    """
    with sqlite3.connect("EFTable_GameMsg.db") as conn:
        cur = conn.cursor()
        cur.execute("ATTACH DATABASE 'EFTable_Ability.db' AS ability")
        result = cur.execute(
            """SELECT DISTINCT a.PrimaryKey, m.MSG
    FROM Ability as a JOIN GameMsg as m on a.Name = m.KEY collate nocase
    WHERE m.KEY like 'tip.name.ability_S3%'"""
        ).fetchall()

    result_dict = {}
    for idx, name in result:
        result_dict[name] = idx

    with open("Ability.json", "w") as fp:
        json.dump(result_dict, fp, ensure_ascii=False)


def dump_elixir_set():  # DEPRECATED
    """
    엘릭서 세트 효과 이름을 id과 매핑하여 저장합니다. {'회심': 101}
    """
    with sqlite3.connect("EFTable_GameMsg.db") as conn:
        cur = conn.cursor()
        cur.execute(
            "ATTACH DATABASE 'EFTable_ItemElixirOptionSet.db' AS itemelixiroptionset"
        )
        result = cur.execute(
            """SELECT DISTINCT i.PrimaryKey, m.MSG
    FROM itemelixiroptionset as i JOIN GameMsg as m on i.SetName = m.KEY collate nocase"""
        ).fetchall()

    result_dict = {}
    for idx, name in result:
        result_dict[name] = idx
    with open("ElixirSet.json", "w") as fp:
        json.dump(result_dict, fp, ensure_ascii=False)


def build_player_class_dict() -> dict[int, str]:
    """
    클래스 id와 실제 한글명을 맞게 설정
    """
    tree = ET.parse(f"{BASE}/EFGameMsg_Enums.xml")
    root = tree.getroot()

    player_class: dict[int, str] = {}
    for node in root.findall("NODE"):
        node_type = node.attrib.get("Type")
        if node_type == "playerclass":
            player_class[int(node.attrib["Index"])] = node.attrib["Name"]

    result = {}
    for idx, keyword in player_class.items():
        msg = game_msg.find(f"tip.name.enum_playerclass_{keyword}")
        result[idx] = msg
    return result


def dump_arkpassive_node_name():
    """
    진화, 깨달음, 도약 직업별 아크패시브 이름과 소모 포인트를 ArkPassive.json으로 저장
    이름만 저장하면 안 되는 이유는 동일한 이름의 노드가 많아서
    """

    with sqlite3.connect(f"{BASE}/EFTable_ArkPassive.db") as conn:
        cur = conn.cursor()
        rows = cur.execute(
            'SELECT Name, "Group", PCClass, ActivatePoint FROM ArkPassive'
        ).fetchall()

    dict_group = {0: "진화", 1: "깨달음", 2: "도약"}
    dict_player_class = build_player_class_dict()

    result = {}

    for name_id, group_id, pc_class_id, activate_point in rows:
        name = game_msg.find(name_id)
        group = dict_group[group_id]
        player_class = dict_player_class[pc_class_id]

        if group not in result:
            result[group] = {}

        if player_class == "ENUMNULL":  # 진화
            result[group][name] = activate_point
        else:
            if player_class not in result[group]:
                result[group][player_class] = {}
            result[group][player_class][name] = activate_point

    with open("ArkPassive.json", "w", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2, ensure_ascii=False)


dump_battle_point_json()
# dump_arkpassive_node_name()
