import { ammunitionFacts, calculateRadius } from "./calculate_radius.ts"

type Projectile = {
  defName: string
  damageAmountBase: number
  explosiveRadius: number
  fillerGrams: number
}

const root = new URL("..", import.meta.url)
const cePath = Deno.args[0]
  ? new URL(`${Deno.args[0]}/`, import.meta.url)
  : new URL("../CombatExtended/", root)
const escapeXml = (value: string) =>
  value.replaceAll("&", "&amp;").replaceAll('"', "&quot;")
const readTag = (xml: string, tag: string) =>
  xml.match(new RegExp(`<${tag}>([^<]+)</${tag}>`))?.[1]?.trim()
const blocks = (xml: string, tag: string) =>
  [...xml.matchAll(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "g"))].map((
    match,
  ) => match[0])

const files = async (directory: URL): Promise<URL[]> => {
  const entries: URL[] = []
  try {
    for await (const entry of Deno.readDir(directory)) {
      const path = new URL(entry.name, directory)
      if (entry.isDirectory && !entry.isSymlink) {
        entries.push(...await files(new URL(`${entry.name}/`, directory)))
      }
      if (entry.isFile && entry.name.endsWith(".xml")) entries.push(path)
    }
  } catch (error) {
    if (!(error instanceof Deno.errors.NotFound)) throw error
  }
  return entries
}

const targets = async () => {
  const xml = (await Promise.all(
    (await files(new URL("Defs/Ammo/", cePath))).map(async (path) => {
      try {
        return await Deno.readTextFile(path)
      } catch (error) {
        if (error instanceof Deno.errors.NotFound) return ""
        throw error
      }
    }),
  )).filter(Boolean)
  const autocannonAmmo = new Set(
    xml.flatMap((file) =>
      blocks(file, "CombatExtended.AmmoSetDef").flatMap((block) => {
        if (
          readTag(block, "defName") !== "AmmoSet_Autocannon" &&
          readTag(block, "similarTo") !== "AmmoSet_Autocannon"
        ) return []
        return [...block.matchAll(/>\s*(Bullet_[^<\s]+)\s*</g)].map((match) =>
          match[1]
        )
      })
    ),
  )
  return xml.flatMap((file) => blocks(file, "ThingDef")).flatMap((block) => {
    const defName = readTag(block, "defName")
    const secondary = block.match(
      /<secondaryDamage>[\s\S]*?<li>[\s\S]*?<def>Bomb_Secondary<\/def>[\s\S]*?<amount>(\d+)<\/amount>[\s\S]*?<\/li>[\s\S]*?<\/secondaryDamage>/,
    )
    if (
      !defName || !autocannonAmmo.has(defName) || !secondary ||
      !(defName in ammunitionFacts)
    ) return []
    const { explosiveRadius, fillerGrams } = calculateRadius(defName)
    return [{
      defName,
      damageAmountBase: Number(secondary[1]),
      explosiveRadius,
      fillerGrams,
    }]
  }).sort((left, right) => left.defName.localeCompare(right.defName))
}

const patch = (projectiles: Projectile[]) =>
  `<?xml version="1.0" encoding="utf-8"?>
<Patch>
  <Operation Class="PatchOperationFindMod">
    <mods><li>CETeam.CombatExtended</li></mods>
    <match Class="PatchOperationSequence">
      <operations>
${
    projectiles.map(({ defName, damageAmountBase, explosiveRadius }) =>
      `        <li Class="PatchOperationAdd">
          <xpath>Defs/ThingDef[defName="${escapeXml(defName)}"]</xpath>
          <value><comps><li Class="CombatExtended.CompProperties_ExplosiveCE"><damageAmountBase>${damageAmountBase}</damageAmountBase><explosiveDamageType>Bomb</explosiveDamageType><explosiveRadius>${explosiveRadius}</explosiveRadius><applyDamageToExplosionCellsNeighbors>true</applyDamageToExplosionCellsNeighbors></li></comps></value>
        </li>`
    ).join("\n")
  }
      </operations>
    </match>
  </Operation>
</Patch>
`

const graph = (projectiles: Projectile[]) => {
  const width = 1400
  const labelWidth = 480
  const chartWidth = 820
  const rowHeight = 38
  const height = projectiles.length * rowHeight + 130
  const maximumRadius = Math.ceil(
    Math.max(...projectiles.map(({ explosiveRadius }) => explosiveRadius)),
  )
  const barWidth = (radius: number) => radius / maximumRadius * chartWidth
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#101418"/><g fill="#d9e2ec" font-family="sans-serif"><text x="40" y="40" font-size="28">Patched CE autocannon ammunition</text><text x="${labelWidth}" y="75" font-size="18">Explosion radius changed from 0 cells to metres/cells</text>${
    projectiles.map(({ defName, explosiveRadius }, index) => {
      const y = 100 + index * rowHeight
      return `<text x="40" y="${
        y + 20
      }" font-size="16">${defName}</text><rect x="${labelWidth}" y="${y}" width="${
        barWidth(explosiveRadius)
      }" height="24" fill="#63b3ed"/><text x="${
        labelWidth + barWidth(explosiveRadius) + 12
      }" y="${y + 19}" font-size="16">0 → ${explosiveRadius}</text>`
    }).join("")
  }</g></svg>`
}

const readme = (projectiles: Projectile[]) =>
  `# CE Realistic Autocannon Explosions

![Patched autocannon explosion radii](graph.webp)

One RimWorld cell is one metre of fragment-danger radius. The graph shows every patched projectile and its radius change from zero.

| Projectile | HE filler (g) | Radius (cells) |
| --- | ---: | ---: |
${
    projectiles.map(({ defName, fillerGrams, explosiveRadius }) =>
      `| ${defName} | ${fillerGrams} | ${explosiveRadius} |`
    ).join("\n")
  }

Run: deno run --allow-read --allow-write --allow-run=magick scripts/generate.ts [CE defs path].
`

const projectiles = await targets()
if (projectiles.length === 0) {
  throw new Error(`no AP-HE autocannon projectiles found in ${cePath.pathname}`)
}
await Deno.mkdir(new URL("Patches/", root), { recursive: true })
await Deno.writeTextFile(
  new URL("Patches/AutocannonExplosions.xml", root),
  patch(projectiles),
)
await Deno.writeTextFile(new URL("README.md", root), readme(projectiles))
const svgPath = new URL("graph.svg", root)
await Deno.writeTextFile(svgPath, graph(projectiles))
const result = await new Deno.Command("magick", {
  args: [svgPath.pathname, new URL("graph.webp", root).pathname],
  clearEnv: true,
}).output()
await Deno.remove(svgPath)
if (!result.success) throw new Error(new TextDecoder().decode(result.stderr))
