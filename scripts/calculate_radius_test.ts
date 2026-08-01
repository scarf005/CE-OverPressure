import { assertEquals, assertThrows } from "jsr:@std/assert"
import { calculateRadius, fitLinearRegression } from "./calculate_radius.ts"

Deno.test("calculates the 30x165mm HE radius from its filler-mass fact", () => {
  assertEquals(calculateRadius("Bullet_30x165mm_HE").explosiveRadius, 3.21)
})

Deno.test("rejects an unknown projectile without a filler-mass fact", () => {
  assertThrows(() => calculateRadius("Bullet_unknown_HE"))
})

Deno.test("rejects a regression with one observation", () => {
  assertThrows(() =>
    fitLinearRegression([{ fillerGrams: 1, fragmentDangerRadiusM: 1 }])
  )
})
