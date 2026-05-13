# Delivery windows and operating hours

Every store and DC has a delivery window expressed as `delivery_window_open` / `delivery_window_close` in 24-hour local time. The solver enforces these as hard constraints on the time dimension of each route.

## Typical patterns
* **Albertsons / Safeway / Smith's / Tom Thumb stores**: 04:00 – 14:00 most weekdays.
* **Rural single-aisle stores**: 06:00 – 11:00 (no overnight receiving staff).
* **DC inbound** (SLC-DC depot): 24/7.
* **Crossdock RDCs (BOI, OGD, MISA)**: 02:00 – 22:00 daily.

## Service time
Each delivery stop adds **30 minutes** of service time (load-out, paperwork, signature) on top of drive time. The solver bakes this into the time matrix.

## Driver hours
Hard cap of 11 driving hours per shift (`max_driver_hours` cost proxy). The validator surfaces violations as `DRIVER_HOURS_EXCEEDED`.

## Late delivery handling
If a route arrives at a store after `delivery_window_close`, the validator flags `DELIVERY_LATE` (severity VIOLATION). The dispatcher is expected to either split the route or call ahead to extend the window manually.
