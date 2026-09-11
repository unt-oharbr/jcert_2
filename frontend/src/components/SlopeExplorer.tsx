import { useRef, useState, type PointerEvent } from 'react'

const VIEW_SIZE = 400
const GRID_RANGE = 10
const SCALE = VIEW_SIZE / (2 * GRID_RANGE)
const SNAP = 0.5
const TICKS = [-8, -6, -4, -2, 2, 4, 6, 8]

interface GridPoint {
  x: number
  y: number
}

const FALLBACK_A: GridPoint = { x: -4, y: -2 }
const FALLBACK_B: GridPoint = { x: 4, y: 4 }

type DisplayMode = 'line' | 'segment-slope' | 'segment-midpoint' | 'segment-distance' | 'line-intercept'

interface SlopeExplorerProps {
  initialPointA?: [number, number]
  initialPointB?: [number, number]
  anchorPoint?: [number, number]
  relationshipMode?: 'perpendicular' | 'parallel'
  displayMode?: DisplayMode
  // The diagram would otherwise print the graded quantity as a plain
  // number right next to the question — trivially readable without doing
  // the maths. Every mode below withholds its answer-quantity text until
  // this is true, while still keeping the diagram itself interactive.
  revealAnswer?: boolean
}

function toGridPoint(pair: [number, number] | undefined, fallback: GridPoint): GridPoint {
  return pair ? { x: pair[0], y: pair[1] } : fallback
}

function toSvg(p: GridPoint): [number, number] {
  return [VIEW_SIZE / 2 + p.x * SCALE, VIEW_SIZE / 2 - p.y * SCALE]
}

function snap(value: number): number {
  return Math.round(value / SNAP) * SNAP
}

function clamp(value: number): number {
  return Math.max(-GRID_RANGE + 0.5, Math.min(GRID_RANGE - 0.5, value))
}

function formatNumber(n: number): string {
  return (Math.round(n * 100) / 100).toString()
}

// Extends a line of slope m through p across the whole visible grid — the
// SVG viewBox clips it automatically, so no bounds-checking is needed here.
function extendedLine(p: GridPoint, m: number): [GridPoint, GridPoint] {
  return [
    { x: -GRID_RANGE, y: p.y - m * (p.x - -GRID_RANGE) },
    { x: GRID_RANGE, y: p.y + m * (GRID_RANGE - p.x) },
  ]
}

function verticalLine(p: GridPoint): [GridPoint, GridPoint] {
  return [
    { x: p.x, y: -GRID_RANGE },
    { x: p.x, y: GRID_RANGE },
  ]
}

function AxisTicks() {
  return (
    <>
      {TICKS.map((t) => {
        const [tx] = toSvg({ x: t, y: 0 })
        const [, ty] = toSvg({ x: 0, y: t })
        return (
          <g key={t} className="mono" style={{ fill: 'var(--ink-muted)' }} fontSize={10}>
            <text x={tx} y={VIEW_SIZE / 2 + 12} textAnchor="middle">
              {t}
            </text>
            <text x={VIEW_SIZE / 2 - 6} y={ty + 3} textAnchor="end">
              {t}
            </text>
          </g>
        )
      })}
    </>
  )
}

function Axes() {
  return (
    <>
      <line x1={0} y1={VIEW_SIZE / 2} x2={VIEW_SIZE} y2={VIEW_SIZE / 2} style={{ stroke: 'var(--surface-border)' }} />
      <line x1={VIEW_SIZE / 2} y1={0} x2={VIEW_SIZE / 2} y2={VIEW_SIZE} style={{ stroke: 'var(--surface-border)' }} />
      <AxisTicks />
    </>
  )
}

interface DraggablePointProps {
  point: GridPoint
  onStartDrag: (event: PointerEvent<SVGCircleElement>) => void
  onDrag: (event: PointerEvent<SVGCircleElement>) => void
}

function DraggablePoint({ point, onStartDrag, onDrag }: DraggablePointProps) {
  const [x, y] = toSvg(point)
  return (
    <circle
      cx={x}
      cy={y}
      r={9}
      onPointerDown={onStartDrag}
      onPointerMove={onDrag}
      style={{ cursor: 'grab', touchAction: 'none', fill: 'var(--accent)' }}
    />
  )
}

// Drag the two points and watch the relevant quantity (slope, midpoint,
// distance, or x-intercept) recompute live. Seeded with THIS question's
// actual points/line, not a generic example, so the diagram answers the
// question in front of her, not a different one.
export function SlopeExplorer({
  initialPointA,
  initialPointB,
  anchorPoint,
  relationshipMode,
  displayMode = 'line',
  revealAnswer = false,
}: SlopeExplorerProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const startA = toGridPoint(initialPointA, FALLBACK_A)
  const startB = toGridPoint(initialPointB, FALLBACK_B)
  const [pointA, setPointA] = useState<GridPoint>(startA)
  const [pointB, setPointB] = useState<GridPoint>(startB)
  const [showRelated, setShowRelated] = useState(Boolean(relationshipMode))
  const draggingRef = useRef<'A' | 'B' | null>(null)

  const slope = (pointB.y - pointA.y) / (pointB.x - pointA.x)

  function handlePointerMove(event: PointerEvent<SVGCircleElement>) {
    const which = draggingRef.current
    if (!which || !svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const sx = ((event.clientX - rect.left) / rect.width) * VIEW_SIZE
    const sy = ((event.clientY - rect.top) / rect.height) * VIEW_SIZE
    const gx = clamp(snap((sx - VIEW_SIZE / 2) / SCALE))
    const gy = clamp(snap((VIEW_SIZE / 2 - sy) / SCALE))

    if (which === 'A') {
      if (gx === pointB.x) return // keep the slope always defined
      setPointA({ x: gx, y: gy })
    } else {
      if (gx === pointA.x) return
      setPointB({ x: gx, y: gy })
    }
  }

  function startDrag(which: 'A' | 'B') {
    return (event: PointerEvent<SVGCircleElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId)
      draggingRef.current = which
    }
  }

  function reset() {
    setPointA(startA)
    setPointB(startB)
  }

  const [ax, ay] = toSvg(pointA)
  const [bx, by] = toSvg(pointB)

  if (displayMode === 'segment-midpoint') {
    const midpoint: GridPoint = { x: (pointA.x + pointB.x) / 2, y: (pointA.y + pointB.y) / 2 }
    const [mx, my] = toSvg(midpoint)
    return (
      <figure className="slope-explorer">
        <svg ref={svgRef} viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} role="img" aria-label="Drag the two points and watch their midpoint update">
          <Axes />
          <line x1={ax} y1={ay} x2={bx} y2={by} strokeWidth={2} style={{ stroke: 'var(--accent)' }} />
          <circle cx={mx} cy={my} r={6} style={{ fill: 'var(--warm)' }} />
          <DraggablePoint point={pointA} onStartDrag={startDrag('A')} onDrag={handlePointerMove} />
          <DraggablePoint point={pointB} onStartDrag={startDrag('B')} onDrag={handlePointerMove} />
        </svg>
        <figcaption>
          {revealAnswer ? (
            <div className="stat-row">
              <span className="stat-number" style={{ color: 'var(--warm)' }}>
                ({formatNumber(midpoint.x)}, {formatNumber(midpoint.y)})
              </span>
              <span className="stat-label">midpoint</span>
            </div>
          ) : (
            <p className="stat-label">Submit your answer to reveal the midpoint.</p>
          )}
          <button type="button" className="quiet" onClick={reset} style={{ alignSelf: 'flex-start' }}>
            Reset
          </button>
        </figcaption>
      </figure>
    )
  }

  if (displayMode === 'segment-distance') {
    const dx = pointB.x - pointA.x
    const dy = pointB.y - pointA.y
    const distance = Math.sqrt(dx * dx + dy * dy)
    const corner: GridPoint = { x: pointB.x, y: pointA.y }
    const [cx, cy] = toSvg(corner)
    return (
      <figure className="slope-explorer">
        <svg ref={svgRef} viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} role="img" aria-label="Drag the two points and watch the distance between them update">
          <Axes />
          <line x1={ax} y1={ay} x2={cx} y2={cy} strokeDasharray="4 3" style={{ stroke: 'var(--ink-muted)' }} />
          <line x1={cx} y1={cy} x2={bx} y2={by} strokeDasharray="4 3" style={{ stroke: 'var(--ink-muted)' }} />
          <line x1={ax} y1={ay} x2={bx} y2={by} strokeWidth={2} style={{ stroke: 'var(--accent)' }} />
          <DraggablePoint point={pointA} onStartDrag={startDrag('A')} onDrag={handlePointerMove} />
          <DraggablePoint point={pointB} onStartDrag={startDrag('B')} onDrag={handlePointerMove} />
        </svg>
        <figcaption>
          {revealAnswer ? (
            <div className="stat-row">
              <span className="stat-number" style={{ color: 'var(--accent-ink)' }}>
                {formatNumber(distance)}
              </span>
              <span className="stat-label">
                distance — legs {formatNumber(Math.abs(dx))} and {formatNumber(Math.abs(dy))}
              </span>
            </div>
          ) : (
            <p className="stat-label">Submit your answer to reveal the distance.</p>
          )}
          <button type="button" className="quiet" onClick={reset} style={{ alignSelf: 'flex-start' }}>
            Reset
          </button>
        </figcaption>
      </figure>
    )
  }

  if (displayMode === 'segment-slope') {
    // Slope is a ratio of two specific things — rise and run — not a
    // general relationship that survives dragging the points anywhere, so
    // this shows the same right-angle-leg construction as distance
    // (rather than an extended line) to keep the drag interaction tied to
    // what the formula is actually built from.
    const dx = pointB.x - pointA.x
    const dy = pointB.y - pointA.y
    const corner: GridPoint = { x: pointB.x, y: pointA.y }
    const [cx, cy] = toSvg(corner)
    return (
      <figure className="slope-explorer">
        <svg ref={svgRef} viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} role="img" aria-label="Drag the two points and watch the rise and run that make up the slope">
          <Axes />
          <line x1={ax} y1={ay} x2={cx} y2={cy} strokeDasharray="4 3" style={{ stroke: 'var(--ink-muted)' }} />
          <line x1={cx} y1={cy} x2={bx} y2={by} strokeDasharray="4 3" style={{ stroke: 'var(--ink-muted)' }} />
          <line x1={ax} y1={ay} x2={bx} y2={by} strokeWidth={2} style={{ stroke: 'var(--accent)' }} />
          <DraggablePoint point={pointA} onStartDrag={startDrag('A')} onDrag={handlePointerMove} />
          <DraggablePoint point={pointB} onStartDrag={startDrag('B')} onDrag={handlePointerMove} />
        </svg>
        <figcaption>
          {revealAnswer ? (
            <div className="stat-row">
              <span className="stat-number" style={{ color: 'var(--accent-ink)' }}>
                {formatNumber(slope)}
              </span>
              <span className="stat-label">
                slope — rise {formatNumber(dy)}, run {formatNumber(dx)}
              </span>
            </div>
          ) : (
            <p className="stat-label">Submit your answer to reveal the slope.</p>
          )}
          <button type="button" className="quiet" onClick={reset} style={{ alignSelf: 'flex-start' }}>
            Reset
          </button>
        </figcaption>
      </figure>
    )
  }

  // 'line' and 'line-intercept' both draw an extended line through A/B.
  const [kStart, kEnd] = extendedLine(pointA, slope)
  const [kx1, ky1] = toSvg(kStart)
  const [kx2, ky2] = toSvg(kEnd)

  if (displayMode === 'line-intercept') {
    const xIntercept = slope === 0 ? null : pointA.x - pointA.y / slope
    const interceptPoint: GridPoint | null = xIntercept === null ? null : { x: xIntercept, y: 0 }
    const interceptSvg = interceptPoint ? toSvg(interceptPoint) : null
    return (
      <figure className="slope-explorer">
        <svg ref={svgRef} viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`} role="img" aria-label="Drag the two points and watch where the line crosses the x-axis">
          <Axes />
          <line x1={kx1} y1={ky1} x2={kx2} y2={ky2} strokeWidth={2} style={{ stroke: 'var(--accent)' }} />
          {interceptSvg && <circle cx={interceptSvg[0]} cy={interceptSvg[1]} r={6} style={{ fill: 'var(--warm)' }} />}
          <DraggablePoint point={pointA} onStartDrag={startDrag('A')} onDrag={handlePointerMove} />
          <DraggablePoint point={pointB} onStartDrag={startDrag('B')} onDrag={handlePointerMove} />
        </svg>
        <figcaption>
          {revealAnswer ? (
            <div className="stat-row">
              <span className="stat-number" style={{ color: 'var(--warm)' }}>
                {interceptPoint ? `(${formatNumber(interceptPoint.x)}, 0)` : '—'}
              </span>
              <span className="stat-label">x-intercept</span>
            </div>
          ) : (
            <p className="stat-label">Submit your answer to reveal the x-intercept.</p>
          )}
          <button type="button" className="quiet" onClick={reset} style={{ alignSelf: 'flex-start' }}>
            Reset
          </button>
        </figcaption>
      </figure>
    )
  }

  // Default: 'line' — slope of k, with an optional parallel/perpendicular partner.
  const mode = relationshipMode ?? 'perpendicular'
  const relatedSlope = mode === 'parallel' ? slope : slope === 0 ? null : -1 / slope
  const anchor: GridPoint = anchorPoint
    ? { x: anchorPoint[0], y: anchorPoint[1] }
    : { x: (pointA.x + pointB.x) / 2, y: (pointA.y + pointB.y) / 2 }
  const [nStart, nEnd] = relatedSlope === null ? verticalLine(anchor) : extendedLine(anchor, relatedSlope)
  const [nx1, ny1] = toSvg(nStart)
  const [nx2, ny2] = toSvg(nEnd)
  const [anchorX, anchorY] = toSvg(anchor)
  const relationLabel = mode === 'parallel' ? 'parallel' : 'perpendicular'
  const relationSummary =
    relatedSlope === null
      ? 'vertical line'
      : mode === 'parallel'
        ? 'line n slope — k = n'
        : `line n slope — k × n = ${formatNumber(slope * relatedSlope)}`

  return (
    <figure className="slope-explorer">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
        role="img"
        // This branch only renders for perpendicular/parallel questions
        // (slope_two_points uses 'segment-slope' instead), where line k's
        // slope is given data stated in the prompt — safe to announce
        // outright, unlike line n's slope below, which is the answer.
        aria-label={`Interactive coordinate grid: drag the two blue points to change line k's slope, currently ${formatNumber(slope)}`}
      >
        <Axes />
        <line x1={kx1} y1={ky1} x2={kx2} y2={ky2} strokeWidth={2} style={{ stroke: 'var(--accent)' }} />
        {showRelated && <line x1={nx1} y1={ny1} x2={nx2} y2={ny2} strokeWidth={2} style={{ stroke: 'var(--warm)' }} />}
        {anchorPoint && showRelated && <circle cx={anchorX} cy={anchorY} r={5} style={{ fill: 'var(--warm)' }} />}
        <DraggablePoint point={pointA} onStartDrag={startDrag('A')} onDrag={handlePointerMove} />
        <DraggablePoint point={pointB} onStartDrag={startDrag('B')} onDrag={handlePointerMove} />
      </svg>

      <figcaption>
        <div className="stat-row">
          <span className="stat-number" style={{ color: 'var(--accent-ink)' }}>
            {formatNumber(slope)}
          </span>
          <span className="stat-label">line k slope</span>
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <input type="checkbox" checked={showRelated} onChange={(e) => setShowRelated(e.target.checked)} />
          Show a {relationLabel} line
        </label>
        {showRelated && !revealAnswer && <p className="stat-label">Submit your answer to reveal line n's slope.</p>}
        {showRelated && revealAnswer && (
          <div className="stat-row">
            <span className="stat-number" style={{ color: 'var(--warm)' }}>
              {relatedSlope === null ? '—' : formatNumber(relatedSlope)}
            </span>
            <span className="stat-label">{relationSummary}</span>
          </div>
        )}
        <button type="button" className="quiet" onClick={reset} style={{ alignSelf: 'flex-start' }}>
          Reset
        </button>
      </figcaption>
    </figure>
  )
}
