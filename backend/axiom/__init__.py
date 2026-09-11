"""Pure, unit-testable business logic for Axiom.

Nothing in this package touches AWS — Lambda handlers in ``lambdas/`` import
from here and stay thin. That split is what lets the whole grading/streak/
badge/nudge rulebook run under pytest with no deployed infrastructure.
"""
