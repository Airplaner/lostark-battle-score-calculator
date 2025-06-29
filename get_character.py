import requests
import json

with open("jwt.txt", "r") as fp:
    jwt = fp.read()
with open("charnames,txt", "r") as fp:
    charnames = fp.readlines()
for charname in charnames:
    res = requests.get(
        f"https://developer-lostark.game.onstove.com/armories/characters/{charname}",
        headers={"authorization": f"Bearer {jwt}"},
    ).json()

    with open(f"character_{charname}.json", "w", encoding="utf-8") as fp:
        json.dump(res, fp, ensure_ascii=False, indent=2)
