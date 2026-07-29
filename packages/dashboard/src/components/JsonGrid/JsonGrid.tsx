import { useState } from 'react'
import JsonView from '@uiw/react-json-view'
import type { JsonValue } from '../../types/job'
import JSONGrid from '@redheadphone/react-json-grid'
import './JsonGrid.scss'

interface JsonGridProps {
  data: JsonValue
}

type ViewTab = 'grid' | 'tree'

/**
 * Coerce an arbitrary [`JsonValue`](../../types/job.ts) into a shape the
 * underlying `@uiw/react-json-view` can render. The view requires an object
 * (or array), so primitives and `null` are wrapped in a labelled container.
 */
function toViewValue(data: JsonValue): Record<string, unknown> | unknown[] {
  if (data !== null && typeof data === 'object') {
    return data as Record<string, unknown> | unknown[]
  }
  return { value: data }
}

function toGridValue(data: JsonValue): Record<string, unknown> {
  if (data !== null && typeof data === 'object' && !Array.isArray(data)) {
    return data as Record<string, unknown>
  }
  return { value: data }
}

/**
 * Tabbed JSON viewer with two rendering modes:
 *
 * - **Grid** (default): `@redheadphone/react-json-grid` spreadsheet-style
 *   view. Brand theming is applied via `--jg-*` CSS custom property
 *   overrides in `JsonGrid.scss`, mapped onto the `--ff-*` token system.
 * - **Tree**: `@uiw/react-json-view` collapsible tree with brand theming
 *   applied via the `--w-rjv-*` CSS custom properties mapped onto the
 *   project's `--ff-*` token system in `JsonGrid.scss`.
 *
 * Both views adapt to light/dark themes automatically through the
 * `--ff-*` token system — no JS theme switching is required.
 *
 * The `data` prop interface is unchanged so all call sites work without
 * modification.
 */
export function JsonGrid({ data }: JsonGridProps) {
  const [tab, setTab] = useState<ViewTab>('grid')

  return (
    <div className="ff-json-grid-wrapper">
      <div className="ff-json-grid__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'grid'}
          className={`ff-json-grid__tab${tab === 'grid' ? ' ff-json-grid__tab--active' : ''}`}
          onClick={() => setTab('grid')}
        >
          Grid
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'tree'}
          className={`ff-json-grid__tab${tab === 'tree' ? ' ff-json-grid__tab--active' : ''}`}
          onClick={() => setTab('tree')}
        >
          Tree
        </button>
      </div>

      {tab === 'grid' ? (
        <JSONGrid data={toGridValue(data)} defaultExpandDepth={100} />
      ) : (
        <JsonView
          value={toViewValue(data)}
          collapsed={false}
          displayObjectSize
          enableClipboard
          shortenTextAfterLength={120}
          displayDataTypes={false}
          className="ff-json-grid"
        />
      )}
    </div>
  )
}
