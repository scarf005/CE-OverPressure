import { assertEquals, assertMatch, assertNotMatch, assertThrows } from "jsr:@std/assert"
import { calculateRadius, fitLinearRegression } from "./calculate_radius.ts"

Deno.test("rounds and bounds a smaller shell below larger reference shells", () => {
  assertEquals(
    calculateRadius(40, [{ caliberMm: 57, radius: 2 }, {
      caliberMm: 90,
      radius: 2.5,
    }]),
    1.5,
  )
})

Deno.test("rejects a regression with one reference round", () => {
  assertThrows(() => fitLinearRegression([{ caliberMm: 30, radius: 1 }]))
})

Deno.test("uses standard libraries for file traversal and paths", async () => {
  const generator = await Deno.readTextFile(new URL("./generate.ts", import.meta.url))
  assertMatch(generator, /jsr:@std\/fs/)
  assertMatch(generator, /jsr:@std\/path/)
  assertNotMatch(generator, /const files = async/)
})
