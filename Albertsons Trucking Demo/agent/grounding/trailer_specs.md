# Trailer specifications

The Salt Lake City DC operates four trailer configurations. The truck routing optimizer
uses these to assign loads to vehicles.

## 40-40 combo (`40-40_COMBO`)

* **Layout**: two 40-foot trailers pulled together (front + rear).
* **Max gross weight**: 102,000 lbs in most states; **80,000 lbs when traveling through Wyoming** (per WY-DOT combo restrictions).
* **Cube capacity (1 stop)**: 4,000 cube units.
* **Max stops per route**: 8.
* **Best for**: long-haul backhauls between SLC and outlying RDCs (Boise, Helena), or any high-cube/low-stop run that stays out of Wyoming.

## 45-45 combo (`45-45_COMBO`)

* **Layout**: two 45-foot trailers.
* **Max gross weight**: 110,000 lbs.
* **Cube capacity (1 stop)**: 4,500 cube units.
* **Max stops per route**: 8.
* **Restrictions**: forbidden on certain Idaho secondary highways and most of Montana east of Helena. Best to keep on Interstate corridors.

## 48-28 combo (`48-28_COMBO`)

* **Layout**: 48-ft front, 28-ft rear (a "rocky-mountain double").
* **Max gross weight**: 105,500 lbs.
* **Cube capacity (1 stop)**: 4,200 cube units.
* **Max stops per route**: 6.
* **Best for**: mixed-density runs through Idaho where 45-45 is restricted but cube > single is required.

## Single 53 (`SINGLE_53`)

* **Layout**: one 53-foot trailer.
* **Max gross weight**: 80,000 lbs.
* **Cube capacity (1 stop)**: 3,800 cube units.
* **Max stops per route**: 12.
* **Best for**: dense multi-stop urban routes, smaller stores, and anywhere combos cannot legally travel.

## Cube degradation by stop count

Effective cube capacity drops as stops increase, because each delivery requires walk-around space and pallet rotation. The constraint workbook contains the full degradation chart per trailer (e.g. a 40-40 combo at 8 stops drops from 4,000 → ~3,120 effective cube). The optimizer reads `sample_constraints.xlsx → cube_degradation` and tightens caps post-solve.
