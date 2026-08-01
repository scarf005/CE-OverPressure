import { ammunitionFacts, calculateRadius } from "./calculate_radius.ts"

type Projectile = {
  defName: string
  label: string
  damageAmountBase: number
  explosiveRadius: number
  tntGrams: number
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
      label: readTag(block, "label") ?? defName,
      damageAmountBase: Number(secondary[1]),
      explosiveRadius,
      tntGrams: fillerGrams,
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
  const width = 1600
  const height = 960
  const chart = { left: 140, right: 260, top: 100, bottom: 110 }
  const maximumTnt = 120
  const maximumRadius = 6
  const x = (value: number) =>
    chart.left + value / maximumTnt * (width - chart.left - chart.right)
  const y = (value: number) =>
    height - chart.bottom -
    value / maximumRadius * (height - chart.top - chart.bottom)
  const ordered = [...projectiles].sort((left, right) =>
    left.tntGrams - right.tntGrams
  )
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#ffffff"/><g font-family="sans-serif"><g stroke="#486581" stroke-width="2"><path d="M${chart.left} ${
    height - chart.bottom
  }H${width - chart.right}M${chart.left} ${
    height - chart.bottom
  }V${chart.top}"/></g><g fill="#102a43"><text x="${
    width / 2
  }" y="920" text-anchor="middle" font-size="24">IRL TNT equivalent (g)</text><text x="38" y="${
    height / 2
  }" transform="rotate(-90 38 ${
    height / 2
  })" text-anchor="middle" font-size="24">RimWorld explosion radius (cells)</text><text x="${chart.left}" y="55" font-size="30">Patched CE autocannon ammunition</text></g>${
    ordered.map(({ label, tntGrams, explosiveRadius }, index) => {
      const pointX = x(tntGrams)
      const pointY = y(explosiveRadius)
      const offset = (index % 2 ? 1 : -1) * (18 + index % 4 * 12)
      return `<path d="M${pointX} ${pointY}L${pointX + 14} ${
        pointY + offset
      }" stroke="#268bd2"/><circle cx="${pointX}" cy="${pointY}" r="7" fill="#268bd2"/><text x="${
        pointX + 18
      }" y="${pointY + offset + 5}" fill="#102a43" font-size="15">${
        escapeXml(label)
      }</text>`
    }).join("")
  }</g></svg>`
}

const readme = (projectiles: Projectile[]) =>
  `# CE Realistic Autocannon Explosions

![Patched autocannon explosion radii](graph.webp)

One RimWorld cell is one metre of fragment-danger radius.

| Projectile ID | CE damage | IRL TNT (g) | Radius (cells) |
| --- | ---: | ---: | ---: |
${
    projectiles.map((
      { defName, damageAmountBase, tntGrams, explosiveRadius },
    ) =>
      `| ${defName} | ${damageAmountBase} | ${tntGrams} | ${explosiveRadius} |`
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
