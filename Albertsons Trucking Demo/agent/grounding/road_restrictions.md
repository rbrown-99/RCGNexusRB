# State road restrictions affecting routing

These rules are loaded from `sample_constraints.xlsx → state_road_restrictions` and applied at solve time. The most operationally significant restrictions:

## Wyoming (WY)
* **40-40 combos** are limited to **Max 80,000 lbs** gross when transiting Wyoming, regardless of axle configuration.
* All multi-trailer combos require Interstate routing only (I-80, I-25). Secondary highways are off-limits.

## Montana (MT)
* **45-45 combos** restricted to specific designated routes: I-90, I-15, US-2 mainline.
* Combos cannot use most state-numbered routes east of Helena (MT 200, MT 87, etc.).

## Idaho (ID)
* **48-28 combos** ("rocky-mountain doubles") permitted on most Interstates and US-20/US-26.
* **45-45 combos** prohibited on US-95 north of Coeur d'Alene and on most secondary highways.
* All combos require pre-clearance on US-30 between Burley and Pocatello during winter weather advisories.

## Utah (UT)
* No special combo restrictions on Interstates within Utah.
* Single-trailer (53') vehicles only into central business districts (Salt Lake City, Ogden downtown).

## Universal ("ALL")
* Driver hours-of-service: maximum 11 driving hours / 14 on-duty hours per shift.
* No fresh/refrigerated loads sitting at dock > 90 minutes without active reefer.

## How the optimizer uses these
The encoder rewrites the per-vehicle weight cap whenever a route enters a restricted state. The validator surfaces every applicable restriction as an INFO finding so dispatchers can see the rationale.
