'use strict';
// Pure chart data preparation; null readings never become zero or bridge a gap.
function weatherChartModel(history, field, options = {}) {
  const points = [];
  let interrupted = true, previousSimulation;
  for (const row of history) {
    const value = row[field], time = Date.parse(row.observed_at);
    if (typeof value !== 'number' || !Number.isFinite(value) || !Number.isFinite(time)) {
      interrupted = true;
      continue;
    }
    const simulation = field === 'wind_speed_mps' ? row.wind_simulated : undefined;
    points.push({time, value, simulated: simulation,
                 breakBefore: interrupted || simulation !== previousSimulation});
    interrupted = false;
    previousSimulation = simulation;
  }
  if (!points.length) return {points, min: null, max: null};
  const values = points.map(point => point.value), min = Math.min(...values), max = Math.max(...values);
  const padding = Math.max((max - min) * .15, options.padding || .3);
  let low = min - padding, high = max + padding;
  if (options.floor != null) low = Math.max(options.floor, low);
  if (options.ceiling != null) high = Math.min(options.ceiling, high);
  if (high <= low) high = low + padding;
  return {points, min, max, low, high, first: points[0].time, last: points.at(-1).time};
}
if (typeof module !== 'undefined' && module.exports) module.exports = weatherChartModel;
else globalThis.weatherChartModel = weatherChartModel;
