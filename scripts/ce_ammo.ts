import { XMLParser } from "npm:fast-xml-parser@^5.2.5"

export type AmmunitionDefinition = {
  defName: string
  label: string
  bombSecondaryDamage?: number
  ceDamage?: number
  explosionRadius?: number
}

type XmlObject = Record<string, unknown>

const parser = new XMLParser({
  ignoreAttributes: false,
  parseTagValue: false,
  trimValues: true,
})
const array = (value: unknown) =>
  Array.isArray(value) ? value : value === undefined ? [] : [value]
const object = (value: unknown): XmlObject | undefined =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as XmlObject
    : undefined
const text = (value: unknown) =>
  typeof value === "string" ? value.trim() : undefined
const number = (value: unknown) => {
  const parsed = Number(text(value))
  return Number.isFinite(parsed) ? parsed : undefined
}
const first = (values: (number | undefined)[]) =>
  values.find((value) => value !== undefined)
const properties = (definition: XmlObject, name: string) =>
  array(object(definition.comps)?.li).map(object).filter((
    value,
  ): value is XmlObject => value !== undefined)
    .filter((component) => component[name] !== undefined)

export const parseAmmunitionDefinitions = (
  xml: string,
): AmmunitionDefinition[] => {
  const defs = object(parser.parse(xml))?.Defs
  return array(object(defs)?.ThingDef).map(object).flatMap((definition) => {
    if (!definition) return []
    const defName = text(definition.defName)
    if (!defName) return []
    const projectile = object(definition.projectile)
    const secondaryDamage = array(
      projectile && object(projectile.secondaryDamage)?.li,
    ).map(object)
      .find((damage) => text(damage?.def) === "Bomb_Secondary")
    return [{
      defName,
      label: text(definition.label) ?? defName,
      bombSecondaryDamage: number(secondaryDamage?.amount),
      ceDamage: first([
        number(projectile?.damageAmountBase),
        number(definition.damageAmountBase),
        ...properties(definition, "damageAmountBase").map((component) =>
          number(component.damageAmountBase)
        ),
      ]),
      explosionRadius: first([
        number(projectile?.explosionRadius),
        ...properties(definition, "explosiveRadius").map((component) =>
          number(component.explosiveRadius)
        ),
      ]),
    }]
  })
}
