import { useEffect, useRef, useState, type FormEvent } from 'react'

import { getWorkedExample, type WorkedExample } from '../api/diagnostic'
import { getNextQuestion, submitAnswer, type AnswerResult, type NextQuestion } from '../api/session'
import { SlopeExplorer } from '../components/SlopeExplorer'

interface SessionScreenProps {
  idToken: string
  onExit: () => void
}

interface BlockSummary {
  questionsToday: number
  tierMovements: string[]
}

const BLOCK_SIZE = 5

function capitalize(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1)
}

export function SessionScreen({ idToken, onExit }: SessionScreenProps) {
  const [question, setQuestion] = useState<NextQuestion | null>(null)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState<AnswerResult | null>(null)
  const [workedExample, setWorkedExample] = useState<WorkedExample | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [questionNumber, setQuestionNumber] = useState(1)
  const [correctStreak, setCorrectStreak] = useState(0)
  const [newlyEarnedBadge, setNewlyEarnedBadge] = useState<'intro' | 'mastery' | null>(null)
  const [blockSummary, setBlockSummary] = useState<BlockSummary | null>(null)

  // Badges are persistent flags from the server — "earned" stays true on
  // every later answer too, so a celebration only makes sense on the
  // false-to-true transition, not every time the flag happens to be true.
  const previousBadgesRef = useRef<{ intro: boolean; mastery: boolean } | null>(null)

  // Every question is freshly generated, so two overlapping requests never
  // return the same thing — a slow or duplicate fetch (React StrictMode's
  // double-invoked effects in dev, a double-click, a slow network) can
  // otherwise land after a newer one and silently swap out the question
  // she's already reading. This id guard keeps only the latest request's
  // result.
  const requestIdRef = useRef(0)

  // So the retry control can re-issue exactly the request that didn't come
  // back, rather than always falling back to a plain random question.
  const lastRetrySameSubtopicRef = useRef(false)

  // Block-of-five bookkeeping. "Today's questions answered" comes from the
  // server (the same counter the daily streak uses) rather than a
  // client-only count, so the block boundary lands correctly even if she
  // reloads mid-block. Tier movements are best-effort and session-local —
  // there's no server-side "this block's events" concept, only per-answer
  // tier snapshots, so a reload mid-block can lose that one summary line
  // without affecting whether the boundary itself fires correctly.
  const lastQuestionsTodayRef = useRef(0)
  const previousTierByTopicRef = useRef<Record<string, string>>({})
  const tierMovementsThisBlockRef = useRef<string[]>([])

  // After a correct answer, a fresh random question keeps the mix going.
  // After a wrong one, "another one like this" — same topic/subtopic — is
  // what actually lets her prove she's fixed the mistake, rather than
  // wandering off to something unrelated that proves nothing either way.
  async function loadNextQuestion(retrySameSubtopic = false) {
    const requestId = ++requestIdRef.current
    lastRetrySameSubtopicRef.current = retrySameSubtopic
    // The very first question shouldn't bump the counter — it's already
    // "Question 1" from the initial state. Every load after that is a
    // genuinely new question replacing what's on screen, so that's the
    // right moment to advance the label — not when she submits an answer,
    // which happens while the *current* question and its result are still
    // the only thing displayed.
    const isFirstQuestion = question === null
    setIsLoading(true)
    setError(null)
    setResult(null)
    setWorkedExample(null)
    setAnswer('')
    try {
      const retry = retrySameSubtopic && question ? { topicId: question.topicId, subtopic: question.subtopic } : undefined
      const next = await getNextQuestion(idToken, retry)
      if (requestId !== requestIdRef.current) return
      setQuestion(next)
      if (!isFirstQuestion) setQuestionNumber((n) => n + 1)
    } catch {
      if (requestId !== requestIdRef.current) return
      setError("Couldn't load a question — try again.")
    } finally {
      if (requestId === requestIdRef.current) setIsLoading(false)
    }
  }

  useEffect(() => {
    loadNextQuestion()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // The boundary check happens here — when she's *leaving* the question she
  // just got feedback on — rather than the instant she submits the fifth
  // answer. That way she still gets to read the verdict (and the worked
  // example, if she wants it) for the question that completed the block;
  // only the next fetch is replaced with the completion screen.
  function advanceToNextQuestion(retrySameSubtopic = false) {
    const questionsToday = lastQuestionsTodayRef.current
    if (questionsToday > 0 && questionsToday % BLOCK_SIZE === 0) {
      setBlockSummary({ questionsToday, tierMovements: [...tierMovementsThisBlockRef.current] })
      return
    }
    void loadNextQuestion(retrySameSubtopic)
  }

  function continueToNextBlock() {
    tierMovementsThisBlockRef.current = []
    setBlockSummary(null)
    void loadNextQuestion()
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!question || !answer.trim()) return
    setError(null)
    try {
      const outcome = await submitAnswer(idToken, question.questionId, answer.trim())
      setResult(outcome)
      setCorrectStreak((n) => (outcome.correct ? n + 1 : 0))
      lastQuestionsTodayRef.current = outcome.questionsToday

      const previousTier = previousTierByTopicRef.current[question.topicId]
      if (previousTier && previousTier !== outcome.progress.tier) {
        tierMovementsThisBlockRef.current.push(`${question.topicLabel}: moved to ${capitalize(outcome.progress.tier)}`)
      }
      previousTierByTopicRef.current[question.topicId] = outcome.progress.tier

      const previous = previousBadgesRef.current
      const { introBadgeEarned, masteryBadgeEarned } = outcome.progress
      if (previous && !previous.mastery && masteryBadgeEarned) {
        setNewlyEarnedBadge('mastery')
      } else if (previous && !previous.intro && introBadgeEarned) {
        setNewlyEarnedBadge('intro')
      } else {
        setNewlyEarnedBadge(null)
      }
      previousBadgesRef.current = { intro: introBadgeEarned, mastery: masteryBadgeEarned }
    } catch {
      setError("Couldn't read that as an answer — check the formatting and try again.")
    }
  }

  async function handleSeeWhy() {
    if (!result?.diagnosticOffer) return
    try {
      setWorkedExample(await getWorkedExample(idToken, result.diagnosticOffer.prerequisiteNodeId))
    } catch {
      setError("Couldn't load the explanation — try again.")
    }
  }

  const nudge = Boolean(result && !result.correct && result.diagnosticOffer?.nudge)

  // Perpendicular/parallel diagrams show a real relationship (do these
  // actually look perpendicular?) that's worth seeing *while* she's still
  // working the problem. The other diagram types just plot the two given
  // points — dragging them mid-attempt doesn't help her check her
  // arithmetic, so they only earn their place once there's an answer to
  // confirm or explain, not before.
  const hasRelationship = Boolean(question?.visualization?.mode)

  function explorationHint(displayMode?: string): string {
    switch (displayMode) {
      case 'segment-slope':
        return 'Drag the points below and watch how rise and run combine into the slope.'
      case 'segment-midpoint':
        return 'Drag the points below — the midpoint always lands exactly halfway between them.'
      case 'segment-distance':
        return 'Drag the points below and watch the legs and the distance update together.'
      case 'line-intercept':
        return 'Drag the points below and watch where the line crosses the x-axis change.'
      default:
        return 'Drag the points below to explore.'
    }
  }

  // A genuine completion state, not a pause: the question card, the "next"
  // controls, none of it renders here. Deliberately identical wording every
  // time — the third block reads the same as the first, since going further
  // is allowed but never scored or called out.
  if (blockSummary) {
    return (
      <>
        <div className="stat-row">
          <h1>Practice</h1>
        </div>
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p>{blockSummary.questionsToday} questions answered today.</p>
          {blockSummary.tierMovements.map((line) => (
            <p key={line}>{line}</p>
          ))}
          <button type="button" onClick={continueToNextBlock} style={{ alignSelf: 'flex-start' }}>
            Continue
          </button>
        </div>
        <button type="button" className="quiet" onClick={onExit} style={{ alignSelf: 'flex-start' }}>
          Done for now
        </button>
      </>
    )
  }

  return (
    <>
      <div className="stat-row">
        <h1>{question?.topicLabel ?? 'Practice'}</h1>
      </div>
      <p className="stat-label">
        Question {questionNumber}
        {correctStreak >= 2 && ` · 🔥 ${correctStreak} in a row`}
      </p>

      {isLoading && <p>Loading…</p>}

      {!isLoading && !question && error && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p role="alert" className="feedback-wrong">
            {error}
          </p>
          <button
            type="button"
            onClick={() => loadNextQuestion(lastRetrySameSubtopicRef.current)}
            style={{ alignSelf: 'flex-start' }}
          >
            Try again
          </button>
        </div>
      )}

      {!isLoading && question && (
        <div className="card question-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p>{question.prompt}</p>

          {question.visualization && hasRelationship && (
            <SlopeExplorer
              initialPointA={question.visualization.pointA}
              initialPointB={question.visualization.pointB}
              anchorPoint={question.visualization.anchorPoint}
              relationshipMode={question.visualization.mode}
              displayMode={question.visualization.displayMode}
              revealAnswer={Boolean(result)}
            />
          )}

          {!result ? (
            <form onSubmit={handleSubmit} className="answer-row">
              <input
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Your answer"
                autoFocus
              />
              <button type="submit">Submit</button>
            </form>
          ) : result.correct ? (
            <>
              <p className="feedback-correct">Correct!</p>
              {newlyEarnedBadge === 'intro' && <div className="badge">🥉 First win badge earned!</div>}
              {newlyEarnedBadge === 'mastery' && <div className="badge">🏆 Mastery badge earned!</div>}
              {question.visualization && !hasRelationship && (
                <SlopeExplorer
                  initialPointA={question.visualization.pointA}
                  initialPointB={question.visualization.pointB}
                  displayMode={question.visualization.displayMode}
                  revealAnswer
                />
              )}
              <button type="button" onClick={() => advanceToNextQuestion()} style={{ alignSelf: 'flex-start' }}>
                Next question
              </button>
            </>
          ) : workedExample ? (
            <>
              <p role="alert" className="feedback-wrong">
                Not quite — the answer was {result.correctAnswer}.
              </p>
              <div className="worked-example">
                <h2>💡 {workedExample.title}</h2>
                <p>{workedExample.explanation}</p>
                <p className="worked-example-line">{workedExample.example}</p>
              </div>
              {question.visualization && !hasRelationship && (
                <>
                  <p className="stat-label">{explorationHint(question.visualization.displayMode)}</p>
                  <SlopeExplorer
                    initialPointA={question.visualization.pointA}
                    initialPointB={question.visualization.pointB}
                    displayMode={question.visualization.displayMode}
                    revealAnswer
                  />
                </>
              )}
              <button type="button" onClick={() => advanceToNextQuestion(true)} style={{ alignSelf: 'flex-start' }}>
                Try a similar question
              </button>
            </>
          ) : (
            <>
              <p role="alert" className="feedback-wrong">
                Not quite.
              </p>
              <p>
                {nudge ? "This one's tricky — want to see why?" : 'Want to see why, or try another one like it?'}
              </p>
              <div className="button-row">
                <button type="button" onClick={handleSeeWhy} className={nudge ? '' : 'secondary'}>
                  See why
                </button>
                <button type="button" onClick={() => advanceToNextQuestion(true)} className="secondary">
                  Try another
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* The no-question case above already renders `error` with its own
          retry control — this covers an error while a question is still on
          screen (e.g. a submit that didn't come back). */}
      {question && error && (
        <p role="alert" className="feedback-wrong">
          {error}
        </p>
      )}

      <button type="button" className="quiet" onClick={onExit} style={{ alignSelf: 'flex-start' }}>
        Done for now
      </button>
    </>
  )
}
