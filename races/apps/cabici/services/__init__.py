"""Domain services.

Operations that span models live here rather than on the models themselves:
explicit arguments, the transaction at the operation boundary, and typed
results. The API is a thin projection over these, so the same logic serves the
legacy views and the new `/api/v1/` package without being re-implemented.

Modules:
    results    race-day result upload
    pointscore tally / recalculate (2.1 follow-up)
    officials  allocation (2.1 follow-up)
    exports    rider XLS / race summary / member CSV (2.5, if wanted)
"""
