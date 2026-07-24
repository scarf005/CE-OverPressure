namespace CEOverPressure

open CombatExtended
open HarmonyLib
open RimWorld
open UnityEngine
open Verse

module internal Overpressure =
    let private settings = lazy (DefDatabase<OverpressureSettingsDef>.AllDefsListForReading |> Seq.exactlyOne)

    let private extensionFor (projectile: ThingDef) =
        if isNull projectile then
            None
        else
            match projectile.GetModExtension<OverpressureExtension>() with
            | null -> None
            | extension -> Some extension

    let private estimateYieldKg parameters damage radius (extension: OverpressureExtension option) =
        match extension with
        | Some value when value.tntEquivalentKg > 0.0f -> value.tntEquivalentKg
        | _ -> PressureModel.estimateYieldKg parameters damage radius

    let private isThermobaric (damageDef: DamageDef) =
        damageDef.isExplosive && not (isNull damageDef.workerClass) && typeof<DamageWorker_Flame>.IsAssignableFrom damageDef.workerClass

    let private stun (configuration: OverpressureSettingsDef) (pawn: Pawn) peakKPa (instigator: Thing) =
        if not pawn.Dead && not (isNull pawn.stances) && not (isNull pawn.stances.stunner) then
            let stunTicks = Mathf.RoundToInt(Mathf.Clamp(peakKPa, configuration.minimumStunTicks, configuration.maximumStunTicks))
            pawn.stances.stunner.StunFor(stunTicks, instigator)

    let private partsToDamage (configuration: OverpressureSettingsDef) peakKPa partCount =
        configuration.injuryBands
        |> Seq.filter (fun band -> not (isNull band) && peakKPa >= band.minimumPressureKPa)
        |> Seq.sortByDescending (fun band -> band.minimumPressureKPa)
        |> Seq.tryHead
        |> Option.map (fun band -> if band.maximumParts < 0 then partCount else min band.maximumParts partCount)
        |> Option.defaultValue 0

    let private applyInjuries (configuration: OverpressureSettingsDef) (pawn: Pawn) peakKPa (instigator: Thing) =
        if peakKPa >= configuration.stunThresholdKPa then
            if peakKPa < configuration.injuryThresholdKPa then
                stun configuration pawn peakKPa instigator
            else
                let internalParts =
                    pawn.health.hediffSet.GetNotMissingParts()
                    |> Seq.filter (fun part -> part.depth = BodyPartDepth.Inside)
                    |> Seq.toArray
                    |> fun parts -> parts.InRandomOrder()
                    |> Seq.toArray

                let damagePerPart =
                    Mathf.Clamp(
                        (peakKPa - configuration.damagePressureOffsetKPa) / configuration.damagePressureDivisor,
                        configuration.minimumDamagePerPart,
                        configuration.maximumDamagePerPart
                    )

                internalParts
                |> Seq.truncate (partsToDamage configuration peakKPa internalParts.Length)
                |> Seq.iter (fun part ->
                    if not pawn.Dead then
                        DamageInfo(configuration.injuryDamageDef, damagePerPart, configuration.armorPenetration, -1.0f, instigator, part)
                        |> pawn.TakeDamage
                        |> ignore)

                stun configuration pawn peakKPa instigator

    let apply (center: IntVec3) (map: Map) (radius: float32) (damageDef: DamageDef) (instigator: Thing) (damage: int) (projectile: ThingDef) (height: float32) =
        if not (isNull map) && center.InBounds map && not (isNull damageDef) then
            let configuration = settings.Value
            let extension = extensionFor projectile

            if not (extension |> Option.exists (fun value -> value.disable)) then
                let hasExplicitYield = extension |> Option.exists (fun value -> value.tntEquivalentKg > 0.0f)

                if hasExplicitYield || (damage > 0 && damageDef.isExplosive) then
                    let parameters = configuration.ModelParameters
                    let yieldKg = estimateYieldKg parameters damage radius extension

                    if yieldKg > 0.0f then
                        let extensionMultiplier =
                            match extension with
                            | Some value when value.pressureMultiplier > 0.0f -> value.pressureMultiplier
                            | _ -> 1.0f

                        let pressureMultiplier = extensionMultiplier * (if isThermobaric damageDef then configuration.thermobaricPressureMultiplier else 1.0f)

                        let scanRadius = max (radius + configuration.scanRadiusPadding) (PressureModel.pressureRangeCells parameters yieldKg)

                        map.mapPawns.AllPawnsSpawned
                        |> Seq.filter (fun pawn -> not (isNull pawn) && not pawn.Dead && pawn.Spawned && pawn.Position.InHorDistOf(center, scanRadius))
                        |> Seq.toArray
                        |> Array.iter (fun pawn ->
                            if GenSight.LineOfSight(center, pawn.Position, map, true) then
                                let distanceCells = max configuration.minimumDistanceCells (pawn.Position.DistanceTo center)
                                let mutable peakKPa = PressureModel.peakPressureKPa parameters (distanceCells * parameters.MetresPerCell) yieldKg

                                if height < configuration.groundReflectionMaximumHeight then
                                    peakKPa <- peakKPa * configuration.groundReflectionMultiplier

                                if center.Roofed map && pawn.Position.Roofed map then
                                    peakKPa <- peakKPa * configuration.enclosedReflectionMultiplier

                                applyInjuries configuration pawn (peakKPa * pressureMultiplier) instigator)

[<HarmonyPatch(typeof<GenExplosionCE>, nameof GenExplosionCE.DoExplosion)>]
module internal GenExplosionCEPatch =
    let Postfix (center: IntVec3, map: Map, radius: float32, damType: DamageDef, instigator: Thing, damAmount: int, projectile: ThingDef, height: float32) =
        Overpressure.apply center map radius damType instigator damAmount projectile height

[<StaticConstructorOnStartup>]
type CEOverPressureBootstrap() =
    static do Harmony("scarf.CombatExtended.OverPressure").PatchAll()
