import json
from decimal import Decimal

with open("BattlePoint.json", "r", encoding="utf-8") as fp:
    battle_point = json.load(fp)


for score_type, battle_point_type, korean_title in [
    ("attack", "ability_attack", "딜러 전투력"),
    ("defense", "ability_attack", "서폿 버프 전투력"),
    ("defense", "ability_defense", "서폿 케어 전투력"),
]:
    fp = open(
        f"./docs/result_{score_type}_{battle_point_type}.md", "w", encoding="utf-8"
    )

    d = battle_point[score_type][battle_point_type]
    for ability in d:
        table = (
            f"|{ability} - {korean_title}||||||\n"
            + "|-|-|-|-|-|-|\n"
            + "|어빌스톤 레벨|0|1|2|3|4|\n"
        )

        for active_level in range(9, 14):
            table += f"|유각 {(active_level - 9) * 5}장|"
            for stone_level in range(0, 5):
                coeff = d[ability][str(stone_level * 20 + active_level)]
                coeff = Decimal(coeff) / 100
                table += f"{coeff:.2f}%|"
            table += "\n"

        fp.write(table)
        fp.write("\n")
        print(table)
    fp.close()
