"""Domain services.

Operations that span models live here rather than on the models themselves:
explicit arguments, the transaction at the operation boundary, and typed
results. The API is a thin projection over these, so the same logic serves the
legacy views and the new `/api/v1/` package without being re-implemented.

Modules:
    results    race-day result upload
    pointscore scoring, tally / recalculate
    officials  allocation, promotion and performance reports
    exports    member CSV and the rider/race-summary row builders
               (XLS serialisation deferred until a consumer wants it)
"""
