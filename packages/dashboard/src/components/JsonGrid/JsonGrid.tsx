import JsonView from '@uiw/react-json-view'
import type { JsonValue } from '../../types/job'
import './JsonGrid.scss'

interface JsonGridProps {
  data: JsonValue
}

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

/**
 * Themed wrapper around `@uiw/react-json-view`.
 *
 * Renders arbitrary JSON (including nested objects/arrays) as a collapsible
 * tree. Brand theming is applied via the `--w-rjv-*` CSS custom properties
 * mapped onto the project's `--ff-*` token system in `JsonGrid.scss`.
 *
 * Defaults: root expanded, children collapsed to `{n}` summaries, clipboard
 * enabled, long strings clamped at 120 chars.
 */
export function JsonGrid({ data }: JsonGridProps) {
  return (
    <JsonView
      value={toViewValue(data)}
      collapsed={1}
      displayObjectSize
      enableClipboard
      shortenTextAfterLength={120}
      displayDataTypes={false}
      className="ff-json-grid"
    />
  )
}
