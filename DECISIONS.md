# Axiom — Architecture & Development Decisions

A running log of the decisions behind Axiom, in the order they were made. Each
entry is here because the *why* isn't obvious from the code alone — the code
shows what happens, this explains what alternative was rejected and for what
reason. Milestone-by-milestone build history lives in Claude Code's plan
storage, not here; this file exists so the reasoning survives even if that
doesn't.

Axiom is a Junior Cycle Higher Level Maths practice app: React+TS/Vite
frontend (Cognito auth, installable PWA), Python 3.12/CDK backend, DynamoDB
(`Users`, `Questions`, `Attempts`, `ProgressState`, `StreakState`, `Flags`),
one HTTP API behind a Cognito JWT authorizer. Live at
`https://d1j5g1iwdlymr9.cloudfront.net`, AWS account `137860826896` /
`eu-west-1`.

---

## Phase 0 — Coordinate Geometry of the Line

### Content is live-generated, not a fixed question bank

Originally planned as a curated bank of ~72 hand-written questions. Revised
mid-build: a fixed bank of that size is memorizable by a single student
practicing daily, which defeats the point of practice. `axiom/question_generators.py`
instead produces a fresh, exactly-correct instance per request using
`Fraction`/`sympy` arithmetic — there's no upper bound on how many times a
subtopic can be practiced without repetition. This also meant Bedrock/SES
were never needed for parametric topics — there's no content pipeline to run,
generation happens synchronously in the Lambda.

### Grading accepts any mathematically-equivalent answer

`axiom/grading.py` uses `sympy` to compare the submitted answer to the
canonical one, not string equality. `0.75` and `3/4` are both accepted for
the same question; `y=2x-1` and `y = 2*x - 1` are the same line. The
alternative — requiring a specific textual format — would penalize correct
maths for formatting reasons, which teaches the wrong lesson.

### The diagnostic offers, it doesn't force, remediation

`axiom/diagnostics.py` tracks misses per subtopic and offers a worked example
("See why") alongside "Try another" rather than forcing the explanation on
every wrong answer. A miss threshold escalates the wording ("This one's
tricky — want to see why?") and makes "See why" the visually primary button,
but the choice stays real — a bug fixed during the design pass made "See
why"/"Try another" visually equal-weight by default; the escalation only
kicks in after a second consecutive miss on the same subtopic.

### Reminders are a calendar file, not push notifications

Real Web Push needs `cryptography`'s compiled extensions, which breaks the
pure-Python Lambda Layer approach used everywhere else in the backend.
Rather than add a compiled-dependency build pipeline for one minor feature,
reminders are a plain `.ics` calendar download. Deliberately simple, not a
placeholder for something bigger later.

### The AI content pipeline was dropped

Originally scoped (milestone 8) on the assumption content would come from a
fixed, curated bank needing generation help. Once content generation moved
to live parametric generation instead, the whole pipeline — and the
Bedrock/SES dependency it implied — became unnecessary and was cut rather
than built and left unused.

---

## Phase 1, slice 1 — Algebra: Solving Equations & Factorising

### Multi-topic support via a small registry, not a rewrite

Adding a second topic exposed several places that hardcoded
`"coordinate_geometry_line"` as if it were the only topic that would ever
exist. Rather than restructure, a single new lookup point —
`axiom/topics.py`'s `TOPICS` dict — was introduced, and the Lambda handlers
were changed to loop over it / read `topicId` off the stored question item
instead of assuming one topic. Minimal-diff on purpose: the working, tested
`question_generators.py` module was left alone beyond adding `TOPIC_ID`/
`TOPIC_LABEL` constants; `algebra_generators.py` is a same-shaped sibling
module, not a shared base class.

### `factored_expression` grading needed more than equivalence

Checking `sympy.expand(submitted) == sympy.expand(canonical)` alone isn't
enough for a "factorise this" question — a student could type back the
original *unfactored* expression and it would trivially pass, since anything
equals its own expansion. The fix requires the submitted expression to
literally differ from its own expansion (`submitted_expr != sympy.expand(submitted_expr)`),
which distinguishes "gave a factored form" from "gave back the sum." This
relies on `sympy` not auto-simplifying `Mul(3, Add(...))` into `Add(...)`
during parsing — verified empirically rather than assumed, since a very
similar sympy-parsing assumption (see below) had already broken once in this
project.

A related, easy-to-miss bug during the same work: sympy auto-distributes a
bare number times a bracket during normal parsing (`3*(2*x+3)` silently
becomes `6*x+9` before the code ever sees it as a structured expression), so
the "must not equal its own expansion" check needs `evaluate=False` parsing
specifically for this answer type — a normal `sympify` call would have made
every correctly-factored answer look unfactored.

### Inequalities as a second seed-misconception subtopic

`perpendicular_lines` already used a `common_wrong_answers` tag
(`mx_negative_one`) to specifically catch a predictable mistake, rather than
just marking a wrong answer generically wrong. `inequalities` repeats that
pattern for forgetting to flip the sign when dividing/multiplying by a
negative — the generator sometimes forces a negative coefficient
specifically to exercise this, and the sign-not-flipped answer is tagged so
the diagnostic can name the actual misconception instead of just saying
"not quite."

### Explicitly deferred from this slice

Weak-spot drill mode (needs more topic breadth to be meaningful), any new
interactive diagram (none of the brief's interactives target algebra), and
Bedrock/SES (still unnecessary — algebra stayed parametric like coordinate
geometry).

---

## Diagram integrity and UX (this session)

### The interactive diagrams were leaking the graded answer

Found via live testing: for every one of the six visualized subtopics
(`slope_two_points`, `perpendicular_lines`, `parallel_lines`, `midpoint`,
`distance`, `axis_intercepts`), the diagram printed the literal graded
answer as a text stat in its caption — e.g. axis-intercept questions showed
`(1.25, 0)` directly, before the question was answered. A student could read
the answer off the widget with no maths at all. The diagram's visual
elements (drawn points, lines, dots) were left alone — reading an exact
value off an ungridded sketch still takes real reasoning — only the literal
number was the problem.

Fix: `SlopeExplorer` takes a `revealAnswer` prop, wired to `Boolean(result)`
in `SessionScreen` (true only once she's submitted). Every mode's
answer-quantity text is gated behind it, replaced beforehand with a plain
"Submit your answer to reveal…" line. The one exception: line k's slope in
perpendicular/parallel questions stays visible throughout, since that's
*given* in the prompt's equation, not the thing being asked for — only line
n's slope (the actual answer) is gated. The same leak existed in the
screen-reader `aria-label`, announcing the live slope value unconditionally;
fixed the same way.

### `slope_two_points`'s draggable diagram had no learning outcome

Once the answer-leak fix hid the slope number pre-answer, dragging the two
points accomplished nothing: the question is "find the slope between these
*two given points*," not a general relationship that survives being dragged
elsewhere. Contrast with perpendicular/parallel, midpoint, and distance,
where dragging demonstrates something that stays true regardless of where
the points land (k×n = −1 always, the midpoint is always exactly halfway,
distance always comes from the same two legs) — that invariance is the
actual "aha," and it's why those diagrams are worth exploring interactively.

Fix: `slope_two_points` changed `displayMode` from `"line"` (an extended
line through the two points) to a new `"segment-slope"` mode — the same
right-angle-leg construction as the distance diagram, but labeled for
rise/run. Dragging now resizes the legs the slope formula is actually built
from, which is a legitimate thing to explore, instead of moving an arbitrary
line around.

### Diagrams only appear when they can actually teach something

Extending the previous point: for the four single-value diagram types
(`segment-slope`, `segment-midpoint`, `segment-distance`, `line-intercept`),
there's nothing for the diagram to do *during* an attempt — she can't read
the number, and dragging doesn't help her check arithmetic on the specific
points the question gave her. These four are now hidden entirely until
there's an answer to confirm or explain: shown after a correct answer as
confirmation, or inside the "why" worked-example box after a wrong answer,
paired with a one-line instruction on what to actually do with it (e.g.
"Drag the points below and watch how rise and run combine into the slope").
Choosing "Try another" without viewing the explanation shows no diagram that
round — she opted out of the explanation, so there's nothing to reinforce.

Perpendicular/parallel diagrams are the exception and stay visible
throughout, including before answering: seeing whether two lines actually
look perpendicular is a legitimate sanity check while still working the
problem, not just an answer reveal.

### "Question N" counter incremented at the wrong moment

Found via live testing: right after submitting a correct answer, the label
read "Question 2" while the prompt on screen and its "Correct!" feedback
were still visibly Question 1's — reading exactly like "the next question
came up pre-answered." Root cause: the counter incremented in `handleSubmit`
(the moment she submits), not when the next question actually loaded, so
label and displayed content briefly disagreed. Fixed by moving the increment
into `loadNextQuestion`, guarded to skip the very first load (which is
already "Question 1" from initial state) — the label now only advances when
the question it's labeling has actually changed.

---

## Operational notes

### Deploying needs the `jc-app` AWS profile, not the shell's default credentials

This dev environment's shell has `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/
`AWS_SESSION_TOKEN` exported directly as environment variables, which take
AWS CLI precedence over any named profile — and that session token expires.
The `jc-app` profile in `~/.aws/config`/`credentials` (IAM user
`jc-app-deploy`, account `137860826896`, matching Axiom's account) stays
valid independently. Deploy commands need the env vars explicitly unset in
favour of that profile:

```
env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
  AWS_PROFILE=jc-app npx cdk deploy AxiomWebStack
```

### `cdk` runs via `npx`, not `uv run`

`cdk.json`'s `app` entry (`uv run python app.py`) only governs how the CDK
*app* (the Python synth script) runs — the `cdk` CLI itself is a Node
package, not something `uv` installs. `uv run cdk ...` fails to find the
binary; `npx cdk ...` is the working invocation.

### Live-reproduce UI bugs before fixing them

Both diagram-related findings and the counter bug were confirmed by
driving the actual deployed site (Claude-in-Chrome browser automation)
rather than reasoning from source alone — the counter bug in particular
wasn't visible by reading `SessionScreen.tsx` top-to-bottom, only by
watching what actually rendered after a real submit. Worth defaulting to
for reported-but-unreproduced UI issues, especially since the frontend has
no component test suite (`tests/test_question_generators.py` etc. only
cover the backend).
