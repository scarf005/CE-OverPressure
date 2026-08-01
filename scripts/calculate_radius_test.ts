import {
  assertEquals,
  assertStringIncludes,
  assertThrows,
} from "jsr:@std/assert"
import { autocannonPatch } from "./autocannon_patch.ts"
import { calculateRadius, fitLinearRegression } from "./calculate_radius.ts"
import { parseAmmunitionDefinitions } from "./ce_ammo.ts"

Deno.test("marks generated autocannon explosions with the setting gate extension", () => {
  const patch = autocannonPatch([
    { defName: "Bullet_Test_APHE", damage: 42, radius: 1 },
  ])

  assertStringIncludes(
    patch,
    '<li Class="CEOverPressure.AutocannonExplosionExtension" />',
  )
  assertStringIncludes(patch, "<damageAmountBase>42</damageAmountBase>")
})

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

Deno.test("reads nested CE projectile and explosive-component data", () => {
  assertEquals(
    parseAmmunitionDefinitions(
      `<Defs><ThingDef><defName>Bullet_25x40mm_HE</defName><label>25mm grenade (HE)</label><projectile><damageAmountBase>18</damageAmountBase><secondaryDamage><li><def>Bomb_Secondary</def><amount>7</amount></li></secondaryDamage></projectile><comps><li><explosiveRadius>1.5</explosiveRadius></li></comps></ThingDef></Defs>`,
    ),
    [{
      bombSecondaryDamage: 7,
      ceDamage: 18,
      defName: "Bullet_25x40mm_HE",
      explosionRadius: 1.5,
      label: "25mm grenade (HE)",
    }],
  )
})

Deno.test("reads explosive component damage without a projectile", () => {
  assertEquals(
    parseAmmunitionDefinitions(
      `<Defs><ThingDef><defName>Ammo_80x256mmFuel_Incendiary</defName><comps><li><explosiveRadius>2</explosiveRadius><damageAmountBase>6</damageAmountBase></li></comps></ThingDef></Defs>`,
    )[0].ceDamage,
    6,
  )
})
