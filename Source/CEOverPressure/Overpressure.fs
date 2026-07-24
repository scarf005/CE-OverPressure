namespace CEOverPressure

open System
open System.Collections.Generic
open CombatExtended
open HarmonyLib
open RimWorld
open UnityEngine
open Verse

[<AllowNullLiteral>]
type OverpressureExtension() as this =
    inherit DefModExtension()

    [<Microsoft.FSharp.Core.DefaultValue>]
    val mutable tntEquivalentKg: float32

    [<Microsoft.FSharp.Core.DefaultValue>]
    val mutable pressureMultiplier: float32

    [<Microsoft.FSharp.Core.DefaultValue>]
    val mutable disable: bool

    do
        this.tntEquivalentKg <- -1.0f
        this.pressureMultiplier <- 1.0f

module internal Overpressure =
    let private yieldOverrides =
        Dictionary<string, float32>(
            [ KeyValuePair("Bullet_105mmHowitzerShell_HE", 2.2f)
              KeyValuePair("Bullet_105mmHowitzerShell_HE_directfire", 2.2f)
              KeyValuePair("Bullet_105mmHowitzerShell_HE_HFuzed", 2.2f) ],
            StringComparer.OrdinalIgnoreCase
        )

    let private lower (value: string) = if String.IsNullOrEmpty value then String.Empty else value.ToLowerInvariant()

    let private extensionFor (projectile: ThingDef) =
        if isNull projectile then
            None
        else
            match projectile.GetModExtension<OverpressureExtension>() with
            | null -> None
            | extension -> Some extension

    let private isNonBlastExplosion (damageDef: DamageDef) (projectile: ThingDef) damage =
        if damage <= 0 then
            true
        else
            let projectileName = if isNull projectile then String.Empty else lower projectile.defName
            let combined = lower damageDef.defName + " " + projectileName

            [ "smoke"
              "emp"
              "extinguish"
              "stun"
              "flash"
              "foam"
              "tox"
              "incendiary"
              "flame" ]
            |> List.exists combined.Contains

    let private estimateYieldKg (projectile: ThingDef) damage (extension: OverpressureExtension option) =
        match extension with
        | Some extension when extension.tntEquivalentKg > 0.0f -> extension.tntEquivalentKg
        | _ when not (isNull projectile) ->
            let mutable yieldKg = 0.0f

            if yieldOverrides.TryGetValue(projectile.defName, &yieldKg) then yieldKg else PressureModel.estimateYieldKg damage
        | _ -> PressureModel.estimateYieldKg damage

    let private blastPriority (part: BodyPartRecord) =
        let name = lower part.def.defName

        if name.Contains "lung" then 100
        elif name.Contains "liver" || name.Contains "kidney" || name.Contains "stomach" then 80
        elif name.Contains "heart" then 60
        elif name.Contains "brain" then 40
        else 20

    let private stun (pawn: Pawn) peakKPa (instigator: Thing) =
        if not pawn.Dead && not (isNull pawn.stances) && not (isNull pawn.stances.stunner) then
            let stunTicks = Mathf.RoundToInt(Mathf.Clamp(peakKPa, 30.0f, 240.0f))
            pawn.stances.stunner.StunFor(stunTicks, instigator)

    let private applyInjuries (pawn: Pawn) peakKPa (instigator: Thing) =
        if peakKPa >= 25.0f then
            if peakKPa < 35.0f then
                stun pawn peakKPa instigator
            else
                let internalParts =
                    pawn.health.hediffSet.GetNotMissingParts()
                    |> Seq.filter (fun part -> part.depth = BodyPartDepth.Inside)
                    |> Seq.sortByDescending blastPriority
                    |> Seq.toArray

                if Array.isEmpty internalParts then
                    stun pawn peakKPa instigator
                else
                    let partsToDamage =
                        if peakKPa >= 140.0f then internalParts.Length
                        elif peakKPa >= 100.0f then min 5 internalParts.Length
                        elif peakKPa >= 60.0f then min 3 internalParts.Length
                        else min 2 internalParts.Length

                    let damagePerPart = Mathf.Clamp((peakKPa - 25.0f) / 8.0f, 2.0f, 30.0f)

                    internalParts
                    |> Seq.truncate partsToDamage
                    |> Seq.iter (fun part ->
                        if not pawn.Dead then
                            DamageInfo(DamageDefOf.Blunt, damagePerPart, 999.0f, -1.0f, instigator, part) |> pawn.TakeDamage |> ignore)

                    stun pawn peakKPa instigator

    let apply (center: IntVec3) (map: Map) (radius: float32) (damageDef: DamageDef) (instigator: Thing) (damage: int) (projectile: ThingDef) (height: float32) =
        if not (isNull map) && center.InBounds map && not (isNull damageDef) then
            let extension = extensionFor projectile

            if not (extension |> Option.exists (fun value -> value.disable)) then
                let hasExplicitYield = extension |> Option.exists (fun value -> value.tntEquivalentKg > 0.0f)

                if hasExplicitYield || not (isNonBlastExplosion damageDef projectile damage) then
                    let yieldKg = estimateYieldKg projectile damage extension

                    if yieldKg > 0.0f then
                        let pressureMultiplier =
                            match extension with
                            | Some value when value.pressureMultiplier > 0.0f -> value.pressureMultiplier
                            | _ -> 1.0f

                        let scanRadius = max (radius + 1.0f) (PressureModel.pressureRangeCells yieldKg)

                        map.mapPawns.AllPawnsSpawned
                        |> Seq.filter (fun pawn -> not (isNull pawn) && not pawn.Dead && pawn.Spawned && pawn.Position.InHorDistOf(center, scanRadius))
                        |> Seq.toArray
                        |> Array.iter (fun pawn ->
                            if GenSight.LineOfSight(center, pawn.Position, map, true) then
                                let distanceCells = max 0.5f (pawn.Position.DistanceTo center)
                                let mutable peakKPa = PressureModel.peakPressureKPa (distanceCells * PressureModel.MetresPerCell) yieldKg

                                if height < 1.5f then
                                    peakKPa <- peakKPa * 1.35f

                                if center.Roofed map && pawn.Position.Roofed map then
                                    peakKPa <- peakKPa * 1.35f

                                applyInjuries pawn (peakKPa * pressureMultiplier) instigator)

[<HarmonyPatch(typeof<GenExplosionCE>, nameof GenExplosionCE.DoExplosion)>]
module internal GenExplosionCEPatch =
    let Postfix (center: IntVec3, map: Map, radius: float32, damType: DamageDef, instigator: Thing, damAmount: int, projectile: ThingDef, height: float32) =
        // GenExplosionCE normalizes damage and radius in its argument slots before this postfix runs.
        Overpressure.apply center map radius damType instigator damAmount projectile height

[<StaticConstructorOnStartup>]
type CEOverPressureBootstrap() =
    static do Harmony("scarf.CombatExtended.OverPressure").PatchAll()
