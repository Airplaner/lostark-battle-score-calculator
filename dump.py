import json
import sqlite3


def dump_ability_json():
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
