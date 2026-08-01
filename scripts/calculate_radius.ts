export type RegressionFact = { caliberMm: number; radius: number }

export const fitLinearRegression = (facts: RegressionFact[]) => {
  if (facts.length < 2) {
    throw new Error("at least two calibration facts are required")
  }
  const mean = (values: number[]) =>
    values.reduce((sum, value) => sum + value, 0) / values.length
  const meanCaliber = mean(facts.map(({ caliberMm }) => caliberMm))
  const meanRadius = mean(facts.map(({ radius }) => radius))
  const variance = facts.reduce(
    (sum, fact) => sum + (fact.caliberMm - meanCaliber) ** 2,
    0,
  )
  if (variance === 0) {
    throw new Error("calibration facts need different calibers")
  }
  const slope = facts.reduce(
    (sum, fact) =>
      sum + (fact.caliberMm - meanCaliber) * (fact.radius - meanRadius),
    0,
  ) / variance
  return { intercept: meanRadius - slope * meanCaliber, slope }
}

export const calculateRadius = (caliberMm: number, facts: RegressionFact[]) => {
  const { intercept, slope } = fitLinearRegression(facts)
  const predicted = intercept + slope * caliberMm
  const largerCaliberRadius = facts
    .filter((fact) => fact.caliberMm > caliberMm)
    .reduce((smallest, fact) => Math.min(smallest, fact.radius), Infinity)
  const bounded = Math.min(predicted, largerCaliberRadius)
  return Math.max(0.5, Math.round(bounded * 2) / 2)
}
