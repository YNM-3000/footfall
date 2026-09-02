import type { Line } from "../../api/types";

export interface Point {
  x: number;
  y: number;
}

export const lineStart = (line: Line): Point => ({ x: line[0], y: line[1] });
export const lineEnd = (line: Line): Point => ({ x: line[2], y: line[3] });

export const withStart = (line: Line, point: Point): Line => [point.x, point.y, line[2], line[3]];
export const withEnd = (line: Line, point: Point): Line => [line[0], line[1], point.x, point.y];

export const horizontalMidline = (width: number, height: number): Line => [
  0,
  height / 2,
  width,
  height / 2,
];

/**
 * Midpoint of the arrow that shows which way counts as "in".
 *
 * The sign convention matches the backend: the cross product of the line
 * direction with a point decides its side, so the positive side lies at the
 * line direction rotated by +90°.
 */
export function inwardArrow(line: Line, invert: boolean, length: number) {
  const dx = line[2] - line[0];
  const dy = line[3] - line[1];
  const magnitude = Math.hypot(dx, dy) || 1;
  const sign = invert ? -1 : 1;
  // Normal to (dx, dy), pointing at the positive side of the line.
  const normal = { x: (-dy / magnitude) * sign, y: (dx / magnitude) * sign };
  const midpoint = { x: (line[0] + line[2]) / 2, y: (line[1] + line[3]) / 2 };

  return {
    from: midpoint,
    to: { x: midpoint.x + normal.x * length, y: midpoint.y + normal.y * length },
  };
}

export const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));
