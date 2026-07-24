/**
 * `Paginator` — reusable, presentational pagination control.
 *
 * Takes `total`, `limit`, `offset` plus `onOffsetChange` / `onLimitChange`
 * callbacks. It is intentionally decoupled from the URL and from job types:
 * the parent wires it to whatever state source it uses (e.g. the
 * `useJobListParams` hook).
 *
 * Features:
 * - "Showing X–Y of Z" range (handles empty pages).
 * - Prev / Next buttons (disabled at bounds).
 * - Numbered page buttons with truncation for large page counts.
 * - Page-size `<select>` (10 / 20 / 50 / 100).
 */

import './Paginator.scss';

export interface PaginatorProps {
  /** Total number of rows matching the current filters (before pagination). */
  total: number;
  /** Current page size. */
  limit: number;
  /** Current page offset (zero-based). */
  offset: number;
  /** Called with a new offset when the user navigates. */
  onOffsetChange: (offset: number) => void;
  /** Called with a new page size when the user changes it. */
  onLimitChange: (limit: number) => void;
}

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

/** Maximum number of page buttons to render around the current page. */
const SIBLING_COUNT = 1;

/**
 * Build the list of page numbers to render, using ellipsis (`null`) markers
 * for truncated ranges. Always includes the first and last page.
 *
 * Example (current=5, totalPages=20): [1, null, 4, 5, 6, null, 20]
 */
function buildPageList(current: number, totalPages: number): (number | null)[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | null)[] = [];

  const leftSibling = Math.max(current - SIBLING_COUNT, 2);
  const rightSibling = Math.min(current + SIBLING_COUNT, totalPages - 1);

  pages.push(1);

  if (leftSibling > 2) {
    pages.push(null);
  }

  for (let p = leftSibling; p <= rightSibling; p++) {
    pages.push(p);
  }

  if (rightSibling < totalPages - 1) {
    pages.push(null);
  }

  pages.push(totalPages);

  return pages;
}

export function Paginator({
  total,
  limit,
  offset,
  onOffsetChange,
  onLimitChange,
}: PaginatorProps) {
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;

  // Clamp current page into range (e.g. after a filter narrows results).
  const clampedPage = Math.min(Math.max(currentPage, 1), totalPages);
  const clampedOffset = (clampedPage - 1) * limit;

  const rangeStart = total === 0 ? 0 : clampedOffset + 1;
  const rangeEnd = Math.min(clampedOffset + limit, total);

  const hasPrev = clampedPage > 1;
  const hasNext = clampedPage < totalPages;

  const pages = buildPageList(clampedPage, totalPages);

  return (
    <div className="ff-paginator">
      <span className="ff-paginator__range">
        {total === 0
          ? 'Showing 0 results'
          : `Showing ${rangeStart}–${rangeEnd} of ${total}`}
      </span>

      <div className="ff-paginator__pages">
        <button
          type="button"
          className="ff-paginator__nav"
          disabled={!hasPrev}
          onClick={() => onOffsetChange(clampedOffset - limit)}
          aria-label="Previous page"
        >
          ‹
        </button>

        {pages.map((page, idx) =>
          page === null ? (
            <span key={`gap-${idx}`} className="ff-paginator__gap">
              …
            </span>
          ) : (
            <button
              key={page}
              type="button"
              className={`ff-paginator__page${
                page === clampedPage ? ' ff-paginator__page--active' : ''
              }`}
              onClick={() => onOffsetChange((page - 1) * limit)}
              aria-current={page === clampedPage ? 'page' : undefined}
            >
              {page}
            </button>
          ),
        )}

        <button
          type="button"
          className="ff-paginator__nav"
          disabled={!hasNext}
          onClick={() => onOffsetChange(clampedOffset + limit)}
          aria-label="Next page"
        >
          ›
        </button>
      </div>

      <label className="ff-paginator__size">
        <span className="ff-paginator__size-label">Per page</span>
        <select
          className="ff-paginator__select"
          value={limit}
          onChange={(e) => onLimitChange(Number(e.target.value))}
        >
          {PAGE_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
