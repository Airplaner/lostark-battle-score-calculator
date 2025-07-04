전투력 시뮬레이터

## Requirements
Python>=3.11

## Directory
```
main.py - BattleScoreCalculator로 전투력을 계산 및 분석해주는 클래스
character.py - OPENAPI 응답을 파싱해주는 CharacterInformation 클래스
BattlePoint.json - 각종 계수
docs/ - 각종 문서
```

## How to use
character.json으로 OPENAPI 응답을 저장한 후에
```
$ uv run main.py
```
혹은
```
$ python main.py
```

아래와 같은 응답이 온다.
```
character.json
공격 점수 41.63616
BattlePointType.LEVEL  +29.45%
BattlePointType.WEAPON_QUALITY  +30.00%
BattlePointType.ARKPASSIVE_EVOLUTION  +40.00%
BattlePointType.ARKPASSIVE_ENLIGHTMENT  +70.00%
BattlePointType.ARKPASSIVE_LEAP  +14.00%
BattlePointType.KARMA_EVOLUTIONRANK  +3.60%
BattlePointType.KARMA_LEAPLEVEL  +0.44%
BattlePointType.ABILITY_ATTACK 원한 +19.50%
BattlePointType.ABILITY_ATTACK 예리한 둔기 +19.40%
BattlePointType.ABILITY_ATTACK 질량 증가 +19.00%
BattlePointType.ABILITY_ATTACK 돌격대장 +21.28%
BattlePointType.ABILITY_ATTACK 저주받은 인형 +14.00%
BattlePointType.ELIXIR_SET 회심 2단계 +12.00%
BattlePointType.ELIXIR_GRADE_ATTACK +19 신념의 업화 투구 - 회심 (질서) Lv.5 +1.44%
BattlePointType.ELIXIR_GRADE_ATTACK +19 신념의 업화 상의 - 공격력 Lv.4 +0.40%
BattlePointType.ELIXIR_GRADE_ATTACK +19 신념의 업화 하의 - 공격력 Lv.4 +0.40%
BattlePointType.ELIXIR_GRADE_ATTACK +19 신념의 업화 하의 - 치명타 피해 Lv.5 +2.40%
BattlePointType.ELIXIR_GRADE_ATTACK +20 신념의 업화 장갑 - 회심 (혼돈) Lv.5 +1.44%
BattlePointType.ELIXIR_GRADE_ATTACK +19 신념의 업화 견갑 - 공격력 Lv.5 +0.54%
BattlePointType.ELIXIR_GRADE_ATTACK +19 신념의 업화 견갑 - 보스 피해 Lv.5 +2.40%
BattlePointType.ACCESSORY_GRINDING_ATTACK 마주한 종언의 목걸이 - 추가 피해 +2.60% +1.999920%
BattlePointType.ACCESSORY_GRINDING_ATTACK 도래한 결전의 귀걸이 - 공격력 +1.55% +1.550000%
BattlePointType.ACCESSORY_GRINDING_ATTACK 도래한 결전의 귀걸이 - 공격력 +1.55% +1.550000%
BattlePointType.ACCESSORY_GRINDING_ATTACK 도래한 결전의 반지 - 치명타 적중률 +0.40% +0.309680%
BattlePointType.ACCESSORY_GRINDING_ATTACK 도래한 결전의 반지 - 치명타 피해 +4.00% +1.200000%
BattlePointType.ACCESSORY_GRINDING_ATTACK 도래한 결전의 반지 - 치명타 적중률 +0.40% +0.309680%
BattlePointType.ACCESSORY_GRINDING_ATTACK 도래한 결전의 반지 - 치명타 피해 +4.00% +1.200000%
BattlePointType.ACCESSORY_GRINDING_ADDONTYPE_ATTACK 마주한 종언의 목걸이 - 적에게 주는 피해 +1.20% +1.20%
BattlePointType.BRACELET_STATTYPE 찬란한 구원자의 팔찌 - 치명타 적중률 +3.40% +2.380000%
BattlePointType.BRACELET_ADDONTYPE_ATTACK 찬란한 구원자의 팔찌 - 치명타 적중률이 3.4% 증가한다. 공격이 치명타로 적중 시 적에게 주는 피해가 1.5% 증가한다. +3.50%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 10 +7.04%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.GEM 광휘 8 +5.76%
BattlePointType.TRANSCENDENCE_ARMOR  +1.26%
BattlePointType.TRANSCENDENCE_ADDITIONAL +25 운명의 업화 대검 21 +0.79%
BattlePointType.TRANSCENDENCE_ADDITIONAL +19 신념의 업화 하의 21 +1.70%
BattlePointType.BATTLESTAT  +76.68%
BattlePointType.CARD_SET 힘찬 화염의 숨결 6세트 (24각성합계) +11.00%
BattlePointType.PET_SPECIALTY 추가 피해 1% 증가 +0.77%
실제 전투력: 2541.23
계산 전투력: 2541.213391
254121
```

## TODO
에스더 무기 추가 전투력 로직 구현
웹 UI
