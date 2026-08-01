import { walk } from "jsr:@std/fs@^1.0.19/walk"
import { dirname, fromFileUrl, join, resolve } from "jsr:@std/path@^1.1.2"
import * as vega from "vega"
import { compile } from "vega-lite"
import { calculateRadius, type RegressionFact } from "./calculate_radius.ts"

type Ammo = {
  defName: string
  label: string
  caliberMm: number
  kind: string
  radius: number
  damage?: number
  tntGrams?: number
  source: "Existing CE" | "Patched"
}

const tntGrams: Record<string, number> = {
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

const root = resolve(dirname(fromFileUrl(import.meta.url)), "..")
const cePath = Deno.args[0] ? resolve(Deno.args[0]) : resolve(root, "../CombatExtended")
const escapeXml = (value: string) =>
  value.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll(
    "<",
    "&lt;",
  )
const readTag = (xml: string, tag: string) =>
  xml.match(new RegExp(`<${tag}>([^<]+)</${tag}>`))?.[1]?.trim()
const blocks = (xml: string, tag: string) =>
  [...xml.matchAll(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "g"))].map((
    match,
  ) => match[0])
const kind = (name: string, label: string) => {
  const text = `${name} ${label}`.toUpperCase()
  if (/(HE_TFUZED|HE_HFUZED|TIME-FUZED|AIRBURST)/.test(text)) return "HE-TF"
  if (text.includes("HEDP")) return "HEDP"
  if (text.includes("HEAT")) return "HEAT"
  if (text.includes("INCENDIARY") || text.includes("AP-I")) return "I"
  if (text.includes("EMP")) return "EMP"
  if (text.includes("SMOKE")) return "Smoke"
  if (/(^|_)HE($|_)/.test(name.toUpperCase()) || text.includes("AP-HE")) {
    return "HE"
  }
  return undefined
}
const caliber = (name: string) => {
  const match = name.match(/(\d+(?:\.\d+)?)(x|mm|cm)/i)
  if (!match) return undefined
  const value = Number(match[1])
  return match[2].toLowerCase() === "cm"
    ? value * 10
    : value > 200
    ? value / 10
    : value
}

const definitions = async () =>
  (await Array.fromAsync(
    walk(join(cePath, "Defs", "Ammo"), { includeDirs: false, match: [/\.xml$/] }),
    ({ path }) => Deno.readTextFile(path),
  )).flatMap((xml) => blocks(xml, "ThingDef"))

const radius = (block: string) =>
  Number(
    readTag(
      block.match(/<projectile[\s\S]*?<\/projectile>/)?.[0] ?? "",
      "explosionRadius",
    ) ?? block.match(/<explosiveRadius>([\d.]+)<\/explosiveRadius>/)?.[1],
  )
const secondaryBombDamage = (block: string) =>
  Number(
    block.match(
      /<secondaryDamage>[\s\S]*?<def>Bomb_Secondary<\/def>[\s\S]*?<amount>(\d+)<\/amount>/,
    )?.[1],
  )
const ceDamage = (block: string) => {
  const projectile = block.match(/<projectile[\s\S]*?<\/projectile>/)?.[0] ?? ""
  const value = readTag(projectile, "damageAmountBase") ?? readTag(block, "damageAmountBase")
  return value ? Number(value) : undefined
}

const existingAmmo = (definitions: string[]) =>
  definitions.flatMap((block) => {
    const defName = readTag(block, "defName") ?? ""
    const label = readTag(block, "label") ?? defName
    const caliberMm = caliber(defName)
    const explosiveRadius = radius(block)
    const ammoKind = kind(defName, label)
    if (!caliberMm || caliberMm <= 20 || !explosiveRadius || !ammoKind) {
      return []
    }
    return [{
      defName,
      label,
      caliberMm,
      kind: ammoKind,
      radius: explosiveRadius,
      damage: ceDamage(block),
      source: "Existing CE" as const,
    }]
  })

const autocannonTargets = (definitions: string[]) =>
  definitions.flatMap((block) => {
    const defName = readTag(block, "defName") ?? ""
    const explosiveDamage = secondaryBombDamage(block)
    const caliberMm = caliber(defName)
    if (!caliberMm || !explosiveDamage || !(defName in tntGrams)) return []
    return [{
      defName,
      label: readTag(block, "label") ?? defName,
      caliberMm,
      kind: "HE",
      damage: explosiveDamage,
      tntGrams: tntGrams[defName],
    }]
  })

const patch = (targets: Ammo[]) =>
  `<?xml version="1.0" encoding="utf-8"?>
<Patch><Operation Class="PatchOperationFindMod"><mods><li>CETeam.CombatExtended</li></mods><match Class="PatchOperationSequence"><operations>
${
    targets.map((ammo) =>
      `  <li Class="PatchOperationAdd"><xpath>Defs/ThingDef[defName="${
        escapeXml(ammo.defName)
      }"]</xpath><value><comps><li Class="CombatExtended.CompProperties_ExplosiveCE"><damageAmountBase>${ammo.damage}</damageAmountBase><explosiveDamageType>Bomb</explosiveDamageType><explosiveRadius>${ammo.radius}</explosiveRadius><applyDamageToExplosionCellsNeighbors>true</applyDamageToExplosionCellsNeighbors></li></comps></value></li>`
    ).join("\n")
  }
</operations></match></Operation></Patch>
`

const graph = async (existing: Ammo[], patched: Ammo[]) => {
  const values = [...existing, ...patched].map((ammo) => ({
    ...ammo,
    name: ammo.label,
    label: [
        "Bullet_90mmCannonShell_HE",
        "Bullet_105mmHowitzerShell_HE",
        "Bullet_120mmCannonShell_HE",
      ].includes(ammo.defName)
      ? ammo.label
      : "",
  }))
  const spec = {
    $schema: "https://vega.github.io/schema/vega-lite/v6.json",
    width: 1000,
    height: 620,
    background: "white",
    title: "CE ammunition explosion-radius comparison",
    layer: [{
      data: { values: existing },
      transform: [{
        regression: "radius",
        on: "caliberMm",
        groupby: ["kind"],
        method: "linear",
      }],
      mark: { type: "line", opacity: 0.55, strokeWidth: 2 },
      encoding: {
        x: { field: "caliberMm", type: "quantitative", title: "Caliber (mm)" },
        y: {
          field: "radius",
          type: "quantitative",
          title: "RimWorld explosion radius (cells)",
        },
        color: { field: "kind", type: "nominal", title: "Ammo kind" },
      },
    }, {
      data: { values },
      mark: { type: "point", filled: true, size: 80 },
      encoding: {
        x: { field: "caliberMm", type: "quantitative", title: "Caliber (mm)" },
        y: {
          field: "radius",
          type: "quantitative",
          title: "RimWorld explosion radius (cells)",
        },
        color: { field: "kind", type: "nominal", title: "Ammo kind" },
        shape: { field: "source", type: "nominal", title: "Source" },
        tooltip: [
          { field: "name", type: "nominal", title: "Ammo" },
          { field: "kind", type: "nominal" },
          { field: "caliberMm", type: "quantitative", title: "Caliber" },
          { field: "radius", type: "quantitative", title: "Radius" },
        ],
      },
    }, {
      data: { values: values.filter(({ label }) => label) },
      mark: { type: "text", align: "left", dx: 8, dy: -8, fontSize: 11 },
      encoding: {
        x: { field: "caliberMm", type: "quantitative" },
        y: { field: "radius", type: "quantitative" },
        text: { field: "label", type: "nominal" },
        color: { value: "#102a43" },
      },
    }],
  }
  return await new vega.View(vega.parse(compile(spec as never).spec), {
    renderer: "none",
  }).toSVG()
}

const definitions_ = await definitions()
const existing = existingAmmo(definitions_)
const targets = autocannonTargets(definitions_).map((target) => {
  const facts: RegressionFact[] = existing.filter((ammo) =>
    ammo.kind === target.kind
  ).map(({ caliberMm, radius }) => ({ caliberMm, radius }))
  if (facts.length < 2) {
    throw new Error(
      `not enough CE ${target.kind} reference rounds for ${target.defName}`,
    )
  }
  return {
    ...target,
    radius: calculateRadius(target.caliberMm, facts),
    source: "Patched" as const,
  }
})
if (!targets.length) throw new Error("no autocannon AP-HE targets found")
await Deno.writeTextFile(
  join(root, "Patches", "AutocannonExplosions.xml"),
  patch(targets),
)
await Deno.writeTextFile(
  join(root, "README.md"),
  `# CE Realistic Autocannon Explosions\n\n![CE ammunition explosion-radius comparison](graph.webp)\n\n## Patched autocannon ammunition\n\n| Projectile ID | CE damage | IRL TNT (g) | Radius (cells) |\n| --- | ---: | ---: | ---: |\n${
    targets.map((ammo) =>
      `| ${ammo.defName} | ${ammo.damage} | ${ammo.tntGrams} | ${ammo.radius} |`
    ).join("\n")
  }\n\n## Existing CE reference ammunition\n\n| Projectile ID | Ammo kind | CE damage | IRL TNT (g) | Caliber (mm) | Radius (cells) |\n| --- | --- | ---: | ---: | ---: | ---: |\n${
    existing.sort((left, right) =>
      left.caliberMm - right.caliberMm || left.kind.localeCompare(right.kind) ||
      left.defName.localeCompare(right.defName)
    ).map((ammo) =>
      `| ${ammo.defName} | ${ammo.kind} | ${ammo.damage ?? "—"} | — | ${ammo.caliberMm} | ${ammo.radius} |`
    ).join("\n")
  }\n`,
)
const svgPath = join(root, "graph.svg")
await Deno.writeTextFile(svgPath, await graph(existing, targets))
const result = await new Deno.Command("magick", {
  args: [svgPath, join(root, "graph.webp")],
  clearEnv: true,
}).output()
await Deno.remove(svgPath)
if (!result.success) throw new Error(new TextDecoder().decode(result.stderr))
