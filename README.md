# CE OverPressure

Adds blast overpressure injuries to [Combat Extended](https://github.com/CombatExtended-Continued/CombatExtended) explosions in RimWorld 1.6

## Behavior

- estimates TNT yield from CE explosion damage
- calibrates 105 mm HE shells to 2.2 kg TNT
- blocks pressure through solid walls
- increases ground-level and enclosed-space pressure
- stuns pawns at low pressure and damages internal organs at higher pressure
- ignores smoke, EMP, incendiary, and other non-blast explosions

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
