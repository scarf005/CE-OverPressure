export type Fact = {
  fillerGrams: number
  fragmentDangerRadiusM: number
}

export const calibrationFacts: Fact[] = [
  { fillerGrams: 4, fragmentDangerRadiusM: 1 },
  { fillerGrams: 10.7, fragmentDangerRadiusM: 1.5 },
  { fillerGrams: 18, fragmentDangerRadiusM: 2 },
  { fillerGrams: 24, fragmentDangerRadiusM: 2.5 },
  { fillerGrams: 49, fragmentDangerRadiusM: 3.5 },
  { fillerGrams: 90, fragmentDangerRadiusM: 5 },
  { fillerGrams: 112, fragmentDangerRadiusM: 5.5 },
]

export const ammunitionFacts: Record<string, number> = {
  Bullet_20x82mmMauser_HE: 6,
  Bullet_20x99mmRShVAK_HE: 4,
  Bullet_20x102mmNATO_HE: 10.7,
  Bullet_20x110mmHispano_HE: 6,
  Bullet_20x128mmOerlikon_HE: 10,
  Bullet_20x138mmB_HE: 11,
  Bullet_20x139mm_HE: 10,
  Bullet_23x115mm_HE: 15,
  Bullet_23x152mmB_APHE: 18,
  Bullet_25x137mmNATO_HE: 22,
  Bullet_27x145mmMauser_HE: 20,
  Bullet_30x113mmB_HE: 24,
  Bullet_30x165mm_HE: 49,
  Bullet_30x170mm_HE: 38,
  Bullet_30x173mmNATO_HE: 44,
  Bullet_35x228mmNATO_HE: 112,
  Bullet_40x311mmR_HE: 90,
}

export const fitLinearRegression = (facts: Fact[]) => {
  if (facts.length < 2) {
    throw new Error("at least two calibration facts are required")
  }
  const mean = (values: number[]) =>
    values.reduce((sum, value) => sum + value, 0) / values.length
  const meanX = mean(facts.map(({ fillerGrams }) => fillerGrams))
  const meanY = mean(
    facts.map(({ fragmentDangerRadiusM }) => fragmentDangerRadiusM),
  )
  const variance = facts.reduce(
    (sum, fact) => sum + (fact.fillerGrams - meanX) ** 2,
    0,
  )
  if (variance === 0) {
    throw new Error("calibration facts need different filler masses")
  }
  const slope = facts.reduce(
    (sum, fact) =>
      sum + (fact.fillerGrams - meanX) * (fact.fragmentDangerRadiusM - meanY),
    0,
  ) / variance
  return { intercept: meanY - slope * meanX, slope }
}

export const calculateRadius = (
  ammo: string,
  fillerGrams = ammunitionFacts[ammo],
) => {
  if (fillerGrams === undefined) {
    throw new Error(`no real-world filler mass is defined for ${ammo}`)
  }
  const { intercept, slope } = fitLinearRegression(calibrationFacts)
  return {
    ammo,
    fillerGrams,
    explosiveRadius: Math.max(
      0.1,
      Math.round((intercept + slope * fillerGrams) * 100) / 100,
    ),
    intercept,
    slope,
  }
}

if (import.meta.main) {
  const arguments_ = new Map(
    Deno.args.flatMap((argument, index, values) =>
      argument.startsWith("--") ? [[argument, values[index + 1]]] : []
    ),
  )
  const payload = arguments_.has("--facts")
    ? { ammunition: ammunitionFacts, calibration: calibrationFacts }
    : arguments_.has("--all")
    ? Object.keys(ammunitionFacts).sort().map((ammo) => calculateRadius(ammo))
    : calculateRadius(
      arguments_.get("--ammo") ?? "",
      Number(arguments_.get("--filler-grams")) || undefined,
    )
  console.log(
    arguments_.has("--json") ? JSON.stringify(payload, null, 2) : payload,
  )
}
