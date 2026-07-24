# CE OverPressure

Adds blast overpressure injuries to [Combat Extended](https://github.com/CombatExtended-Continued/CombatExtended) explosions in RimWorld 1.6

## Behavior

- estimates TNT yield from CE explosion damage and radius
- traverses nearby RimWorld regions and blocks pressure at closed doors and solid walls
- scales enclosed-space pressure by native room size and roof coverage
- stuns pawns at low pressure and damages randomly selected internal organs at higher pressure
- detects conventional and thermobaric blasts from `DamageDef` behavior
- ignores non-explosive incendiary effects

## Configuration

`Defs/OverpressureSettings.xml` controls yield weighting, the pressure model, reflection, thermobaric pressure, injury thresholds, and injury bands

## Projectile overrides

Other mods can override yield, pressure, or disable overpressure on a projectile `ThingDef`

```xml
<modExtensions>
  <li Class="CEOverPressure.OverpressureExtension">
    <tntEquivalentKg>2.2</tntEquivalentKg>
    <pressureMultiplier>1.0</pressureMultiplier>
    <disable>false</disable>
  </li>
</modExtensions>
```

A positive explicit yield also enables overpressure for projectile definitions that would otherwise be filtered by damage type

## Build

Set `COMBAT_EXTENDED_DIR` if Combat Extended is installed outside the default Steam Workshop location

```sh
just test
just fmt
just build
```
